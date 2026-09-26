import os
from pathlib import Path

from dotenv import load_dotenv

from report.analysis.shared.load_summary import load_summary
from report.analysis.shared.parser import parse_int_env, parse_int_list_env
from report.analysis.shared.paths import REPORT_NAME, TEMPLATE_DIR
from report.analysis.shared.statistics import (
    energy_statistics,
    memory_case_statistics,
    memory_statistics,
    timing_statistics,
)
from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import (
    THROTTLED as ENERGY_THROTTLED,
    EnergyCase,
)
from report.model.memory.memory_aggregation import MemoryAggregation
from report.model.memory.memory_case import PEAK_RSS_BYTES
from report.model.timing.timing_aggregation import TimingAggregation
from report.model.timing.timing_case import (
    NS_PER_OP,
    SERIALIZED_BYTES,
    THROTTLED as TIMING_THROTTLED,
)
from report.render.chart import (
    plot_full_schema_energy,
    plot_full_schema_latency,
    plot_full_schema_latency_overview,
    plot_full_schema_memory,
    plot_full_schema_serialized_envelope_size,
)
from report.render.formatting import MEGABYTE, NS_PER_MICROSECOND
from report.render.html import write_full_schema_report

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_FILE = PROJECT_ROOT / "environment" / "benchmark.env"

BENCHMARK_PREFIX = "BenchmarkFullSchema"
PARAMETER = "payload_size"
CONFIGURATIONS = (
    "PSKStandard",
    "PSKLightweight",
    "RSAStandard",
    "RSALightweight",
    "CPABEStandard",
    "CPABELightweight",
)
PARAMETER_BY_ALGORITHM = dict.fromkeys(CONFIGURATIONS, PARAMETER)
PARAMETER_SUFFIX = "B"

TIMING_RESULT_NAME = "timing.txt"
MEMORY_RESULT_NAME = "memory.txt"
ENERGY_RESULT_NAME = "energy.txt"
REPORT_TEMPLATE_NAME = "full_schema_template.html"

LATENCY_PLOT = "latency.png"
LATENCY_OVERVIEW_PLOT = "latency_overview.png"
SERIALIZED_ENVELOPE_SIZE_PLOT = "serialized_envelope_size.png"
ENERGY_PLOT = "energy.png"
MEMORY_PLOT = "memory.png"

MICROJOULES_PER_JOULE = 1_000_000


