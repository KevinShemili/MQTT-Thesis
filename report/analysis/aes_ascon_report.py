import os
from pathlib import Path
from typing import cast

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

SCENARIO = "aes-ascon"
HTML_TEMPLATE_NAME = "aes_ascon_template.html"

LATENCY_PLOT = "plot.png"
THROUGHPUT_PLOT = "throughput.png"

BENCHMARK_PREFIX = "BenchmarkAESASCON"


def collect_aggregations(
    results: BenchmarkSummary,
    payload_sizes: list[int],
) -> tuple[
    list[CaseAggregation],
    list[CaseAggregation],
    list[CaseAggregation],
    list[CaseAggregation],
]:
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

    return aes_encrypt, aes_decrypt, ascon_encrypt, ascon_decrypt


def analyze_aggregations(
    aes_encrypt: list[CaseAggregation],
    aes_decrypt: list[CaseAggregation],
    ascon_encrypt: list[CaseAggregation],
    ascon_decrypt: list[CaseAggregation],
) -> tuple[
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[int | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[int | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[int | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[int | None],
]:
    aes_encrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in aes_encrypt
    ]
    aes_encrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in aes_encrypt
    ]
    aes_encrypt_throughput_list = [
        None if aggregation.out_of_memory else aggregation.mean(MB_PER_SECOND)
        for aggregation in aes_encrypt
    ]
    aes_encrypt_throughput_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(MB_PER_SECOND)
        )
        for aggregation in aes_encrypt
    ]
    aes_encrypt_overhead_list = [
        None if aggregation.out_of_memory else aggregation.mean(WIRE_OVERHEAD_BYTES)
        for aggregation in aes_encrypt
    ]
    aes_encrypt_iterations_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in aes_encrypt
    ]

    aes_decrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in aes_decrypt
    ]
    aes_decrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in aes_decrypt
    ]
    aes_decrypt_throughput_list = [
        None if aggregation.out_of_memory else aggregation.mean(MB_PER_SECOND)
        for aggregation in aes_decrypt
    ]
    aes_decrypt_throughput_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(MB_PER_SECOND)
        )
        for aggregation in aes_decrypt
    ]
    aes_decrypt_overhead_list = [
        None if aggregation.out_of_memory else aggregation.mean(WIRE_OVERHEAD_BYTES)
        for aggregation in aes_decrypt
    ]
    aes_decrypt_iterations_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in aes_decrypt
    ]

    ascon_encrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in ascon_encrypt
    ]
    ascon_encrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in ascon_encrypt
    ]
    ascon_encrypt_throughput_list = [
        None if aggregation.out_of_memory else aggregation.mean(MB_PER_SECOND)
        for aggregation in ascon_encrypt
    ]
    ascon_encrypt_throughput_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(MB_PER_SECOND)
        )
        for aggregation in ascon_encrypt
    ]
    ascon_encrypt_overhead_list = [
        None if aggregation.out_of_memory else aggregation.mean(WIRE_OVERHEAD_BYTES)
        for aggregation in ascon_encrypt
    ]
    ascon_encrypt_iterations_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in ascon_encrypt
    ]

    ascon_decrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in ascon_decrypt
    ]
    ascon_decrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in ascon_decrypt
    ]
    ascon_decrypt_throughput_list = [
        None if aggregation.out_of_memory else aggregation.mean(MB_PER_SECOND)
        for aggregation in ascon_decrypt
    ]
    ascon_decrypt_throughput_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(MB_PER_SECOND)
        )
        for aggregation in ascon_decrypt
    ]
    ascon_decrypt_overhead_list = [
        None if aggregation.out_of_memory else aggregation.mean(WIRE_OVERHEAD_BYTES)
        for aggregation in ascon_decrypt
    ]
    ascon_decrypt_iterations_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in ascon_decrypt
    ]

    return (
        aes_encrypt_latency_list,
        aes_encrypt_latency_ci_list,
        aes_encrypt_throughput_list,
        aes_encrypt_throughput_ci_list,
        aes_encrypt_overhead_list,
        aes_encrypt_iterations_list,
        aes_decrypt_latency_list,
        aes_decrypt_latency_ci_list,
        aes_decrypt_throughput_list,
        aes_decrypt_throughput_ci_list,
        aes_decrypt_overhead_list,
        aes_decrypt_iterations_list,
        ascon_encrypt_latency_list,
        ascon_encrypt_latency_ci_list,
        ascon_encrypt_throughput_list,
        ascon_encrypt_throughput_ci_list,
        ascon_encrypt_overhead_list,
        ascon_encrypt_iterations_list,
        ascon_decrypt_latency_list,
        ascon_decrypt_latency_ci_list,
        ascon_decrypt_throughput_list,
        ascon_decrypt_throughput_ci_list,
        ascon_decrypt_overhead_list,
        ascon_decrypt_iterations_list,
    )


