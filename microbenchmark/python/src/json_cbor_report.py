from dataclasses import dataclass

from reporting.benchmark import (
    ENVELOPE_BYTES,
    NS_PER_MICROSECOND,
    NS_PER_OP,
    RAW_BYTES,
    BenchmarkSummary,
    FeatureSweep,
    load_results,
)
from reporting.charts import (
    AMBER,
    TEAL,
    VIOLET,
    Axes,
    PANEL_FIGURE_SIZE,
    apply_mesh_grid,
    draw_summary,
    plt,
    save_figure,
    draw_two_panel_figure,
)
from reporting.environment import (
    FilePaths,
    parse_int_env,
    parse_int_list_env,
    resolve_paths,
)
from reporting.formatting import format_mean_with_ci
from reporting.html import build_html_generic_data, build_html_report, build_html_table
from reporting.statistics import get_student_t_critical_95

SCENARIO = "json-cbor"
TEMPLATE_NAME = "json_cbor_template.html"

LATENCY_PLOT = "plot.png"
SIZE_PLOT = "size.png"

FORMATS = ["JSON", "CBOR", "CBORKeyAsInt"]
OPERATIONS = ["serialize", "deserialize"]

FORMAT_COLORS = {"JSON": AMBER, "CBOR": VIOLET, "CBORKeyAsInt": TEAL}
FORMAT_LABELS = {"CBORKeyAsInt": "CBOR (int keys)"}

X_LABEL = "Attribute count"

BENCHMARK_PREFIX = "BenchmarkEnvelope"


@dataclass(frozen=True)
class Config:
    runs: int
    t_critical: float
    attribute_counts: list[int]
    paths: FilePaths


def load_config() -> Config:
    runs = parse_int_env("JSON_CBOR_RUNS")

    return Config(
        runs=runs,
        t_critical=get_student_t_critical_95(runs - 1),
        attribute_counts=parse_int_list_env("JSON_CBOR_ATTRIBUTE_COUNTS"),
        paths=resolve_paths(SCENARIO, TEMPLATE_NAME),
    )


def configure_attribute_axis(config: Config, axis: Axes) -> None:
    axis.set_xticks(config.attribute_counts)
    apply_mesh_grid(axis)


def plot_latency(results: BenchmarkSummary, config: Config) -> None:

    def collect(operation: str, format_name: str) -> FeatureSweep:
        return results.sweep_features(
            operation,
            format_name,
            config.attribute_counts,
            NS_PER_OP,
            NS_PER_MICROSECOND,
            with_ci=True,
        )

    draw_two_panel_figure(
        OPERATIONS,
        FORMATS,
        collect,
        title="JSON vs. CBOR vs. CBOR (Int Keys): Latency vs. Policy Attributes",
        x_label=X_LABEL,
        y_label="Latency (µs) ± 95% CI",
        colors=FORMAT_COLORS,
        labels=FORMAT_LABELS,
        configure_axis=lambda axis: configure_attribute_axis(config, axis),
        output_path=config.paths.figure(LATENCY_PLOT),
    )


def plot_size(results: BenchmarkSummary, config: Config) -> None:

    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)

    figure.suptitle(
        "JSON vs. CBOR vs. CBOR (Int Keys): Envelope Size vs. Attribute Count",
        fontsize=13,
    )

    for format_name in FORMATS:

        envelope_sizes = results.sweep_features(
            "serialize", format_name, config.attribute_counts, ENVELOPE_BYTES
        )
        raw_sizes = results.sweep_features(
            "serialize", format_name, config.attribute_counts, RAW_BYTES
        )

        format_tax = FeatureSweep(
            sweep_values=envelope_sizes.sweep_values,
            means=[
                envelope - raw
                for envelope, raw in zip(envelope_sizes.means, raw_sizes.means)
            ],
        )

        for axis, series in ((axes[0], envelope_sizes), (axes[1], format_tax)):
            draw_summary(
                axis,
                series,
                FORMAT_LABELS.get(format_name, format_name),
                FORMAT_COLORS[format_name],
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
    results: BenchmarkSummary,
    config: Config,
    operation: str,
    format_name: str,
) -> str:

    rows = []

    for attribute_count in config.attribute_counts:

        case = results.get_case_summary(operation, format_name, attribute_count)

        latency = case.get_feature(NS_PER_OP)

        envelope_size = case.get_feature(ENVELOPE_BYTES).mean
        raw_size = case.get_feature(RAW_BYTES).mean

        overhead_percent = (envelope_size - raw_size) / raw_size * 100.0

        rows.append(
            [
                str(attribute_count),
                format_mean_with_ci(latency.mean, latency.ci),
                f"{raw_size:,.0f}",
                f"{envelope_size:,.0f}",
                f"{overhead_percent:.2f}%",
                f"{case.iterations:,}",
            ]
        )

    return build_html_table(
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


def write_html_report(results: BenchmarkSummary, config: Config) -> None:

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
        **build_html_generic_data(
            config.runs, config.t_critical, results.get_total_iterations
        ),
        **tables,
        "LatencyPlot": LATENCY_PLOT,
        "SizePlot": SIZE_PLOT,
    }

    build_html_report(config.paths.template, config.paths.report, placeholders)


def main() -> None:
    config = load_config()
    results = load_results(
        config.paths.bench_output, BENCHMARK_PREFIX, config.t_critical, "Attrs"
    )

    plot_latency(results, config)
    plot_size(results, config)
    write_html_report(results, config)


if __name__ == "__main__":
    main()
