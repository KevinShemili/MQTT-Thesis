import os
from pathlib import Path
from typing import cast

import numpy as np
from scipy import stats

from report.config import *
from report.model.benchmark_summary import *
from report.model.case_aggregation import *
from report.model.measurement import *
from report.model.populate_model import *
from report.render.chart import *
from report.render.formatting import *
from report.render.html import *

NO_MEASUREMENT = float("nan")

SCENARIO = "payload-scaling"
HTML_TEMPLATE_NAME = "payload_scaling_template.html"

LATENCY_PLOT = "plot.png"
THROUGHPUT_PLOT = "throughput.png"

BENCHMARK_PREFIX = "BenchmarkPayloadScaling"


def collect_aggregations(
    results: BenchmarkSummary,
    payload_sizes: list[int],
) -> tuple[
    list[CaseAggregation],
    list[CaseAggregation],
    list[CaseAggregation],
    list[CaseAggregation],
    list[CaseAggregation],
    list[CaseAggregation],
]:
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

    return (
        psk_encrypt,
        psk_decrypt,
        rsa_encrypt,
        rsa_decrypt,
        cpabe_encrypt,
        cpabe_decrypt,
    )


def analyze_aggregations(
    psk_encrypt: list[CaseAggregation],
    psk_decrypt: list[CaseAggregation],
    rsa_encrypt: list[CaseAggregation],
    rsa_decrypt: list[CaseAggregation],
    cpabe_encrypt: list[CaseAggregation],
    cpabe_decrypt: list[CaseAggregation],
    payload_sizes: list[int],
) -> tuple[
    list[float | None] | list[int | None],
    ...,
]:
    psk_encrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in psk_encrypt
    ]
    psk_encrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in psk_encrypt
    ]
    psk_encrypt_throughput_list = [
        None if aggregation.out_of_memory else aggregation.mean(MB_PER_SECOND)
        for aggregation in psk_encrypt
    ]
    psk_encrypt_throughput_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(MB_PER_SECOND)
        )
        for aggregation in psk_encrypt
    ]
    psk_encrypt_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in psk_encrypt
    ]

    psk_decrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in psk_decrypt
    ]
    psk_decrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in psk_decrypt
    ]
    psk_decrypt_throughput_list = [
        None if aggregation.out_of_memory else aggregation.mean(MB_PER_SECOND)
        for aggregation in psk_decrypt
    ]
    psk_decrypt_throughput_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(MB_PER_SECOND)
        )
        for aggregation in psk_decrypt
    ]
    psk_decrypt_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in psk_decrypt
    ]

    psk_completed_overheads = [
        aggregation.mean(WIRE_OVERHEAD_BYTES)
        for aggregation in psk_encrypt
        if not aggregation.out_of_memory
    ]
    if psk_completed_overheads:
        psk_overhead_bytes = int(round(np.mean(psk_completed_overheads)))
        psk_wire_size_list = [
            payload_size + psk_overhead_bytes for payload_size in payload_sizes
        ]
        psk_overhead_percent_list = [
            psk_overhead_bytes / payload_size * 100.0 for payload_size in payload_sizes
        ]
    else:
        psk_wire_size_list = [None] * len(payload_sizes)
        psk_overhead_percent_list = [None] * len(payload_sizes)

    rsa_encrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in rsa_encrypt
    ]
    rsa_encrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in rsa_encrypt
    ]
    rsa_encrypt_throughput_list = [
        None if aggregation.out_of_memory else aggregation.mean(MB_PER_SECOND)
        for aggregation in rsa_encrypt
    ]
    rsa_encrypt_throughput_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(MB_PER_SECOND)
        )
        for aggregation in rsa_encrypt
    ]
    rsa_encrypt_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in rsa_encrypt
    ]

    rsa_decrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in rsa_decrypt
    ]
    rsa_decrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in rsa_decrypt
    ]
    rsa_decrypt_throughput_list = [
        None if aggregation.out_of_memory else aggregation.mean(MB_PER_SECOND)
        for aggregation in rsa_decrypt
    ]
    rsa_decrypt_throughput_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(MB_PER_SECOND)
        )
        for aggregation in rsa_decrypt
    ]
    rsa_decrypt_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in rsa_decrypt
    ]

    rsa_completed_overheads = [
        aggregation.mean(WIRE_OVERHEAD_BYTES)
        for aggregation in rsa_encrypt
        if not aggregation.out_of_memory
    ]
    if rsa_completed_overheads:
        rsa_overhead_bytes = int(round(np.mean(rsa_completed_overheads)))
        rsa_wire_size_list = [
            payload_size + rsa_overhead_bytes for payload_size in payload_sizes
        ]
        rsa_overhead_percent_list = [
            rsa_overhead_bytes / payload_size * 100.0 for payload_size in payload_sizes
        ]
    else:
        rsa_wire_size_list = [None] * len(payload_sizes)
        rsa_overhead_percent_list = [None] * len(payload_sizes)

    cpabe_encrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in cpabe_encrypt
    ]
    cpabe_encrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in cpabe_encrypt
    ]
    cpabe_encrypt_throughput_list = [
        None if aggregation.out_of_memory else aggregation.mean(MB_PER_SECOND)
        for aggregation in cpabe_encrypt
    ]
    cpabe_encrypt_throughput_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(MB_PER_SECOND)
        )
        for aggregation in cpabe_encrypt
    ]
    cpabe_encrypt_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in cpabe_encrypt
    ]

    cpabe_decrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in cpabe_decrypt
    ]
    cpabe_decrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in cpabe_decrypt
    ]
    cpabe_decrypt_throughput_list = [
        None if aggregation.out_of_memory else aggregation.mean(MB_PER_SECOND)
        for aggregation in cpabe_decrypt
    ]
    cpabe_decrypt_throughput_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(MB_PER_SECOND)
        )
        for aggregation in cpabe_decrypt
    ]
    cpabe_decrypt_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in cpabe_decrypt
    ]

    cpabe_completed_overheads = [
        aggregation.mean(WIRE_OVERHEAD_BYTES)
        for aggregation in cpabe_encrypt
        if not aggregation.out_of_memory
    ]
    if cpabe_completed_overheads:
        cpabe_overhead_bytes = int(round(np.mean(cpabe_completed_overheads)))
        cpabe_wire_size_list = [
            payload_size + cpabe_overhead_bytes for payload_size in payload_sizes
        ]
        cpabe_overhead_percent_list = [
            cpabe_overhead_bytes / payload_size * 100.0
            for payload_size in payload_sizes
        ]
    else:
        cpabe_wire_size_list = [None] * len(payload_sizes)
        cpabe_overhead_percent_list = [None] * len(payload_sizes)

    return (
        psk_encrypt_latency_list,
        psk_encrypt_latency_ci_list,
        psk_encrypt_throughput_list,
        psk_encrypt_throughput_ci_list,
        psk_encrypt_iteration_list,
        psk_decrypt_latency_list,
        psk_decrypt_latency_ci_list,
        psk_decrypt_throughput_list,
        psk_decrypt_throughput_ci_list,
        psk_decrypt_iteration_list,
        psk_wire_size_list,
        psk_overhead_percent_list,
        rsa_encrypt_latency_list,
        rsa_encrypt_latency_ci_list,
        rsa_encrypt_throughput_list,
        rsa_encrypt_throughput_ci_list,
        rsa_encrypt_iteration_list,
        rsa_decrypt_latency_list,
        rsa_decrypt_latency_ci_list,
        rsa_decrypt_throughput_list,
        rsa_decrypt_throughput_ci_list,
        rsa_decrypt_iteration_list,
        rsa_wire_size_list,
        rsa_overhead_percent_list,
        cpabe_encrypt_latency_list,
        cpabe_encrypt_latency_ci_list,
        cpabe_encrypt_throughput_list,
        cpabe_encrypt_throughput_ci_list,
        cpabe_encrypt_iteration_list,
        cpabe_decrypt_latency_list,
        cpabe_decrypt_latency_ci_list,
        cpabe_decrypt_throughput_list,
        cpabe_decrypt_throughput_ci_list,
        cpabe_decrypt_iteration_list,
        cpabe_wire_size_list,
        cpabe_overhead_percent_list,
    )


