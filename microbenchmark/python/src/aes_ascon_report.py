from dataclasses import dataclass

from matplotlib.ticker import FuncFormatter

from reporting.benchmark import (
    MB_PER_SECOND,
    NS_PER_MICROSECOND,
    NS_PER_OP,
    WIRE_OVERHEAD_BYTES,
    BenchmarkMetrics,
    BenchmarkSpec,
    Series,
    case_id,
    collect_series,
    load_results,
    sum_iterations,
    total_iterations,
)
from reporting.charts import AMBER, VIOLET, Axes, apply_value_grid
from reporting.environment import (
    ScenarioPaths,
    parse_int_env,
    parse_int_list_env,
    resolve_paths,
)
from reporting.formatting import format_compact_byte_size, format_mean_with_ci
from reporting.html import common_placeholders, render_report, render_table
from reporting.panels import render_operation_panels
from reporting.statistics import (
    mean,
    mean_and_confidence_interval,
    student_t_critical_95,
)

SLUG = "aes-ascon"
RESULT_DIR_VAR = "AES_ASCON_RESULT_DIR"
TEMPLATE_NAME = "aes_ascon_template.html"

LATENCY_PLOT = "plot.png"
THROUGHPUT_PLOT = "throughput.png"

ALGORITHMS = ["AES-GCM", "ASCON"]
OPERATIONS = ["encrypt", "decrypt"]

ALGORITHM_COLORS = {"AES-GCM": AMBER, "ASCON": VIOLET}
FALLBACK_COLOR = VIOLET

SPEC = BenchmarkSpec(
    prefix="BenchmarkAESASCON",
    value_suffix="B",
    required_units=(NS_PER_OP, MB_PER_SECOND, WIRE_OVERHEAD_BYTES),
)


@dataclass(frozen=True)
class Config:
    runs: int
    t_critical: float
    payload_sizes: list[int]
    paths: ScenarioPaths


def load_config() -> Config:
    runs = parse_int_env("AES_ASCON_RUNS")

    return Config(
        runs=runs,
        t_critical=student_t_critical_95(runs - 1),
        payload_sizes=parse_int_list_env("AES_ASCON_PAYLOAD_SIZES"),
        paths=resolve_paths(SLUG, RESULT_DIR_VAR, TEMPLATE_NAME),
    )


def algorithm_color(algorithm: str) -> str:
    return ALGORITHM_COLORS.get(algorithm, FALLBACK_COLOR)


def configure_payload_axis(config: Config, axis: Axes) -> None:
    axis.set_xticks(config.payload_sizes)
    axis.set_xlim(left=0)
    axis.xaxis.set_major_formatter(
        FuncFormatter(lambda value, _: format_compact_byte_size(int(value)))
    )
    axis.tick_params(axis="x", rotation=30)
    apply_value_grid(axis)


def plot_metric(
    results: dict[str, BenchmarkMetrics],
    config: Config,
    unit: str,
    divisor: float,
    title: str,
    y_label: str,
    output_path: str,
) -> None:

    def collect(operation: str, algorithm: str) -> Series:
        return collect_series(
            results,
            [
                (size, case_id(operation, algorithm, size))
                for size in config.payload_sizes
            ],
            unit,
            config.t_critical,
            divisor,
        )

    render_operation_panels(
        OPERATIONS,
        ALGORITHMS,
        collect,
        title=title,
        x_label="Payload size",
        y_label=y_label,
        color_for=algorithm_color,
        configure_axis=lambda axis: configure_payload_axis(config, axis),
        output_path=output_path,
    )


def build_table(
    results: dict[str, BenchmarkMetrics],
    config: Config,
    operation: str,
    algorithm: str,
) -> str:

    rows = []

    for payload_size in config.payload_sizes:

        metrics = results.get(case_id(operation, algorithm, payload_size))
        if metrics is None:
            continue

        latency_mean, latency_ci = mean_and_confidence_interval(
            metrics.ns_per_op, config.t_critical
        )

        throughput, throughput_ci = 0.0, 0.0
        if len(metrics.samples(MB_PER_SECOND)) > 0:
            throughput, throughput_ci = mean_and_confidence_interval(
                metrics.samples(MB_PER_SECOND), config.t_critical
            )

        overhead = 0.0
        if len(metrics.samples(WIRE_OVERHEAD_BYTES)) > 0:
            overhead = mean(metrics.samples(WIRE_OVERHEAD_BYTES))

        rows.append(
            [
                format_compact_byte_size(payload_size),
                format_mean_with_ci(latency_mean, latency_ci),
                format_mean_with_ci(throughput, throughput_ci, decimals=1),
                f"{overhead:.0f}" if overhead != 0.0 else "—",
                f"{sum_iterations(metrics):,}",
            ]
        )

    return render_table(
        [
            "Payload",
            "Latency (ns/op)",
            "Throughput (MB/s)",
            "Tag + Nonce (B)",
            f"Iters (Σ{config.runs} runs)",
        ],
        rows,
    )


def write_html_report(results: dict[str, BenchmarkMetrics], config: Config) -> None:

    placeholders = {
        **common_placeholders(
            config.runs, config.t_critical, total_iterations(results)
        ),
        "EncryptAesTable": build_table(results, config, "encrypt", "AES-GCM"),
        "EncryptAsconTable": build_table(results, config, "encrypt", "ASCON"),
        "DecryptAesTable": build_table(results, config, "decrypt", "AES-GCM"),
        "DecryptAsconTable": build_table(results, config, "decrypt", "ASCON"),
        "LatencyPlot": LATENCY_PLOT,
        "ThroughputPlot": THROUGHPUT_PLOT,
    }

    render_report(config.paths.template, config.paths.report, placeholders)


def main() -> None:
    config = load_config()
    results = load_results(config.paths.bench_output, SPEC)

    plot_metric(
        results,
        config,
        NS_PER_OP,
        NS_PER_MICROSECOND,
        "AES-GCM vs. ASCON: Latency vs. Payload Size",
        "Latency (µs) ± 95% CI",
        config.paths.figure(LATENCY_PLOT),
    )
    plot_metric(
        results,
        config,
        MB_PER_SECOND,
        1.0,
        "AES-GCM vs. ASCON: Throughput vs. Payload Size",
        "Throughput (MB/s) ± 95% CI",
        config.paths.figure(THROUGHPUT_PLOT),
    )

    write_html_report(results, config)


if __name__ == "__main__":
    main()
