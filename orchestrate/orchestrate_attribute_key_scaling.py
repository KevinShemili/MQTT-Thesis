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

REMOTE_PACKAGE = "./micro/attribute_key_scaling"
REMOTE_PROVISION_PACKAGE = "./cmd/provision"

REMOTE_BINARY = "/tmp/attribute-key-scaling-benchmark"
REMOTE_PROVISION_BINARY = "/tmp/attribute-key-scaling-provision"

# UM24C Bluetooth serial port
UM24C_PORT = "COM11"


def load_environment_variables():

    global RUNS
    global KEYGEN_RUNS
    global ATTRIBUTE_COUNTS
    global SUBSCRIBER_COUNTS
    global RSA_KEY_BITS
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

    RUNS = int(os.environ["ATTRIBUTE_KEY_SCALING_RUNS"])
    KEYGEN_RUNS = int(os.environ["ATTRIBUTE_KEY_SCALING_KEYGEN_RUNS"])

    ATTRIBUTE_COUNTS = [
        int(attribute_count)
        for attribute_count in os.environ[
            "ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT"
        ].split(",")
    ]

    SUBSCRIBER_COUNTS = [
        int(subscriber_count)
        for subscriber_count in os.environ[
            "ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT"
        ].split(",")
    ]

    RSA_KEY_BITS = [
        int(rsa_key_bits)
        for rsa_key_bits in os.environ["ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES"].split(",")
    ]

    TIMING_DURATION = int(os.environ["TIMING_DURATION"])

    BASELINE_DURATION = int(os.environ["BASELINE_DURATION"])
    WARMUP_DURATION = int(os.environ["WARMUP_DURATION"])
    MEASUREMENT_DURATION = int(os.environ["MEASUREMENT_DURATION"])
    TAIL_DURATION = int(os.environ["TAIL_DURATION"])

    TOTAL_WORKLOAD_DURATION = WARMUP_DURATION + MEASUREMENT_DURATION + TAIL_DURATION

    RESULT_DIRECTORY = PROJECT_ROOT / os.environ["ATTRIBUTE_KEY_SCALING_RESULT_DIR"]

    MEMORY_RESULT_FILE = RESULT_DIRECTORY / "memory.txt"
    ENERGY_RESULT_FILE = RESULT_DIRECTORY / "energy.txt"
    TIMING_RESULT_FILE = RESULT_DIRECTORY / "timing.txt"


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

    subprocess.run(["ssh", SSH_TARGET, command], check=True)


def run_provision_case(algorithm, parameter_value):

    command = (
        f"cd {REMOTE_PROJECT_DIRECTORY} && "
        f"set -a && "
        f". {REMOTE_ENVIRONMENT_FILE} && "
        f"set +a && "
        f"{REMOTE_PROVISION_BINARY} "
        f"{algorithm} "
        f"{parameter_value}"
    )

    result = subprocess.run(
        ["ssh", SSH_TARGET, command], stderr=subprocess.PIPE, text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Provision Failed: {algorithm} {parameter_value}\n" f"{result.stderr}"
        )


def orchestrate_provision():

    print("Provisioning Attribute & Key Scaling Fixtures...")

    # Start with an empty fixture cache
    subprocess.run(
        [
            "ssh",
            SSH_TARGET,
            f"rm -rf {REMOTE_CACHE_DIRECTORY}",
        ],
        check=True,
    )

    for attribute_count in ATTRIBUTE_COUNTS:
        run_provision_case("CPABEAttributes", attribute_count)
    for subscriber_count in SUBSCRIBER_COUNTS:
        run_provision_case("RSASubscribers", subscriber_count)
    for rsa_key_bits in RSA_KEY_BITS:
        run_provision_case("RSAKeyBits", rsa_key_bits)

    print("Finished Provisioning")


def run_memory_case(output, operation, algorithm, parameter_value):

    benchmark_case = (
        f"^BenchmarkAttributeKeyScaling{operation}$/"
        f"^{algorithm}$/"
        f"^{parameter_value}$"
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

    # Each sample needs its own process because VmHWM is process-wide.
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
                f"{algorithm} {operation} {parameter_value}\n"
                f"{result.stderr}"
            )


def orchestrate_memory():

    with MEMORY_RESULT_FILE.open("w", encoding="utf-8") as output:

        run_memory_case(output, "MemoryBaseline", "Runtime", 0)

        for attribute_count in ATTRIBUTE_COUNTS:
            run_memory_case(output, "MemoryEncrypt", "CPABEAttributes", attribute_count)
            run_memory_case(output, "MemoryDecrypt", "CPABEAttributes", attribute_count)

        for subscriber_count in SUBSCRIBER_COUNTS:
            run_memory_case(output, "MemoryEncrypt", "RSASubscribers", subscriber_count)

        for rsa_key_bits in RSA_KEY_BITS:
            run_memory_case(output, "MemoryEncrypt", "RSAKeyBits", rsa_key_bits)
            run_memory_case(output, "MemoryDecrypt", "RSAKeyBits", rsa_key_bits)

    print(f"Finished: {MEMORY_RESULT_FILE}")


