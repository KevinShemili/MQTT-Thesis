import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Everything is found relative to this file, so no process depends on the directory
# it was started from. orchestration/linux/ is two levels below the suite
MICROBENCHMARK_DIRECTORY = Path(__file__).resolve().parents[2]

ENVIRONMENT_FILE = MICROBENCHMARK_DIRECTORY / "config" / "benchmark.env"
GO_DIRECTORY = MICROBENCHMARK_DIRECTORY / "golang"
BINARY_DIRECTORY = MICROBENCHMARK_DIRECTORY / "bin"
RESULT_DIRECTORY = MICROBENCHMARK_DIRECTORY / "results" / "attribute-key-scaling"

OUTPUT_FILE = RESULT_DIRECTORY / "bench_output.txt"
MEMORY_OUTPUT_FILE = RESULT_DIRECTORY / "memory_output.txt"
STATUS_FILE = RESULT_DIRECTORY / "case_status.txt"

BENCHMARK_BINARY = str(BINARY_DIRECTORY / "benchmark-binary")
PROVISION_BINARY = str(BINARY_DIRECTORY / "provision-binary")
REPORT_SCRIPT = str(
    MICROBENCHMARK_DIRECTORY / "python" / "src" / "attribute_key_scaling_report.py"
)


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def load_environment_variables():

    global ATTRIBUTE_COUNTS, SUBSCRIBER_COUNTS, RSA_KEY_SIZES
    global BENCHMARK_RUNS, KEYGEN_RUNS, CACHE_DIRECTORY

    load_dotenv(ENVIRONMENT_FILE, override=True)

    # The Go binaries resolve a relative cache directory against the directory they
    # were started from, so it is anchored to the project before either one reads it
    CACHE_DIRECTORY = MICROBENCHMARK_DIRECTORY / os.environ["CACHE_DIRECTORY"]
    os.environ["CACHE_DIRECTORY"] = str(CACHE_DIRECTORY)

    # The report would otherwise look for this run under the results root the
    # container mounted, which is what this override exists for
    os.environ["ATTRIBUTE_KEY_SCALING_RESULT_DIR"] = str(RESULT_DIRECTORY)

    ATTRIBUTE_COUNTS = os.environ["ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT"].split(",")
    SUBSCRIBER_COUNTS = os.environ["ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT"].split(",")
    RSA_KEY_SIZES = os.environ["ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES"].split(",")

    BENCHMARK_RUNS = int(os.environ["ATTRIBUTE_KEY_SCALING_RUNS"])
    KEYGEN_RUNS = int(os.environ["ATTRIBUTE_KEY_SCALING_KEYGEN_RUNS"])


def build_binaries():

    # The image used to compile these ahead of the run, so that a measurement is
    # never attributed to a binary older than the source it is reported against
    print("Building benchmark and provision binaries...")

    BINARY_DIRECTORY.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["go", "test", "-c", "-o", BENCHMARK_BINARY, "./benchmark"],
        cwd=GO_DIRECTORY,
        check=True,
    )

    subprocess.run(
        ["go", "build", "-o", PROVISION_BINARY, "./cmd/provision"],
        cwd=GO_DIRECTORY,
        check=True,
    )


