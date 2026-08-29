import os
import sys
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from dotenv import load_dotenv

# Project Root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from um24c.um24c import UM24C

# Environment File
ENVIRONMENT_FILE = PROJECT_ROOT / "environment" / "benchmark.env"

# Raspberry Pi - SSH
SSH_TARGET = "pi"
REMOTE_BENCHMARK_DIRECTORY = "/home/thesis/latest/benchmark"
REMOTE_ENVIRONMENT_FILE = "/home/thesis/latest/environment/benchmark.env"
REMOTE_PACKAGE = "./micro/aes_ascon"
REMOTE_BINARY = "/tmp/aes-ascon-benchmark"

# UM24C Bluetooth serial port
UM24C_PORT = "COM11"


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

    RUNS = int(os.environ["AES_ASCON_RUNS"])

    PAYLOAD_SIZES = [
        int(payload_size)
        for payload_size in os.environ["AES_ASCON_PAYLOAD_SIZES"].split(",")
    ]
    TIMING_DURATION = int(os.environ["TIMING_DURATION"])
    BASELINE_DURATION = int(os.environ["BASELINE_DURATION"])
    WARMUP_DURATION = int(os.environ["WARMUP_DURATION"])
    MEASUREMENT_DURATION = int(os.environ["MEASUREMENT_DURATION"])
    TAIL_DURATION = int(os.environ["TAIL_DURATION"])

    TOTAL_WORKLOAD_DURATION = WARMUP_DURATION + MEASUREMENT_DURATION + TAIL_DURATION

    RESULT_DIRECTORY = PROJECT_ROOT / os.environ["AES_ASCON_RESULT_DIR"]
    TIMING_RESULT_FILE = RESULT_DIRECTORY / "timing.txt"
    ENERGY_RESULT_FILE = RESULT_DIRECTORY / "energy.txt"


def read_um24c(um24c, duration):

    samples = []

    start = time.monotonic()
    deadline = start + duration

    while time.monotonic() < deadline:

        voltage, current, power = um24c.read()

        elapsed = time.monotonic() - start

        samples.append((elapsed, voltage, current, power))

    return samples


def write_to_file(output, samples):

    for elapsed, voltage, current, power in samples:
        output.write(
            f"elapsed_s={elapsed:.6f} "
            f"voltage_v={voltage:.3f} "
            f"current_a={current:.3f} "
            f"power_w={power:.3f}\n"
        )


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

    output.write(
        f"\n[case algorithm={algorithm} operation={operation} payload_size={payload_size}]\n"
    )

    benchmark_case = (
        f"^BenchmarkAESASCONEnergy{operation}$/" f"^{algorithm}$/" f"^{payload_size}B$"
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

    # Popen -> Ensures call is not blocking and returns control to python
    # PIPE -> Ensures we can read stdout produced by binary
    process = subprocess.Popen(
        ["ssh", SSH_TARGET, command],
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    stress_sample_future = None

    # Main thread: Reads benchmark stdout
    # Worker thread: Reads power samples from the UM24C
    with ThreadPoolExecutor(max_workers=1) as executor:

        # Read the output
        for line in process.stdout:

            if "ENRG-START" in line:
                if stress_sample_future is not None:
                    raise RuntimeError(
                        "Received ENRG-START before previous run was completed"
                    )

                stress_sample_future = executor.submit(
                    read_um24c,
                    meter,
                    TOTAL_WORKLOAD_DURATION,
                )
                continue

            if "ns/op" in line:

                if stress_sample_future is None:
                    raise RuntimeError(
                        "Received benchmark result without corresponding power samples"
                    )

                parts = line.split()
                ns_per_op = parts[
                    parts.index("ns/op") - 1
                ]  # Because value is directly before ns/op
                throttled = parts[parts.index("throttled") - 1]  # Same convention

                # Obtain the samples belonging to this exact run
                # If sampling is still finishing, this waits for it...
                stress_samples = stress_sample_future.result()

                output.write("\n[run]\n")
                output.write(f"ns_per_op={ns_per_op}\n")
                output.write(f"throttled={throttled}\n")
                write_to_file(output, stress_samples)

                stress_sample_future = None

    if process.wait() != 0:
        raise RuntimeError(
            f"Benchmark Failed: " f"{algorithm} " f"{operation} " f"{payload_size}B"
        )


def orchestrate_energy():

    # Create the UM24C Instance & Ensure Auto Close in Case of Exception
    with closing(UM24C(UM24C_PORT)) as um24c:

        print(f"Using UM24C on Port {UM24C_PORT}")
        print(f"Collection of Idle Baseline Power for {BASELINE_DURATION}s...")

        # Record Baseline
        baseline_samples = read_um24c(um24c, BASELINE_DURATION)

        with ENERGY_RESULT_FILE.open("w", encoding="utf-8") as output:

            output.write("[baseline]\n")
            write_to_file(output, baseline_samples)

            for payload_size in PAYLOAD_SIZES:

                run_energy_case(um24c, output, "AES-GCM", "Encrypt", payload_size)
                run_energy_case(um24c, output, "AES-GCM", "Decrypt", payload_size)
                run_energy_case(um24c, output, "ASCON", "Encrypt", payload_size)
                run_energy_case(um24c, output, "ASCON", "Decrypt", payload_size)

    print(f"Finished: {ENERGY_RESULT_FILE}")


def run_timing_case(output, algorithm, operation, payload_size):

    benchmark_case = (
        f"^BenchmarkAESASCON{operation}$/" f"^{algorithm}$/" f"^{payload_size}B$"
    )

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

            run_timing_case(destination_file, "AES-GCM", "Encrypt", payload_size)
            run_timing_case(destination_file, "AES-GCM", "Decrypt", payload_size)
            run_timing_case(destination_file, "ASCON", "Encrypt", payload_size)
            run_timing_case(destination_file, "ASCON", "Decrypt", payload_size)

    print(f"Finished: {TIMING_RESULT_FILE}")


def generate_report():

    print("Generating AES vs ASCON HTML Report...")

    subprocess.run(
        [sys.executable, "-m", "report.analysis.aes_ascon_report"],
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
