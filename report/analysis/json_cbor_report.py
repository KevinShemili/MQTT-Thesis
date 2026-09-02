import os
from pathlib import Path

from dotenv import load_dotenv

from report.analysis.shared.load_summary import load_summary
from report.analysis.shared.statistics import (
    confidence_interval_multiplier,
    energy_statistics,
    timing_statistics,
)
from report.config import REPORT_NAME, TEMPLATE_DIR, parse_int_env, parse_int_list_env
from report.model.benchmark_summary import BenchmarkSummary
from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import THROTTLED as ENERGY_THROTTLED
from report.model.timing.timing_aggregation import TimingAggregation
from report.model.timing.timing_case import (
    ENVELOPE_BYTES,
    NS_PER_OP,
    RAW_BYTES,
    THROTTLED as TIMING_THROTTLED,
)
from report.render.chart import (
    plot_json_cbor_energy,
    plot_json_cbor_latency,
    plot_json_cbor_size,
)
from report.render.formatting import NS_PER_MICROSECOND
from report.render.html import write_json_cbor_report

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_FILE = PROJECT_ROOT / "environment" / "benchmark.env"

BENCHMARK_PREFIX = "BenchmarkEnvelope"
PARAMETER = "attribute_count"
PARAMETER_SUFFIX = "Attrs"

TIMING_RESULT_NAME = "timing.txt"
ENERGY_RESULT_NAME = "energy.txt"
REPORT_TEMPLATE_NAME = "json_cbor_template.html"

LATENCY_PLOT = "latency.png"
SIZE_PLOT = "size.png"
ENERGY_PLOT = "energy.png"

MICROJOULES_PER_JOULE = 1_000_000


def collect_timing_aggregations(
    summary: BenchmarkSummary,
    format_name: str,
    operation: str,
    attribute_counts: list[int],
) -> list[TimingAggregation]:

    matching_aggregations = {
        aggregation.parameter_value: aggregation
        for aggregation in summary.timing_aggregations
        if aggregation.algorithm == format_name
        and aggregation.operation == operation
        and aggregation.parameter == PARAMETER
    }

    return [
        matching_aggregations[attribute_count] for attribute_count in attribute_counts
    ]


def collect_energy_aggregations(
    summary: BenchmarkSummary,
    format_name: str,
    operation: str,
    attribute_counts: list[int],
) -> list[EnergyAggregation]:

    matching_aggregations = {
        aggregation.parameter_value: aggregation
        for aggregation in summary.energy_aggregations
        if aggregation.algorithm == format_name
        and aggregation.operation == operation
        and aggregation.parameter == PARAMETER
    }

    return [
        matching_aggregations[attribute_count] for attribute_count in attribute_counts
    ]


def collect_iterations(
    aggregations: list[TimingAggregation],
) -> list[int]:

    return [
        sum(case.iterations for case in aggregation.cases)
        for aggregation in aggregations
    ]


def collect_timing_throttle_flags(
    aggregations: list[TimingAggregation],
) -> list[bool]:

    return [
        any(case.measurements[TIMING_THROTTLED] > 0 for case in aggregation.cases)
        for aggregation in aggregations
    ]


def collect_energy_throttle_flags(
    aggregations: list[EnergyAggregation],
) -> list[bool]:

    return [
        any(case.measurements[ENERGY_THROTTLED] > 0 for case in aggregation.cases)
        for aggregation in aggregations
    ]


def to_microseconds(values: list[float]) -> list[float]:
    return [value / NS_PER_MICROSECOND for value in values]


def to_microjoules(values: list[float]) -> list[float]:
    return [value * MICROJOULES_PER_JOULE for value in values]


