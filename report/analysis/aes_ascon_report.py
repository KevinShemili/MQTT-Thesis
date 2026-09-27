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
from report.analysis.shared.metrics import (
    MEGABYTE,
    collect_energy_throttle_flags,
    collect_timing_throttle_flags,
    to_megabytes,
    to_microjoules,
    to_microseconds,
)
from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import EnergyCase
from report.model.memory.memory_aggregation import MemoryAggregation
from report.model.memory.memory_case import PEAK_RSS_BYTES
from report.model.timing.timing_aggregation import TimingAggregation
from report.model.timing.timing_case import (
    MB_PER_SECOND,
    NS_PER_OP,
)
from report.render.chart import (
    plot_aes_ascon_energy,
    plot_aes_ascon_energy_reduction,
    plot_aes_ascon_latency,
    plot_aes_ascon_latency_speedup,
    plot_aes_ascon_memory,
    plot_aes_ascon_throughput,
)
from report.render.html import write_aes_ascon_report

# Project Root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Environment File
ENVIRONMENT_FILE = PROJECT_ROOT / "environment" / "benchmark.env"

# Benchmark
PARAMETER = "payload_size"

# Results
TIMING_RESULT_NAME = "timing.csv"
MEMORY_RESULT_NAME = "memory.csv"
ENERGY_RESULT_NAME = "energy.csv"
REPORT_TEMPLATE_NAME = "aes_ascon_template.html"

# Plots
LATENCY_PLOT = "latency.png"
LATENCY_SPEEDUP_PLOT = "latency_speedup.png"
THROUGHPUT_PLOT = "throughput.png"
ENERGY_PLOT = "energy.png"
ENERGY_REDUCTION_PLOT = "energy_reduction.png"
MEMORY_PLOT = "memory.png"


# Analyze one algorithm and operation combination
def analyze_case(
    timing_aggregations: list[TimingAggregation],
    energy_aggregations: list[EnergyAggregation],
    energy_baseline_cases: list[EnergyCase],
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
        energy_baseline_cases,
        timing_aggregations,
    )

    return {
        "latency_means": to_microseconds(latency_means),
        "latency_cis": to_microseconds(latency_cis),
        "throughput_means": throughput_means,
        "throughput_cis": throughput_cis,
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


def main():

    # Load Environment Variables
    load_dotenv(
        ENVIRONMENT_FILE,
        override=True,
    )

    runs = parse_int_env("AES_ASCON_RUNS")
    payload_sizes = parse_int_list_env("PAYLOAD_SIZES")
    warmup_duration = parse_int_env("WARMUP_DURATION")
    measurement_duration = parse_int_env("MEASUREMENT_DURATION")

    # Result Files
    result_directory = PROJECT_ROOT / os.environ["AES_ASCON_RESULT_DIR"]

    timing_result_file = result_directory / TIMING_RESULT_NAME

    memory_result_file = result_directory / MEMORY_RESULT_NAME

    energy_result_file = result_directory / ENERGY_RESULT_NAME

    template_path = TEMPLATE_DIR / REPORT_TEMPLATE_NAME

    report_path = result_directory / REPORT_NAME

    # Load Benchmark Summary
    summary = load_summary(
        timing_filepath=str(timing_result_file),
        memory_filepath=str(memory_result_file),
        energy_filepath=str(energy_result_file),
    )

    # Analyze Benchmark Cases
    case_results = {}
    memory_results = {}

    for algorithm in ("AES-GCM", "ASCON"):
        for operation in ("Encrypt", "Decrypt"):

            timing_aggregations = [
                summary.find_timing_aggregation(
                    algorithm,
                    operation,
                    PARAMETER,
                    payload_size,
                )
                for payload_size in payload_sizes
            ]

            energy_aggregations = [
                summary.find_energy_aggregation(
                    algorithm,
                    operation,
                    PARAMETER,
                    payload_size,
                )
                for payload_size in payload_sizes
            ]

            case_results[(algorithm, operation)] = analyze_case(
                timing_aggregations,
                energy_aggregations,
                summary.energy_baseline_cases,
            )

            memory_aggregations = [
                summary.find_memory_aggregation(
                    algorithm,
                    f"Memory{operation}",
                    PARAMETER,
                    payload_size,
                )
                for payload_size in payload_sizes
            ]
            memory_results[(algorithm, operation)] = analyze_memory_case(
                memory_aggregations
            )

    baseline_memory_mean, baseline_memory_ci = memory_case_statistics(
        summary.memory_baseline_cases,
        PEAK_RSS_BYTES,
    )

    # Prepare Latency Chart Data
    latency_results = {
        case: (
            values["latency_means"],
            values["latency_cis"],
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

    latency_speedups = {
        operation: [
            aes_latency / ascon_latency
            for aes_latency, ascon_latency in zip(
                case_results[("AES-GCM", operation)]["latency_means"],
                case_results[("ASCON", operation)]["latency_means"],
                strict=True,
            )
        ]
        for operation in ("Encrypt", "Decrypt")
    }

    energy_reductions = {
        operation: [
            (aes_energy - ascon_energy) / aes_energy * 100.0
            for aes_energy, ascon_energy in zip(
                case_results[("AES-GCM", operation)]["energy_means"],
                case_results[("ASCON", operation)]["energy_means"],
                strict=True,
            )
        ]
        for operation in ("Encrypt", "Decrypt")
    }

    interpretations = {
        "latency_speedup": {
            "encrypt_min": min(latency_speedups["Encrypt"]),
            "encrypt_max": max(latency_speedups["Encrypt"]),
            "decrypt_min": min(latency_speedups["Decrypt"]),
            "decrypt_max": max(latency_speedups["Decrypt"]),
        },
        "energy_reduction": {
            "encrypt_min": min(energy_reductions["Encrypt"]),
            "encrypt_max": max(energy_reductions["Encrypt"]),
            "decrypt_min": min(energy_reductions["Decrypt"]),
            "decrypt_max": max(energy_reductions["Decrypt"]),
        },
    }

    memory_plot_results = {
        case: (values["means"], values["cis"])
        for case, values in memory_results.items()
    }

    # Generate Charts
    plot_aes_ascon_latency(
        payload_sizes,
        latency_results,
        str(result_directory / LATENCY_PLOT),
    )

    plot_aes_ascon_latency_speedup(
        payload_sizes,
        latency_speedups,
        str(result_directory / LATENCY_SPEEDUP_PLOT),
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

    plot_aes_ascon_energy_reduction(
        payload_sizes,
        energy_reductions,
        str(result_directory / ENERGY_REDUCTION_PLOT),
    )

    plot_aes_ascon_memory(
        payload_sizes,
        memory_plot_results,
        baseline_memory_mean / MEGABYTE,
        str(result_directory / MEMORY_PLOT),
    )

    # Prepare Report Data
    report_data = {
        "runs": runs,
        "payload_sizes": payload_sizes,
        "energy_window_start": warmup_duration,
        "energy_window_end": (warmup_duration + measurement_duration),
        "cases": case_results,
        "interpretations": interpretations,
        "memory": memory_results,
        "baseline_memory_mean": baseline_memory_mean / MEGABYTE,
        "baseline_memory_ci": baseline_memory_ci / MEGABYTE,
        "plots": {
            "latency": LATENCY_PLOT,
            "latency_speedup": LATENCY_SPEEDUP_PLOT,
            "throughput": THROUGHPUT_PLOT,
            "energy": ENERGY_PLOT,
            "energy_reduction": ENERGY_REDUCTION_PLOT,
            "memory": MEMORY_PLOT,
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