def main() -> None:
    runs = parse_int_env("AES_ASCON_RUNS")
    payload_sizes = parse_int_list_env("AES_ASCON_PAYLOAD_SIZES")

    result_dir = Path(
        os.environ.get("AES_ASCON_RESULT_DIR", f"{DEFAULT_RESULT_ROOT}/{SCENARIO}")
    )
    bench_output = result_dir / BENCH_OUTPUT_NAME
    case_status = result_dir / CASE_STATUS_NAME
    template_path = Path(TEMPLATE_DIR) / HTML_TEMPLATE_NAME
    report_path = result_dir / REPORT_NAME

    results = BenchmarkSummary()
    load_results(results, str(bench_output), BENCHMARK_PREFIX, "B")
    load_out_of_memory_status(results, str(case_status))

    aes_encrypt, aes_decrypt, ascon_encrypt, ascon_decrypt = collect_aggregations(
        results, payload_sizes
    )

    (
        aes_encrypt_latency_list,
        aes_encrypt_latency_ci_list,
        aes_encrypt_throughput_list,
        aes_encrypt_throughput_ci_list,
        aes_encrypt_overhead_list,
        aes_encrypt_iterations_list,
        aes_decrypt_latency_list,
        aes_decrypt_latency_ci_list,
        aes_decrypt_throughput_list,
        aes_decrypt_throughput_ci_list,
        aes_decrypt_overhead_list,
        aes_decrypt_iterations_list,
        ascon_encrypt_latency_list,
        ascon_encrypt_latency_ci_list,
        ascon_encrypt_throughput_list,
        ascon_encrypt_throughput_ci_list,
        ascon_encrypt_overhead_list,
        ascon_encrypt_iterations_list,
        ascon_decrypt_latency_list,
        ascon_decrypt_latency_ci_list,
        ascon_decrypt_throughput_list,
        ascon_decrypt_throughput_ci_list,
        ascon_decrypt_overhead_list,
        ascon_decrypt_iterations_list,
    ) = analyze_aggregations(
        aes_encrypt,
        aes_decrypt,
        ascon_encrypt,
        ascon_decrypt,
    )

    total_benchmark_iterations = sum(
        aggregation.iterations
        for aggregation in results.aggregations
        if not aggregation.out_of_memory
    )
    out_of_memory_aggregations = [
        aggregation for aggregation in results.aggregations if aggregation.out_of_memory
    ]

    plot_aes_ascon_latency(
        payload_sizes,
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in aes_encrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in aes_encrypt_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in ascon_encrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in ascon_encrypt_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in aes_decrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in aes_decrypt_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in ascon_decrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in ascon_decrypt_latency_ci_list
        ],
        str(result_dir / LATENCY_PLOT),
    )

    plot_aes_ascon_throughput(
        payload_sizes,
        [
            NO_MEASUREMENT if value is None else value
            for value in aes_encrypt_throughput_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in aes_encrypt_throughput_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in ascon_encrypt_throughput_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in ascon_encrypt_throughput_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in aes_decrypt_throughput_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in aes_decrypt_throughput_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in ascon_decrypt_throughput_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in ascon_decrypt_throughput_ci_list
        ],
        str(result_dir / THROUGHPUT_PLOT),
    )

    write_aes_ascon_report(
        runs=runs,
        t_multiplier=float(stats.t.ppf(0.975, runs - 1)),
        total_iterations=total_benchmark_iterations,
        payload_sizes=payload_sizes,
        aes_encrypt_latency_means=aes_encrypt_latency_list,
        aes_encrypt_latency_cis=aes_encrypt_latency_ci_list,
        aes_encrypt_throughput_means=aes_encrypt_throughput_list,
        aes_encrypt_throughput_cis=aes_encrypt_throughput_ci_list,
        aes_encrypt_overhead_bytes=aes_encrypt_overhead_list,
        aes_encrypt_iterations=aes_encrypt_iterations_list,
        aes_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", "AES-GCM", payload_sizes
        ),
        ascon_encrypt_latency_means=ascon_encrypt_latency_list,
        ascon_encrypt_latency_cis=ascon_encrypt_latency_ci_list,
        ascon_encrypt_throughput_means=ascon_encrypt_throughput_list,
        ascon_encrypt_throughput_cis=ascon_encrypt_throughput_ci_list,
        ascon_encrypt_overhead_bytes=ascon_encrypt_overhead_list,
        ascon_encrypt_iterations=ascon_encrypt_iterations_list,
        ascon_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", "ASCON", payload_sizes
        ),
        aes_decrypt_latency_means=aes_decrypt_latency_list,
        aes_decrypt_latency_cis=aes_decrypt_latency_ci_list,
        aes_decrypt_throughput_means=aes_decrypt_throughput_list,
        aes_decrypt_throughput_cis=aes_decrypt_throughput_ci_list,
        aes_decrypt_overhead_bytes=aes_decrypt_overhead_list,
        aes_decrypt_iterations=aes_decrypt_iterations_list,
        aes_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", "AES-GCM", payload_sizes
        ),
        ascon_decrypt_latency_means=ascon_decrypt_latency_list,
        ascon_decrypt_latency_cis=ascon_decrypt_latency_ci_list,
        ascon_decrypt_throughput_means=ascon_decrypt_throughput_list,
        ascon_decrypt_throughput_cis=ascon_decrypt_throughput_ci_list,
        ascon_decrypt_overhead_bytes=ascon_decrypt_overhead_list,
        ascon_decrypt_iterations=ascon_decrypt_iterations_list,
        ascon_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", "ASCON", payload_sizes
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
