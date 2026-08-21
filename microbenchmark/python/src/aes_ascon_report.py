import os
from pathlib import Path

from template_builder.chart import *
from template_builder.formatting import *
from template_builder.html import *
from template_builder.color import *

from model.benchmark_summary import *
from model.measurement import *
from model.populate_model import *

from config.environment import *

from statistics_tbd.summary import *

SCENARIO = "aes-ascon"
HTML_TEMPLATE_NAME = "aes_ascon_template.html"

LATENCY_PLOT = "plot.png"
THROUGHPUT_PLOT = "throughput.png"

ALGORITHMS = ["AES-GCM", "ASCON"]
OPERATIONS = ["Encrypt", "Decrypt"]
ALGORITHM_COLORS = {"AES-GCM": AMBER, "ASCON": VIOLET}

BENCHMARK_PREFIX = "BenchmarkAESASCON"


def plot_metric(
    summary: BenchmarkSummary,
    payload_sizes: list[int],
    measurement_name: str,
    divisor: float,
    title: str,
    y_label: str,
    output_path: str,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(title, fontsize=13)

    for axis, operation in zip(axes, OPERATIONS):
        for algorithm in ALGORITHMS:
            aggregations = [
                summary.find_aggregation(operation, algorithm, payload_size)
                for payload_size in payload_sizes
            ]
            assert all(aggregation is not None for aggregation in aggregations)

            means = [
                aggregation.mean(measurement_name) / divisor
                for aggregation in aggregations
                if aggregation is not None
            ]
            confidence_intervals = [
                aggregation.confidence_interval(measurement_name) / divisor
                for aggregation in aggregations
                if aggregation is not None
            ]

            draw_summary(
                axis,
                payload_sizes,
                means,
                confidence_intervals,
                algorithm,
                ALGORITHM_COLORS[algorithm],
                with_ci=True,
            )

        axis.set_title(operation.capitalize(), fontsize=11)
        axis.set_xlabel("Payload size")
        axis.set_ylabel(y_label)
        axis.set_ylim(bottom=0)
        configure_byte_axis(axis, payload_sizes[-1], 16 * KILOBYTE)
        axis.legend(fontsize=10)

    figure.tight_layout()
    save_figure(figure, output_path)


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
            get_student_t_critical_95(runs - 1),
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

    plot_metric(
        results,
        payload_sizes,
        NS_PER_OP,
        NS_PER_MICROSECOND,
        "AES-GCM vs. ASCON: Latency vs. Payload Size",
        "Latency (µs) ± 95% CI",
        str(result_dir / LATENCY_PLOT),
    )
    plot_metric(
        results,
        payload_sizes,
        MB_PER_SECOND,
        1.0,
        "AES-GCM vs. ASCON: Throughput vs. Payload Size",
        "Throughput (MB/s) ± 95% CI",
        str(result_dir / THROUGHPUT_PLOT),
    )

    write_html_report(
        results, payload_sizes, runs, str(template_path), str(report_path)
    )


if __name__ == "__main__":
    main()
