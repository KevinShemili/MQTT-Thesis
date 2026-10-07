import os

from dotenv import load_dotenv

from report.analysis.shared.load_summary import load_macro_summary
from utility.python.path.path import (
    ENVIRONMENT_FILE,
    PROJECT_ROOT,
    PUBLISHER_RESULT_NAME,
    REPORT_NAME,
    SUBSCRIBER_RESULT_NAME,
    TEMPLATE_DIR,
)
from report.analysis.shared.metrics import to_microseconds
from report.analysis.shared.statistics import (
    macro_cycle_statistics,
    macro_latency_statistics,
)
from report.model.macro.macro_aggregation import MacroAggregation
from report.render.chart import plot_macro_cpu_cycles, plot_macro_latency
from report.render.html import write_macro_report

REPORT_TEMPLATE_NAME = "macro_template.html"
LATENCY_PLOT = "latency.png"
CPU_CYCLES_PLOT = "cpu_cycles.png"


SCENARIOS = (
    "tls",
    "tls_light",
    "tls_psk",
    "tls_psk_light",
    "tls_rsa",
    "tls_rsa_light",
    "tls_cpabe",
    "tls_cpabe_light",
)


# Analyze one scenario's recorded payload sweep
def analyze_case(aggregations: list[MacroAggregation]) -> dict:

    aggregations = sorted(
        aggregations, key=lambda aggregation: aggregation.payload_size
    )
    latency_means, latency_cis = macro_latency_statistics(aggregations)

    return {
        "payload_sizes": [aggregation.payload_size for aggregation in aggregations],
        "repetition_counts": [len(aggregation.cases) for aggregation in aggregations],
        "message_counts": [
            [
                len(case.publisher_timestamps)
                for case in sorted(aggregation.cases, key=lambda case: case.repetition)
            ]
            for aggregation in aggregations
        ],
        "latency_means": to_microseconds(latency_means),
        "latency_cis": to_microseconds(latency_cis),
        "cycles": macro_cycle_statistics(aggregations),
    }


def main():

    # Load Environment Variables
    load_dotenv(ENVIRONMENT_FILE, override=True)

    # Result Files
    result_directory = PROJECT_ROOT / os.environ["MACRO_RESULT_DIR"]
    template_path = TEMPLATE_DIR / REPORT_TEMPLATE_NAME
    report_path = result_directory / REPORT_NAME

    # Load Benchmark Summaries
    summaries = {}
    for name in SCENARIOS:
        scenario_directory = result_directory / name
        summaries[name] = load_macro_summary(
            str(scenario_directory / PUBLISHER_RESULT_NAME),
            str(scenario_directory / SUBSCRIBER_RESULT_NAME),
            name,
        )

    # Analyze Benchmark Cases
    case_results = {}
    for name, summary in summaries.items():
        case_results[name] = analyze_case(summary.macro_aggregations)

    # Generate Charts
    plot_macro_latency(case_results, str(result_directory / LATENCY_PLOT))
    plot_macro_cpu_cycles(case_results, str(result_directory / CPU_CYCLES_PLOT))

    # Prepare Report Data
    report_data = {
        "scenarios": case_results,
        "plots": {"latency": LATENCY_PLOT, "cpu_cycles": CPU_CYCLES_PLOT},
    }

    # Generate HTML Report
    write_macro_report(
        report_data,
        str(template_path),
        str(report_path),
    )


if __name__ == "__main__":
    main()
