import os
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


# A scheme's wire overhead does not depend on payload size, so it is averaged over every
# payload size measured for that scheme.
def scheme_overhead_bytes(
    results: BenchmarkSummary,
    payload_sizes: list[int],
    scheme_name: str,
) -> float:
    values = []

    for payload_size in payload_sizes:
        aggregation = results.find_aggregation("Encrypt", scheme_name, payload_size)
        assert aggregation is not None
        values.append(aggregation.mean(WIRE_OVERHEAD_BYTES))

    return mean(values)


def build_table(
    results: BenchmarkSummary,
    payload_sizes: list[int],
    runs: int,
    operation: str,
    scheme_name: str,
    overhead_by_payload: dict[int, tuple[int, float]],
) -> str:
    rows = []

    for payload_size in payload_sizes:
        aggregation = results.find_aggregation(operation, scheme_name, payload_size)
        assert aggregation is not None

        latency_mean = aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND
        latency_ci = aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
        wire_size, overhead_percent = overhead_by_payload[payload_size]

        rows.append(
            [
                format_byte_size(payload_size),
                format_mean_with_ci(latency_mean, latency_ci),
                format_mean_with_ci(
                    aggregation.mean(MB_PER_SECOND),
                    aggregation.confidence_interval(MB_PER_SECOND),
                    decimals=1,
                ),
                format_byte_size(wire_size),
                f"{overhead_percent:.2f}%" if overhead_percent >= 0.01 else "&lt;0.01%",
                f"{aggregation.iterations:,}",
            ]
        )

    return build_html_table(
        [
            "Raw Size",
            "Latency (µs/op)",
            "Throughput (MB/s)",
            "Wire Size",
            "Overhead (%)",
            f"Iters (Σ{runs} runs)",
        ],
        rows,
        results.get_throttle_flags(operation, scheme_name, payload_sizes),
    )


def write_html_report(
    results: BenchmarkSummary,
    payload_sizes: list[int],
    runs: int,
    template_path: str,
    report_path: str,
) -> None:
    psk_overhead_bytes = int(
        round(scheme_overhead_bytes(results, payload_sizes, "PSK"))
    )
    rsa_overhead_bytes = int(
        round(scheme_overhead_bytes(results, payload_sizes, "RSA"))
    )
    cpabe_overhead_bytes = int(
        round(scheme_overhead_bytes(results, payload_sizes, "CPABE"))
    )

    psk_overhead_by_payload = {
        payload_size: (
            payload_size + psk_overhead_bytes,
            psk_overhead_bytes / payload_size * 100.0,
        )
        for payload_size in payload_sizes
    }
    rsa_overhead_by_payload = {
        payload_size: (
            payload_size + rsa_overhead_bytes,
            rsa_overhead_bytes / payload_size * 100.0,
        )
        for payload_size in payload_sizes
    }
    cpabe_overhead_by_payload = {
        payload_size: (
            payload_size + cpabe_overhead_bytes,
            cpabe_overhead_bytes / payload_size * 100.0,
        )
        for payload_size in payload_sizes
    }

    placeholders = {
        **build_html_generic_data(
            runs,
            sum(aggregation.iterations for aggregation in results.aggregations),
        ),
        "EncryptPskTable": build_table(
            results,
            payload_sizes,
            runs,
            "Encrypt",
            "PSK",
            psk_overhead_by_payload,
        ),
        "EncryptRsaTable": build_table(
            results,
            payload_sizes,
            runs,
            "Encrypt",
            "RSA",
            rsa_overhead_by_payload,
        ),
        "EncryptCpabeTable": build_table(
            results,
            payload_sizes,
            runs,
            "Encrypt",
            "CPABE",
            cpabe_overhead_by_payload,
        ),
        "DecryptPskTable": build_table(
            results,
            payload_sizes,
            runs,
            "Decrypt",
            "PSK",
            psk_overhead_by_payload,
        ),
        "DecryptRsaTable": build_table(
            results,
            payload_sizes,
            runs,
            "Decrypt",
            "RSA",
            rsa_overhead_by_payload,
        ),
        "DecryptCpabeTable": build_table(
            results,
            payload_sizes,
            runs,
            "Decrypt",
            "CPABE",
            cpabe_overhead_by_payload,
        ),
        "LatencyPlot": LATENCY_PLOT,
        "ThroughputPlot": THROUGHPUT_PLOT,
    }

    build_html_report(template_path, report_path, placeholders)


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

    results = BenchmarkSummary()
    load_results(results, str(bench_output), BENCHMARK_PREFIX, "B")

    plot_payload_scaling_latency(results, payload_sizes, str(result_dir / LATENCY_PLOT))
    plot_payload_scaling_throughput(
        results, payload_sizes, str(result_dir / THROUGHPUT_PLOT)
    )

    write_html_report(
        results, payload_sizes, runs, str(template_path), str(report_path)
    )


if __name__ == "__main__":
    main()
