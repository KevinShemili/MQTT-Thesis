from reporting.benchmark import (
    ENVELOPE_BYTES,
    NS_PER_MICROSECOND,
    NS_PER_OP,
    RAW_BYTES,
    BenchmarkSummary,
    FeatureSweep,
    load_results,
    throttle_flags,
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
from reporting.environment import Config
from reporting.formatting import format_mean_with_ci
from reporting.html import build_html_generic_data, build_html_report, build_html_table

SCENARIO = "json-cbor"
ENV_PREFIX = "JSON_CBOR"
TEMPLATE_NAME = "json_cbor_template.html"

LATENCY_PLOT = "plot.png"
SIZE_PLOT = "size.png"

FORMATS = ["JSON", "CBOR", "CBORKeyAsInt"]
OPERATIONS = ["serialize", "deserialize"]

FORMAT_COLORS = {"JSON": AMBER, "CBOR": VIOLET, "CBORKeyAsInt": TEAL}
FORMAT_LABELS = {"CBORKeyAsInt": "CBOR (int keys)"}

X_LABEL = "Attribute count"

BENCHMARK_PREFIX = "BenchmarkEnvelope"


def configure_attribute_axis(config: Config, axis: Axes) -> None:
    axis.set_xticks(config.integers("ATTRIBUTE_COUNTS"))
    apply_mesh_grid(axis)


def plot_latency(results: BenchmarkSummary, config: Config) -> None:

    def collect(operation: str, format_name: str) -> FeatureSweep:
        return results.sweep_features(
            operation,
            format_name,
            config.integers("ATTRIBUTE_COUNTS"),
            NS_PER_OP,
            NS_PER_MICROSECOND,
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
        output_path=config.figure(LATENCY_PLOT),
    )


def plot_size(results: BenchmarkSummary, config: Config) -> None:

    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)

    figure.suptitle(
        "JSON vs. CBOR vs. CBOR (Int Keys): Envelope Size vs. Attribute Count",
        fontsize=13,
    )

    for format_name in FORMATS:

        label = FORMAT_LABELS.get(format_name, format_name)
        color = FORMAT_COLORS[format_name]

        attribute_counts = config.integers("ATTRIBUTE_COUNTS")

        envelope_sizes = results.sweep_features(
            "serialize", format_name, attribute_counts, ENVELOPE_BYTES
        )
        raw_sizes = results.sweep_features(
            "serialize", format_name, attribute_counts, RAW_BYTES
        )

        draw_summary(axes[0], envelope_sizes, label, color)

        # The format tax is the difference between two measured sizes rather than a
        # measurement in its own right, so it is drawn as the plain line it is
        axes[1].plot(
            envelope_sizes.sweep_values,
            [
                envelope - raw
                for envelope, raw in zip(envelope_sizes.means, raw_sizes.means)
            ],
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
        axis.set_xlabel(X_LABEL)
        axis.set_ylabel(y_label)
        axis.set_ylim(bottom=0)
        configure_attribute_axis(config, axis)
        axis.legend(fontsize=10)

    figure.tight_layout()
    save_figure(figure, config.figure(SIZE_PLOT))


def build_table(
    results: BenchmarkSummary,
    config: Config,
    operation: str,
    format_name: str,
) -> str:

    rows = []
    cases = []

    for attribute_count in config.integers("ATTRIBUTE_COUNTS"):

        case = results.get_case_summary(operation, format_name, attribute_count)
        cases.append(case)

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
        throttle_flags(cases),
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
            config.runs, config.t_critical, results.total_iterations
        ),
        **tables,
        "LatencyPlot": LATENCY_PLOT,
        "SizePlot": SIZE_PLOT,
    }

    build_html_report(config.template, config.report, placeholders)


def main() -> None:
    config = Config(SCENARIO, TEMPLATE_NAME, ENV_PREFIX)
    results = load_results(config.bench_output, BENCHMARK_PREFIX, "Attrs")

    plot_latency(results, config)
    plot_size(results, config)
    write_html_report(results, config)


if __name__ == "__main__":
    main()
