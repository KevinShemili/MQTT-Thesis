import os
import re
import shlex
import subprocess
import time
from pathlib import Path

from dotenv import load_dotenv

from um24c import UM24C


PROJECT_DIRECTORY = Path(__file__).resolve().parents[2]

ENVIRONMENT_FILE = PROJECT_DIRECTORY / "environment" / "benchmark.env"


# Raspberry Pi
SSH_TARGET = "pi"
REMOTE_BENCHMARK_DIR = "/home/thesis/latest/benchmark"
REMOTE_PACKAGE = "./cmd/energy/aes_ascon"
REMOTE_BINARY = "/tmp/aes-ascon-energy"

# UM24C Bluetooth serial port
UM24C_PORT = "COM11"

# Energy experiment durations
BASELINE_DURATION = 10
WARMUP_DURATION = 2
MEASUREMENT_DURATION = 10
TAIL_DURATION = 2

TOTAL_WORKLOAD_DURATION = (
    WARMUP_DURATION
    + MEASUREMENT_DURATION
    + TAIL_DURATION
)

# Results
DEFAULT_RESULT_DIRECTORY = (
    PROJECT_DIRECTORY
    / "results"
    / "aes-ascon"
    / "with-acceleration"
)
ENERGY_RESULT_NAME = "aes_ascon_energy.txt"


def load_environment_variables():

    global RUNS, PAYLOAD_SIZES, KEY_SIZE, TEMPERATURE_THRESHOLD

    load_dotenv(
        ENVIRONMENT_FILE,
        override=True,
    )

    RUNS = int(
        os.environ["AES_ASCON_RUNS"]
    )

    PAYLOAD_SIZES = [
        int(payload_size)
        for payload_size in os.environ[
            "AES_ASCON_PAYLOAD_SIZES"
        ].split(",")
    ]

    KEY_SIZE = int(
        os.environ["AES_ASCON_KEY_SIZE"]
    )

    TEMPERATURE_THRESHOLD = int(
        os.environ["TEMPERATURE_THRESHOLD"]
    )


def collect_power(
    meter,
    duration,
):

    samples = []

    start = time.monotonic_ns()
    deadline = time.monotonic() + duration

    while time.monotonic() < deadline:

        voltage, current, power = meter.read()

        elapsed_ns = (
            time.monotonic_ns()
            - start
        )

        samples.append(
            (
                elapsed_ns,
                voltage,
                current,
                power,
            )
        )

    return samples


def write_power_samples(
    output,
    samples,
):

    for (
        elapsed_ns,
        voltage,
        current,
        power,
    ) in samples:

        output.write(
            f"elapsed_ns={elapsed_ns} "
            f"voltage_v={voltage:.3f} "
            f"current_a={current:.3f} "
            f"power_w={power:.3f}\n"
        )


def build_benchmark():

    command = (
        f"cd {shlex.quote(REMOTE_BENCHMARK_DIR)}"
        f" && /usr/local/go/bin/go test"
        f" -c"
        f" -o {shlex.quote(REMOTE_BINARY)}"
        f" {shlex.quote(REMOTE_PACKAGE)}"
    )

    subprocess.run(
        ["ssh", SSH_TARGET, command],
        check=True,
    )


def run_case(
    meter,
    output,
    algorithm,
    operation,
    payload_size,
):

    output.write(
        f"\n[case "
        f"algorithm={algorithm} "
        f"operation={operation} "
        f"payload_size={payload_size}"
        f"]\n"
    )

    output.flush()

    benchmark_name = (
        f"^BenchmarkAESASCONEnergy{operation}$/"
        f"^{algorithm}$/"
        f"^{payload_size}B$"
    )

    payload_sizes = ",".join(
        str(size)
        for size in PAYLOAD_SIZES
    )

    command = (
        f"cd {shlex.quote(REMOTE_BENCHMARK_DIR)}"
        f" && AES_ASCON_PAYLOAD_SIZES={shlex.quote(payload_sizes)}"
        f" AES_ASCON_KEY_SIZE={KEY_SIZE}"
        f" TEMPERATURE_THRESHOLD={TEMPERATURE_THRESHOLD}"
        f" {shlex.quote(REMOTE_BINARY)}"
        f" -test.run=^$"
        f" -test.bench={shlex.quote(benchmark_name)}"
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

    if process.stdout is None:
        raise RuntimeError(
            "Could not read Raspberry Pi benchmark output"
        )

    power_samples = None
    completed_runs = 0

    for line in process.stdout:

        line = line.strip()

        if not line:
            continue

        print(
            f"{algorithm} "
            f"{operation} "
            f"{payload_size}B: "
            f"{line}"
        )

        if line.endswith("RUN START"):
            power_samples = collect_power(
                meter=meter,
                duration=TOTAL_WORKLOAD_DURATION,
            )
            continue

        if "ns/op" in line:
            if power_samples is None:
                raise RuntimeError(
                    "Received benchmark result "
                    "without corresponding power samples"
                )

            match = re.search(
                r"([0-9]+(?:\.[0-9]+)?)\s+ns/op",
                line,
            )

            if match is None:
                raise RuntimeError(
                    f"Could not parse ns/op from: {line}"
                )

            ns_per_op = match.group(1)

            output.write(
                "\n[run]\n"
            )
            output.write(
                f"ns_per_op={ns_per_op}\n"
            )

            write_power_samples(
                output,
                power_samples,
            )

            output.flush()

            power_samples = None
            completed_runs += 1

    if process.wait() != 0:
        raise RuntimeError(
            f"Benchmark failed: "
            f"{algorithm} "
            f"{operation} "
            f"{payload_size}B"
        )

    if completed_runs != RUNS:
        raise RuntimeError(
            f"Expected {RUNS} benchmark results for "
            f"{algorithm} {operation} {payload_size}B, "
            f"but observed {completed_runs}"
        )


def main():

    load_environment_variables()

    result_directory = Path(
        os.environ.get(
            "AES_ASCON_RESULT_DIR",
            str(DEFAULT_RESULT_DIRECTORY),
        )
    )
    result_directory.mkdir(parents=True, exist_ok=True)
    result_file = result_directory / ENERGY_RESULT_NAME

    meter = UM24C(
        UM24C_PORT
    )

    try:

        print(
            "Collecting idle baseline..."
        )

        baseline_samples = collect_power(
            meter=meter,
            duration=BASELINE_DURATION,
        )

        print(
            "Building Raspberry Pi energy benchmark..."
        )

        build_benchmark()

        with result_file.open(
            "w",
            encoding="utf-8",
        ) as output:

            output.write(
                "[baseline]\n"
            )

            write_power_samples(
                output,
                baseline_samples,
            )

            for payload_size in PAYLOAD_SIZES:

                run_case(
                    meter=meter,
                    output=output,
                    algorithm="AES-GCM",
                    operation="Encrypt",
                    payload_size=payload_size,
                )

                run_case(
                    meter=meter,
                    output=output,
                    algorithm="AES-GCM",
                    operation="Decrypt",
                    payload_size=payload_size,
                )

            for payload_size in PAYLOAD_SIZES:

                run_case(
                    meter=meter,
                    output=output,
                    algorithm="ASCON",
                    operation="Encrypt",
                    payload_size=payload_size,
                )

                run_case(
                    meter=meter,
                    output=output,
                    algorithm="ASCON",
                    operation="Decrypt",
                    payload_size=payload_size,
                )

        print(
            f"Finished: {result_file}"
        )

    finally:

        meter.close()


if __name__ == "__main__":
    main()
