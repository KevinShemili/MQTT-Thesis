import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_DIRECTORY = Path(__file__).resolve().parents[2]

ENVIRONMENT_FILE = PROJECT_DIRECTORY / "environment" / "benchmark.env"

BENCHMARK_DIRECTORY = PROJECT_DIRECTORY / "benchmark"
BINARY_DIRECTORY = PROJECT_DIRECTORY / "bin"
RESULT_DIRECTORY = PROJECT_DIRECTORY / "results" / "aes-ascon" / "with-acceleration"

OUTPUT_FILE = RESULT_DIRECTORY / "bench_output.txt"
STATUS_FILE = RESULT_DIRECTORY / "case_status.txt"

BENCHMARK_BINARY = str(BINARY_DIRECTORY / "benchmark-binary")


def load_environment_variables():

    global PAYLOAD_SIZES, BENCHMARK_RUNS

    load_dotenv(ENVIRONMENT_FILE, override=True)

    # Tell the report exactly where this orchestrator stores its results.
    os.environ["AES_ASCON_RESULT_DIR"] = str(RESULT_DIRECTORY)

    PAYLOAD_SIZES = os.environ["AES_ASCON_PAYLOAD_SIZES"].split(",")
    BENCHMARK_RUNS = int(os.environ["AES_ASCON_RUNS"])


def build_binaries():

    # Always compile immediately before the experiment so benchmark results
    # cannot accidentally come from a binary older than the current source.
    print("Building AES vs ASCON benchmark binary...")

    BINARY_DIRECTORY.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["go", "test", "-c", "-o", BENCHMARK_BINARY, "./micro/aes_ascon"],
        cwd=BENCHMARK_DIRECTORY,
        check=True,
    )


def prepare_output_directories():

    RESULT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    # Previous benchmark results must not leak into the new run.
    OUTPUT_FILE.write_text("")

    STATUS_FILE.write_text(
        "# operation group sweep_value out_of_memory\n"
    )


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
        status.write(
            f"{operation} {group} {sweep_value} true\n"
        )


def run_benchmark(
    operation,
    group,
    sweep_value,
):

    """
    Run one exact AES/ASCON Go benchmark case in its own process.

    Benchmark output is appended to bench_output.txt. Stderr is captured only
    long enough to determine whether the entire benchmark case failed due to
    an out-of-memory condition.
    """

    print(f"  {operation} {group}/{sweep_value}B")

    benchmark_name = (
        f"^BenchmarkAESASCON{operation}$/"
        f"^{group}$/"
        f"^{sweep_value}B$"
    )

    command = [
        BENCHMARK_BINARY,
        "-test.run=^$",
        f"-test.bench={benchmark_name}",
        "-test.benchtime=5s",
        f"-test.count={BENCHMARK_RUNS}",
        "-test.timeout=0",
    ]

    with OUTPUT_FILE.open("a") as benchmark_output:
        result = subprocess.run(
            command,
            stdout=benchmark_output,
            stderr=subprocess.PIPE,
            text=True,
        )

    if is_out_of_memory(result.returncode, result.stderr or ""):
        record_out_of_memory(operation, group, sweep_value)


# ---------------------------------------------------------------------------
# Benchmark phases
# ---------------------------------------------------------------------------


def run_timing_benchmarks():

    print("Phase 1 of 2 - AES-GCM payload scaling")

    for payload_size in PAYLOAD_SIZES:

        run_benchmark(
            operation="Encrypt",
            group="AES-GCM",
            sweep_value=payload_size,
        )

        run_benchmark(
            operation="Decrypt",
            group="AES-GCM",
            sweep_value=payload_size,
        )

    print("Phase 2 of 2 - ASCON payload scaling")

    for payload_size in PAYLOAD_SIZES:

        run_benchmark(
            operation="Encrypt",
            group="ASCON",
            sweep_value=payload_size,
        )

        run_benchmark(
            operation="Decrypt",
            group="ASCON",
            sweep_value=payload_size,
        )


def generate_report():

    print("Generating AES vs ASCON HTML report...")

    # Use the same interpreter as the orchestrator and execute the report
    # through the report package.
    subprocess.run(
        [sys.executable, "-m", "report.analysis.aes_ascon_report"],
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