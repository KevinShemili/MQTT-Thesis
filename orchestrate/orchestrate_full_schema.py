import csv
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
    REMOTE_CACHE_DIRECTORY,
    REMOTE_ENVIRONMENT_FILE,
    REMOTE_PROJECT_DIRECTORY,
    SSH_TARGET,
)

from shared.txt_to_csv import (
    convert_memory_results,
    convert_timing_results,
)

from shared.energy import (
    ENERGY_FIELDS,
    read_um24c,
    write_samples,
)

sys.path.insert(0, str(PROJECT_ROOT))

from um24c.um24c import UM24C

REMOTE_PACKAGE = "./micro/full_schema"
REMOTE_PROVISION_PACKAGE = "./cmd/provision_full_schema"
REMOTE_BINARY = "/tmp/full-schema-benchmark"
REMOTE_ENERGY_PACKAGE = "./cmd/energy_full_schema"
REMOTE_ENERGY_BINARY = "/tmp/full-schema-energy"
REMOTE_PROVISION_BINARY = "/tmp/full-schema-provision"


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
    global MEMORY_RESULT_FILE
    global TIMING_RESULT_FILE
    global ENERGY_RESULT_FILE

    load_dotenv(
        ENVIRONMENT_FILE,
        override=True,
    )

    RUNS = int(os.environ["FULL_SCHEMA_RUNS"])

    PAYLOAD_SIZES = [
        int(payload_size)
        for payload_size in os.environ["FULL_SCHEMA_PAYLOAD_SIZES"].split(",")
    ]

    TIMING_DURATION = int(os.environ["TIMING_DURATION"])
    BASELINE_DURATION = int(os.environ["BASELINE_DURATION"])
    WARMUP_DURATION = int(os.environ["WARMUP_DURATION"])
    MEASUREMENT_DURATION = int(os.environ["MEASUREMENT_DURATION"])
    TAIL_DURATION = int(os.environ["TAIL_DURATION"])

    TOTAL_WORKLOAD_DURATION = WARMUP_DURATION + MEASUREMENT_DURATION + TAIL_DURATION

    RESULT_DIRECTORY = PROJECT_ROOT / os.environ["FULL_SCHEMA_RESULT_DIR"]
    MEMORY_RESULT_FILE = RESULT_DIRECTORY / "memory.txt"
    TIMING_RESULT_FILE = RESULT_DIRECTORY / "timing.txt"
    ENERGY_RESULT_FILE = RESULT_DIRECTORY / "energy.csv"


def build_binaries():

    command = (
        f"cd {REMOTE_BENCHMARK_DIRECTORY}; "
        f"/usr/local/go/bin/go test -c "
        f"-o {REMOTE_BINARY} "
        f"{REMOTE_PACKAGE} && "
        f"/usr/local/go/bin/go build "
        f"-o {REMOTE_PROVISION_BINARY} "
        f"{REMOTE_PROVISION_PACKAGE} && "
        f"/usr/local/go/bin/go build "
        f"-o {REMOTE_ENERGY_BINARY} "
        f"{REMOTE_ENERGY_PACKAGE}"
    )

    subprocess.run(
        ["ssh", SSH_TARGET, command],
        check=True,
    )


