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
    ADDITIONAL_OVERHEAD_BYTES,
    MB_PER_SECOND,
    NS_PER_OP,
    THROTTLED as TIMING_THROTTLED,
)
from report.render.chart import (
    plot_aes_ascon_energy,
    plot_aes_ascon_latency,
    plot_aes_ascon_throughput,
)
from report.render.formatting import NS_PER_MICROSECOND
from report.render.html import write_aes_ascon_report

# Project Root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Environment File
ENVIRONMENT_FILE = PROJECT_ROOT / "environment" / "benchmark.env"

# Benchmark
BENCHMARK_PREFIX = "BenchmarkAESASCON"
PARAMETER = "payload_size"
PARAMETER_SUFFIX = "B"

# Results
TIMING_RESULT_NAME = "timing.txt"
ENERGY_RESULT_NAME = "energy.txt"
REPORT_TEMPLATE_NAME = "aes_ascon_template.html"

# Plots
LATENCY_PLOT = "latency.png"
THROUGHPUT_PLOT = "throughput.png"
ENERGY_PLOT = "energy.png"

# Unit Conversion
MICROJOULES_PER_JOULE = 1_000_000


# Collect timing aggregations in payload-size order
def collect_timing_aggregations(
    summary: BenchmarkSummary,
    algorithm: str,
    operation: str,
    payload_sizes: list[int],
) -> list[TimingAggregation]:

    matching_aggregations = {
        aggregation.parameter_value: aggregation
        for aggregation in summary.timing_aggregations
        if aggregation.algorithm == algorithm
        and aggregation.operation == operation
        and aggregation.parameter == PARAMETER
    }

    return [matching_aggregations[payload_size] for payload_size in payload_sizes]


# Collect energy aggregations in payload-size order
def collect_energy_aggregations(
    summary: BenchmarkSummary,
    algorithm: str,
    operation: str,
    payload_sizes: list[int],
) -> list[EnergyAggregation]:

    matching_aggregations = {
        aggregation.parameter_value: aggregation
        for aggregation in summary.energy_aggregations
        if aggregation.algorithm == algorithm
        and aggregation.operation == operation
        and aggregation.parameter == PARAMETER
    }

    return [matching_aggregations[payload_size] for payload_size in payload_sizes]


# Collect deterministic additional overhead
def collect_overhead(
    aggregations: list[TimingAggregation],
) -> list[float]:

    return [
        aggregation.cases[0].measurements[ADDITIONAL_OVERHEAD_BYTES]
        for aggregation in aggregations
    ]


# Collect total benchmark iterations
def collect_iterations(
    aggregations: list[TimingAggregation],
) -> list[int]:

    return [
        sum(case.iterations for case in aggregation.cases)
        for aggregation in aggregations
    ]


# Check whether each timing aggregation experienced throttling
def collect_timing_throttle_flags(
    aggregations: list[TimingAggregation],
) -> list[bool]:

    return [
        any(case.measurements[TIMING_THROTTLED] > 0 for case in aggregation.cases)
        for aggregation in aggregations
    ]


# Check whether each energy aggregation experienced throttling
def collect_energy_throttle_flags(
    aggregations: list[EnergyAggregation],
) -> list[bool]:

    return [
        any(case.measurements[ENERGY_THROTTLED] > 0 for case in aggregation.cases)
        for aggregation in aggregations
    ]


# Convert nanoseconds to microseconds
def to_microseconds(
    values: list[float],
) -> list[float]:

    return [value / NS_PER_MICROSECOND for value in values]


# Convert joules to microjoules
def to_microjoules(
    values: list[float],
) -> list[float]:

    return [value * MICROJOULES_PER_JOULE for value in values]


