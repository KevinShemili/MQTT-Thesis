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
REMOTE_PROJECT_DIRECTORY = "/home/thesis/MQTT-Thesis"
REMOTE_BENCHMARK_DIRECTORY = "/home/thesis/MQTT-Thesis/benchmark"
REMOTE_ENVIRONMENT_FILE = "/home/thesis/MQTT-Thesis/environment/benchmark.env"
REMOTE_CACHE_DIRECTORY = f"{REMOTE_PROJECT_DIRECTORY}/disk-cache"
REMOTE_PACKAGE = "./micro/full_schema"
REMOTE_PROVISION_PACKAGE = "./cmd/provision_full_schema"
REMOTE_BINARY = "/tmp/full-schema-benchmark"
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


def build_binaries():

    command = (
        f"cd {REMOTE_BENCHMARK_DIRECTORY}; "
        f"/usr/local/go/bin/go test -c "
        f"-o {REMOTE_BINARY} "
        f"{REMOTE_PACKAGE} && "
        f"/usr/local/go/bin/go build "
        f"-o {REMOTE_PROVISION_BINARY} "
        f"{REMOTE_PROVISION_PACKAGE}"
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
    benchmark_case = (
        f"^BenchmarkFullSchema{operation}$/" f"^{algorithm}$/" f"^{payload_size}B$"
    )

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

    print(f"Finished: {MEMORY_RESULT_FILE}")


def run_energy_case(meter, output, algorithm, operation, payload_size):

    print(f"Energy: {algorithm} {operation} {payload_size}B")
    output.write(
        f"\n[case algorithm={algorithm} operation={operation} parameter_value={payload_size}]\n"
    )

    benchmark_case = (
        f"^BenchmarkFullSchemaEnergy{operation}$/"
        f"^{algorithm}$/"
        f"^{payload_size}B$"
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
                output.write(f"ns/op={ns_per_op}\n")
                output.write(f"throttled={throttled}\n")
                write_to_file(output, stress_samples)

                stress_sample_future = None

    if process.wait() != 0:
        raise RuntimeError(
            f"Benchmark Failed: " f"{algorithm} " f"{operation} " f"{payload_size}B"
        )


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

                run_energy_case(um24c, output, "PSKStandard", "Encrypt", payload_size)
                run_energy_case(um24c, output, "PSKStandard", "Decrypt", payload_size)
                run_energy_case(
                    um24c, output, "PSKLightweight", "Encrypt", payload_size
                )
                run_energy_case(
                    um24c, output, "PSKLightweight", "Decrypt", payload_size
                )
                run_energy_case(um24c, output, "RSAStandard", "Encrypt", payload_size)
                run_energy_case(um24c, output, "RSAStandard", "Decrypt", payload_size)
                run_energy_case(
                    um24c, output, "RSALightweight", "Encrypt", payload_size
                )
                run_energy_case(
                    um24c, output, "RSALightweight", "Decrypt", payload_size
                )
                run_energy_case(um24c, output, "CPABEStandard", "Encrypt", payload_size)
                run_energy_case(um24c, output, "CPABEStandard", "Decrypt", payload_size)
                run_energy_case(
                    um24c, output, "CPABELightweight", "Encrypt", payload_size
                )
                run_energy_case(
                    um24c, output, "CPABELightweight", "Decrypt", payload_size
                )

    print(f"Finished: {ENERGY_RESULT_FILE}")


def run_timing_case(output, algorithm, operation, payload_size):

    print(f"Timing: {algorithm} {operation} {payload_size}B")
    benchmark_case = (
        f"^BenchmarkFullSchema{operation}$/" f"^{algorithm}$/" f"^{payload_size}B$"
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

    print(f"Finished: {TIMING_RESULT_FILE}")


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