def orchestrate_provision():

    print("Provisioning Full Schema Fixtures...")

    subprocess.run(
        ["ssh", SSH_TARGET, f"rm -rf {REMOTE_CACHE_DIRECTORY}"],
        check=True,
    )

    command = (
        f"cd {REMOTE_PROJECT_DIRECTORY} && "
        f"set -a && "
        f". {REMOTE_ENVIRONMENT_FILE} && "
        f"set +a && "
        f"{REMOTE_PROVISION_BINARY}"
    )

    result = subprocess.run(
        ["ssh", SSH_TARGET, command],
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Provision Failed: Full Schema\n{result.stderr}")

    print("Finished Provisioning")


def run_memory_case(output, operation, algorithm, payload_size):

    print(f"Memory: {algorithm} {operation} {payload_size}B")
    benchmark_case = f"^BenchmarkFullSchema{operation}$/^{algorithm}$/^{payload_size}B$"

    command = (
        f"cd {REMOTE_PROJECT_DIRECTORY} && "
        f"set -a && "
        f". {REMOTE_ENVIRONMENT_FILE} && "
        f"set +a && "
        f"{REMOTE_BINARY}"
        f" -test.run=^$"
        f" -test.bench='{benchmark_case}'"
        f" -test.benchtime=1x"
        f" -test.count=1"
        f" -test.timeout=0"
    )

    for _ in range(RUNS):
        result = subprocess.run(
            ["ssh", SSH_TARGET, command],
            stdout=output,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Memory Benchmark Failed: "
                f"{algorithm} {operation} {payload_size}B\n"
                f"{result.stderr}"
            )


def orchestrate_memory():

    with MEMORY_RESULT_FILE.open("w", encoding="utf-8") as output:

        run_memory_case(output, "MemoryBaseline", "Runtime", 0)

        for payload_size in PAYLOAD_SIZES:
            run_memory_case(output, "MemoryEncrypt", "PSKStandard", payload_size)
            run_memory_case(output, "MemoryDecrypt", "PSKStandard", payload_size)
            run_memory_case(output, "MemoryEncrypt", "PSKLightweight", payload_size)
            run_memory_case(output, "MemoryDecrypt", "PSKLightweight", payload_size)
            run_memory_case(output, "MemoryEncrypt", "RSAStandard", payload_size)
            run_memory_case(output, "MemoryDecrypt", "RSAStandard", payload_size)
            run_memory_case(output, "MemoryEncrypt", "RSALightweight", payload_size)
            run_memory_case(output, "MemoryDecrypt", "RSALightweight", payload_size)
            run_memory_case(output, "MemoryEncrypt", "CPABEStandard", payload_size)
            run_memory_case(output, "MemoryDecrypt", "CPABEStandard", payload_size)
            run_memory_case(output, "MemoryEncrypt", "CPABELightweight", payload_size)
            run_memory_case(output, "MemoryDecrypt", "CPABELightweight", payload_size)

    csv_filepath = convert_memory_results(MEMORY_RESULT_FILE, "full_schema")
    print(f"Finished: {csv_filepath}")


def run_energy_case(meter, writer, algorithm, operation, payload_size):

    print(f"Energy: {algorithm} {operation} {payload_size}")

    command = (
        f"cd {REMOTE_PROJECT_DIRECTORY} && "
        f"set -a && "
        f". {REMOTE_ENVIRONMENT_FILE} && "
        f"set +a && "
        f"{REMOTE_ENERGY_BINARY}"
        f" -algorithm={algorithm}"
        f" -operation={operation}"
        f" -payload-size={payload_size}"
        f" -duration={TOTAL_WORKLOAD_DURATION}s"
    )

    for run in range(1, RUNS + 1):

        process = subprocess.Popen(["ssh", SSH_TARGET, command])

        time.sleep(WARMUP_DURATION)
        samples = read_um24c(meter, MEASUREMENT_DURATION)

        returncode = process.wait()

        if returncode not in (0, 3):
            raise RuntimeError(
                f"Energy Workload Failed: {algorithm} {operation} {payload_size}"
            )

        write_samples(
            writer,
            samples,
            {
                "scenario": "full_schema",
                "row_type": "workload",
                "algorithm": algorithm,
                "operation": operation,
                "parameter": "payload_size",
                "parameter_value": payload_size,
                "run": run,
                "throttled": int(returncode == 3),
            },
        )

        # Leave the device idle between independent workload processes.
        time.sleep(4)


def orchestrate_energy():

    # Create the UM24C Instance & Ensure Auto Close in Case of Exception
    with closing(UM24C()) as um24c:

        print(f"Using UM24C at {UM24C.MAC_ADDRESS}")
        print(
            f"Collection of {RUNS} Idle Baseline Power Windows "
            f"for {BASELINE_DURATION}s each..."
        )

        with ENERGY_RESULT_FILE.open("w", encoding="utf-8", newline="") as output:

            writer = csv.DictWriter(output, fieldnames=ENERGY_FIELDS)
            writer.writeheader()

            for run in range(1, RUNS + 1):
                write_samples(
                    writer,
                    read_um24c(um24c, BASELINE_DURATION),
                    {"scenario": "full_schema", "row_type": "baseline", "run": run},
                )

            for payload_size in PAYLOAD_SIZES:

                run_energy_case(um24c, writer, "PSKStandard", "Encrypt", payload_size)
                run_energy_case(um24c, writer, "PSKStandard", "Decrypt", payload_size)
                run_energy_case(
                    um24c, writer, "PSKLightweight", "Encrypt", payload_size
                )
                run_energy_case(
                    um24c, writer, "PSKLightweight", "Decrypt", payload_size
                )
                run_energy_case(um24c, writer, "RSAStandard", "Encrypt", payload_size)
                run_energy_case(um24c, writer, "RSAStandard", "Decrypt", payload_size)
                run_energy_case(
                    um24c, writer, "RSALightweight", "Encrypt", payload_size
                )
                run_energy_case(
                    um24c, writer, "RSALightweight", "Decrypt", payload_size
                )
                run_energy_case(um24c, writer, "CPABEStandard", "Encrypt", payload_size)
                run_energy_case(um24c, writer, "CPABEStandard", "Decrypt", payload_size)
                run_energy_case(
                    um24c, writer, "CPABELightweight", "Encrypt", payload_size
                )
                run_energy_case(
                    um24c, writer, "CPABELightweight", "Decrypt", payload_size
                )

    print(f"Finished: {ENERGY_RESULT_FILE}")


def run_timing_case(output, algorithm, operation, payload_size):

    print(f"Timing: {algorithm} {operation} {payload_size}B")
    benchmark_case = f"^BenchmarkFullSchema{operation}$/^{algorithm}$/^{payload_size}B$"

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
            f"Benchmark Failed: {algorithm} {operation} {payload_size}B\n"
            f"{result.stderr}"
        )


