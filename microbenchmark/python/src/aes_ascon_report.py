import os
from pathlib import Path

from template_builder.chart import *
from template_builder.formatting import *
from template_builder.html import *

from model.benchmark_summary import *
from model.measurement import *
from model.populate_model import *

from config.environment import *

SCENARIO = "aes-ascon"
HTML_TEMPLATE_NAME = "aes_ascon_template.html"

LATENCY_PLOT = "plot.png"
THROUGHPUT_PLOT = "throughput.png"

BENCHMARK_PREFIX = "BenchmarkAESASCON"


def build_table(
    summary: BenchmarkSummary,
    payload_sizes: list[int],
    runs: int,
    operation: str,
    algorithm: str,
) -> str:
    rows = []

    for payload_size in payload_sizes:
        aggregation = summary.find_aggregation(operation, algorithm, payload_size)
        assert aggregation is not None

        rows.append(
            [
                format_byte_size(payload_size, compact=True),
                format_mean_with_ci(
                    aggregation.mean(NS_PER_OP),
                    aggregation.confidence_interval(NS_PER_OP),
                ),
                format_mean_with_ci(
                    aggregation.mean(MB_PER_SECOND),
                    aggregation.confidence_interval(MB_PER_SECOND),
                    decimals=1,
                ),
                f"{aggregation.mean(WIRE_OVERHEAD_BYTES):.0f}",
                f"{aggregation.iterations:,}",
            ]
        )

    return build_html_table(
        [
            "Payload",
            "Latency (ns/op)",
            "Throughput (MB/s)",
            "Tag + Nonce (B)",
            f"Iters (Σ{runs} runs)",
        ],
        rows,
        summary.get_throttle_flags(operation, algorithm, payload_sizes),
    )


def write_html_report(
    results: BenchmarkSummary,
    payload_sizes: list[int],
    runs: int,
    template_path: str,
    report_path: str,
) -> None:
    placeholders = {
        **build_html_generic_data(
            runs,
            sum(aggregation.iterations for aggregation in results.aggregations),
        ),
        "EncryptAesTable": build_table(
            results, payload_sizes, runs, "Encrypt", "AES-GCM"
        ),
        "EncryptAsconTable": build_table(
            results, payload_sizes, runs, "Encrypt", "ASCON"
        ),
        "DecryptAesTable": build_table(
            results, payload_sizes, runs, "Decrypt", "AES-GCM"
        ),
        "DecryptAsconTable": build_table(
            results, payload_sizes, runs, "Decrypt", "ASCON"
        ),
        "LatencyPlot": LATENCY_PLOT,
        "ThroughputPlot": THROUGHPUT_PLOT,
    }

    build_html_report(template_path, report_path, placeholders)


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

    plot_aes_ascon_latency(results, payload_sizes, str(result_dir / LATENCY_PLOT))
    plot_aes_ascon_throughput(results, payload_sizes, str(result_dir / THROUGHPUT_PLOT))

    write_html_report(
        results, payload_sizes, runs, str(template_path), str(report_path)
    )


if __name__ == "__main__":
    main()
