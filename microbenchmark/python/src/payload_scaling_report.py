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

SCENARIO = "payload-scaling"
HTML_TEMPLATE_NAME = "payload_scaling_template.html"

LATENCY_PLOT = "plot.png"
THROUGHPUT_PLOT = "throughput.png"

SCHEMES = ["PSK", "RSA", "CPABE"]
OPERATIONS = ["Encrypt", "Decrypt"]
SCHEME_COLORS = {"PSK": TEAL, "RSA": VIOLET, "CPABE": CRIMSON}

LEGEND = {"fontsize": 10, "loc": "upper left"}

BENCHMARK_PREFIX = "BenchmarkPayloadScaling"
AXIS_TICK_STEP = 4 * MEGABYTE

ZOOM_BOUNDS = [0.08, 0.08, 0.47, 0.32]
ZOOM_HEADROOM = 1.10


def configure_payload_axis(payload_sizes: list[int], axis: Axes) -> None:
    configure_byte_axis(axis, payload_sizes[-1], AXIS_TICK_STEP)


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


def plot_metric(
    results: BenchmarkSummary,
    payload_sizes: list[int],
    measurement_name: str,
    divisor: float,
    title: str,
    y_label: str,
    output_path: str,
    with_encrypt_zoom: bool = False,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(title, fontsize=13)

    for axis, operation in zip(axes, OPERATIONS):
        drawn = []

        for scheme_name in SCHEMES:
            aggregations = [
                results.find_aggregation(operation, scheme_name, payload_size)
                for payload_size in payload_sizes
            ]
            assert all(aggregation is not None for aggregation in aggregations)

            statistics = [
                scaled_mean_and_ci(aggregation, measurement_name, divisor)
                for aggregation in aggregations
                if aggregation is not None
            ]
            means = [mean_value for mean_value, _ in statistics]
            confidence_intervals = [ci for _, ci in statistics]

            draw_summary(
                axis,
                payload_sizes,
                means,
                confidence_intervals,
                scheme_name,
                SCHEME_COLORS[scheme_name],
                with_ci=True,
            )
            drawn.append((scheme_name, means, confidence_intervals))

        axis.set_title(operation.capitalize(), fontsize=11)
        axis.set_xlabel("Payload Size")
        axis.set_ylabel(y_label)
        axis.set_ylim(bottom=0)
        configure_payload_axis(payload_sizes, axis)
        axis.legend(**LEGEND)

        if with_encrypt_zoom and operation == "Encrypt":
            zoom_axis = axis.inset_axes(ZOOM_BOUNDS)  # type: ignore
            zoomed = [entry for entry in drawn if entry[0] != "CPABE"]

            for scheme_name, means, confidence_intervals in zoomed:
                draw_summary(
                    zoom_axis,
                    payload_sizes,
                    means,
                    confidence_intervals,
                    scheme_name,
                    SCHEME_COLORS[scheme_name],
                    linewidth=1.6,
                    markersize=4,
                    capsize=3,
                )

            zoom_axis.set_ylim(
                0.0,
                max(
                    calculate_axis_top(means, confidence_intervals)
                    for _, means, confidence_intervals in zoomed
                )
                * ZOOM_HEADROOM,
            )
            zoom_axis.set_xlim(0, payload_sizes[-1] * AXIS_HEADROOM)
            zoom_axis.set_xticks([])
            zoom_axis.set_title("PSK + RSA Zoom", fontsize=9)
            zoom_axis.set_ylabel("µs", fontsize=8)
            zoom_axis.tick_params(axis="both", labelsize=8)
            apply_value_grid(zoom_axis, linewidth=0.4)
            zoom_axis.legend(fontsize=8, loc="upper left")

    figure.tight_layout()
    save_figure(figure, output_path)


def build_table(
    results: BenchmarkSummary,
    payload_sizes: list[int],
    runs: int,
    operation: str,
    scheme_name: str,
) -> str:
    overhead_bytes = int(
        round(scheme_overhead_bytes(results, payload_sizes, scheme_name))
    )
    rows = []

    for payload_size in payload_sizes:
        aggregation = results.find_aggregation(operation, scheme_name, payload_size)
        assert aggregation is not None

        latency_mean, latency_ci = scaled_mean_and_ci(
            aggregation, NS_PER_OP, NS_PER_MICROSECOND
        )
        overhead_percent = overhead_bytes / payload_size * 100.0

        rows.append(
            [
                format_byte_size(payload_size),
                format_mean_with_ci(latency_mean, latency_ci),
                format_mean_with_ci(
                    aggregation.mean(MB_PER_SECOND),
                    aggregation.confidence_interval(MB_PER_SECOND),
                    decimals=1,
                ),
                format_byte_size(payload_size + overhead_bytes),
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
    tables = {
        f"{operation}{scheme_name.capitalize()}Table": build_table(
            results, payload_sizes, runs, operation, scheme_name
        )
        for operation in OPERATIONS
        for scheme_name in SCHEMES
    }

    placeholders = {
        **build_html_generic_data(
            runs,
            get_student_t_critical_95(runs - 1),
            sum(aggregation.iterations for aggregation in results.aggregations),
        ),
        **tables,
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

    plot_metric(
        results,
        payload_sizes,
        NS_PER_OP,
        NS_PER_MICROSECOND,
        "PSK vs. RSA vs. CP-ABE: Latency vs. Payload Size",
        "Latency (µs) ± 95% CI",
        str(result_dir / LATENCY_PLOT),
        with_encrypt_zoom=True,
    )
    plot_metric(
        results,
        payload_sizes,
        MB_PER_SECOND,
        1.0,
        "PSK vs. RSA vs. CP-ABE: Throughput vs. Payload Size",
        "Throughput (MB/s) ± 95% CI",
        str(result_dir / THROUGHPUT_PLOT),
    )

    write_html_report(
        results, payload_sizes, runs, str(template_path), str(report_path)
    )


if __name__ == "__main__":
    main()
