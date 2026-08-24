import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIRECTORY = Path(__file__).resolve().parents[2]

ENVIRONMENT_FILE = PROJECT_DIRECTORY / "environment" / "benchmark.env"

BENCHMARK_DIRECTORY = PROJECT_DIRECTORY / "benchmark"
BINARY_DIRECTORY = PROJECT_DIRECTORY / "bin"
RESULT_DIRECTORY = PROJECT_DIRECTORY / "results" / "json-cbor"

OUTPUT_FILE = RESULT_DIRECTORY / "bench_output.txt"
STATUS_FILE = RESULT_DIRECTORY / "case_status.txt"

BENCHMARK_BINARY = str(BINARY_DIRECTORY / "benchmark-binary")


def load_environment_variables():

    global ATTRIBUTE_COUNTS, BENCHMARK_RUNS

    load_dotenv(ENVIRONMENT_FILE, override=True)

    # The report would otherwise look for this run under the results root the
    # container mounted, which is what this override exists for
    os.environ["JSON_CBOR_RESULT_DIR"] = str(RESULT_DIRECTORY)

    ATTRIBUTE_COUNTS = os.environ["JSON_CBOR_ATTRIBUTE_COUNTS"].split(",")

    BENCHMARK_RUNS = int(os.environ["JSON_CBOR_RUNS"])


def build_binaries():

    # The image used to compile these ahead of the run, so that a measurement is
    # never attributed to a binary older than the source it is reported against
    print("Building benchmark binary...")

    BINARY_DIRECTORY.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["go", "test", "-c", "-o", BENCHMARK_BINARY, "./micro/json_cbor"],
        cwd=BENCHMARK_DIRECTORY,
        check=True,
    )


def prepare_output_directories():

    RESULT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    # Previous benchmark results must not leak into the new run.
    OUTPUT_FILE.write_text("")

    STATUS_FILE.write_text("# operation group sweep_value out_of_memory\n")


# ---------------------------------------------------------------------------
# Process execution
# ---------------------------------------------------------------------------


def is_out_of_memory(return_code, stderr):

    # Python reports a child killed by SIGKILL as -9. Normalize it to the shell's 137
    # representation before applying the controlled OOM rules.
    normalized_return_code = 128 - return_code if return_code < 0 else return_code

    return normalized_return_code == 137 or (
        return_code != 0 and "out of memory" in stderr
    )


def record_out_of_memory(operation, group, sweep_value):

    with STATUS_FILE.open("a") as status:
        status.write(f"{operation} {group} {sweep_value} true\n")


def run_benchmark(
    operation,
    group,
    sweep_value,
    sample,
    output_file,
    bench_time,
    count,
    record_oom=False,
):
    """
    Run one exact Go benchmark case in its own process.

    Benchmark output is appended to the experiment output file. Timing cases
    capture stderr only long enough to detect whole-case OOM.
    """

    sample_label = "" if sample is None else f" #{sample}"
    print(f"  {operation} {group}/{sweep_value}{sample_label}")

    benchmark_name = (
        f"^BenchmarkEnvelope{operation}$/"
        f"^{group}$/"
        f"^{sweep_value}Attrs$"
    )

    command = [
        BENCHMARK_BINARY,
        "-test.run=^$",
        f"-test.bench={benchmark_name}",
        f"-test.benchtime={bench_time}",
        f"-test.count={count}",
        "-test.timeout=0",
    ]

    # Give the child process the output file directly. Only timing stderr is
    # held temporarily because that is where the Go runtime reports allocation failure.
    with output_file.open("a") as benchmark_output:
        result = subprocess.run(
            command,
            stdout=benchmark_output,
            stderr=subprocess.PIPE if record_oom else subprocess.DEVNULL,
            text=True,
        )

    if record_oom and is_out_of_memory(result.returncode, result.stderr or ""):
        record_out_of_memory(operation, group, sweep_value)


# ---------------------------------------------------------------------------
# Benchmark phases
# ---------------------------------------------------------------------------


def run_timing_benchmarks():

    print("Phase 1 of 2 - Envelope serialization")

    for attribute_count in ATTRIBUTE_COUNTS:

        run_benchmark(
            "Serialize",
            "JSON",
            attribute_count,
            None,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
            record_oom=True,
        )

        run_benchmark(
            "Serialize",
            "CBOR",
            attribute_count,
            None,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
            record_oom=True,
        )

        run_benchmark(
            "Serialize",
            "CBORKeyAsInt",
            attribute_count,
            None,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
            record_oom=True,
        )

    print("Phase 2 of 2 - Envelope deserialization")

    for attribute_count in ATTRIBUTE_COUNTS:

        run_benchmark(
            "Deserialize",
            "JSON",
            attribute_count,
            None,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
            record_oom=True,
        )

        run_benchmark(
            "Deserialize",
            "CBOR",
            attribute_count,
            None,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
            record_oom=True,
        )

        run_benchmark(
            "Deserialize",
            "CBORKeyAsInt",
            attribute_count,
            None,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
            record_oom=True,
        )


def generate_report():

    print("Generating JSON/CBOR Serialization HTML report...")

    # Use the same interpreter as the orchestrator and execute the report as a module.
    subprocess.run(
        [sys.executable, "-m", "report.analysis.json_cbor_report"],
        cwd=PROJECT_DIRECTORY,
        check=True,
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def main():

    load_environment_variables()
    build_binaries()

    prepare_output_directories()

    run_timing_benchmarks()

    generate_report()


if __name__ == "__main__":
    main()