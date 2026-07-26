from dataclasses import dataclass

from reporting.benchmark import (
    ENVELOPE_BYTES,
    NS_PER_MICROSECOND,
    NS_PER_OP,
    RAW_BYTES,
    BenchmarkMetrics,
    BenchmarkSpec,
    Series,
    case_id,
    collect_means,
    collect_series,
    load_results,
    sum_iterations,
    total_iterations,
)
from reporting.charts import (
    AMBER,
    TEAL,
    VIOLET,
    Axes,
    PANEL_FIGURE_SIZE,
    apply_mesh_grid,
    draw_line_series,
    plt,
    save_figure,
)
from reporting.environment import (
    ScenarioPaths,
    parse_int_env,
    parse_int_list_env,
    resolve_paths,
)
from reporting.formatting import format_mean_with_ci
from reporting.html import common_placeholders, render_report, render_table
from reporting.panels import render_operation_panels
from reporting.statistics import (
    mean,
    mean_and_confidence_interval,
    student_t_critical_95,
)

SCENARIO = "json-cbor"
RESULT_DIR_VAR = "JSON_CBOR_RESULT_DIR"
TEMPLATE_NAME = "json_cbor_template.html"

LATENCY_PLOT = "plot.png"
SIZE_PLOT = "size.png"

FORMATS = ["JSON", "CBOR", "CBORKeyAsInt"]
OPERATIONS = ["serialize", "deserialize"]

FORMAT_COLORS = {"JSON": AMBER, "CBOR": VIOLET, "CBORKeyAsInt": TEAL}
FALLBACK_COLOR = TEAL

FORMAT_LABELS = {"CBORKeyAsInt": "CBOR (int keys)"}

X_LABEL = "Attribute count"

SPEC = BenchmarkSpec(
    prefix="BenchmarkEnvelope",
    value_suffix="Attrs",
    required_units=(NS_PER_OP, ENVELOPE_BYTES, RAW_BYTES),
)


@dataclass(frozen=True)
class Config:
    runs: int
    t_critical: float
    attribute_counts: list[int]
    paths: ScenarioPaths


def load_config() -> Config:
    runs = parse_int_env("JSON_CBOR_RUNS")

    return Config(
        runs=runs,
        t_critical=student_t_critical_95(runs - 1),
        attribute_counts=parse_int_list_env("JSON_CBOR_ATTRIBUTE_COUNTS"),
        paths=resolve_paths(SCENARIO, RESULT_DIR_VAR, TEMPLATE_NAME),
    )


def format_color(format_name: str) -> str:
    return FORMAT_COLORS.get(format_name, FALLBACK_COLOR)


def format_label(format_name: str) -> str:
    return FORMAT_LABELS.get(format_name, format_name)


def attribute_cases(config: Config, operation: str, format_name: str):
    return [
        (count, case_id(operation, format_name, count))
        for count in config.attribute_counts
    ]


def configure_attribute_axis(config: Config, axis: Axes) -> None:
    axis.set_xticks(config.attribute_counts)
    apply_mesh_grid(axis)


def plot_latency(results: dict[str, BenchmarkMetrics], config: Config) -> None:

    def collect(operation: str, format_name: str) -> Series:
        return collect_series(
            results,
            attribute_cases(config, operation, format_name),
            NS_PER_OP,
            config.t_critical,
            NS_PER_MICROSECOND,
        )

    render_operation_panels(
        OPERATIONS,
        FORMATS,
        collect,
        title="JSON vs. CBOR vs. CBOR (Int Keys): Latency vs. Policy Attributes",
        x_label=X_LABEL,
        y_label="Latency (µs) ± 95% CI",
        color_for=format_color,
        label_for=format_label,
        configure_axis=lambda axis: configure_attribute_axis(config, axis),
        output_path=config.paths.figure(LATENCY_PLOT),
    )


def plot_size(results: dict[str, BenchmarkMetrics], config: Config) -> None:

    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)

    figure.suptitle(
        "JSON vs. CBOR vs. CBOR (Int Keys): Envelope Size vs. Attribute Count",
        fontsize=13,
    )

    for format_name in FORMATS:

        cases = attribute_cases(config, "serialize", format_name)
        counts, envelope_sizes = collect_means(results, cases, ENVELOPE_BYTES)
        _, raw_sizes = collect_means(results, cases, RAW_BYTES)

        format_tax = [
            envelope - raw for envelope, raw in zip(envelope_sizes, raw_sizes)
        ]

        for axis, values in ((axes[0], envelope_sizes), (axes[1], format_tax)):
            draw_line_series(
                axis,
                counts,
                values,
                format_label(format_name),
                format_color(format_name),
            )

    for axis, title, y_label in (
        (axes[0], "Absolute Size", "Envelope size (bytes)"),
        (axes[1], "Format Tax", "Bytes added over raw payload"),
    ):
        axis.set_title(title, fontsize=11)
        axis.set_xlabel(X_LABEL)
        axis.set_ylabel(y_label)
        axis.set_ylim(bottom=0)
        configure_attribute_axis(config, axis)
        axis.legend(fontsize=10)

    figure.tight_layout()
    save_figure(figure, config.paths.figure(SIZE_PLOT))


def build_table(
    results: dict[str, BenchmarkMetrics],
    config: Config,
    operation: str,
    format_name: str,
) -> str:

    rows = []

    for attribute_count in config.attribute_counts:

        metrics = results.get(case_id(operation, format_name, attribute_count))
        if metrics is None:
            continue

        latency_mean, latency_ci = mean_and_confidence_interval(
            metrics.ns_per_op, config.t_critical
        )

        envelope_size = mean(metrics.samples(ENVELOPE_BYTES))
        raw_size = mean(metrics.samples(RAW_BYTES))

        overhead_percent = (envelope_size - raw_size) / raw_size * 100.0

        rows.append(
            [
                str(attribute_count),
                format_mean_with_ci(latency_mean, latency_ci),
                f"{raw_size:,.0f}",
                f"{envelope_size:,.0f}",
                f"{overhead_percent:.2f}%",
                f"{sum_iterations(metrics):,}",
            ]
        )

    return render_table(
        [
            "Attributes",
            "Latency (ns/op)",
            "Raw (B)",
            "Envelope Size (B)",
            "Format Overhead (%)",
            f"Iters (Σ{config.runs} runs)",
        ],
        rows,
    )


def write_html_report(results: dict[str, BenchmarkMetrics], config: Config) -> None:

    tables = {
        f"{operation.capitalize()}{key}Table": build_table(
            results, config, operation, format_name
        )
        for operation in OPERATIONS
        for key, format_name in (
            ("Json", "JSON"),
            ("Cbor", "CBOR"),
            ("CborKeyAsInt", "CBORKeyAsInt"),
        )
    }

    placeholders = {
        **common_placeholders(
            config.runs, config.t_critical, total_iterations(results)
        ),
        **tables,
        "LatencyPlot": LATENCY_PLOT,
        "SizePlot": SIZE_PLOT,
    }

    render_report(config.paths.template, config.paths.report, placeholders)


def main() -> None:
    config = load_config()
    results = load_results(config.paths.bench_output, SPEC)

    plot_latency(results, config)
    plot_size(results, config)
    write_html_report(results, config)


if __name__ == "__main__":
    main()
