import os
from typing import cast
from pathlib import Path

from template_builder.chart import *
from template_builder.formatting import *
from template_builder.html import *

from model.benchmark_summary import *
from model.measurement import *
from model.populate_model import *

from config.environment import *
from statistics_tbd.summary import *

SCENARIO = "aes-ascon"
HTML_TEMPLATE_NAME = "aes_ascon_template.html"

LATENCY_PLOT = "plot.png"
THROUGHPUT_PLOT = "throughput.png"

BENCHMARK_PREFIX = "BenchmarkAESASCON"


def main() -> None:
    runs = parse_int_env("AES_ASCON_RUNS")
    payload_sizes = parse_int_list_env("AES_ASCON_PAYLOAD_SIZES")

    result_dir = Path(
        os.environ.get("AES_ASCON_RESULT_DIR", f"{DEFAULT_RESULT_ROOT}/{SCENARIO}")
    )
    bench_output = result_dir / BENCH_OUTPUT_NAME
    template_path = Path(TEMPLATE_DIR) / HTML_TEMPLATE_NAME
    report_path = result_dir / REPORT_NAME

    # Create object and load benchmark results into it
    results = BenchmarkSummary()
    load_results(results, str(bench_output), BENCHMARK_PREFIX, "B")

    aes_encrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Encrypt", "AES-GCM", payload_size),
        )
        for payload_size in payload_sizes
    ]
    aes_decrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Decrypt", "AES-GCM", payload_size),
        )
        for payload_size in payload_sizes
    ]

    ascon_encrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Encrypt", "ASCON", payload_size),
        )
        for payload_size in payload_sizes
    ]
    ascon_decrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Decrypt", "ASCON", payload_size),
        )
        for payload_size in payload_sizes
    ]

    # AES Calculations
    # 1. Latency of Encrypt and Decrypt
    aes_encrypt_latency_list = [
        aggregation.mean(NS_PER_OP) for aggregation in aes_encrypt
    ]
    aes_encrypt_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in aes_encrypt
    ]
    aes_decrypt_latency_list = [
        aggregation.mean(NS_PER_OP) for aggregation in aes_decrypt
    ]
    aes_decrypt_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in aes_decrypt
    ]
    # 2. Throughput of Encrypt and Decrypt
    aes_encrypt_throughput_list = [
        aggregation.mean(MB_PER_SECOND) for aggregation in aes_encrypt
    ]
    aes_encrypt_throughput_ci_list = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in aes_encrypt
    ]
    aes_decrypt_throughput_list = [
        aggregation.mean(MB_PER_SECOND) for aggregation in aes_decrypt
    ]
    aes_decrypt_throughput_ci_list = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in aes_decrypt
    ]
    # 3. Overhead of Encrypt and Decrypt
    aes_encrypt_overhead_list = [
        aggregation.mean(WIRE_OVERHEAD_BYTES) for aggregation in aes_encrypt
    ]
    aes_decrypt_overhead_list = [
        aggregation.mean(WIRE_OVERHEAD_BYTES) for aggregation in aes_decrypt
    ]
    # 4. Iterations of Encrypt and Decrypt
    aes_encrypt_iterations_list = [
        aggregation.iterations for aggregation in aes_encrypt
    ]
    aes_decrypt_iterations_list = [
        aggregation.iterations for aggregation in aes_decrypt
    ]
    # 5. Throttle Check of Encrypt and Decrypt
    aes_encrypt_throttled_list = results.get_throttle_flags(
        "Encrypt", "AES-GCM", payload_sizes
    )
    aes_decrypt_throttled_list = results.get_throttle_flags(
        "Decrypt", "AES-GCM", payload_sizes
    )

    # ASCON Calculations
    # 1. Latency of Encrypt and Decrypt
    ascon_encrypt_latency_list = [
        aggregation.mean(NS_PER_OP) for aggregation in ascon_encrypt
    ]
    ascon_encrypt_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in ascon_encrypt
    ]
    ascon_decrypt_latency_list = [
        aggregation.mean(NS_PER_OP) for aggregation in ascon_decrypt
    ]
    ascon_decrypt_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in ascon_decrypt
    ]
    # 2. Throughput of Encrypt and Decrypt
    ascon_encrypt_throughput_list = [
        aggregation.mean(MB_PER_SECOND) for aggregation in ascon_encrypt
    ]
    ascon_encrypt_throughput_ci_list = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in ascon_encrypt
    ]
    ascon_decrypt_throughput_list = [
        aggregation.mean(MB_PER_SECOND) for aggregation in ascon_decrypt
    ]
    ascon_decrypt_throughput_ci_list = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in ascon_decrypt
    ]
    # 3. Overhead of Encrypt and Decrypt
    ascon_encrypt_overhead_list = [
        aggregation.mean(WIRE_OVERHEAD_BYTES) for aggregation in ascon_encrypt
    ]
    ascon_decrypt_overhead_list = [
        aggregation.mean(WIRE_OVERHEAD_BYTES) for aggregation in ascon_decrypt
    ]
    # 4. Iterations of Encrypt and Decrypt
    ascon_encrypt_iterations_list = [
        aggregation.iterations for aggregation in ascon_encrypt
    ]
    ascon_decrypt_iterations_list = [
        aggregation.iterations for aggregation in ascon_decrypt
    ]
    # 5. Throttle Check of Encrypt and Decrypt
    ascon_encrypt_throttled_list = results.get_throttle_flags(
        "Encrypt", "ASCON", payload_sizes
    )
    ascon_decrypt_throttled_list = results.get_throttle_flags(
        "Decrypt", "ASCON", payload_sizes
    )

    # Total Benchmark Iterations
    total_benchmark_iterations = sum(
        aggregation.iterations for aggregation in results.aggregations
    )

    # Generate latency plot (Divide by 1000 to convert from ns to us)
    plot_aes_ascon_latency(
        payload_sizes,
        [value / NS_PER_MICROSECOND for value in aes_encrypt_latency_list],
        [value / NS_PER_MICROSECOND for value in aes_encrypt_latency_ci_list],
        [value / NS_PER_MICROSECOND for value in ascon_encrypt_latency_list],
        [value / NS_PER_MICROSECOND for value in ascon_encrypt_latency_ci_list],
        [value / NS_PER_MICROSECOND for value in aes_decrypt_latency_list],
        [value / NS_PER_MICROSECOND for value in aes_decrypt_latency_ci_list],
        [value / NS_PER_MICROSECOND for value in ascon_decrypt_latency_list],
        [value / NS_PER_MICROSECOND for value in ascon_decrypt_latency_ci_list],
        str(result_dir / LATENCY_PLOT),
    )

    # Generate throughput plot (Don't divide by anything, already in MB/s)
    plot_aes_ascon_throughput(
        payload_sizes,
        aes_encrypt_throughput_list,
        aes_encrypt_throughput_ci_list,
        ascon_encrypt_throughput_list,
        ascon_encrypt_throughput_ci_list,
        aes_decrypt_throughput_list,
        aes_decrypt_throughput_ci_list,
        ascon_decrypt_throughput_list,
        ascon_decrypt_throughput_ci_list,
        str(result_dir / THROUGHPUT_PLOT),
    )

    # Write HTML
    write_aes_ascon_report(
        runs=runs,
        t_multiplier=get_student_t_critical_95(runs - 1),
        total_iterations=total_benchmark_iterations,
        payload_sizes=payload_sizes,
        aes_encrypt_latency_means=aes_encrypt_latency_list,
        aes_encrypt_latency_cis=aes_encrypt_latency_ci_list,
        aes_encrypt_throughput_means=aes_encrypt_throughput_list,
        aes_encrypt_throughput_cis=aes_encrypt_throughput_ci_list,
        aes_encrypt_overhead_bytes=aes_encrypt_overhead_list,
        aes_encrypt_iterations=aes_encrypt_iterations_list,
        aes_encrypt_throttled=aes_encrypt_throttled_list,
        ascon_encrypt_latency_means=ascon_encrypt_latency_list,
        ascon_encrypt_latency_cis=ascon_encrypt_latency_ci_list,
        ascon_encrypt_throughput_means=ascon_encrypt_throughput_list,
        ascon_encrypt_throughput_cis=ascon_encrypt_throughput_ci_list,
        ascon_encrypt_overhead_bytes=ascon_encrypt_overhead_list,
        ascon_encrypt_iterations=ascon_encrypt_iterations_list,
        ascon_encrypt_throttled=ascon_encrypt_throttled_list,
        aes_decrypt_latency_means=aes_decrypt_latency_list,
        aes_decrypt_latency_cis=aes_decrypt_latency_ci_list,
        aes_decrypt_throughput_means=aes_decrypt_throughput_list,
        aes_decrypt_throughput_cis=aes_decrypt_throughput_ci_list,
        aes_decrypt_overhead_bytes=aes_decrypt_overhead_list,
        aes_decrypt_iterations=aes_decrypt_iterations_list,
        aes_decrypt_throttled=aes_decrypt_throttled_list,
        ascon_decrypt_latency_means=ascon_decrypt_latency_list,
        ascon_decrypt_latency_cis=ascon_decrypt_latency_ci_list,
        ascon_decrypt_throughput_means=ascon_decrypt_throughput_list,
        ascon_decrypt_throughput_cis=ascon_decrypt_throughput_ci_list,
        ascon_decrypt_overhead_bytes=ascon_decrypt_overhead_list,
        ascon_decrypt_iterations=ascon_decrypt_iterations_list,
        ascon_decrypt_throttled=ascon_decrypt_throttled_list,
        latency_plot=LATENCY_PLOT,
        throughput_plot=THROUGHPUT_PLOT,
        template_path=str(template_path),
        report_path=str(report_path),
    )


if __name__ == "__main__":
    main()
