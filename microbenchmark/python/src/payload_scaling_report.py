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

SCENARIO = "payload-scaling"
HTML_TEMPLATE_NAME = "payload_scaling_template.html"

LATENCY_PLOT = "plot.png"
THROUGHPUT_PLOT = "throughput.png"

BENCHMARK_PREFIX = "BenchmarkPayloadScaling"


def main() -> None:
    runs = parse_int_env("PAYLOAD_SCALING_RUNS")
    payload_sizes = parse_int_list_env("PAYLOAD_SCALING_PAYLOAD_SIZES")

    result_dir = Path(
        os.environ.get(
            "PAYLOAD_SCALING_RESULT_DIR", f"{DEFAULT_RESULT_ROOT}/{SCENARIO}"
        )
    )
    bench_output = result_dir / BENCH_OUTPUT_NAME
    template_path = Path(TEMPLATE_DIR) / HTML_TEMPLATE_NAME
    report_path = result_dir / REPORT_NAME

    # Create object and load benchmark results into it
    results = BenchmarkSummary()
    load_results(results, str(bench_output), BENCHMARK_PREFIX, "B")

    psk_encrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Encrypt", "PSK", payload_size),
        )
        for payload_size in payload_sizes
    ]
    psk_decrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Decrypt", "PSK", payload_size),
        )
        for payload_size in payload_sizes
    ]

    rsa_encrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Encrypt", "RSA", payload_size),
        )
        for payload_size in payload_sizes
    ]
    rsa_decrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Decrypt", "RSA", payload_size),
        )
        for payload_size in payload_sizes
    ]

    cpabe_encrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Encrypt", "CPABE", payload_size),
        )
        for payload_size in payload_sizes
    ]
    cpabe_decrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Decrypt", "CPABE", payload_size),
        )
        for payload_size in payload_sizes
    ]

    # PSK Calculations
    # 1. Latency of Encrypt and Decrypt
    psk_encrypt_latency_list = [
        aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND for aggregation in psk_encrypt
    ]
    psk_encrypt_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in psk_encrypt
    ]
    psk_decrypt_latency_list = [
        aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND for aggregation in psk_decrypt
    ]
    psk_decrypt_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in psk_decrypt
    ]
    # 2. Throughput of Encrypt and Decrypt
    psk_encrypt_throughput_list = [
        aggregation.mean(MB_PER_SECOND) for aggregation in psk_encrypt
    ]
    psk_encrypt_throughput_ci_list = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in psk_encrypt
    ]
    psk_decrypt_throughput_list = [
        aggregation.mean(MB_PER_SECOND) for aggregation in psk_decrypt
    ]
    psk_decrypt_throughput_ci_list = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in psk_decrypt
    ]
    # 3. Fixed Wire Overhead
    psk_overhead_value_list = [
        aggregation.mean(WIRE_OVERHEAD_BYTES) for aggregation in psk_encrypt
    ]
    psk_overhead_byte_list = int(round(mean(psk_overhead_value_list)))
    psk_wire_size_list = [
        payload_size + psk_overhead_byte_list for payload_size in payload_sizes
    ]
    psk_overhead_percent_list = [
        psk_overhead_byte_list / payload_size * 100.0 for payload_size in payload_sizes
    ]
    # 4. Iterations of Encrypt and Decrypt
    psk_encrypt_iteration_list = [aggregation.iterations for aggregation in psk_encrypt]
    psk_decrypt_iteration_list = [aggregation.iterations for aggregation in psk_decrypt]

    # 5. Throttle Check of Encrypt and Decrypt
    psk_encrypt_throttled_list = results.get_throttle_flags(
        "Encrypt", "PSK", payload_sizes
    )
    psk_decrypt_throttled_list = results.get_throttle_flags(
        "Decrypt", "PSK", payload_sizes
    )

    # RSA Calculations
    # 1. Latency of Encrypt and Decrypt
    rsa_encrypt_latency_list = [
        aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND for aggregation in rsa_encrypt
    ]
    rsa_encrypt_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in rsa_encrypt
    ]
    rsa_decrypt_latency_list = [
        aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND for aggregation in rsa_decrypt
    ]
    rsa_decrypt_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in rsa_decrypt
    ]
    # 2. Throughput of Encrypt and Decrypt
    rsa_encrypt_throughput_list = [
        aggregation.mean(MB_PER_SECOND) for aggregation in rsa_encrypt
    ]
    rsa_encrypt_throughput_ci_list = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in rsa_encrypt
    ]
    rsa_decrypt_throughput_list = [
        aggregation.mean(MB_PER_SECOND) for aggregation in rsa_decrypt
    ]
    rsa_decrypt_throughput_ci_list = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in rsa_decrypt
    ]
    # 3. Fixed Wire Overhead
    rsa_overhead_value_list = [
        aggregation.mean(WIRE_OVERHEAD_BYTES) for aggregation in rsa_encrypt
    ]
    rsa_overhead_byte_list = int(round(mean(rsa_overhead_value_list)))
    rsa_wire_size_list = [
        payload_size + rsa_overhead_byte_list for payload_size in payload_sizes
    ]
    rsa_overhead_percent_list = [
        rsa_overhead_byte_list / payload_size * 100.0 for payload_size in payload_sizes
    ]
    # 4. Iterations of Encrypt and Decrypt
    rsa_encrypt_iteration_list = [aggregation.iterations for aggregation in rsa_encrypt]
    rsa_decrypt_iteration_list = [aggregation.iterations for aggregation in rsa_decrypt]
    # 5. Throttle Check of Encrypt and Decrypt
    rsa_encrypt_throttled_list = results.get_throttle_flags(
        "Encrypt", "RSA", payload_sizes
    )
    rsa_decrypt_throttled_list = results.get_throttle_flags(
        "Decrypt", "RSA", payload_sizes
    )

    # CP-ABE Calculations
    # 1. Latency of Encrypt and Decrypt
    cpabe_encrypt_latency_list = [
        aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in cpabe_encrypt
    ]
    cpabe_encrypt_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in cpabe_encrypt
    ]
    cpabe_decrypt_latency_list = [
        aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in cpabe_decrypt
    ]
    cpabe_decrypt_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in cpabe_decrypt
    ]
    # 2. Throughput of Encrypt and Decrypt
    cpabe_encrypt_throughput_list = [
        aggregation.mean(MB_PER_SECOND) for aggregation in cpabe_encrypt
    ]
    cpabe_encrypt_throughput_ci_list = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in cpabe_encrypt
    ]
    cpabe_decrypt_throughput_list = [
        aggregation.mean(MB_PER_SECOND) for aggregation in cpabe_decrypt
    ]
    cpabe_decrypt_throughput_ci_list = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in cpabe_decrypt
    ]
    # 3. Fixed Wire Overhead
    cpabe_overhead_value_list = [
        aggregation.mean(WIRE_OVERHEAD_BYTES) for aggregation in cpabe_encrypt
    ]
    cpabe_overhead_byte_list = int(round(mean(cpabe_overhead_value_list)))
    cpabe_wire_size_list = [
        payload_size + cpabe_overhead_byte_list for payload_size in payload_sizes
    ]
    cpabe_overhead_percent_list = [
        cpabe_overhead_byte_list / payload_size * 100.0
        for payload_size in payload_sizes
    ]
    # 4. Iterations of Encrypt and Decrypt
    cpabe_encrypt_iteration_list = [
        aggregation.iterations for aggregation in cpabe_encrypt
    ]
    cpabe_decrypt_iteration_list = [
        aggregation.iterations for aggregation in cpabe_decrypt
    ]
    # 5. Throttle Check of Encrypt and Decrypt
    cpabe_encrypt_throttled_list = results.get_throttle_flags(
        "Encrypt", "CPABE", payload_sizes
    )
    cpabe_decrypt_throttled_list = results.get_throttle_flags(
        "Decrypt", "CPABE", payload_sizes
    )

    # Total Benchmark Iterations
    total_benchmark_iterations = sum(
        aggregation.iterations for aggregation in results.aggregations
    )

    # Generate the latency graph
    plot_payload_scaling_latency(
        payload_sizes,
        psk_encrypt_latency_list,
        psk_encrypt_latency_ci_list,
        rsa_encrypt_latency_list,
        rsa_encrypt_latency_ci_list,
        cpabe_encrypt_latency_list,
        cpabe_encrypt_latency_ci_list,
        psk_decrypt_latency_list,
        psk_decrypt_latency_ci_list,
        rsa_decrypt_latency_list,
        rsa_decrypt_latency_ci_list,
        cpabe_decrypt_latency_list,
        cpabe_decrypt_latency_ci_list,
        str(result_dir / LATENCY_PLOT),
    )

    # Generate the throughput graph
    plot_payload_scaling_throughput(
        payload_sizes,
        psk_encrypt_throughput_list,
        psk_encrypt_throughput_ci_list,
        rsa_encrypt_throughput_list,
        rsa_encrypt_throughput_ci_list,
        cpabe_encrypt_throughput_list,
        cpabe_encrypt_throughput_ci_list,
        psk_decrypt_throughput_list,
        psk_decrypt_throughput_ci_list,
        rsa_decrypt_throughput_list,
        rsa_decrypt_throughput_ci_list,
        cpabe_decrypt_throughput_list,
        cpabe_decrypt_throughput_ci_list,
        str(result_dir / THROUGHPUT_PLOT),
    )

    # Write HTML
    write_payload_scaling_report(
        runs=runs,
        t_multiplier=get_student_t_critical_95(runs - 1),
        total_iterations=total_benchmark_iterations,
        payload_sizes=payload_sizes,
        psk_wire_sizes=psk_wire_size_list,
        psk_overhead_percents=psk_overhead_percent_list,
        rsa_wire_sizes=rsa_wire_size_list,
        rsa_overhead_percents=rsa_overhead_percent_list,
        cpabe_wire_sizes=cpabe_wire_size_list,
        cpabe_overhead_percents=cpabe_overhead_percent_list,
        psk_encrypt_latency_means=psk_encrypt_latency_list,
        psk_encrypt_latency_cis=psk_encrypt_latency_ci_list,
        psk_encrypt_throughput_means=psk_encrypt_throughput_list,
        psk_encrypt_throughput_cis=psk_encrypt_throughput_ci_list,
        psk_encrypt_iterations=psk_encrypt_iteration_list,
        psk_encrypt_throttled=psk_encrypt_throttled_list,
        rsa_encrypt_latency_means=rsa_encrypt_latency_list,
        rsa_encrypt_latency_cis=rsa_encrypt_latency_ci_list,
        rsa_encrypt_throughput_means=rsa_encrypt_throughput_list,
        rsa_encrypt_throughput_cis=rsa_encrypt_throughput_ci_list,
        rsa_encrypt_iterations=rsa_encrypt_iteration_list,
        rsa_encrypt_throttled=rsa_encrypt_throttled_list,
        cpabe_encrypt_latency_means=cpabe_encrypt_latency_list,
        cpabe_encrypt_latency_cis=cpabe_encrypt_latency_ci_list,
        cpabe_encrypt_throughput_means=cpabe_encrypt_throughput_list,
        cpabe_encrypt_throughput_cis=cpabe_encrypt_throughput_ci_list,
        cpabe_encrypt_iterations=cpabe_encrypt_iteration_list,
        cpabe_encrypt_throttled=cpabe_encrypt_throttled_list,
        psk_decrypt_latency_means=psk_decrypt_latency_list,
        psk_decrypt_latency_cis=psk_decrypt_latency_ci_list,
        psk_decrypt_throughput_means=psk_decrypt_throughput_list,
        psk_decrypt_throughput_cis=psk_decrypt_throughput_ci_list,
        psk_decrypt_iterations=psk_decrypt_iteration_list,
        psk_decrypt_throttled=psk_decrypt_throttled_list,
        rsa_decrypt_latency_means=rsa_decrypt_latency_list,
        rsa_decrypt_latency_cis=rsa_decrypt_latency_ci_list,
        rsa_decrypt_throughput_means=rsa_decrypt_throughput_list,
        rsa_decrypt_throughput_cis=rsa_decrypt_throughput_ci_list,
        rsa_decrypt_iterations=rsa_decrypt_iteration_list,
        rsa_decrypt_throttled=rsa_decrypt_throttled_list,
        cpabe_decrypt_latency_means=cpabe_decrypt_latency_list,
        cpabe_decrypt_latency_cis=cpabe_decrypt_latency_ci_list,
        cpabe_decrypt_throughput_means=cpabe_decrypt_throughput_list,
        cpabe_decrypt_throughput_cis=cpabe_decrypt_throughput_ci_list,
        cpabe_decrypt_iterations=cpabe_decrypt_iteration_list,
        cpabe_decrypt_throttled=cpabe_decrypt_throttled_list,
        latency_plot=LATENCY_PLOT,
        throughput_plot=THROUGHPUT_PLOT,
        template_path=str(template_path),
        report_path=str(report_path),
    )


if __name__ == "__main__":
    main()
