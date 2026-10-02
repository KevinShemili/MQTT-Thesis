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

REMOTE_PACKAGE = "./micro/cpabe_rsa"
REMOTE_PROVISION_PACKAGE = "./cmd/provision/provision_cpabe_rsa"
REMOTE_BINARY = "/tmp/cpabe-rsa-benchmark"
REMOTE_ENERGY_PACKAGE = "./cmd/energy/energy_cpabe_rsa"
REMOTE_ENERGY_BINARY = "/tmp/cpabe-rsa-energy"
REMOTE_PROVISION_BINARY = "/tmp/cpabe-rsa-provision"


def load_environment_variables():

    global RUNS
    global ATTRIBUTE_COUNTS
    global SUBSCRIBER_COUNTS
    global RSA_KEY_BITS
    global FIXED_RSA_KEY_BITS
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

    RUNS = int(os.environ["CPABE_RSA_RUNS"])

    ATTRIBUTE_COUNTS = [
        int(attribute_count)
        for attribute_count in os.environ["CPABE_RSA_ATTRIBUTE_COUNT"].split(",")
    ]

    SUBSCRIBER_COUNTS = [
        int(subscriber_count)
        for subscriber_count in os.environ["CPABE_RSA_SUBSCRIBER_COUNT"].split(",")
    ]

    RSA_KEY_BITS = [
        int(rsa_key_bits)
        for rsa_key_bits in os.environ["CPABE_RSA_RSA_KEY_SIZES"].split(",")
    ]
    FIXED_RSA_KEY_BITS = int(os.environ["CPABE_RSA_FIXED_RSA_KEY_SIZE"])

    TIMING_DURATION = int(os.environ["TIMING_DURATION"])

    BASELINE_DURATION = int(os.environ["BASELINE_DURATION"])
    WARMUP_DURATION = int(os.environ["WARMUP_DURATION"])
    MEASUREMENT_DURATION = int(os.environ["MEASUREMENT_DURATION"])
    TAIL_DURATION = int(os.environ["TAIL_DURATION"])

    TOTAL_WORKLOAD_DURATION = WARMUP_DURATION + MEASUREMENT_DURATION + TAIL_DURATION

    RESULT_DIRECTORY = PROJECT_ROOT / os.environ["CPABE_RSA_RESULT_DIR"]

    MEMORY_RESULT_FILE = RESULT_DIRECTORY / "memory.txt"
    ENERGY_RESULT_FILE = RESULT_DIRECTORY / "energy.csv"
    TIMING_RESULT_FILE = RESULT_DIRECTORY / "timing.txt"


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

    subprocess.run(["ssh", SSH_TARGET, command], check=True)


def orchestrate_provision():

    print("Provisioning CP-ABE vs. RSA Fixtures...")

    # Start with an empty fixture cache
    subprocess.run(
        [
            "ssh",
            SSH_TARGET,
            f"rm -rf {REMOTE_CACHE_DIRECTORY}",
        ],
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
        ["ssh", SSH_TARGET, command], stderr=subprocess.PIPE, text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Provision Failed: CP-ABE vs. RSA\n{result.stderr}")

    print("Finished Provisioning")


def run_memory_case(output, operation, algorithm, parameter_value):

    print(f"Memory: {algorithm} {operation} {parameter_value}")
    benchmark_case = f"^BenchmarkCPABERSA{operation}$/^{algorithm}$/^{parameter_value}$"

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

        run_memory_case(
            output,
            "MemoryDecrypt",
            "RSAKeyBits",
            FIXED_RSA_KEY_BITS,
        )

    csv_filepath = convert_memory_results(MEMORY_RESULT_FILE, "cpabe_rsa")
    print(f"Finished: {csv_filepath}")


def run_energy_case(meter, writer, algorithm, operation, parameter_value):

    print(f"Energy: {algorithm} {operation} {parameter_value}")

    if algorithm == "CPABEAttributes":
        parameter = "attribute_count"
        case_arguments = f" -attribute-count={parameter_value}"
    elif algorithm == "RSASubscribers":
        parameter = "subscriber_count"
        case_arguments = f" -subscriber-count={parameter_value}"
    else:
        parameter = "rsa_key_bits"
        case_arguments = ""

    command = (
        f"cd {REMOTE_PROJECT_DIRECTORY} && "
        f"set -a && "
        f". {REMOTE_ENVIRONMENT_FILE} && "
        f"set +a && "
        f"{REMOTE_ENERGY_BINARY}"
        f" -algorithm={algorithm}"
        f" -operation={operation}"
        f"{case_arguments}"
        f" -duration={TOTAL_WORKLOAD_DURATION}s"
    )

    for run in range(1, RUNS + 1):

        process = subprocess.Popen(["ssh", SSH_TARGET, command])

        time.sleep(WARMUP_DURATION)
        samples = read_um24c(meter, MEASUREMENT_DURATION)

        returncode = process.wait()

        if returncode not in (0, 3):
            raise RuntimeError(
                f"Energy Workload Failed: {algorithm} {operation} {parameter_value}"
            )

        write_samples(
            writer,
            samples,
            {
                "scenario": "cpabe_rsa",
                "row_type": "workload",
                "algorithm": algorithm,
                "operation": operation,
                "parameter": parameter,
                "parameter_value": parameter_value,
                "run": run,
                "throttled": int(returncode == 3),
            },
        )

        # Leave the device idle between independent workload processes.
        time.sleep(4)


def orchestrate_energy():

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
                    {"scenario": "cpabe_rsa", "row_type": "baseline", "run": run},
                )

            # CP-ABE attribute scaling
            for attribute_count in ATTRIBUTE_COUNTS:
                run_energy_case(
                    um24c, writer, "CPABEAttributes", "Encrypt", attribute_count
                )
                run_energy_case(
                    um24c, writer, "CPABEAttributes", "Decrypt", attribute_count
                )

            # RSA subscriber scaling
            for subscriber_count in SUBSCRIBER_COUNTS:
                run_energy_case(
                    um24c, writer, "RSASubscribers", "Encrypt", subscriber_count
                )

            # Fixed RSA decrypt reference
            run_energy_case(
                um24c,
                writer,
                "RSAKeyBits",
                "Decrypt",
                FIXED_RSA_KEY_BITS,
            )

    print(f"Finished: {ENERGY_RESULT_FILE}")


def run_timing_case(
    output, algorithm, operation, parameter_value, benchmark_time, runs
):

    print(f"Timing: {algorithm} {operation} {parameter_value}")
    benchmark_case = f"^BenchmarkCPABERSA{operation}$/^{algorithm}$/^{parameter_value}$"

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

    csv_filepath = convert_timing_results(TIMING_RESULT_FILE, "cpabe_rsa")
    print(f"Finished: {csv_filepath}")


def generate_report():

    print("Generating CP-ABE vs. RSA HTML Report...")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "report.analysis.cpabe_rsa_report",
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
