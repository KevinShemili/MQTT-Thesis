from reporting.benchmark import (
    MB_PER_SECOND,
    NS_PER_MICROSECOND,
    NS_PER_OP,
    WIRE_OVERHEAD_BYTES,
    BenchmarkSummary,
    FeatureSweep,
    load_results,
)
from reporting.charts import (
    AMBER,
    VIOLET,
    Axes,
    configure_byte_axis,
    draw_two_panel_figure,
)
from reporting.environment import Config
from reporting.formatting import (
    KILOBYTE,
    format_byte_size,
    format_mean_with_ci,
)
from reporting.html import build_html_generic_data, build_html_report, build_html_table

SCENARIO = "aes-ascon"
ENV_PREFIX = "AES_ASCON"
TEMPLATE_NAME = "aes_ascon_template.html"

LATENCY_PLOT = "plot.png"
THROUGHPUT_PLOT = "throughput.png"

ALGORITHMS = ["AES-GCM", "ASCON"]
OPERATIONS = ["encrypt", "decrypt"]

ALGORITHM_COLORS = {"AES-GCM": AMBER, "ASCON": VIOLET}

BENCHMARK_PREFIX = "BenchmarkAESASCON"
AXIS_TICK_STEP = 16 * KILOBYTE


def configure_payload_axis(config: Config, axis: Axes) -> None:
    configure_byte_axis(axis, config.integers("PAYLOAD_SIZES")[-1], AXIS_TICK_STEP)


def plot_metric(
    summary: BenchmarkSummary,
    config: Config,
    feature_name: str,
    divisor: float,
    title: str,
    y_label: str,
    output_path: str,
) -> None:

    def collect(operation: str, algorithm: str) -> FeatureSweep:
        return summary.sweep_features(
            operation,
            algorithm,
            config.integers("PAYLOAD_SIZES"),
            feature_name,
            divisor,
        )

    draw_two_panel_figure(
        OPERATIONS,
        ALGORITHMS,
        collect,
        title=title,
        x_label="Payload size",
        y_label=y_label,
        colors=ALGORITHM_COLORS,
        configure_axis=lambda axis: configure_payload_axis(config, axis),
        output_path=output_path,
    )


def build_table(
    summary: BenchmarkSummary,
    config: Config,
    operation: str,
    algorithm: str,
) -> str:

    rows = []

    for payload_size in config.integers("PAYLOAD_SIZES"):

        case = summary.get_case_summary(operation, algorithm, payload_size)

        latency = case.get_feature(NS_PER_OP)
        throughput = case.get_feature(MB_PER_SECOND)

        rows.append(
            [
                format_byte_size(payload_size, compact=True),
                format_mean_with_ci(latency.mean, latency.ci),
                format_mean_with_ci(throughput.mean, throughput.ci, decimals=1),
                f"{case.get_feature(WIRE_OVERHEAD_BYTES).mean:.0f}",
                f"{case.iterations:,}",
            ]
        )

    return build_html_table(
        [
            "Payload",
            "Latency (ns/op)",
            "Throughput (MB/s)",
            "Tag + Nonce (B)",
            f"Iters (Σ{config.runs} runs)",
        ],
        rows,
    )


def write_html_report(results: BenchmarkSummary, config: Config) -> None:

    placeholders = {
        **build_html_generic_data(
            config.runs, config.t_critical, results.total_iterations
        ),
        "EncryptAesTable": build_table(results, config, "encrypt", "AES-GCM"),
        "EncryptAsconTable": build_table(results, config, "encrypt", "ASCON"),
        "DecryptAesTable": build_table(results, config, "decrypt", "AES-GCM"),
        "DecryptAsconTable": build_table(results, config, "decrypt", "ASCON"),
        "LatencyPlot": LATENCY_PLOT,
        "ThroughputPlot": THROUGHPUT_PLOT,
    }

    build_html_report(config.template, config.report, placeholders)


def main() -> None:
    config = Config(SCENARIO, TEMPLATE_NAME, ENV_PREFIX)

    results = load_results(config.bench_output, BENCHMARK_PREFIX, "B")

    plot_metric(
        results,
        config,
        NS_PER_OP,
        NS_PER_MICROSECOND,
        "AES-GCM vs. ASCON: Latency vs. Payload Size",
        "Latency (µs) ± 95% CI",
        config.figure(LATENCY_PLOT),
    )

    plot_metric(
        results,
        config,
        MB_PER_SECOND,
        1.0,
        "AES-GCM vs. ASCON: Throughput vs. Payload Size",
        "Throughput (MB/s) ± 95% CI",
        config.figure(THROUGHPUT_PLOT),
    )

    write_html_report(results, config)


if __name__ == "__main__":
    main()
