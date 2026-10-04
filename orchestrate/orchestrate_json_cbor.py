import csv
import os
import sys
import subprocess
import time
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from utility.python.parser.env_parser import parse_int_env, parse_int_list_env

from utility.python.path.path import (
    ENERGY_RESULT_NAME,
    ENVIRONMENT_FILE,
    PROJECT_ROOT,
    REMOTE_BENCHMARK_DIRECTORY,
    REMOTE_ENVIRONMENT_FILE,
    REMOTE_GO_EXECUTABLE,
    REMOTE_PROJECT_DIRECTORY,
    SSH_TARGET,
    TIMING_TEXT_NAME,
)

from orchestrate.shared.csv import (
    ENERGY_FIELDS,
    convert_timing_results,
    write_samples,
)

from utility.python.um24c.um24c import UM24C

REMOTE_PACKAGE = "./micro/json_cbor"
REMOTE_BINARY = "/tmp/json-cbor-benchmark"
REMOTE_ENERGY_PACKAGE = "./cmd/energy/energy_json_cbor"
REMOTE_ENERGY_BINARY = "/tmp/json-cbor-energy"


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

    RUNS = parse_int_env("JSON_CBOR_RUNS")

    PAYLOAD_SIZES = parse_int_list_env("PAYLOAD_SIZES")

    TIMING_DURATION = parse_int_env("TIMING_DURATION")
    BASELINE_DURATION = parse_int_env("BASELINE_DURATION")
    WARMUP_DURATION = parse_int_env("WARMUP_DURATION")
    MEASUREMENT_DURATION = parse_int_env("MEASUREMENT_DURATION")
    TAIL_DURATION = parse_int_env("TAIL_DURATION")

    TOTAL_WORKLOAD_DURATION = WARMUP_DURATION + MEASUREMENT_DURATION + TAIL_DURATION

    RESULT_DIRECTORY = PROJECT_ROOT / os.environ["JSON_CBOR_RESULT_DIR"]
    TIMING_RESULT_FILE = RESULT_DIRECTORY / TIMING_TEXT_NAME
    ENERGY_RESULT_FILE = RESULT_DIRECTORY / ENERGY_RESULT_NAME


def build_benchmark_binary():

    command = (
        f"cd {REMOTE_BENCHMARK_DIRECTORY }; "
        f"{REMOTE_GO_EXECUTABLE} test -c "
        f"-o {REMOTE_BINARY} "
        f"{REMOTE_PACKAGE} && "
        f"{REMOTE_GO_EXECUTABLE} build "
        f"-o {REMOTE_ENERGY_BINARY} "
        f"{REMOTE_ENERGY_PACKAGE}"
    )

    subprocess.run(
        ["ssh", SSH_TARGET, command],
        check=True,
    )


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
        samples = meter.sample(MEASUREMENT_DURATION)

        returncode = process.wait()

        if returncode not in (0, 3):
            raise RuntimeError(
                f"Energy Workload Failed: {algorithm} {operation} {payload_size}"
            )

        write_samples(
            writer,
            samples,
            {
                "scenario": "json_cbor",
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
                    um24c.sample(BASELINE_DURATION),
                    {"scenario": "json_cbor", "row_type": "baseline", "run": run},
                )

            for payload_size in PAYLOAD_SIZES:

                run_energy_case(um24c, writer, "JSON", "Serialize", payload_size)
                run_energy_case(um24c, writer, "JSON", "Deserialize", payload_size)
                run_energy_case(um24c, writer, "CBOR", "Serialize", payload_size)
                run_energy_case(um24c, writer, "CBOR", "Deserialize", payload_size)
                run_energy_case(
                    um24c, writer, "CBORKeyAsInt", "Serialize", payload_size
                )
                run_energy_case(
                    um24c, writer, "CBORKeyAsInt", "Deserialize", payload_size
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

    csv_filepath = convert_timing_results(TIMING_RESULT_FILE, "json_cbor")
    print(f"Finished: {csv_filepath}")


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
