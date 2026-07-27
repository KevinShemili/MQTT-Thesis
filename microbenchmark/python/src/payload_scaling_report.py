from dataclasses import dataclass

from reporting.benchmark import (
    MB_PER_SECOND,
    NS_PER_MICROSECOND,
    NS_PER_OP,
    WIRE_OVERHEAD_BYTES,
    BenchmarkMetrics,
    BenchmarkParserConfig,
    BenchmarkSummaryData,
    generate_case_id,
    produce_summary,
    parse_benchmark_file,
    calculate_iterations,
    calculate_total_iterations,
)
from reporting.charts import (
    CRIMSON,
    TEAL,
    VIOLET,
    Axes,
    apply_value_grid,
    draw_summary,
)
from reporting.environment import (
    FilePaths,
    parse_int_env,
    parse_int_list_env,
    resolve_paths,
)
from reporting.formatting import (
    MEGABYTE,
    format_byte_size,
    format_byte_size_compact,
    format_mean_with_ci,
)
from reporting.html import common_placeholders, render_report, render_table
from reporting.panels import render_operation_panels, series_maximum
from reporting.statistics import (
    mean,
    mean_and_confidence_interval,
    student_t_critical_95,
)

SLUG = "payload-scaling"
RESULT_DIR_VAR = "PAYLOAD_SCALING_RESULT_DIR"
TEMPLATE_NAME = "payload_scaling_template.html"

LATENCY_PLOT = "plot.png"
THROUGHPUT_PLOT = "throughput.png"

SCHEMES = ["PSK", "RSA", "CPABE"]
OPERATIONS = ["encrypt", "decrypt"]

SCHEME_COLORS = {"PSK": TEAL, "RSA": VIOLET, "CPABE": CRIMSON}
FALLBACK_COLOR = CRIMSON

X_LABEL = "Payload size"
LEGEND = {"fontsize": 10, "loc": "upper left"}

AXIS_TICK_STEP = 4 * MEGABYTE

AXIS_HEADROOM = 1.03

ZOOM_BOUNDS = [0.08, 0.08, 0.47, 0.32]
ZOOM_HEADROOM = 1.10

SPEC = BenchmarkParserConfig(
    prefix="BenchmarkPayloadScaling",
    value_suffix="B",
    required_units=(NS_PER_OP, MB_PER_SECOND),
    optional_units=(WIRE_OVERHEAD_BYTES,),
)


@dataclass(frozen=True)
class Config:
    runs: int
    t_critical: float
    payload_sizes: list[int]
    paths: FilePaths


def load_config() -> Config:
    runs = parse_int_env("PAYLOAD_SCALING_RUNS")

    return Config(
        runs=runs,
        t_critical=student_t_critical_95(runs - 1),
        payload_sizes=parse_int_list_env("PAYLOAD_SCALING_PAYLOAD_SIZES"),
        paths=resolve_paths(SLUG, RESULT_DIR_VAR, TEMPLATE_NAME),
    )


def scheme_color(scheme_name: str) -> str:
    return SCHEME_COLORS.get(scheme_name, FALLBACK_COLOR)


def configure_payload_axis(config: Config, axis: Axes) -> None:

    max_payload_size = config.payload_sizes[-1]
    tick_values = list(range(0, max_payload_size + AXIS_TICK_STEP, AXIS_TICK_STEP))

    axis.set_xticks(tick_values)
    axis.set_xticklabels(
        ["0" if tick == 0 else format_byte_size_compact(tick) for tick in tick_values]
    )
    axis.set_xlim(0, max_payload_size * AXIS_HEADROOM)

    apply_value_grid(axis)


def scheme_overhead_bytes(
    results: dict[str, BenchmarkMetrics],
    config: Config,
    scheme_name: str,
) -> float:

    overhead_samples = []

    for payload_size in config.payload_sizes:
        metrics = results.get(generate_case_id("encrypt", scheme_name, payload_size))
        if metrics is None:
            continue

        overhead_samples.extend(metrics.samples(WIRE_OVERHEAD_BYTES))

    return mean(overhead_samples)


