from dataclasses import dataclass

from reporting.benchmark import (
    MB_PER_SECOND,
    NS_PER_MICROSECOND,
    NS_PER_OP,
    WIRE_OVERHEAD_BYTES,
    BenchmarkMetrics,
    BenchmarkSummaryData,
    build_cases,
    generate_case_id,
    produce_summary,
    parse_benchmark_file,
    calculate_iterations,
    calculate_total_iterations,
)
from reporting.charts import (
    AXIS_HEADROOM,
    CRIMSON,
    TEAL,
    VIOLET,
    Axes,
    apply_value_grid,
    configure_byte_axis,
    draw_summary,
    draw_two_panel_figure,
    calculate_axis_top,
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
    format_mean_with_ci,
)
from reporting.html import build_html_generic_data, build_html_report, build_html_table
from reporting.statistics import (
    mean,
    mean_and_confidence_interval,
    get_student_t_critical_95,
)

SCENARIO = "payload-scaling"
TEMPLATE_NAME = "payload_scaling_template.html"

LATENCY_PLOT = "plot.png"
THROUGHPUT_PLOT = "throughput.png"

SCHEMES = ["PSK", "RSA", "CPABE"]
OPERATIONS = ["encrypt", "decrypt"]

SCHEME_COLORS = {"PSK": TEAL, "RSA": VIOLET, "CPABE": CRIMSON}

X_LABEL = "Payload size"
LEGEND = {"fontsize": 10, "loc": "upper left"}

BENCHMARK_PREFIX = "BenchmarkPayloadScaling"
AXIS_TICK_STEP = 4 * MEGABYTE

ZOOM_BOUNDS = [0.08, 0.08, 0.47, 0.32]
ZOOM_HEADROOM = 1.10


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
        t_critical=get_student_t_critical_95(runs - 1),
        payload_sizes=parse_int_list_env("PAYLOAD_SCALING_PAYLOAD_SIZES"),
        paths=resolve_paths(SCENARIO, TEMPLATE_NAME),
    )


def configure_payload_axis(config: Config, axis: Axes) -> None:
    configure_byte_axis(axis, config.payload_sizes[-1], AXIS_TICK_STEP)


# A scheme's wire overhead does not depend on payload size, so it is averaged
# over every payload size measured for that scheme
def scheme_overhead_bytes(
    results: dict[str, BenchmarkMetrics],
    config: Config,
    scheme_name: str,
) -> float:

    overhead_samples = []

    for payload_size in config.payload_sizes:
        overhead_samples.extend(
            results[
                generate_case_id("encrypt", scheme_name, payload_size)
            ].samples(WIRE_OVERHEAD_BYTES)
        )

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
            SCHEME_COLORS[name],
            linewidth=1.6,
            markersize=4,
            capsize=3,
        )

    zoom_axis.set_ylim(
        0.0, calculate_axis_top(series for _, series in zoomed) * ZOOM_HEADROOM
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
    on_panel=None,
) -> None:

    def collect(operation: str, scheme_name: str) -> BenchmarkSummaryData:
        return produce_summary(
            results,
            build_cases(operation, scheme_name, config.payload_sizes),
            unit,
            config.t_critical,
            divisor,
        )

    draw_two_panel_figure(
        OPERATIONS,
        SCHEMES,
        collect,
        title=title,
        x_label=X_LABEL,
        y_label=y_label,
        colors=SCHEME_COLORS,
        configure_axis=lambda axis: configure_payload_axis(config, axis),
        output_path=output_path,
        legend_kwargs=LEGEND,
        on_panel=on_panel,
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

        metrics = results[generate_case_id(operation, scheme_name, payload_size)]

        latency_mean, latency_ci = mean_and_confidence_interval(
            metrics.ns_per_op, config.t_critical
        )

        throughput_mean, throughput_ci = mean_and_confidence_interval(
            metrics.samples(MB_PER_SECOND), config.t_critical
        )

        overhead_percent = overhead_bytes / payload_size * 100.0
        rows.append(
            [
                format_byte_size(payload_size),
                format_mean_with_ci(
                    latency_mean / NS_PER_MICROSECOND, latency_ci / NS_PER_MICROSECOND
                ),
                format_mean_with_ci(throughput_mean, throughput_ci, decimals=1),
                format_byte_size(payload_size + overhead_bytes),
                f"{overhead_percent:.2f}%" if overhead_percent >= 0.01 else "&lt;0.01%",
                f"{calculate_iterations(metrics):,}",
            ]
        )

    return build_html_table(
        [
            "Raw Size",
            "Latency (µs/op)",
            "Throughput (MB/s)",
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
        **build_html_generic_data(
            config.runs, config.t_critical, calculate_total_iterations(results)
        ),
        **tables,
        "LatencyPlot": LATENCY_PLOT,
        "ThroughputPlot": THROUGHPUT_PLOT,
    }

    build_html_report(config.paths.template, config.paths.report, placeholders)


def main() -> None:
    config = load_config()
    results = parse_benchmark_file(config.paths.bench_output, BENCHMARK_PREFIX, "B")

    plot_metric(
        results,
        config,
        NS_PER_OP,
        NS_PER_MICROSECOND,
        "PSK vs. RSA vs. CP-ABE: Latency vs. Payload Size",
        "Latency (µs) ± 95% CI",
        config.paths.figure(LATENCY_PLOT),
        on_panel=lambda axis, operation, drawn: add_zoom_inset(
            config, axis, operation, drawn
        ),
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