def prepare_output_directories():

    # Start every benchmark suite from an empty fixture cache.
    if CACHE_DIRECTORY.exists():
        shutil.rmtree(CACHE_DIRECTORY)

    RESULT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    # Previous benchmark results must not leak into the new run.
    OUTPUT_FILE.write_text("")
    MEMORY_OUTPUT_FILE.write_text("")

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

    Benchmark output is appended to the experiment output file. Timing and key
    generation cases capture stderr only long enough to detect whole-case OOM.
    """

    sample_label = "" if sample is None else f" #{sample}"
    print(f"  {operation} {group}/{sweep_value}{sample_label}")

    benchmark_name = (
        f"^BenchmarkAttributeKeyScaling{operation}$/" f"^{group}$/" f"^{sweep_value}$"
    )

    command = [
        BENCHMARK_BINARY,
        "-test.run=^$",
        f"-test.bench={benchmark_name}",
        f"-test.benchtime={bench_time}",
        f"-test.count={count}",
        "-test.timeout=0",
    ]

    # Give the child process the output file directly. Only timing/keygen stderr is
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


def run_provision(group, sweep_value):
    """
    Build the cached prerequisites required by one peak-memory case.

    Provisioning runs in a separate process so expensive fixture creation
    cannot contaminate the memory process that will later be measured.
    """

    print(f"  Provision {group}/{sweep_value}")

    command = [
        PROVISION_BINARY,
        group,
        str(sweep_value),
    ]

    subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def run_memory_case(group, sweep_value, has_decrypt):
    """
    Provision one sweep point, then collect independent peak-memory samples.

    Every memory sample launches a fresh benchmark process because VmHWM
    belongs to the process rather than to an individual benchmark loop.
    """

    run_provision(group, sweep_value)

    for sample in range(1, BENCHMARK_RUNS + 1):

        run_benchmark(
            operation="MemoryEncrypt",
            group=group,
            sweep_value=sweep_value,
            sample=sample,
            output_file=MEMORY_OUTPUT_FILE,
            bench_time="1x",
            count=1,
        )

        if has_decrypt:
            run_benchmark(
                operation="MemoryDecrypt",
                group=group,
                sweep_value=sweep_value,
                sample=sample,
                output_file=MEMORY_OUTPUT_FILE,
                bench_time="1x",
                count=1,
            )


# ---------------------------------------------------------------------------
# Benchmark phases
# ---------------------------------------------------------------------------


def run_timing_benchmarks():

    print("Phase 1 of 4 - CP-ABE attribute scaling")

    for attribute_count in ATTRIBUTE_COUNTS:

        run_benchmark(
            "Encrypt",
            "CPABEAttributes",
            attribute_count,
            None,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
            record_oom=True,
        )

        run_benchmark(
            "Decrypt",
            "CPABEAttributes",
            attribute_count,
            None,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
            record_oom=True,
        )

    print("Phase 2 of 4 - RSA subscriber and key-size scaling")

    # Recipient count affects publisher-side RSA work only.
    for subscriber_count in SUBSCRIBER_COUNTS:

        run_benchmark(
            "Encrypt",
            "RSASubscribers",
            subscriber_count,
            None,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
            record_oom=True,
        )

    for rsa_key_size in RSA_KEY_SIZES:

        run_benchmark(
            "Encrypt",
            "RSAKeyBits",
            rsa_key_size,
            None,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
            record_oom=True,
        )

        run_benchmark(
            "Decrypt",
            "RSAKeyBits",
            rsa_key_size,
            None,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
            record_oom=True,
        )


def run_key_generation_benchmarks():

    print("Phase 3 of 4 - RSA key generation")

    # Each KeyGen benchmark invocation performs one generation per Go
    # benchmark sample. Repetition is controlled by -test.count.
    for rsa_key_size in RSA_KEY_SIZES:

        run_benchmark(
            "KeyGen",
            "RSAKeyBits",
            rsa_key_size,
            None,
            OUTPUT_FILE,
            "1x",
            KEYGEN_RUNS,
            record_oom=True,
        )


def run_baseline_memory_case():

    for sample in range(1, BENCHMARK_RUNS + 1):

        run_benchmark(
            operation="MemoryBaseline",
            group="Runtime",
            sweep_value=0,
            sample=sample,
            output_file=MEMORY_OUTPUT_FILE,
            bench_time="1x",
            count=1,
        )


def run_memory_benchmarks():

    print("Phase 4 of 4 - Peak process memory")

    run_baseline_memory_case()

    for attribute_count in ATTRIBUTE_COUNTS:
        run_memory_case(
            "CPABEAttributes",
            attribute_count,
            has_decrypt=True,
        )

    # Subscriber count changes publisher encryption work but does not change
    # what one RSA subscriber does during decryption.
    for subscriber_count in SUBSCRIBER_COUNTS:
        run_memory_case(
            "RSASubscribers",
            subscriber_count,
            has_decrypt=False,
        )

    for rsa_key_size in RSA_KEY_SIZES:
        run_memory_case(
            "RSAKeyBits",
            rsa_key_size,
            has_decrypt=True,
        )


def generate_report():

    print("Generating Attribute & Key Scaling HTML report...")

    # The interpreter running the orchestrator is the one that has the reporting
    # dependencies installed, which is not necessarily the one "python3" resolves to
    subprocess.run(
        [sys.executable, REPORT_SCRIPT],
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
    run_key_generation_benchmarks()
    run_memory_benchmarks()

    generate_report()


if __name__ == "__main__":
    main()
