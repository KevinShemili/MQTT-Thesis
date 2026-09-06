import os
from pathlib import Path

from dotenv import load_dotenv

from report.analysis.shared.load_summary import load_summary
from report.analysis.shared.statistics import (
    energy_baseline_statistics,
    energy_statistics,
    timing_statistics,
)
from report.config import REPORT_NAME, TEMPLATE_DIR, parse_int_env, parse_int_list_env
from report.model.benchmark_summary import BenchmarkSummary
from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import (
    THROTTLED as ENERGY_THROTTLED,
    EnergyCase,
)
from report.model.timing.timing_aggregation import TimingAggregation
from report.model.timing.timing_case import (
    ENVELOPE_BYTES,
    NS_PER_OP,
    THROTTLED as TIMING_THROTTLED,
)
from report.render.chart import (
    plot_json_cbor_energy,
    plot_json_cbor_energy_reduction,
    plot_json_cbor_latency,
    plot_json_cbor_latency_speedup,
    plot_json_cbor_size,
    plot_json_cbor_size_reduction,
)
from report.render.formatting import NS_PER_MICROSECOND
from report.render.html import write_json_cbor_report

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_FILE = PROJECT_ROOT / "environment" / "benchmark.env"

BENCHMARK_PREFIX = "BenchmarkEnvelope"
PARAMETER = "attribute_count"
PARAMETER_BY_ALGORITHM = {
    "JSON": PARAMETER,
    "CBOR": PARAMETER,
    "CBORKeyAsInt": PARAMETER,
}
PARAMETER_SUFFIX = "Attrs"

TIMING_RESULT_NAME = "timing.txt"
ENERGY_RESULT_NAME = "energy.txt"
REPORT_TEMPLATE_NAME = "json_cbor_template.html"

