import os
from pathlib import Path

from template_builder.chart import *
from template_builder.formatting import *
from template_builder.html import *

from model.benchmark_summary import *
from model.measurement import *
from model.populate_model import *

from config.environment import *

SCENARIO = "json-cbor"
HTML_TEMPLATE_NAME = "json_cbor_template.html"

LATENCY_PLOT = "plot.png"
SIZE_PLOT = "size.png"

BENCHMARK_PREFIX = "BenchmarkEnvelope"


def build_table(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    runs: int,
    operation: str,
    format_name: str,
) -> str:
    rows = []

    for attribute_count in attribute_counts:
        aggregation = results.find_aggregation(operation, format_name, attribute_count)
        assert aggregation is not None

        envelope_size = aggregation.mean(ENVELOPE_BYTES)
        raw_size = aggregation.mean(RAW_BYTES)
        overhead_percent = (envelope_size - raw_size) / raw_size * 100.0

        rows.append(
            [
                str(attribute_count),
                format_mean_with_ci(
                    aggregation.mean(NS_PER_OP),
                    aggregation.confidence_interval(NS_PER_OP),
                ),
                f"{raw_size:,.0f}",
                f"{envelope_size:,.0f}",
                f"{overhead_percent:.2f}%",
                f"{aggregation.iterations:,}",
            ]
        )

    return build_html_table(
        [
            "Attributes",
            "Latency (ns/op)",
            "Raw (B)",
            "Envelope Size (B)",
            "Format Overhead (%)",
            f"Iters (Σ{runs} runs)",
        ],
        rows,
        results.get_throttle_flags(operation, format_name, attribute_counts),
    )


def write_html_report(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    runs: int,
    template_path: str,
    report_path: str,
) -> None:
    placeholders = {
        **build_html_generic_data(
            runs,
            sum(aggregation.iterations for aggregation in results.aggregations),
        ),
        "SerializeJsonTable": build_table(
            results, attribute_counts, runs, "Serialize", "JSON"
        ),
        "SerializeCborTable": build_table(
            results, attribute_counts, runs, "Serialize", "CBOR"
        ),
        "SerializeCborKeyAsIntTable": build_table(
            results, attribute_counts, runs, "Serialize", "CBORKeyAsInt"
        ),
        "DeserializeJsonTable": build_table(
            results, attribute_counts, runs, "Deserialize", "JSON"
        ),
        "DeserializeCborTable": build_table(
            results, attribute_counts, runs, "Deserialize", "CBOR"
        ),
        "DeserializeCborKeyAsIntTable": build_table(
            results, attribute_counts, runs, "Deserialize", "CBORKeyAsInt"
        ),
        "LatencyPlot": LATENCY_PLOT,
        "SizePlot": SIZE_PLOT,
    }

    build_html_report(template_path, report_path, placeholders)


def main() -> None:
    runs = parse_int_env("JSON_CBOR_RUNS")
    attribute_counts = parse_int_list_env("JSON_CBOR_ATTRIBUTE_COUNTS")

    result_dir = Path(
        os.environ.get("JSON_CBOR_RESULT_DIR", f"{DEFAULT_RESULT_ROOT}/{SCENARIO}")
    )
    bench_output = result_dir / BENCH_OUTPUT_NAME
    template_path = Path(TEMPLATE_DIR) / HTML_TEMPLATE_NAME
    report_path = result_dir / REPORT_NAME

    results = BenchmarkSummary()
    load_results(results, str(bench_output), BENCHMARK_PREFIX, "Attrs")

    plot_json_cbor_latency(results, attribute_counts, str(result_dir / LATENCY_PLOT))
    plot_json_cbor_size(results, attribute_counts, str(result_dir / SIZE_PLOT))
    write_html_report(
        results, attribute_counts, runs, str(template_path), str(report_path)
    )


if __name__ == "__main__":
    main()
