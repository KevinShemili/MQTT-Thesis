import os
from pathlib import Path

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
from report.render.chart import plot_macro_cpu_cycles, plot_macro_latency
from report.render.html import write_macro_report
from report.render.color import VIOLET, TEAL, AMBER, CRIMSON

REPORT_TEMPLATE_NAME = "macro_template.html"
LATENCY_PLOT = "latency.png"
CPU_CYCLES_PLOT = "cpu_cycles.png"


SCENARIOS = [
    ("tls_json", "TLS + JSON", VIOLET, "-"),
    ("tls_cbor", "TLS + CBOR", VIOLET, "--"),
    ("tls_psk_aes", "TLS + PSK (AES + JSON)", TEAL, "-"),
    ("tls_psk_ascon", "TLS + PSK (ASCON + CBOR)", TEAL, "--"),
    ("tls_rsa_aes_json", "TLS + RSA (AES + JSON)", AMBER, "-"),
    ("tls_rsa_ascon_cbor", "TLS + RSA (ASCON + CBOR)", AMBER, "--"),
    ("tls_cpabe_aes_json", "TLS + CP-ABE (AES + JSON)", CRIMSON, "-"),
    ("tls_cpabe_ascon_cbor", "TLS + CP-ABE (ASCON + CBOR)", CRIMSON, "--"),
]


# Analyze each scenario's recorded sweep and render one comparison report
def generate_report(result_directory: Path) -> None:

    scenarios = []
    for name, label, color, linestyle in SCENARIOS:
        scenario_directory = result_directory / name
        summary = load_macro_summary(
            str(scenario_directory / PUBLISHER_RESULT_NAME),
            str(scenario_directory / SUBSCRIBER_RESULT_NAME),
            name,
        )
        aggregations = sorted(
            summary.macro_aggregations, key=lambda aggregation: aggregation.payload_size
        )
        latency_means, latency_cis = macro_latency_statistics(aggregations)

        scenarios.append(
            {
                "reference": name == SCENARIOS[0][0],
                "label": label,
                "color": color,
                "linestyle": linestyle,
                "payload_sizes": [
                    aggregation.payload_size for aggregation in aggregations
                ],
                "repetition_counts": [
                    len(aggregation.cases) for aggregation in aggregations
                ],
                "message_counts": [
                    [
                        len(case.publisher_timestamps)
                        for case in sorted(
                            aggregation.cases, key=lambda case: case.repetition
                        )
                    ]
                    for aggregation in aggregations
                ],
                "latency_means": to_microseconds(latency_means),
                "latency_cis": to_microseconds(latency_cis),
                "cycles": macro_cycle_statistics(aggregations),
            }
        )

    plot_macro_latency(scenarios, str(result_directory / LATENCY_PLOT))
    plot_macro_cpu_cycles(scenarios, str(result_directory / CPU_CYCLES_PLOT))
    write_macro_report(
        {
            "scenarios": scenarios,
            "plots": {"latency": LATENCY_PLOT, "cpu_cycles": CPU_CYCLES_PLOT},
        },
        str(TEMPLATE_DIR / REPORT_TEMPLATE_NAME),
        str(result_directory / REPORT_NAME),
    )


def main():

    load_dotenv(ENVIRONMENT_FILE, override=True)
    result_directory = PROJECT_ROOT / os.environ["MACRO_RESULT_DIR"]
    generate_report(result_directory)


if __name__ == "__main__":
    main()