LATENCY_PLOT = "latency.png"
LATENCY_SPEEDUP_PLOT = "latency_speedup.png"
SIZE_PLOT = "size.png"
SIZE_REDUCTION_PLOT = "size_reduction.png"
ENERGY_PLOT = "energy.png"
ENERGY_REDUCTION_PLOT = "energy_reduction.png"

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
    energy_baseline_cases: list[EnergyCase],
):

    latency_means, latency_cis = timing_statistics(
        timing_aggregations,
        NS_PER_OP,
    )

    energy_means, energy_cis = energy_statistics(
        energy_aggregations,
        energy_baseline_cases,
    )

    return {
        "latency_means": to_microseconds(latency_means),
        "latency_cis": to_microseconds(latency_cis),
        "energy_means": to_microjoules(energy_means),
        "energy_cis": to_microjoules(energy_cis),
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
    baseline_duration = parse_int_env("BASELINE_DURATION")
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
        parameter_by_algorithm=PARAMETER_BY_ALGORITHM,
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
                summary.energy_baseline_cases,
            )

    latency_results = {
        case: (
            values["latency_means"],
            values["latency_cis"],
        )
        for case, values in case_results.items()
    }

    size_results = {}
    for format_name in ("JSON", "CBOR", "CBORKeyAsInt"):
        serialization_aggregations = collect_timing_aggregations(
            summary,
            format_name,
            "Serialize",
            attribute_counts,
        )
        size_results[format_name] = [
            int(aggregation.cases[0].measurements[ENVELOPE_BYTES])
            for aggregation in serialization_aggregations
        ]

    energy_results = {
        case: (
            values["energy_means"],
            values["energy_cis"],
        )
        for case, values in case_results.items()
    }

    latency_speedups = {
        (format_name, operation): [
            json_latency / alternative_latency
            for json_latency, alternative_latency in zip(
                case_results[("JSON", operation)]["latency_means"],
                case_results[(format_name, operation)]["latency_means"],
                strict=True,
            )
        ]
        for format_name in ("CBOR", "CBORKeyAsInt")
        for operation in ("Serialize", "Deserialize")
    }

    size_reductions = {
        format_name: [
            (json_size - alternative_size) / json_size * 100.0
            for json_size, alternative_size in zip(
                size_results["JSON"],
                size_results[format_name],
                strict=True,
            )
        ]
        for format_name in ("CBOR", "CBORKeyAsInt")
    }

    integer_key_size_reductions = [
        (cbor_size - integer_key_size) / cbor_size * 100.0
        for cbor_size, integer_key_size in zip(
            size_results["CBOR"],
            size_results["CBORKeyAsInt"],
            strict=True,
        )
    ]

    energy_reductions = {
        (format_name, operation): [
            (json_energy - alternative_energy) / json_energy * 100.0
            for json_energy, alternative_energy in zip(
                case_results[("JSON", operation)]["energy_means"],
                case_results[(format_name, operation)]["energy_means"],
                strict=True,
            )
        ]
        for format_name in ("CBOR", "CBORKeyAsInt")
        for operation in ("Serialize", "Deserialize")
    }

    interpretations = {
        "latency_speedup": {
            "serialize_cbor_min": min(latency_speedups[("CBOR", "Serialize")]),
            "serialize_cbor_max": max(latency_speedups[("CBOR", "Serialize")]),
            "serialize_cbor_int_min": min(
                latency_speedups[("CBORKeyAsInt", "Serialize")]
            ),
            "serialize_cbor_int_max": max(
                latency_speedups[("CBORKeyAsInt", "Serialize")]
            ),
            "deserialize_cbor_min": min(latency_speedups[("CBOR", "Deserialize")]),
            "deserialize_cbor_max": max(latency_speedups[("CBOR", "Deserialize")]),
            "deserialize_cbor_int_min": min(
                latency_speedups[("CBORKeyAsInt", "Deserialize")]
            ),
            "deserialize_cbor_int_max": max(
                latency_speedups[("CBORKeyAsInt", "Deserialize")]
            ),
        },
        "size_reduction": {
            "cbor_min": min(size_reductions["CBOR"]),
            "cbor_max": max(size_reductions["CBOR"]),
            "cbor_int_min": min(size_reductions["CBORKeyAsInt"]),
            "cbor_int_max": max(size_reductions["CBORKeyAsInt"]),
        },
        "integer_key_size_reduction": {
            "additional_bytes": size_results["CBOR"][0]
            - size_results["CBORKeyAsInt"][0],
            "first": integer_key_size_reductions[0],
            "last": integer_key_size_reductions[-1],
        },
        "energy_reduction": {
            "serialize_cbor_min": min(energy_reductions[("CBOR", "Serialize")]),
            "serialize_cbor_max": max(energy_reductions[("CBOR", "Serialize")]),
            "serialize_cbor_int_min": min(
                energy_reductions[("CBORKeyAsInt", "Serialize")]
            ),
            "serialize_cbor_int_max": max(
                energy_reductions[("CBORKeyAsInt", "Serialize")]
            ),
            "deserialize_cbor_min": min(energy_reductions[("CBOR", "Deserialize")]),
            "deserialize_cbor_max": max(energy_reductions[("CBOR", "Deserialize")]),
            "deserialize_cbor_int_min": min(
                energy_reductions[("CBORKeyAsInt", "Deserialize")]
            ),
            "deserialize_cbor_int_max": max(
                energy_reductions[("CBORKeyAsInt", "Deserialize")]
            ),
        },
    }

    plot_json_cbor_latency(
        attribute_counts,
        latency_results,
        str(result_directory / LATENCY_PLOT),
    )

    plot_json_cbor_latency_speedup(
        attribute_counts,
        latency_speedups,
        str(result_directory / LATENCY_SPEEDUP_PLOT),
    )

    plot_json_cbor_size(
        attribute_counts,
        size_results,
        str(result_directory / SIZE_PLOT),
    )

    plot_json_cbor_size_reduction(
        attribute_counts,
        size_reductions,
        str(result_directory / SIZE_REDUCTION_PLOT),
    )

    plot_json_cbor_energy(
        attribute_counts,
        energy_results,
        str(result_directory / ENERGY_PLOT),
    )

    plot_json_cbor_energy_reduction(
        attribute_counts,
        energy_reductions,
        str(result_directory / ENERGY_REDUCTION_PLOT),
    )

    energy_baseline_mean, energy_baseline_ci = energy_baseline_statistics(
        summary.energy_baseline_cases,
        baseline_duration,
    )

    report_data = {
        "runs": runs,
        "energy_baseline_mean": energy_baseline_mean,
        "energy_baseline_ci": energy_baseline_ci,
        "energy_baseline_duration": baseline_duration,
        "attribute_counts": attribute_counts,
        "sizes": size_results,
        "energy_window_start": warmup_duration,
        "energy_window_end": warmup_duration + measurement_duration,
        "cases": case_results,
        "interpretations": interpretations,
        "plots": {
            "latency": LATENCY_PLOT,
            "latency_speedup": LATENCY_SPEEDUP_PLOT,
            "size": SIZE_PLOT,
            "size_reduction": SIZE_REDUCTION_PLOT,
            "energy": ENERGY_PLOT,
            "energy_reduction": ENERGY_REDUCTION_PLOT,
        },
    }

    write_json_cbor_report(
        report_data,
        str(template_path),
        str(report_path),
    )


if __name__ == "__main__":
    main()
