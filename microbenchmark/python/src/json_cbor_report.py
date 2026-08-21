import os
from pathlib import Path

from template_builder.chart import *
from template_builder.formatting import *
from template_builder.html import *
from template_builder.color import *

from model.benchmark_summary import *
from model.case_aggregation import *
from model.case import *
from model.measurement import *
from model.populate_model import *

from config.environment import *

from statistics_tbd.summary import *
from statistics_tbd.linear_regression import *

SCENARIO = "json-cbor"
HTML_TEMPLATE_NAME = "json_cbor_template.html"

LATENCY_PLOT = "plot.png"
SIZE_PLOT = "size.png"

FORMATS = ["JSON", "CBOR", "CBORKeyAsInt"]
OPERATIONS = ["Serialize", "Deserialize"]

FORMAT_COLORS = {"JSON": AMBER, "CBOR": VIOLET, "CBORKeyAsInt": TEAL}
FORMAT_LABELS = {"CBORKeyAsInt": "CBOR (int keys)"}

BENCHMARK_PREFIX = "BenchmarkEnvelope"


def configure_attribute_axis(attribute_counts: list[int], axis: Axes) -> None:
    axis.set_xticks(attribute_counts)
    apply_mesh_grid(axis)


def scaled_mean_and_ci(
    aggregation: CaseAggregation, measurement_name: str, divisor: float
) -> tuple[float, float]:
    values = [
        value / divisor
        for value in aggregation.get_all_measurement_values(measurement_name)
    ]
    return mean_and_confidence_interval(
        values, get_student_t_critical_95(len(values) - 1)
    )


def plot_latency(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    output_path: str,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(
        "JSON vs. CBOR vs. CBOR (Int Keys): Latency vs. Policy Attributes",
        fontsize=13,
    )

    for axis, operation in zip(axes, OPERATIONS):
        for format_name in FORMATS:
            aggregations = [
                results.find_aggregation(operation, format_name, attribute_count)
                for attribute_count in attribute_counts
            ]
            assert all(aggregation is not None for aggregation in aggregations)

            statistics = [
                scaled_mean_and_ci(aggregation, NS_PER_OP, NS_PER_MICROSECOND)
                for aggregation in aggregations
                if aggregation is not None
            ]

            draw_summary(
                axis,
                attribute_counts,
                [mean for mean, _ in statistics],
                [ci for _, ci in statistics],
                FORMAT_LABELS.get(format_name, format_name),
                FORMAT_COLORS[format_name],
                with_ci=True,
            )

        axis.set_title(operation.capitalize(), fontsize=11)
        axis.set_xlabel("Attribute Count")
        axis.set_ylabel("Latency (µs) ± 95% CI")
        axis.set_ylim(bottom=0)
        configure_attribute_axis(attribute_counts, axis)
        axis.legend(fontsize=10)

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_size(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    output_path: str,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(
        "JSON vs. CBOR vs. CBOR (Int Keys): Envelope Size vs. Attribute Count",
        fontsize=13,
    )

    for format_name in FORMATS:
        label = FORMAT_LABELS.get(format_name, format_name)
        color = FORMAT_COLORS[format_name]
        aggregations = [
            results.find_aggregation("Serialize", format_name, attribute_count)
            for attribute_count in attribute_counts
        ]
        assert all(aggregation is not None for aggregation in aggregations)

        envelope_means = [
            aggregation.mean(ENVELOPE_BYTES)
            for aggregation in aggregations
            if aggregation is not None
        ]
        envelope_cis = [
            aggregation.confidence_interval(ENVELOPE_BYTES)
            for aggregation in aggregations
            if aggregation is not None
        ]
        raw_means = [
            aggregation.mean(RAW_BYTES)
            for aggregation in aggregations
            if aggregation is not None
        ]

        draw_summary(
            axes[0],
            attribute_counts,
            envelope_means,
            envelope_cis,
            label,
            color,
        )

        axes[1].plot(
            attribute_counts,
            [envelope - raw for envelope, raw in zip(envelope_means, raw_means)],
            label=label,
            color=color,
            marker="o",
            linewidth=1.8,
            markersize=5,
        )

    for axis, title, y_label in (
        (axes[0], "Absolute Size", "Envelope size (bytes)"),
        (axes[1], "Format Tax", "Bytes added over raw payload"),
    ):
        axis.set_title(title, fontsize=11)
        axis.set_xlabel("Attribute Count")
        axis.set_ylabel(y_label)
        axis.set_ylim(bottom=0)
        configure_attribute_axis(attribute_counts, axis)
        axis.legend(fontsize=10)

    figure.tight_layout()
    save_figure(figure, output_path)


def build_table(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    runs: int,
    operation: str,
    format_name: str,
) -> str:
    rows = []

    for attribute_count in attribute_counts:
        aggregation = results.find_aggregation(operation, format_name, attribute_count)
        assert aggregation is not None

        envelope_size = aggregation.mean(ENVELOPE_BYTES)
        raw_size = aggregation.mean(RAW_BYTES)
        overhead_percent = (envelope_size - raw_size) / raw_size * 100.0

        rows.append(
            [
                str(attribute_count),
                format_mean_with_ci(
                    aggregation.mean(NS_PER_OP),
                    aggregation.confidence_interval(NS_PER_OP),
                ),
                f"{raw_size:,.0f}",
                f"{envelope_size:,.0f}",
                f"{overhead_percent:.2f}%",
                f"{aggregation.iterations:,}",
            ]
        )

    return build_html_table(
        [
            "Attributes",
            "Latency (ns/op)",
            "Raw (B)",
            "Envelope Size (B)",
            "Format Overhead (%)",
            f"Iters (Σ{runs} runs)",
        ],
        rows,
        results.get_throttle_flags(operation, format_name, attribute_counts),
    )


def write_html_report(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    runs: int,
    template_path: str,
    report_path: str,
) -> None:
    tables = {
        f"{operation}{key}Table": build_table(
            results, attribute_counts, runs, operation, format_name
        )
        for operation in OPERATIONS
        for key, format_name in (
            ("Json", "JSON"),
            ("Cbor", "CBOR"),
            ("CborKeyAsInt", "CBORKeyAsInt"),
        )
    }

    placeholders = {
        **build_html_generic_data(
            runs,
            get_student_t_critical_95(runs - 1),
            sum(aggregation.iterations for aggregation in results.aggregations),
        ),
        **tables,
        "LatencyPlot": LATENCY_PLOT,
        "SizePlot": SIZE_PLOT,
    }

    build_html_report(template_path, report_path, placeholders)


def main() -> None:
    runs = parse_int_env("JSON_CBOR_RUNS")
    attribute_counts = parse_int_list_env("JSON_CBOR_ATTRIBUTE_COUNTS")

    result_dir = Path(
        os.environ.get("JSON_CBOR_RESULT_DIR", f"{DEFAULT_RESULT_ROOT}/{SCENARIO}")
    )
    bench_output = result_dir / BENCH_OUTPUT_NAME
    template_path = Path(TEMPLATE_DIR) / HTML_TEMPLATE_NAME
    report_path = result_dir / REPORT_NAME

    results = BenchmarkSummary()
    load_results(results, str(bench_output), BENCHMARK_PREFIX, "Attrs")

    plot_latency(results, attribute_counts, str(result_dir / LATENCY_PLOT))
    plot_size(results, attribute_counts, str(result_dir / SIZE_PLOT))
    write_html_report(
        results, attribute_counts, runs, str(template_path), str(report_path)
    )


if __name__ == "__main__":
    main()