def orchestrate_timing():

    with TIMING_RESULT_FILE.open("w", encoding="utf-8") as destination_file:

        for payload_size in PAYLOAD_SIZES:

            run_timing_case(destination_file, "PSKStandard", "Encrypt", payload_size)
            run_timing_case(destination_file, "PSKStandard", "Decrypt", payload_size)
            run_timing_case(destination_file, "PSKLightweight", "Encrypt", payload_size)
            run_timing_case(destination_file, "PSKLightweight", "Decrypt", payload_size)
            run_timing_case(destination_file, "RSAStandard", "Encrypt", payload_size)
            run_timing_case(destination_file, "RSAStandard", "Decrypt", payload_size)
            run_timing_case(destination_file, "RSALightweight", "Encrypt", payload_size)
            run_timing_case(destination_file, "RSALightweight", "Decrypt", payload_size)
            run_timing_case(destination_file, "CPABEStandard", "Encrypt", payload_size)
            run_timing_case(destination_file, "CPABEStandard", "Decrypt", payload_size)
            run_timing_case(
                destination_file, "CPABELightweight", "Encrypt", payload_size
            )
            run_timing_case(
                destination_file, "CPABELightweight", "Decrypt", payload_size
            )

    csv_filepath = convert_timing_results(TIMING_RESULT_FILE, "full_schema")
    print(f"Finished: {csv_filepath}")


def generate_report():

    print("Generating Full Schema HTML Report...")

    subprocess.run(
        [sys.executable, "-m", "report.analysis.full_schema_report"],
        cwd=PROJECT_ROOT,
        check=True,
    )


def main():

    # Load Environment Variables
    load_environment_variables()

    # Create Result Directory Under Root
    RESULT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    # Build Benchmark & Provision Binaries
    build_binaries()

    # Provision Memory Fixtures
    orchestrate_provision()

    # Allow Device to Stabilize after Provisioning
    time.sleep(5)

    # Run Memory Benchmark
    orchestrate_memory()

    # Allow Device to Stabilize before Energy Measurement
    time.sleep(5)

    # Run Energy Benchmark
    orchestrate_energy()

    # Run Timing Benchmark
    orchestrate_timing()

    # Generate Report
    generate_report()


if __name__ == "__main__":
    main()
