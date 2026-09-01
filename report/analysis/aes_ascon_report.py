import os
from pathlib import Path

from report.analysis.shared.load_summary import load_benchmark_summary
from report.analysis.shared.statistics import (
    confidence_interval_multiplier,
    energy_statistics,
    timing_statistics,
)
from report.config import (
    REPORT_NAME,
    TEMPLATE_DIR,
    parse_int_env,
    parse_int_list_env,
)
from report.model.benchmark_summary import BenchmarkSummary
from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.timing.timing_aggregation import TimingAggregation
from report.model.timing.timing_case import (
    ADDITIONAL_OVERHEAD_BYTES,
    MB_PER_SECOND,
    NS_PER_OP,
    THROTTLED,
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


# Collect additional overhead for each timing aggregation
def collect_overhead(
    aggregations: list[TimingAggregation],
) -> list[float]:

    return [
        aggregation.cases[0].measurements[ADDITIONAL_OVERHEAD_BYTES]
        for aggregation in aggregations
    ]


# Collect total benchmark iterations for each timing aggregation
def collect_iterations(
    aggregations: list[TimingAggregation],
) -> list[int]:

    return [
        sum(case.iterations for case in aggregation.cases)
        for aggregation in aggregations
    ]


# Check whether each aggregation experienced throttling
def collect_throttle_flags(
    aggregations: list[TimingAggregation] | list[EnergyAggregation],
) -> list[bool]:

    return [
        any(case.measurements[THROTTLED] > 0 for case in aggregation.cases)
        for aggregation in aggregations
    ]


# Convert nanoseconds to microseconds
def to_microseconds(values: list[float]) -> list[float]:

    return [value / NS_PER_MICROSECOND for value in values]


# Convert joules to microjoules
def to_microjoules(values: list[float]) -> list[float]:

    return [value * MICROJOULES_PER_JOULE for value in values]


def main():

    # Load Environment Variables
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
    summary = load_benchmark_summary(
        timing_filepath=str(timing_result_file),
        energy_filepath=str(energy_result_file),
        case_prefix=BENCHMARK_PREFIX,
        parameter=PARAMETER,
        warmup_duration=warmup_duration,
        measurement_duration=measurement_duration,
        parameter_suffix=PARAMETER_SUFFIX,
    )

    # TIMING AGGREGATIONS

    aes_encrypt = collect_timing_aggregations(
        summary,
        "AES-GCM",
        "Encrypt",
        payload_sizes,
    )

    aes_decrypt = collect_timing_aggregations(
        summary,
        "AES-GCM",
        "Decrypt",
        payload_sizes,
    )

    ascon_encrypt = collect_timing_aggregations(
        summary,
        "ASCON",
        "Encrypt",
        payload_sizes,
    )

    ascon_decrypt = collect_timing_aggregations(
        summary,
        "ASCON",
        "Decrypt",
        payload_sizes,
    )

    # ENERGY AGGREGATIONS

    aes_encrypt_energy = collect_energy_aggregations(
        summary,
        "AES-GCM",
        "Encrypt",
        payload_sizes,
    )

    aes_decrypt_energy = collect_energy_aggregations(
        summary,
        "AES-GCM",
        "Decrypt",
        payload_sizes,
    )

    ascon_encrypt_energy = collect_energy_aggregations(
        summary,
        "ASCON",
        "Encrypt",
        payload_sizes,
    )

    ascon_decrypt_energy = collect_energy_aggregations(
        summary,
        "ASCON",
        "Decrypt",
        payload_sizes,
    )

    # LATENCY

    (
        aes_encrypt_latency_list,
        aes_encrypt_latency_ci_list,
    ) = timing_statistics(
        aes_encrypt,
        NS_PER_OP,
    )

    (
        aes_decrypt_latency_list,
        aes_decrypt_latency_ci_list,
    ) = timing_statistics(
        aes_decrypt,
        NS_PER_OP,
    )

    (
        ascon_encrypt_latency_list,
        ascon_encrypt_latency_ci_list,
    ) = timing_statistics(
        ascon_encrypt,
        NS_PER_OP,
    )

    (
        ascon_decrypt_latency_list,
        ascon_decrypt_latency_ci_list,
    ) = timing_statistics(
        ascon_decrypt,
        NS_PER_OP,
    )

    # THROUGHPUT

    (
        aes_encrypt_throughput_list,
        aes_encrypt_throughput_ci_list,
    ) = timing_statistics(
        aes_encrypt,
        MB_PER_SECOND,
    )

    (
        aes_decrypt_throughput_list,
        aes_decrypt_throughput_ci_list,
    ) = timing_statistics(
        aes_decrypt,
        MB_PER_SECOND,
    )

    (
        ascon_encrypt_throughput_list,
        ascon_encrypt_throughput_ci_list,
    ) = timing_statistics(
        ascon_encrypt,
        MB_PER_SECOND,
    )

    (
        ascon_decrypt_throughput_list,
        ascon_decrypt_throughput_ci_list,
    ) = timing_statistics(
        ascon_decrypt,
        MB_PER_SECOND,
    )

    # ADDITIONAL OVERHEAD

    aes_encrypt_overhead_list = collect_overhead(aes_encrypt)
    aes_decrypt_overhead_list = collect_overhead(aes_decrypt)
    ascon_encrypt_overhead_list = collect_overhead(ascon_encrypt)
    ascon_decrypt_overhead_list = collect_overhead(ascon_decrypt)

    # ITERATIONS

    aes_encrypt_iterations_list = collect_iterations(aes_encrypt)
    aes_decrypt_iterations_list = collect_iterations(aes_decrypt)
    ascon_encrypt_iterations_list = collect_iterations(ascon_encrypt)
    ascon_decrypt_iterations_list = collect_iterations(ascon_decrypt)

    total_benchmark_iterations = sum(
        aes_encrypt_iterations_list
        + aes_decrypt_iterations_list
        + ascon_encrypt_iterations_list
        + ascon_decrypt_iterations_list
    )

    # ENERGY

    (
        aes_encrypt_energy_list,
        aes_encrypt_energy_ci_list,
    ) = energy_statistics(aes_encrypt_energy)

    (
        aes_decrypt_energy_list,
        aes_decrypt_energy_ci_list,
    ) = energy_statistics(aes_decrypt_energy)

    (
        ascon_encrypt_energy_list,
        ascon_encrypt_energy_ci_list,
    ) = energy_statistics(ascon_encrypt_energy)

    (
        ascon_decrypt_energy_list,
        ascon_decrypt_energy_ci_list,
    ) = energy_statistics(ascon_decrypt_energy)

    # Convert Energy to Microjoules
    aes_encrypt_energy_list = to_microjoules(aes_encrypt_energy_list)
    aes_encrypt_energy_ci_list = to_microjoules(aes_encrypt_energy_ci_list)

    aes_decrypt_energy_list = to_microjoules(aes_decrypt_energy_list)
    aes_decrypt_energy_ci_list = to_microjoules(aes_decrypt_energy_ci_list)

    ascon_encrypt_energy_list = to_microjoules(ascon_encrypt_energy_list)
    ascon_encrypt_energy_ci_list = to_microjoules(ascon_encrypt_energy_ci_list)

    ascon_decrypt_energy_list = to_microjoules(ascon_decrypt_energy_list)
    ascon_decrypt_energy_ci_list = to_microjoules(ascon_decrypt_energy_ci_list)

    # THROTTLING

    aes_encrypt_throttled = (
        collect_throttle_flags(aes_encrypt),
        collect_throttle_flags(aes_encrypt_energy),
    )

    aes_decrypt_throttled = (
        collect_throttle_flags(aes_decrypt),
        collect_throttle_flags(aes_decrypt_energy),
    )

    ascon_encrypt_throttled = (
        collect_throttle_flags(ascon_encrypt),
        collect_throttle_flags(ascon_encrypt_energy),
    )

    ascon_decrypt_throttled = (
        collect_throttle_flags(ascon_decrypt),
        collect_throttle_flags(ascon_decrypt_energy),
    )

    # CHARTS

    plot_aes_ascon_latency(
        payload_sizes,
        to_microseconds(aes_encrypt_latency_list),
        to_microseconds(aes_encrypt_latency_ci_list),
        to_microseconds(ascon_encrypt_latency_list),
        to_microseconds(ascon_encrypt_latency_ci_list),
        to_microseconds(aes_decrypt_latency_list),
        to_microseconds(aes_decrypt_latency_ci_list),
        to_microseconds(ascon_decrypt_latency_list),
        to_microseconds(ascon_decrypt_latency_ci_list),
        str(result_directory / LATENCY_PLOT),
    )

    plot_aes_ascon_throughput(
        payload_sizes,
        aes_encrypt_throughput_list,
        aes_encrypt_throughput_ci_list,
        ascon_encrypt_throughput_list,
        ascon_encrypt_throughput_ci_list,
        aes_decrypt_throughput_list,
        aes_decrypt_throughput_ci_list,
        ascon_decrypt_throughput_list,
        ascon_decrypt_throughput_ci_list,
        str(result_directory / THROUGHPUT_PLOT),
    )

    plot_aes_ascon_energy(
        payload_sizes,
        aes_encrypt_energy_list,
        aes_encrypt_energy_ci_list,
        ascon_encrypt_energy_list,
        ascon_encrypt_energy_ci_list,
        aes_decrypt_energy_list,
        aes_decrypt_energy_ci_list,
        ascon_decrypt_energy_list,
        ascon_decrypt_energy_ci_list,
        str(result_directory / ENERGY_PLOT),
    )

    # HTML REPORT

    write_aes_ascon_report(
        runs=runs,
        t_multiplier=confidence_interval_multiplier(runs),
        total_iterations=total_benchmark_iterations,
        payload_sizes=payload_sizes,
        aes_encrypt_latency_means=aes_encrypt_latency_list,
        aes_encrypt_latency_cis=aes_encrypt_latency_ci_list,
        aes_encrypt_throughput_means=aes_encrypt_throughput_list,
        aes_encrypt_throughput_cis=aes_encrypt_throughput_ci_list,
        aes_encrypt_overhead_bytes=aes_encrypt_overhead_list,
        aes_encrypt_iterations=aes_encrypt_iterations_list,
        aes_encrypt_throttled=aes_encrypt_throttled,
        ascon_encrypt_latency_means=ascon_encrypt_latency_list,
        ascon_encrypt_latency_cis=ascon_encrypt_latency_ci_list,
        ascon_encrypt_throughput_means=ascon_encrypt_throughput_list,
        ascon_encrypt_throughput_cis=ascon_encrypt_throughput_ci_list,
        ascon_encrypt_overhead_bytes=ascon_encrypt_overhead_list,
        ascon_encrypt_iterations=ascon_encrypt_iterations_list,
        ascon_encrypt_throttled=ascon_encrypt_throttled,
        aes_decrypt_latency_means=aes_decrypt_latency_list,
        aes_decrypt_latency_cis=aes_decrypt_latency_ci_list,
        aes_decrypt_throughput_means=aes_decrypt_throughput_list,
        aes_decrypt_throughput_cis=aes_decrypt_throughput_ci_list,
        aes_decrypt_overhead_bytes=aes_decrypt_overhead_list,
        aes_decrypt_iterations=aes_decrypt_iterations_list,
        aes_decrypt_throttled=aes_decrypt_throttled,
        ascon_decrypt_latency_means=ascon_decrypt_latency_list,
        ascon_decrypt_latency_cis=ascon_decrypt_latency_ci_list,
        ascon_decrypt_throughput_means=ascon_decrypt_throughput_list,
        ascon_decrypt_throughput_cis=ascon_decrypt_throughput_ci_list,
        ascon_decrypt_overhead_bytes=ascon_decrypt_overhead_list,
        ascon_decrypt_iterations=ascon_decrypt_iterations_list,
        ascon_decrypt_throttled=ascon_decrypt_throttled,
        aes_encrypt_energy_means=aes_encrypt_energy_list,
        aes_encrypt_energy_cis=aes_encrypt_energy_ci_list,
        ascon_encrypt_energy_means=ascon_encrypt_energy_list,
        ascon_encrypt_energy_cis=ascon_encrypt_energy_ci_list,
        aes_decrypt_energy_means=aes_decrypt_energy_list,
        aes_decrypt_energy_cis=aes_decrypt_energy_ci_list,
        ascon_decrypt_energy_means=ascon_decrypt_energy_list,
        ascon_decrypt_energy_cis=ascon_decrypt_energy_ci_list,
        out_of_memory_operations=[],
        out_of_memory_cases=[],
        latency_plot=LATENCY_PLOT,
        throughput_plot=THROUGHPUT_PLOT,
        energy_plot=ENERGY_PLOT,
        template_path=str(template_path),
        report_path=str(report_path),
    )


if __name__ == "__main__":
    main()
