import os
import sys
import subprocess
import time
from contextlib import closing

from dotenv import load_dotenv

from shared.paths import (
    ENVIRONMENT_FILE,
    PROJECT_ROOT,
    REMOTE_BENCHMARK_DIRECTORY,
    REMOTE_ENVIRONMENT_FILE,
    SSH_TARGET,
)

from orchestrate.shared.energy import (
    collect_energy_runs,
    read_um24c,
    write_to_file,
)

sys.path.insert(0, str(PROJECT_ROOT))

from um24c.um24c import UM24C

REMOTE_PACKAGE = "./micro/json_cbor"
REMOTE_BINARY = "/tmp/json-cbor-benchmark"


def load_environment_variables():

    global RUNS
    global PAYLOAD_SIZES
    global TIMING_DURATION
    global BASELINE_DURATION
    global WARMUP_DURATION
    global MEASUREMENT_DURATION
    global TAIL_DURATION
    global TOTAL_WORKLOAD_DURATION
    global RESULT_DIRECTORY
    global TIMING_RESULT_FILE
    global ENERGY_RESULT_FILE

    load_dotenv(
        ENVIRONMENT_FILE,
        override=True,
    )

    RUNS = int(os.environ["JSON_CBOR_RUNS"])

    PAYLOAD_SIZES = [
        int(payload_size) for payload_size in os.environ["PAYLOAD_SIZES"].split(",")
    ]

    TIMING_DURATION = int(os.environ["TIMING_DURATION"])
    BASELINE_DURATION = int(os.environ["BASELINE_DURATION"])
    WARMUP_DURATION = int(os.environ["WARMUP_DURATION"])
    MEASUREMENT_DURATION = int(os.environ["MEASUREMENT_DURATION"])
    TAIL_DURATION = int(os.environ["TAIL_DURATION"])

    TOTAL_WORKLOAD_DURATION = WARMUP_DURATION + MEASUREMENT_DURATION + TAIL_DURATION

    RESULT_DIRECTORY = PROJECT_ROOT / os.environ["JSON_CBOR_RESULT_DIR"]
    TIMING_RESULT_FILE = RESULT_DIRECTORY / "timing.txt"
    ENERGY_RESULT_FILE = RESULT_DIRECTORY / "energy.txt"


def build_benchmark_binary():

    command = (
        f"cd {REMOTE_BENCHMARK_DIRECTORY }; "
        f"/usr/local/go/bin/go test -c "
        f"-o {REMOTE_BINARY} "
        f"{REMOTE_PACKAGE}"
    )

    subprocess.run(
        ["ssh", SSH_TARGET, command],
        check=True,
    )


def run_energy_case(meter, output, algorithm, operation, payload_size):

    print(f"Energy: {algorithm} {operation} {payload_size}B")

    output.write(
        f"\n[case algorithm={algorithm} operation={operation} parameter_value={payload_size}]\n"
    )

    benchmark_case = (
        f"^BenchmarkMessageEnergy{operation}$/^{algorithm}$/^{payload_size}B$"
    )

    command = (
        f"set -a && "
        f". {REMOTE_ENVIRONMENT_FILE} && "
        f"set +a && "
        f"{REMOTE_BINARY}"
        f" -test.run=^$"
        f" -test.bench='{benchmark_case}'"
        f" -test.benchtime={MEASUREMENT_DURATION}s"
        f" -test.count={RUNS}"
        f" -test.timeout=0"
    )

    process = subprocess.Popen(
        ["ssh", SSH_TARGET, command],
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    collect_energy_runs(process, meter, output, TOTAL_WORKLOAD_DURATION)

    if process.wait() != 0:
        raise RuntimeError(f"Benchmark Failed: {algorithm} {operation} {payload_size}B")


def orchestrate_energy():

    # Create the UM24C Instance & Ensure Auto Close in Case of Exception
    with closing(UM24C()) as um24c:

        print(f"Using UM24C at {UM24C.MAC_ADDRESS}")
        print(
            f"Collection of {RUNS} Idle Baseline Power Windows "
            f"for {BASELINE_DURATION}s each..."
        )

        with ENERGY_RESULT_FILE.open("w", encoding="utf-8") as output:

            for _ in range(RUNS):
                output.write("[baseline]\n")
                write_to_file(output, read_um24c(um24c, BASELINE_DURATION))

            for payload_size in PAYLOAD_SIZES:

                run_energy_case(um24c, output, "JSON", "Serialize", payload_size)
                run_energy_case(um24c, output, "JSON", "Deserialize", payload_size)
                run_energy_case(um24c, output, "CBOR", "Serialize", payload_size)
                run_energy_case(um24c, output, "CBOR", "Deserialize", payload_size)
                run_energy_case(
                    um24c, output, "CBORKeyAsInt", "Serialize", payload_size
                )
                run_energy_case(
                    um24c, output, "CBORKeyAsInt", "Deserialize", payload_size
                )

    print(f"Finished: {ENERGY_RESULT_FILE}")


def run_timing_case(output, algorithm, operation, payload_size):

    print(f"Timing: {algorithm} {operation} {payload_size}B")
    benchmark_case = f"^BenchmarkMessage{operation}$/^{algorithm}$/^{payload_size}B$"

    command = (
        f"set -a && "
        f". {REMOTE_ENVIRONMENT_FILE} && "
        f"set +a && "
        f"{REMOTE_BINARY}"
        f" -test.run=^$"
        f" -test.bench='{benchmark_case}'"
        f" -test.benchtime={TIMING_DURATION}s"
        f" -test.count={RUNS}"
        f" -test.timeout=0"
    )

    result = subprocess.run(
        ["ssh", SSH_TARGET, command],
        stdout=output,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Benchmark Failed: "
            f"{algorithm} "
            f"{operation} "
            f"{payload_size}B\n"
            f"{result.stderr}"
        )


def orchestrate_timing():

    with TIMING_RESULT_FILE.open("w", encoding="utf-8") as destination_file:

        for payload_size in PAYLOAD_SIZES:

            run_timing_case(destination_file, "JSON", "Serialize", payload_size)
            run_timing_case(destination_file, "JSON", "Deserialize", payload_size)
            run_timing_case(destination_file, "CBOR", "Serialize", payload_size)
            run_timing_case(destination_file, "CBOR", "Deserialize", payload_size)
            run_timing_case(destination_file, "CBORKeyAsInt", "Serialize", payload_size)
            run_timing_case(
                destination_file, "CBORKeyAsInt", "Deserialize", payload_size
            )

    print(f"Finished: {TIMING_RESULT_FILE}")


def generate_report():

    print("Generating JSON vs CBOR HTML Report...")

    subprocess.run(
        [sys.executable, "-m", "report.analysis.json_cbor_report"],
        cwd=PROJECT_ROOT,
        check=True,
    )


def main():

    # Load Environment Variables
    load_environment_variables()

    # Create Result Directory Under Root
    RESULT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    # Build the Binary
    build_benchmark_binary()

    # Allow Energy-Baseline to Stabilize after Build
    time.sleep(5)

    # Run Energy Benchmark
    orchestrate_energy()

    # Run Timing Benchmark
    orchestrate_timing()

    # Generate Report
    generate_report()


if __name__ == "__main__":
    main()