def main() -> None:
    runs = parse_int_env("PAYLOAD_SCALING_RUNS")
    payload_sizes = parse_int_list_env("PAYLOAD_SCALING_PAYLOAD_SIZES")

    result_dir = Path(
        os.environ.get(
            "PAYLOAD_SCALING_RESULT_DIR", f"{DEFAULT_RESULT_ROOT}/{SCENARIO}"
        )
    )
    bench_output = result_dir / BENCH_OUTPUT_NAME
    case_status = result_dir / CASE_STATUS_NAME
    template_path = Path(TEMPLATE_DIR) / HTML_TEMPLATE_NAME
    report_path = result_dir / REPORT_NAME

    results = BenchmarkSummary()
    load_results(results, str(bench_output), BENCHMARK_PREFIX, "B")
    load_out_of_memory_status(results, str(case_status))

    (
        psk_encrypt,
        psk_decrypt,
        rsa_encrypt,
        rsa_decrypt,
        cpabe_encrypt,
        cpabe_decrypt,
    ) = collect_aggregations(results, payload_sizes)

    (
        psk_encrypt_latency_list,
        psk_encrypt_latency_ci_list,
        psk_encrypt_throughput_list,
        psk_encrypt_throughput_ci_list,
        psk_encrypt_iteration_list,
        psk_decrypt_latency_list,
        psk_decrypt_latency_ci_list,
        psk_decrypt_throughput_list,
        psk_decrypt_throughput_ci_list,
        psk_decrypt_iteration_list,
        psk_wire_size_list,
        psk_overhead_percent_list,
        rsa_encrypt_latency_list,
        rsa_encrypt_latency_ci_list,
        rsa_encrypt_throughput_list,
        rsa_encrypt_throughput_ci_list,
        rsa_encrypt_iteration_list,
        rsa_decrypt_latency_list,
        rsa_decrypt_latency_ci_list,
        rsa_decrypt_throughput_list,
        rsa_decrypt_throughput_ci_list,
        rsa_decrypt_iteration_list,
        rsa_wire_size_list,
        rsa_overhead_percent_list,
        cpabe_encrypt_latency_list,
        cpabe_encrypt_latency_ci_list,
        cpabe_encrypt_throughput_list,
        cpabe_encrypt_throughput_ci_list,
        cpabe_encrypt_iteration_list,
        cpabe_decrypt_latency_list,
        cpabe_decrypt_latency_ci_list,
        cpabe_decrypt_throughput_list,
        cpabe_decrypt_throughput_ci_list,
        cpabe_decrypt_iteration_list,
        cpabe_wire_size_list,
        cpabe_overhead_percent_list,
    ) = analyze_aggregations(
        psk_encrypt,
        psk_decrypt,
        rsa_encrypt,
        rsa_decrypt,
        cpabe_encrypt,
        cpabe_decrypt,
        payload_sizes,
    )

    total_benchmark_iterations = sum(
        aggregation.iterations
        for aggregation in results.aggregations
        if not aggregation.out_of_memory
    )
    out_of_memory_aggregations = [
        aggregation for aggregation in results.aggregations if aggregation.out_of_memory
    ]

    plot_payload_scaling_latency(
        payload_sizes,
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in psk_encrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in psk_encrypt_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in rsa_encrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in rsa_encrypt_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in cpabe_encrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in cpabe_encrypt_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in psk_decrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in psk_decrypt_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in rsa_decrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in rsa_decrypt_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in cpabe_decrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in cpabe_decrypt_latency_ci_list
        ],
        str(result_dir / LATENCY_PLOT),
    )

    plot_payload_scaling_throughput(
        payload_sizes,
        [
            NO_MEASUREMENT if value is None else value
            for value in psk_encrypt_throughput_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in psk_encrypt_throughput_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in rsa_encrypt_throughput_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in rsa_encrypt_throughput_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in cpabe_encrypt_throughput_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in cpabe_encrypt_throughput_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in psk_decrypt_throughput_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in psk_decrypt_throughput_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in rsa_decrypt_throughput_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in rsa_decrypt_throughput_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in cpabe_decrypt_throughput_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in cpabe_decrypt_throughput_ci_list
        ],
        str(result_dir / THROUGHPUT_PLOT),
    )

    write_payload_scaling_report(
        runs=runs,
        t_multiplier=float(stats.t.ppf(0.975, runs - 1)),
        total_iterations=total_benchmark_iterations,
        payload_sizes=payload_sizes,
        psk_wire_sizes=psk_wire_size_list,
        psk_overhead_percents=psk_overhead_percent_list,
        rsa_wire_sizes=rsa_wire_size_list,
        rsa_overhead_percents=rsa_overhead_percent_list,
        cpabe_wire_sizes=cpabe_wire_size_list,
        cpabe_overhead_percents=cpabe_overhead_percent_list,
        psk_encrypt_latency_means=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in psk_encrypt_latency_list
        ],
        psk_encrypt_latency_cis=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in psk_encrypt_latency_ci_list
        ],
        psk_encrypt_throughput_means=psk_encrypt_throughput_list,
        psk_encrypt_throughput_cis=psk_encrypt_throughput_ci_list,
        psk_encrypt_iterations=psk_encrypt_iteration_list,
        psk_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", "PSK", payload_sizes
        ),
        rsa_encrypt_latency_means=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in rsa_encrypt_latency_list
        ],
        rsa_encrypt_latency_cis=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in rsa_encrypt_latency_ci_list
        ],
        rsa_encrypt_throughput_means=rsa_encrypt_throughput_list,
        rsa_encrypt_throughput_cis=rsa_encrypt_throughput_ci_list,
        rsa_encrypt_iterations=rsa_encrypt_iteration_list,
        rsa_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", "RSA", payload_sizes
        ),
        cpabe_encrypt_latency_means=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in cpabe_encrypt_latency_list
        ],
        cpabe_encrypt_latency_cis=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in cpabe_encrypt_latency_ci_list
        ],
        cpabe_encrypt_throughput_means=cpabe_encrypt_throughput_list,
        cpabe_encrypt_throughput_cis=cpabe_encrypt_throughput_ci_list,
        cpabe_encrypt_iterations=cpabe_encrypt_iteration_list,
        cpabe_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", "CPABE", payload_sizes
        ),
        psk_decrypt_latency_means=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in psk_decrypt_latency_list
        ],
        psk_decrypt_latency_cis=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in psk_decrypt_latency_ci_list
        ],
        psk_decrypt_throughput_means=psk_decrypt_throughput_list,
        psk_decrypt_throughput_cis=psk_decrypt_throughput_ci_list,
        psk_decrypt_iterations=psk_decrypt_iteration_list,
        psk_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", "PSK", payload_sizes
        ),
        rsa_decrypt_latency_means=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in rsa_decrypt_latency_list
        ],
        rsa_decrypt_latency_cis=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in rsa_decrypt_latency_ci_list
        ],
        rsa_decrypt_throughput_means=rsa_decrypt_throughput_list,
        rsa_decrypt_throughput_cis=rsa_decrypt_throughput_ci_list,
        rsa_decrypt_iterations=rsa_decrypt_iteration_list,
        rsa_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", "RSA", payload_sizes
        ),
        cpabe_decrypt_latency_means=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in cpabe_decrypt_latency_list
        ],
        cpabe_decrypt_latency_cis=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in cpabe_decrypt_latency_ci_list
        ],
        cpabe_decrypt_throughput_means=cpabe_decrypt_throughput_list,
        cpabe_decrypt_throughput_cis=cpabe_decrypt_throughput_ci_list,
        cpabe_decrypt_iterations=cpabe_decrypt_iteration_list,
        cpabe_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", "CPABE", payload_sizes
        ),
        out_of_memory_operations=[
            aggregation.operation for aggregation in out_of_memory_aggregations
        ],
        out_of_memory_cases=[
            f"{aggregation.parameter}/{aggregation.parameter_value}"
            for aggregation in out_of_memory_aggregations
        ],
        latency_plot=LATENCY_PLOT,
        throughput_plot=THROUGHPUT_PLOT,
        template_path=str(template_path),
        report_path=str(report_path),
    )


if __name__ == "__main__":
    main()