# Analyze one algorithm and operation combination
def analyze_case(
    timing_aggregations: list[TimingAggregation],
    energy_aggregations: list[EnergyAggregation],
):

    latency_means, latency_cis = timing_statistics(
        timing_aggregations,
        NS_PER_OP,
    )

    throughput_means, throughput_cis = timing_statistics(
        timing_aggregations,
        MB_PER_SECOND,
    )

    energy_means, energy_cis = energy_statistics(
        energy_aggregations,
    )

    return {
        "latency_means": latency_means,
        "latency_cis": latency_cis,
        "throughput_means": throughput_means,
        "throughput_cis": throughput_cis,
        "energy_means": to_microjoules(energy_means),
        "energy_cis": to_microjoules(energy_cis),
        "overhead_bytes": collect_overhead(timing_aggregations),
        "iterations": collect_iterations(timing_aggregations),
        "timing_throttled": collect_timing_throttle_flags(timing_aggregations),
        "energy_throttled": collect_energy_throttle_flags(energy_aggregations),
    }


def main():

    # Load Environment Variables
    load_dotenv(
        ENVIRONMENT_FILE,
        override=True,
    )

    runs = parse_int_env("AES_ASCON_RUNS")
    payload_sizes = parse_int_list_env("AES_ASCON_PAYLOAD_SIZES")
    warmup_duration = parse_int_env("WARMUP_DURATION")
    measurement_duration = parse_int_env("MEASUREMENT_DURATION")

    # Result Files
    result_directory = PROJECT_ROOT / os.environ["AES_ASCON_RESULT_DIR"]

    timing_result_file = result_directory / TIMING_RESULT_NAME

    energy_result_file = result_directory / ENERGY_RESULT_NAME

    template_path = Path(TEMPLATE_DIR) / REPORT_TEMPLATE_NAME

    report_path = result_directory / REPORT_NAME

    # Load Benchmark Summary
    summary = load_summary(
        timing_filepath=str(timing_result_file),
        energy_filepath=str(energy_result_file),
        case_prefix=BENCHMARK_PREFIX,
        parameter=PARAMETER,
        warmup_duration=warmup_duration,
        measurement_duration=measurement_duration,
        parameter_suffix=PARAMETER_SUFFIX,
    )

    # Analyze Benchmark Cases
    case_results = {}

    for algorithm in ("AES-GCM", "ASCON"):
        for operation in ("Encrypt", "Decrypt"):

            timing_aggregations = collect_timing_aggregations(
                summary,
                algorithm,
                operation,
                payload_sizes,
            )

            energy_aggregations = collect_energy_aggregations(
                summary,
                algorithm,
                operation,
                payload_sizes,
            )

            case_results[(algorithm, operation)] = analyze_case(
                timing_aggregations,
                energy_aggregations,
            )

    # Prepare Latency Chart Data
    latency_results = {
        case: (
            to_microseconds(values["latency_means"]),
            to_microseconds(values["latency_cis"]),
        )
        for case, values in case_results.items()
    }

    # Prepare Throughput Chart Data
    throughput_results = {
        case: (
            values["throughput_means"],
            values["throughput_cis"],
        )
        for case, values in case_results.items()
    }

    # Prepare Energy Chart Data
    energy_results = {
        case: (
            values["energy_means"],
            values["energy_cis"],
        )
        for case, values in case_results.items()
    }

    # Generate Charts
    plot_aes_ascon_latency(
        payload_sizes,
        latency_results,
        str(result_directory / LATENCY_PLOT),
    )

    plot_aes_ascon_throughput(
        payload_sizes,
        throughput_results,
        str(result_directory / THROUGHPUT_PLOT),
    )

    plot_aes_ascon_energy(
        payload_sizes,
        energy_results,
        str(result_directory / ENERGY_PLOT),
    )

    # Calculate Report Metadata
    total_iterations = sum(
        sum(values["iterations"]) for values in case_results.values()
    )

    # Prepare Report Data
    report_data = {
        "runs": runs,
        "t_multiplier": confidence_interval_multiplier(runs),
        "total_iterations": total_iterations,
        "payload_sizes": payload_sizes,
        "energy_window_start": warmup_duration,
        "energy_window_end": (warmup_duration + measurement_duration),
        "cases": case_results,
        "plots": {
            "latency": LATENCY_PLOT,
            "throughput": THROUGHPUT_PLOT,
            "energy": ENERGY_PLOT,
        },
    }

    # Generate HTML Report
    write_aes_ascon_report(
        report_data,
        str(template_path),
        str(report_path),
    )


if __name__ == "__main__":
    main()