def run_energy_case(meter, output, algorithm, operation, parameter_value):

    output.write(
        f"\n[case "
        f"algorithm={algorithm} "
        f"operation={operation} "
        f"parameter_value={parameter_value}]\n"
    )

    benchmark_case = (
        f"^BenchmarkAttributeKeyScalingEnergy{operation}$/"
        f"^{algorithm}$/"
        f"^{parameter_value}$"
    )

    command = (
        f"cd {REMOTE_PROJECT_DIRECTORY} && "
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
        ["ssh", SSH_TARGET, command], stdout=subprocess.PIPE, text=True, bufsize=1
    )

    stress_sample_future = None

    # Main thread: benchmark stdout
    # Worker thread: UM24C samples
    with ThreadPoolExecutor(max_workers=1) as executor:

        for line in process.stdout:

            if "ENRG-START" in line:

                if stress_sample_future is not None:
                    raise RuntimeError(
                        "Received ENRG-START before previous run was completed"
                    )

                stress_sample_future = executor.submit(
                    read_um24c, meter, TOTAL_WORKLOAD_DURATION
                )

                continue

            if "ns/op" in line:

                if stress_sample_future is None:
                    raise RuntimeError(
                        "Received benchmark result without corresponding power samples"
                    )

                parts = line.split()

                ns_per_op = parts[parts.index("ns/op") - 1]

                throttled = parts[parts.index("throttled") - 1]

                stress_samples = stress_sample_future.result()

                output.write("\n[run]\n")
                output.write(f"ns/op={ns_per_op}\n")
                output.write(f"throttled={throttled}\n")

                write_to_file(output, stress_samples)

                stress_sample_future = None

    if process.wait() != 0:
        raise RuntimeError(
            f"Energy Benchmark Failed: " f"{algorithm} {operation} {parameter_value}"
        )


def orchestrate_energy():

    with closing(UM24C(UM24C_PORT)) as um24c:

        print(f"Using UM24C on Port {UM24C_PORT}")
        print(f"Collection of Idle Baseline Power " f"for {BASELINE_DURATION}s...")

        baseline_samples = read_um24c(um24c, BASELINE_DURATION)

        with ENERGY_RESULT_FILE.open("w", encoding="utf-8") as output:

            output.write("[baseline]\n")
            write_to_file(output, baseline_samples)

            # CP-ABE attribute scaling
            for attribute_count in ATTRIBUTE_COUNTS:
                run_energy_case(
                    um24c, output, "CPABEAttributes", "Encrypt", attribute_count
                )
                run_energy_case(
                    um24c, output, "CPABEAttributes", "Decrypt", attribute_count
                )

            # RSA subscriber scaling
            for subscriber_count in SUBSCRIBER_COUNTS:
                run_energy_case(
                    um24c, output, "RSASubscribers", "Encrypt", subscriber_count
                )

            # RSA key-size scaling
            for rsa_key_bits in RSA_KEY_BITS:
                run_energy_case(um24c, output, "RSAKeyBits", "Encrypt", rsa_key_bits)
                run_energy_case(um24c, output, "RSAKeyBits", "Decrypt", rsa_key_bits)
                run_energy_case(um24c, output, "RSAKeyBits", "KeyGen", rsa_key_bits)

    print(f"Finished: {ENERGY_RESULT_FILE}")


def run_timing_case(
    output, algorithm, operation, parameter_value, benchmark_time, runs
):

    benchmark_case = (
        f"^BenchmarkAttributeKeyScaling{operation}$/"
        f"^{algorithm}$/"
        f"^{parameter_value}$"
    )

    command = (
        f"cd {REMOTE_PROJECT_DIRECTORY} && "
        f"set -a && "
        f". {REMOTE_ENVIRONMENT_FILE} && "
        f"set +a && "
        f"{REMOTE_BINARY}"
        f" -test.run=^$"
        f" -test.bench='{benchmark_case}'"
        f" -test.benchtime={benchmark_time}"
        f" -test.count={runs}"
        f" -test.timeout=0"
    )

    result = subprocess.run(
        ["ssh", SSH_TARGET, command], stdout=output, stderr=subprocess.PIPE, text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Timing Benchmark Failed: "
            f"{algorithm} {operation} {parameter_value}\n"
            f"{result.stderr}"
        )


def orchestrate_timing():

    with TIMING_RESULT_FILE.open("w", encoding="utf-8") as output:

        # CP-ABE attribute scaling
        for attribute_count in ATTRIBUTE_COUNTS:
            run_timing_case(
                output,
                "CPABEAttributes",
                "Encrypt",
                attribute_count,
                f"{TIMING_DURATION}s",
                RUNS,
            )
            run_timing_case(
                output,
                "CPABEAttributes",
                "Decrypt",
                attribute_count,
                f"{TIMING_DURATION}s",
                RUNS,
            )

        # RSA subscriber scaling
        for subscriber_count in SUBSCRIBER_COUNTS:
            run_timing_case(
                output,
                "RSASubscribers",
                "Encrypt",
                subscriber_count,
                f"{TIMING_DURATION}s",
                RUNS,
            )

        # RSA key-size scaling
        for rsa_key_bits in RSA_KEY_BITS:
            run_timing_case(
                output,
                "RSAKeyBits",
                "Encrypt",
                rsa_key_bits,
                f"{TIMING_DURATION}s",
                RUNS,
            )
            run_timing_case(
                output,
                "RSAKeyBits",
                "Decrypt",
                rsa_key_bits,
                f"{TIMING_DURATION}s",
                RUNS,
            )

        # RSA key generation
        for rsa_key_bits in RSA_KEY_BITS:
            run_timing_case(
                output,
                "RSAKeyBits",
                "KeyGen",
                rsa_key_bits,
                "1x",
                KEYGEN_RUNS,
            )

    print(f"Finished: {TIMING_RESULT_FILE}")


def generate_report():

    print("Generating Attribute & Key Scaling HTML Report...")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "report.analysis.attribute_key_scaling_report",
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )


def main():

    # Load Environment Variables
    load_environment_variables()

    # Create Result Directory Under Root
    RESULT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Build Benchmark & Provision Binaries
    build_binaries()

    # Provision Expensive Fixtures
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
