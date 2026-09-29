import os
from pathlib import Path

from dotenv import load_dotenv

from report.analysis.shared.load_summary import load_macro_summary
from report.analysis.shared.paths import REPORT_NAME, TEMPLATE_DIR
from report.analysis.shared.metrics import to_microseconds
from report.analysis.shared.statistics import (
    macro_cycle_statistics,
    macro_latency_statistics,
)
from report.render.chart import plot_macro_cpu_cycles, plot_macro_latency
from report.render.html import write_macro_report

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_FILE = PROJECT_ROOT / "environment" / "benchmark.env"

PUBLISHER_RESULT_NAME = "publisher.csv"
SUBSCRIBER_RESULT_NAME = "subscriber.csv"
REPORT_TEMPLATE_NAME = "macro_template.html"
LATENCY_PLOT = "latency.png"
CPU_CYCLES_PLOT = "cpu_cycles.png"


# Analyze the recorded sweep and render its charts and HTML report
def generate_report(result_directory: Path) -> None:

    summary = load_macro_summary(
        str(result_directory / PUBLISHER_RESULT_NAME),
        str(result_directory / SUBSCRIBER_RESULT_NAME),
    )
    aggregations = sorted(
        summary.macro_aggregations, key=lambda aggregation: aggregation.payload_size
    )
    payload_sizes = [aggregation.payload_size for aggregation in aggregations]

    latency_means, latency_cis = macro_latency_statistics(aggregations)
    latency_means = to_microseconds(latency_means)
    latency_cis = to_microseconds(latency_cis)
    cycles = macro_cycle_statistics(aggregations)

    plot_macro_latency(
        payload_sizes, latency_means, latency_cis, str(result_directory / LATENCY_PLOT)
    )
    plot_macro_cpu_cycles(
        payload_sizes, cycles, str(result_directory / CPU_CYCLES_PLOT)
    )

    report_data = {
        "payload_sizes": payload_sizes,
        "repetition_counts": [len(aggregation.cases) for aggregation in aggregations],
        "message_counts": [
            [
                len(case.publisher_timestamps)
                for case in sorted(aggregation.cases, key=lambda case: case.repetition)
            ]
            for aggregation in aggregations
        ],
        "latency_means": latency_means,
        "latency_cis": latency_cis,
        "cycles": cycles,
        "plots": {"latency": LATENCY_PLOT, "cpu_cycles": CPU_CYCLES_PLOT},
    }
    write_macro_report(
        report_data,
        str(TEMPLATE_DIR / REPORT_TEMPLATE_NAME),
        str(result_directory / REPORT_NAME),
    )


def main():

    load_dotenv(ENVIRONMENT_FILE, override=True)
    result_directory = PROJECT_ROOT / os.environ["MACRO_RESULT_DIR"]
    generate_report(result_directory)


if __name__ == "__main__":
    main()