def analyze_case(
    timing_aggregations: list[TimingAggregation],
    energy_aggregations: list[EnergyAggregation],
):

    latency_means, latency_cis = timing_statistics(
        timing_aggregations,
        NS_PER_OP,
    )

    raw_size_means, raw_size_cis = timing_statistics(
        timing_aggregations,
        RAW_BYTES,
    )

    envelope_size_means, envelope_size_cis = timing_statistics(
        timing_aggregations,
        ENVELOPE_BYTES,
    )

    energy_means, energy_cis = energy_statistics(
        energy_aggregations,
    )

    overhead_bytes = [
        envelope_size - raw_size
        for envelope_size, raw_size in zip(
            envelope_size_means,
            raw_size_means,
            strict=True,
        )
    ]

    overhead_percents = [
        overhead / raw_size * 100.0
        for overhead, raw_size in zip(
            overhead_bytes,
            raw_size_means,
            strict=True,
        )
    ]

    return {
        "latency_means": to_microseconds(latency_means),
        "latency_cis": to_microseconds(latency_cis),
        "raw_size_means": raw_size_means,
        "raw_size_cis": raw_size_cis,
        "envelope_size_means": envelope_size_means,
        "envelope_size_cis": envelope_size_cis,
        "overhead_bytes": overhead_bytes,
        "overhead_percents": overhead_percents,
        "energy_means": to_microjoules(energy_means),
        "energy_cis": to_microjoules(energy_cis),
        "iterations": collect_iterations(timing_aggregations),
        "timing_throttled": collect_timing_throttle_flags(timing_aggregations),
        "energy_throttled": collect_energy_throttle_flags(energy_aggregations),
    }


def main() -> None:

    load_dotenv(
        ENVIRONMENT_FILE,
        override=True,
    )

    runs = parse_int_env("JSON_CBOR_RUNS")
    attribute_counts = parse_int_list_env("JSON_CBOR_ATTRIBUTE_COUNTS")
    warmup_duration = parse_int_env("WARMUP_DURATION")
    measurement_duration = parse_int_env("MEASUREMENT_DURATION")

    result_directory = PROJECT_ROOT / os.environ["JSON_CBOR_RESULT_DIR"]
    timing_result_file = result_directory / TIMING_RESULT_NAME
    energy_result_file = result_directory / ENERGY_RESULT_NAME
    template_path = Path(TEMPLATE_DIR) / REPORT_TEMPLATE_NAME
    report_path = result_directory / REPORT_NAME

    summary = load_summary(
        timing_filepath=str(timing_result_file),
        energy_filepath=str(energy_result_file),
        case_prefix=BENCHMARK_PREFIX,
        parameter=PARAMETER,
        warmup_duration=warmup_duration,
        measurement_duration=measurement_duration,
        parameter_suffix=PARAMETER_SUFFIX,
    )

    case_results = {}

    for format_name in ("JSON", "CBOR", "CBORKeyAsInt"):
        for operation in ("Serialize", "Deserialize"):

            timing_aggregations = collect_timing_aggregations(
                summary,
                format_name,
                operation,
                attribute_counts,
            )

            energy_aggregations = collect_energy_aggregations(
                summary,
                format_name,
                operation,
                attribute_counts,
            )

            case_results[(format_name, operation)] = analyze_case(
                timing_aggregations,
                energy_aggregations,
            )

    latency_results = {
        case: (
            values["latency_means"],
            values["latency_cis"],
        )
        for case, values in case_results.items()
    }

    size_results = {
        format_name: (
            case_results[(format_name, "Serialize")]["envelope_size_means"],
            case_results[(format_name, "Serialize")]["envelope_size_cis"],
            case_results[(format_name, "Serialize")]["overhead_bytes"],
        )
        for format_name in ("JSON", "CBOR", "CBORKeyAsInt")
    }

    energy_results = {
        case: (
            values["energy_means"],
            values["energy_cis"],
        )
        for case, values in case_results.items()
    }

    plot_json_cbor_latency(
        attribute_counts,
        latency_results,
        str(result_directory / LATENCY_PLOT),
    )

    plot_json_cbor_size(
        attribute_counts,
        size_results,
        str(result_directory / SIZE_PLOT),
    )

    plot_json_cbor_energy(
        attribute_counts,
        energy_results,
        str(result_directory / ENERGY_PLOT),
    )

    total_iterations = sum(
        sum(values["iterations"]) for values in case_results.values()
    )

    report_data = {
        "runs": runs,
        "t_multiplier": confidence_interval_multiplier(runs),
        "total_iterations": total_iterations,
        "attribute_counts": attribute_counts,
        "energy_window_start": warmup_duration,
        "energy_window_end": warmup_duration + measurement_duration,
        "cases": case_results,
        "plots": {
            "latency": LATENCY_PLOT,
            "size": SIZE_PLOT,
            "energy": ENERGY_PLOT,
        },
    }

    write_json_cbor_report(
        report_data,
        str(template_path),
        str(report_path),
    )


if __name__ == "__main__":
    main()