def collect_envelope_sizes(
    aggregations: list[TimingAggregation],
) -> list[float]:

    return [
        aggregation.cases[0].measurements[SERIALIZED_BYTES]
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


def to_megabytes(values: list[float]) -> list[float]:
    return [value / MEGABYTE for value in values]


def analyze_case(
    timing_aggregations: list[TimingAggregation],
    energy_aggregations: list[EnergyAggregation],
    energy_baseline_cases: list[EnergyCase],
) -> dict:

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


def analyze_memory_case(
    aggregations: list[MemoryAggregation],
) -> dict:

    means, confidence_intervals = memory_statistics(aggregations, PEAK_RSS_BYTES)

    return {
        "means": to_megabytes(means),
        "cis": to_megabytes(confidence_intervals),
    }


def main() -> None:

    load_dotenv(
        ENVIRONMENT_FILE,
        override=True,
    )

    runs = parse_int_env("FULL_SCHEMA_RUNS")
    payload_sizes = parse_int_list_env("FULL_SCHEMA_PAYLOAD_SIZES")
    warmup_duration = parse_int_env("WARMUP_DURATION")
    measurement_duration = parse_int_env("MEASUREMENT_DURATION")

    result_directory = PROJECT_ROOT / os.environ["FULL_SCHEMA_RESULT_DIR"]
    timing_result_file = result_directory / TIMING_RESULT_NAME
    memory_result_file = result_directory / MEMORY_RESULT_NAME
    energy_result_file = result_directory / ENERGY_RESULT_NAME
    template_path = TEMPLATE_DIR / REPORT_TEMPLATE_NAME
    report_path = result_directory / REPORT_NAME

    summary = load_summary(
        timing_filepath=str(timing_result_file),
        memory_filepath=str(memory_result_file),
        energy_filepath=str(energy_result_file),
        case_prefix=BENCHMARK_PREFIX,
        parameter_by_algorithm=PARAMETER_BY_ALGORITHM,
        warmup_duration=warmup_duration,
        measurement_duration=measurement_duration,
        parameter_suffix=PARAMETER_SUFFIX,
    )

    case_results = {}
    memory_results = {}
    envelope_sizes = {}

    for configuration in CONFIGURATIONS:
        for operation in ("Encrypt", "Decrypt"):

            timing_aggregations = [
                summary.find_timing_aggregation(
                    configuration,
                    operation,
                    PARAMETER,
                    payload_size,
                )
                for payload_size in payload_sizes
            ]

            energy_aggregations = [
                summary.find_energy_aggregation(
                    configuration,
                    operation,
                    PARAMETER,
                    payload_size,
                )
                for payload_size in payload_sizes
            ]

            case_results[(configuration, operation)] = analyze_case(
                timing_aggregations,
                energy_aggregations,
                summary.energy_baseline_cases,
            )

            if operation == "Encrypt":
                envelope_sizes[configuration] = collect_envelope_sizes(
                    timing_aggregations
                )

            memory_aggregations = [
                summary.find_memory_aggregation(
                    configuration,
                    f"Memory{operation}",
                    PARAMETER,
                    payload_size,
                )
                for payload_size in payload_sizes
            ]
            memory_results[(configuration, operation)] = analyze_memory_case(
                memory_aggregations
            )

    baseline_memory_mean, baseline_memory_ci = memory_case_statistics(
        summary.memory_baseline_cases,
        PEAK_RSS_BYTES,
    )

    latency_results = {
        case: (
            values["latency_means"],
            values["latency_cis"],
        )
        for case, values in case_results.items()
    }

    energy_results = {
        case: (
            values["energy_means"],
            values["energy_cis"],
        )
        for case, values in case_results.items()
    }

    memory_plot_results = {
        case: (values["means"], values["cis"])
        for case, values in memory_results.items()
    }

    plot_full_schema_latency_overview(
        payload_sizes,
        latency_results,
        str(result_directory / LATENCY_OVERVIEW_PLOT),
    )

    plot_full_schema_latency(
        payload_sizes,
        latency_results,
        str(result_directory / LATENCY_PLOT),
    )

    plot_full_schema_serialized_envelope_size(
        payload_sizes,
        envelope_sizes,
        str(result_directory / SERIALIZED_ENVELOPE_SIZE_PLOT),
    )

    plot_full_schema_energy(
        payload_sizes,
        energy_results,
        str(result_directory / ENERGY_PLOT),
    )

    plot_full_schema_memory(
        payload_sizes,
        memory_plot_results,
        baseline_memory_mean / MEGABYTE,
        str(result_directory / MEMORY_PLOT),
    )

    report_data = {
        "runs": runs,
        "payload_sizes": payload_sizes,
        "cases": case_results,
        "envelope_sizes": envelope_sizes,
        "memory": memory_results,
        "baseline_memory_mean": baseline_memory_mean / MEGABYTE,
        "baseline_memory_ci": baseline_memory_ci / MEGABYTE,
        "plots": {
            "latency": LATENCY_PLOT,
            "latency_overview": LATENCY_OVERVIEW_PLOT,
            "serialized_envelope_size": SERIALIZED_ENVELOPE_SIZE_PLOT,
            "energy": ENERGY_PLOT,
            "memory": MEMORY_PLOT,
        },
    }

    write_full_schema_report(
        report_data,
        str(template_path),
        str(report_path),
    )


if __name__ == "__main__":
    main()