def add_zoom_inset(
    config: Config,
    axis: Axes,
    operation: str,
    drawn: list[tuple[str, BenchmarkSummaryData]],
) -> None:

    if operation != "encrypt":
        return

    zoom_axis = axis.inset_axes(ZOOM_BOUNDS)  # type: ignore
    zoomed = [(name, series) for name, series in drawn if name != "CPABE"]

    for name, series in zoomed:
        draw_summary(
            zoom_axis,
            series,
            name,
            scheme_color(name),
            linewidth=1.6,
            markersize=4,
            capsize=3,
        )

    zoom_axis.set_ylim(
        0.0, series_maximum(series for _, series in zoomed) * ZOOM_HEADROOM
    )
    zoom_axis.set_xlim(0, config.payload_sizes[-1] * AXIS_HEADROOM)
    zoom_axis.set_xticks([])
    zoom_axis.set_title("PSK + RSA Zoom", fontsize=9)
    zoom_axis.set_ylabel("µs", fontsize=8)
    zoom_axis.tick_params(axis="both", labelsize=8)
    apply_value_grid(zoom_axis, linewidth=0.4)
    zoom_axis.legend(fontsize=8, loc="upper left")


def plot_metric(
    results: dict[str, BenchmarkMetrics],
    config: Config,
    unit: str,
    divisor: float,
    title: str,
    y_label: str,
    output_path: str,
    with_zoom: bool = False,
) -> None:

    def collect(operation: str, scheme_name: str) -> BenchmarkSummaryData:
        return produce_summary(
            results,
            [
                (size, generate_case_id(operation, scheme_name, size))
                for size in config.payload_sizes
            ],
            unit,
            config.t_critical,
            divisor,
        )

    render_operation_panels(
        OPERATIONS,
        SCHEMES,
        collect,
        title=title,
        x_label=X_LABEL,
        y_label=y_label,
        color_for=scheme_color,
        configure_axis=lambda axis: configure_payload_axis(config, axis),
        output_path=output_path,
        legend_kwargs=LEGEND,
        on_panel=(
            (
                lambda axis, operation, drawn: add_zoom_inset(
                    config, axis, operation, drawn
                )
            )
            if with_zoom
            else None
        ),
    )


def build_table(
    results: dict[str, BenchmarkMetrics],
    config: Config,
    operation: str,
    scheme_name: str,
) -> str:

    overhead_bytes = int(round(scheme_overhead_bytes(results, config, scheme_name)))

    rows = []

    for payload_size in config.payload_sizes:

        metrics = results.get(generate_case_id(operation, scheme_name, payload_size))
        if metrics is None:
            continue

        latency_mean, latency_ci = mean_and_confidence_interval(
            metrics.ns_per_op, config.t_critical
        )

        overhead_percent = overhead_bytes / payload_size * 100.0

        rows.append(
            [
                format_byte_size(payload_size),
                format_mean_with_ci(
                    latency_mean / NS_PER_MICROSECOND, latency_ci / NS_PER_MICROSECOND
                ),
                format_byte_size(payload_size + overhead_bytes),
                f"{overhead_percent:.2f}%" if overhead_percent >= 0.01 else "&lt;0.01%",
                f"{calculate_iterations(metrics):,}",
            ]
        )

    return render_table(
        [
            "Raw Size",
            "Latency (µs/op)",
            "Wire Size",
            "Overhead (%)",
            f"Iters (Σ{config.runs} runs)",
        ],
        rows,
    )


def write_html_report(results: dict[str, BenchmarkMetrics], config: Config) -> None:

    tables = {
        f"{operation.capitalize()}{scheme_name.capitalize()}Table": build_table(
            results, config, operation, scheme_name
        )
        for operation in OPERATIONS
        for scheme_name in SCHEMES
    }

    placeholders = {
        **common_placeholders(
            config.runs, config.t_critical, calculate_total_iterations(results)
        ),
        **tables,
        "LatencyPlot": LATENCY_PLOT,
        "ThroughputPlot": THROUGHPUT_PLOT,
    }

    render_report(config.paths.template, config.paths.report, placeholders)


def main() -> None:
    config = load_config()
    results = parse_benchmark_file(config.paths.bench_output, SPEC)

    plot_metric(
        results,
        config,
        NS_PER_OP,
        NS_PER_MICROSECOND,
        "PSK vs. RSA vs. CP-ABE: Latency vs. Payload Size",
        "Latency (µs) ± 95% CI",
        config.paths.figure(LATENCY_PLOT),
        with_zoom=True,
    )
    plot_metric(
        results,
        config,
        MB_PER_SECOND,
        1.0,
        "PSK vs. RSA vs. CP-ABE: Throughput vs. Payload Size",
        "Throughput (MB/s) ± 95% CI",
        config.paths.figure(THROUGHPUT_PLOT),
    )

    write_html_report(results, config)


if __name__ == "__main__":
    main()
