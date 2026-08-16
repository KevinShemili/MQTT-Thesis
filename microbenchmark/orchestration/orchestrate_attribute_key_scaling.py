import os
import shutil
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

RESULT_DIRECTORY = Path("/results/attribute-key-scaling")

OUTPUT_FILE = RESULT_DIRECTORY / "bench_output.txt"
MEMORY_OUTPUT_FILE = RESULT_DIRECTORY / "memory_output.txt"
STATUS_FILE = RESULT_DIRECTORY / "case_status.txt"
LOG_DIRECTORY = RESULT_DIRECTORY / "case_logs"

BENCHMARK_BINARY = "./benchmark-binary"
PROVISION_BINARY = "./provision-binary"
REPORT_SCRIPT = "src/attribute_key_scaling_report.py"


# ---------------------------------------------------------------------------
# Benchmark configuration
# ---------------------------------------------------------------------------

ATTRIBUTE_COUNTS = os.environ["ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT"].split(",")
SUBSCRIBER_COUNTS = os.environ["ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT"].split(",")
RSA_KEY_SIZES = os.environ["ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES"].split(",")

BENCHMARK_RUNS = int(os.environ["ATTRIBUTE_KEY_SCALING_RUNS"])
KEYGEN_RUNS = int(os.environ["ATTRIBUTE_KEY_SCALING_KEYGEN_RUNS"])

CACHE_DIRECTORY = Path(os.environ["CACHE_DIRECTORY"])


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def prepare_output_directories():

    # Start every benchmark suite from an empty fixture cache and clean log directory.
    if CACHE_DIRECTORY.exists():
        shutil.rmtree(CACHE_DIRECTORY)

    if LOG_DIRECTORY.exists():
        shutil.rmtree(LOG_DIRECTORY)

    RESULT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)

    # Previous benchmark results must not leak into the new run.
    OUTPUT_FILE.write_text("")
    MEMORY_OUTPUT_FILE.write_text("")

    STATUS_FILE.write_text("# operation group sweep_value sample exit_code log_file\n")


# ---------------------------------------------------------------------------
# Process execution
# ---------------------------------------------------------------------------


def record_status(operation, group, sweep_value, sample, exit_code, log_file):

    with STATUS_FILE.open("a") as status:
        status.write(
            f"{operation} "
            f"{group} "
            f"{sweep_value} "
            f"{sample} "
            f"{exit_code} "
            f"{log_file}\n"
        )


def run_benchmark(
    operation,
    group,
    sweep_value,
    sample,
    output_file,
    bench_time,
    count,
):
    """
    Run one exact Go benchmark case in its own process.

    Benchmark output is appended to the experiment output file.
    Errors are kept separately so a failed or OOM-killed case can be
    attributed to the exact operation and sweep point that produced it.
    """

    log_file = f"{operation}-{group}-{sweep_value}-{sample}.log"
    log_path = LOG_DIRECTORY / log_file

    print(f"  {operation} {group}/{sweep_value} #{sample}")

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

    # Give the child process the output files directly. This avoids holding
    # potentially large benchmark output in Python memory.
    with output_file.open("a") as benchmark_output:
        with log_path.open("w") as benchmark_log:

            result = subprocess.run(
                command,
                stdout=benchmark_output,
                stderr=benchmark_log,
            )

    record_status(
        operation,
        group,
        sweep_value,
        sample,
        result.returncode,
        log_file,
    )


def run_provision(group, sweep_value):
    """
    Build the cached prerequisites required by one peak-memory case.

    Provisioning runs in a separate process so expensive fixture creation
    cannot contaminate the memory process that will later be measured.
    """

    log_file = f"Provision-{group}-{sweep_value}-1.log"
    log_path = LOG_DIRECTORY / log_file

    print(f"  Provision {group}/{sweep_value}")

    command = [
        PROVISION_BINARY,
        group,
        str(sweep_value),
    ]

    # Provisioning has no benchmark output of its own, so both stdout and
    # stderr are kept together in the case log.
    with log_path.open("w") as provision_log:

        result = subprocess.run(
            command,
            stdout=provision_log,
            stderr=subprocess.STDOUT,
        )

    record_status(
        "Provision",
        group,
        sweep_value,
        1,
        result.returncode,
        log_file,
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
            1,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
        )

        run_benchmark(
            "Decrypt",
            "CPABEAttributes",
            attribute_count,
            1,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
        )

    print("Phase 2 of 4 - RSA subscriber and key-size scaling")

    # Recipient count affects publisher-side RSA work only.
    for subscriber_count in SUBSCRIBER_COUNTS:

        run_benchmark(
            "Encrypt",
            "RSASubscribers",
            subscriber_count,
            1,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
        )

    for rsa_key_size in RSA_KEY_SIZES:

        run_benchmark(
            "Encrypt",
            "RSAKeyBits",
            rsa_key_size,
            1,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
        )

        run_benchmark(
            "Decrypt",
            "RSAKeyBits",
            rsa_key_size,
            1,
            OUTPUT_FILE,
            "5s",
            BENCHMARK_RUNS,
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
            1,
            OUTPUT_FILE,
            "1x",
            KEYGEN_RUNS,
        )


def run_memory_benchmarks():

    print("Phase 4 of 4 - Peak process memory")

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

    subprocess.run(
        ["python3", REPORT_SCRIPT],
        check=True,
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def main():

    prepare_output_directories()

    run_timing_benchmarks()
    run_key_generation_benchmarks()
    run_memory_benchmarks()

    generate_report()


if __name__ == "__main__":
    main()
