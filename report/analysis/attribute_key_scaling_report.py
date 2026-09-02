import os
from pathlib import Path

from dotenv import load_dotenv

from report.analysis.shared.load_summary import load_summary
from report.analysis.shared.statistics import (
    confidence_interval_multiplier,
    energy_statistics,
    linear_regression_statistics,
    memory_case_statistics,
    memory_statistics,
    timing_distribution_statistics,
    timing_statistics,
)
from report.config import REPORT_NAME, TEMPLATE_DIR, parse_int_env, parse_int_list_env
from report.model.benchmark_summary import BenchmarkSummary
from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import (
    THROTTLED as ENERGY_THROTTLED,
    EnergySample,
)
from report.model.memory.memory_aggregation import MemoryAggregation
from report.model.memory.memory_case import PEAK_RSS_BYTES
from report.model.timing.timing_aggregation import TimingAggregation
from report.model.timing.timing_case import (
    CIPHERTEXT_BYTES,
    NS_PER_OP,
    STORED_KEY_BYTES,
    THROTTLED as TIMING_THROTTLED,
    TOTAL_CIPHERTEXT_BYTES,
)
from report.render.chart import (
    plot_attribute_key_scaling_energy,
    plot_attribute_key_scaling_memory,
    plot_ciphertext_size_crossover,
    plot_cpabe_attributes,
    plot_decrypt_latency_comparison,
    plot_encrypt_decrypt_asymmetry,
    plot_encrypt_latency_crossover,
    plot_rsa_key_bits,
    plot_rsa_subscribers,
)
from report.render.formatting import MEGABYTE, NS_PER_MICROSECOND
from report.render.html import write_attribute_key_scaling_report

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_FILE = PROJECT_ROOT / "environment" / "benchmark.env"

BENCHMARK_PREFIX = "BenchmarkAttributeKeyScaling"

TIMING_RESULT_NAME = "timing.txt"
MEMORY_RESULT_NAME = "memory.txt"
ENERGY_RESULT_NAME = "energy.txt"
REPORT_TEMPLATE_NAME = "attribute_key_scaling_template.html"

CPABE_PLOT = "cpabe_attributes.png"
RSA_SUBSCRIBERS_PLOT = "rsa_subscribers.png"
RSA_KEY_BITS_PLOT = "rsa_key_bits.png"
ENERGY_PLOT = "energy.png"
PEAK_MEMORY_PLOT = "peak_memory.png"
CIPHERTEXT_SIZE_CROSSOVER_PLOT = "ciphertext_size_crossover.png"
ENCRYPT_LATENCY_CROSSOVER_PLOT = "encrypt_latency_crossover.png"
DECRYPT_LATENCY_COMPARISON_PLOT = "decrypt_latency_comparison.png"
ASYMMETRY_PLOT = "encrypt_decrypt_asymmetry.png"

CPABE_ATTRIBUTES = "CPABEAttributes"
RSA_SUBSCRIBERS = "RSASubscribers"
RSA_KEY_BITS = "RSAKeyBits"

PARAMETER_BY_ALGORITHM = {
    CPABE_ATTRIBUTES: "attribute_count",
    RSA_SUBSCRIBERS: "subscriber_count",
    RSA_KEY_BITS: "rsa_key_bits",
}

NS_PER_MILLISECOND = 1_000_000.0
MICROJOULES_PER_JOULE = 1_000_000.0


def collect_timing_aggregations(
    summary: BenchmarkSummary,
    algorithm: str,
    operation: str,
    parameter: str,
    parameter_values: list[int],
) -> list[TimingAggregation]:
    matching = {
        aggregation.parameter_value: aggregation
        for aggregation in summary.timing_aggregations
        if aggregation.algorithm == algorithm
        and aggregation.operation == operation
        and aggregation.parameter == parameter
    }
    return [matching[parameter_value] for parameter_value in parameter_values]


def collect_memory_aggregations(
    summary: BenchmarkSummary,
    algorithm: str,
    operation: str,
    parameter: str,
    parameter_values: list[int],
) -> list[MemoryAggregation]:
    matching = {
        aggregation.parameter_value: aggregation
        for aggregation in summary.memory_aggregations
        if aggregation.algorithm == algorithm
        and aggregation.operation == operation
        and aggregation.parameter == parameter
    }
    return [matching[parameter_value] for parameter_value in parameter_values]


def collect_energy_aggregations(
    summary: BenchmarkSummary,
    algorithm: str,
    operation: str,
    parameter: str,
    parameter_values: list[int],
) -> list[EnergyAggregation]:
    matching = {
        aggregation.parameter_value: aggregation
        for aggregation in summary.energy_aggregations
        if aggregation.algorithm == algorithm
        and aggregation.operation == operation
        and aggregation.parameter == parameter
    }
    return [matching[parameter_value] for parameter_value in parameter_values]


def collect_iterations(aggregations: list[TimingAggregation]) -> list[int]:
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


def to_milliseconds(values: list[float]) -> list[float]:
    return [value / NS_PER_MILLISECOND for value in values]


def to_microjoules(values: list[float]) -> list[float]:
    return [value * MICROJOULES_PER_JOULE for value in values]


def to_megabytes(values: list[float]) -> list[float]:
    return [value / MEGABYTE for value in values]


def add_timing_measurement(
    result: dict,
    aggregations: list[TimingAggregation],
    measurement: str,
    name: str,
) -> None:
    means, confidence_intervals = timing_statistics(aggregations, measurement)
    result[f"{name}_means"] = means
    result[f"{name}_cis"] = confidence_intervals


def analyze_case(
    timing_aggregations: list[TimingAggregation],
    energy_aggregations: list[EnergyAggregation],
    energy_baseline_samples: list[EnergySample],
) -> dict:
    latency_means, latency_cis = timing_statistics(timing_aggregations, NS_PER_OP)
    energy_means, energy_cis = energy_statistics(
        energy_aggregations,
        energy_baseline_samples,
    )

    return {
        "latency_means": to_microseconds(latency_means),
        "latency_cis": to_microseconds(latency_cis),
        "energy_means": to_microjoules(energy_means),
        "energy_cis": to_microjoules(energy_cis),
        "iterations": collect_iterations(timing_aggregations),
        "timing_throttled": collect_timing_throttle_flags(timing_aggregations),
        "energy_throttled": collect_energy_throttle_flags(energy_aggregations),
    }


def analyze_keygen_case(
    timing_aggregations: list[TimingAggregation],
    energy_aggregations: list[EnergyAggregation],
    energy_baseline_samples: list[EnergySample],
) -> dict:
    result = analyze_case(
        timing_aggregations,
        energy_aggregations,
        energy_baseline_samples,
    )
    (
        medians,
        minimums,
        maximums,
        first_quartiles,
        third_quartiles,
        interquartile_ranges,
    ) = timing_distribution_statistics(timing_aggregations, NS_PER_OP)

    result.update(
        {
            "medians": to_milliseconds(medians),
            "minimums": to_milliseconds(minimums),
            "maximums": to_milliseconds(maximums),
            "first_quartiles": to_milliseconds(first_quartiles),
            "third_quartiles": to_milliseconds(third_quartiles),
            "iqrs": to_milliseconds(interquartile_ranges),
            "sample_counts": [
                len(aggregation.cases) for aggregation in timing_aggregations
            ],
        }
    )
    add_timing_measurement(result, timing_aggregations, STORED_KEY_BYTES, "stored_key")
    return result


def analyze_memory_case(aggregations: list[MemoryAggregation]) -> dict:
    means, confidence_intervals = memory_statistics(aggregations, PEAK_RSS_BYTES)
    return {
        "means": to_megabytes(means),
        "cis": to_megabytes(confidence_intervals),
        "sample_counts": [len(aggregation.cases) for aggregation in aggregations],
    }


def memory_change(values: list[float]) -> dict:
    first = values[0]
    last = values[-1]
    return {
        "first": first,
        "last": last,
        "absolute_change": last - first,
        "percent_change": (last / first - 1.0) * 100.0,
    }


def slower_operation(
    encrypt_latency: float, decrypt_latency: float
) -> tuple[str, float]:
    if encrypt_latency >= decrypt_latency:
        return "Encrypt", encrypt_latency / decrypt_latency
    return "Decrypt", decrypt_latency / encrypt_latency


def main() -> None:
    load_dotenv(ENVIRONMENT_FILE, override=True)

    runs = parse_int_env("ATTRIBUTE_KEY_SCALING_RUNS")
    attribute_counts = parse_int_list_env("ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT")
    subscriber_counts = parse_int_list_env("ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT")
    rsa_key_bits = parse_int_list_env("ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES")
    fixed_rsa_key_bits = parse_int_env("ATTRIBUTE_KEY_SCALING_FIXED_RSA_KEY_SIZE")
    warmup_duration = parse_int_env("WARMUP_DURATION")
    measurement_duration = parse_int_env("MEASUREMENT_DURATION")

    result_directory = PROJECT_ROOT / os.environ["ATTRIBUTE_KEY_SCALING_RESULT_DIR"]
    template_path = Path(TEMPLATE_DIR) / REPORT_TEMPLATE_NAME
    report_path = result_directory / REPORT_NAME

    summary = load_summary(
        timing_filepath=str(result_directory / TIMING_RESULT_NAME),
        memory_filepath=str(result_directory / MEMORY_RESULT_NAME),
        energy_filepath=str(result_directory / ENERGY_RESULT_NAME),
        case_prefix=BENCHMARK_PREFIX,
        parameter_by_algorithm=PARAMETER_BY_ALGORITHM,
        warmup_duration=warmup_duration,
        measurement_duration=measurement_duration,
    )

    parameter_values_by_algorithm = {
        CPABE_ATTRIBUTES: attribute_counts,
        RSA_SUBSCRIBERS: subscriber_counts,
        RSA_KEY_BITS: rsa_key_bits,
    }
    case_order = (
        (CPABE_ATTRIBUTES, "Encrypt"),
        (CPABE_ATTRIBUTES, "Decrypt"),
        (RSA_SUBSCRIBERS, "Encrypt"),
        (RSA_KEY_BITS, "Encrypt"),
        (RSA_KEY_BITS, "Decrypt"),
        (RSA_KEY_BITS, "KeyGen"),
    )

    case_results = {}
    for algorithm, operation in case_order:
        parameter = PARAMETER_BY_ALGORITHM[algorithm]
        parameter_values = parameter_values_by_algorithm[algorithm]
        timing_aggregations = collect_timing_aggregations(
            summary,
            algorithm,
            operation,
            parameter,
            parameter_values,
        )
        energy_aggregations = collect_energy_aggregations(
            summary,
            algorithm,
            operation,
            parameter,
            parameter_values,
        )

        if operation == "KeyGen":
            result = analyze_keygen_case(
                timing_aggregations,
                energy_aggregations,
                summary.energy_baseline_samples,
            )
        else:
            result = analyze_case(
                timing_aggregations,
                energy_aggregations,
                summary.energy_baseline_samples,
            )

        if (algorithm, operation) in (
            (CPABE_ATTRIBUTES, "Encrypt"),
            (RSA_SUBSCRIBERS, "Encrypt"),
            (RSA_KEY_BITS, "Encrypt"),
        ):
            add_timing_measurement(
                result, timing_aggregations, CIPHERTEXT_BYTES, "ciphertext"
            )
        if (algorithm, operation) == (RSA_SUBSCRIBERS, "Encrypt"):
            add_timing_measurement(
                result,
                timing_aggregations,
                TOTAL_CIPHERTEXT_BYTES,
                "total_ciphertext",
            )
        if (algorithm, operation) == (CPABE_ATTRIBUTES, "Decrypt"):
            add_timing_measurement(
                result, timing_aggregations, STORED_KEY_BYTES, "stored_key"
            )

        case_results[(algorithm, operation)] = result

    baseline_memory_mean, baseline_memory_ci = memory_case_statistics(
        summary.memory_baseline_cases,
        PEAK_RSS_BYTES,
    )

    memory_results = {}
    memory_order = (
        (CPABE_ATTRIBUTES, "Encrypt"),
        (CPABE_ATTRIBUTES, "Decrypt"),
        (RSA_SUBSCRIBERS, "Encrypt"),
        (RSA_KEY_BITS, "Encrypt"),
        (RSA_KEY_BITS, "Decrypt"),
    )
    for algorithm, operation in memory_order:
        aggregations = collect_memory_aggregations(
            summary,
            algorithm,
            f"Memory{operation}",
            PARAMETER_BY_ALGORITHM[algorithm],
            parameter_values_by_algorithm[algorithm],
        )
        memory_results[(algorithm, operation)] = analyze_memory_case(aggregations)

    fixed_rsa_index = rsa_key_bits.index(fixed_rsa_key_bits)
    fixed_rsa_decrypt_latency = case_results[(RSA_KEY_BITS, "Decrypt")][
        "latency_means"
    ][fixed_rsa_index]
    fixed_rsa_decrypt_memory = memory_results[(RSA_KEY_BITS, "Decrypt")]["means"][
        fixed_rsa_index
    ]
    fixed_rsa_decrypt_memory_ci = memory_results[(RSA_KEY_BITS, "Decrypt")]["cis"][
        fixed_rsa_index
    ]

    regressions = {
        "cpabe_encrypt": linear_regression_statistics(
            attribute_counts,
            case_results[(CPABE_ATTRIBUTES, "Encrypt")]["latency_means"],
        ),
        "cpabe_decrypt": linear_regression_statistics(
            attribute_counts,
            case_results[(CPABE_ATTRIBUTES, "Decrypt")]["latency_means"],
        ),
        "cpabe_ciphertext": linear_regression_statistics(
            attribute_counts,
            case_results[(CPABE_ATTRIBUTES, "Encrypt")]["ciphertext_means"],
        ),
        "cpabe_stored_key": linear_regression_statistics(
            attribute_counts,
            case_results[(CPABE_ATTRIBUTES, "Decrypt")]["stored_key_means"],
        ),
        "subscriber_encrypt": linear_regression_statistics(
            subscriber_counts,
            case_results[(RSA_SUBSCRIBERS, "Encrypt")]["latency_means"],
        ),
    }

    cpabe_encrypt = case_results[(CPABE_ATTRIBUTES, "Encrypt")]
    cpabe_decrypt = case_results[(CPABE_ATTRIBUTES, "Decrypt")]
    subscriber_encrypt = case_results[(RSA_SUBSCRIBERS, "Encrypt")]
    rsa_encrypt = case_results[(RSA_KEY_BITS, "Encrypt")]
    rsa_decrypt = case_results[(RSA_KEY_BITS, "Decrypt")]

    bytes_per_subscriber = subscriber_encrypt["ciphertext_means"][0]
    bytes_crossover_low = cpabe_encrypt["ciphertext_means"][0] / bytes_per_subscriber
    bytes_crossover_high = cpabe_encrypt["ciphertext_means"][-1] / bytes_per_subscriber

    subscriber_slope, subscriber_intercept, _, _ = regressions["subscriber_encrypt"]
    latency_crossover_low = (
        cpabe_encrypt["latency_means"][0] - subscriber_intercept
    ) / subscriber_slope
    latency_crossover_high = (
        cpabe_encrypt["latency_means"][-1] - subscriber_intercept
    ) / subscriber_slope

    decrypt_penalty_low = cpabe_decrypt["latency_means"][0] / fixed_rsa_decrypt_latency
    decrypt_penalty_high = (
        cpabe_decrypt["latency_means"][-1] / fixed_rsa_decrypt_latency
    )

    rsa_slower_operation, rsa_ratio = slower_operation(
        rsa_encrypt["latency_means"][fixed_rsa_index],
        fixed_rsa_decrypt_latency,
    )
    cpabe_slower_operation, cpabe_ratio = slower_operation(
        cpabe_encrypt["latency_means"][0],
        cpabe_decrypt["latency_means"][0],
    )

    memory_changes = {
        "cpabe_encrypt": memory_change(
            memory_results[(CPABE_ATTRIBUTES, "Encrypt")]["means"]
        ),
        "cpabe_decrypt": memory_change(
            memory_results[(CPABE_ATTRIBUTES, "Decrypt")]["means"]
        ),
        "subscriber_encrypt": memory_change(
            memory_results[(RSA_SUBSCRIBERS, "Encrypt")]["means"]
        ),
        "rsa_encrypt": memory_change(
            memory_results[(RSA_KEY_BITS, "Encrypt")]["means"]
        ),
        "rsa_decrypt": memory_change(
            memory_results[(RSA_KEY_BITS, "Decrypt")]["means"]
        ),
    }

    projection_end_subscribers = latency_crossover_high * 1.15
    comparisons = {
        "bytes_per_subscriber": bytes_per_subscriber,
        "bytes_crossover_low": bytes_crossover_low,
        "bytes_crossover_high": bytes_crossover_high,
        "latency_crossover_low": latency_crossover_low,
        "latency_crossover_high": latency_crossover_high,
        "decrypt_penalty_low": decrypt_penalty_low,
        "decrypt_penalty_high": decrypt_penalty_high,
        "ciphertext": {
            "rsa_means": subscriber_encrypt["total_ciphertext_means"],
            "rsa_cis": subscriber_encrypt["total_ciphertext_cis"],
            "low_attribute_count": attribute_counts[0],
            "low_cpabe_level": cpabe_encrypt["ciphertext_means"][0],
            "low_crossover": bytes_crossover_low,
            "high_attribute_count": attribute_counts[-1],
            "high_cpabe_level": cpabe_encrypt["ciphertext_means"][-1],
            "high_crossover": bytes_crossover_high,
        },
        "encrypt": {
            "rsa_means": subscriber_encrypt["latency_means"],
            "rsa_cis": subscriber_encrypt["latency_cis"],
            "projection_start_subscribers": float(subscriber_counts[-1]),
            "projection_start_micros": subscriber_intercept
            + subscriber_slope * subscriber_counts[-1],
            "projection_end_subscribers": projection_end_subscribers,
            "projection_end_micros": subscriber_intercept
            + subscriber_slope * projection_end_subscribers,
            "low_attribute_count": attribute_counts[0],
            "low_cpabe_level": cpabe_encrypt["latency_means"][0],
            "low_crossover": latency_crossover_low,
            "high_attribute_count": attribute_counts[-1],
            "high_cpabe_level": cpabe_encrypt["latency_means"][-1],
            "high_crossover": latency_crossover_high,
        },
        "decrypt": {
            "cpabe_means": cpabe_decrypt["latency_means"],
            "cpabe_cis": cpabe_decrypt["latency_cis"],
            "rsa_key_bits": rsa_key_bits,
            "rsa_means": rsa_decrypt["latency_means"],
            "rsa_cis": rsa_decrypt["latency_cis"],
        },
        "asymmetry": {
            "fixed_rsa_key_bits": fixed_rsa_key_bits,
            "min_attribute_count": attribute_counts[0],
            "rsa_encrypt_micros": rsa_encrypt["latency_means"][fixed_rsa_index],
            "rsa_decrypt_micros": fixed_rsa_decrypt_latency,
            "rsa_slower_operation": rsa_slower_operation,
            "rsa_ratio": rsa_ratio,
            "cpabe_encrypt_micros": cpabe_encrypt["latency_means"][0],
            "cpabe_decrypt_micros": cpabe_decrypt["latency_means"][0],
            "cpabe_slower_operation": cpabe_slower_operation,
            "cpabe_ratio": cpabe_ratio,
        },
    }

    plot_cpabe_attributes(
        attribute_counts,
        {
            "encrypt_latency": (
                cpabe_encrypt["latency_means"],
                cpabe_encrypt["latency_cis"],
            ),
            "decrypt_latency": (
                cpabe_decrypt["latency_means"],
                cpabe_decrypt["latency_cis"],
            ),
            "ciphertext": (
                cpabe_encrypt["ciphertext_means"],
                cpabe_encrypt["ciphertext_cis"],
            ),
            "stored_key": (
                cpabe_decrypt["stored_key_means"],
                cpabe_decrypt["stored_key_cis"],
            ),
        },
        str(result_directory / CPABE_PLOT),
    )
    plot_rsa_subscribers(
        subscriber_counts,
        {
            "encrypt_latency": (
                subscriber_encrypt["latency_means"],
                subscriber_encrypt["latency_cis"],
            ),
            "decrypt_latency": fixed_rsa_decrypt_latency,
            "ciphertext": (
                subscriber_encrypt["ciphertext_means"],
                subscriber_encrypt["ciphertext_cis"],
            ),
            "total_ciphertext": (
                subscriber_encrypt["total_ciphertext_means"],
                subscriber_encrypt["total_ciphertext_cis"],
            ),
        },
        fixed_rsa_key_bits,
        str(result_directory / RSA_SUBSCRIBERS_PLOT),
    )
    keygen = case_results[(RSA_KEY_BITS, "KeyGen")]
    plot_rsa_key_bits(
        rsa_key_bits,
        {
            "keygen": keygen,
            "encrypt_latency": (
                rsa_encrypt["latency_means"],
                rsa_encrypt["latency_cis"],
            ),
            "decrypt_latency": (
                rsa_decrypt["latency_means"],
                rsa_decrypt["latency_cis"],
            ),
            "ciphertext": (
                rsa_encrypt["ciphertext_means"],
                rsa_encrypt["ciphertext_cis"],
            ),
            "stored_key": (
                keygen["stored_key_means"],
                keygen["stored_key_cis"],
            ),
        },
        str(result_directory / RSA_KEY_BITS_PLOT),
    )

    energy_chart_results = {
        key: (value["energy_means"], value["energy_cis"])
        for key, value in case_results.items()
    }
    plot_attribute_key_scaling_energy(
        parameter_values_by_algorithm,
        energy_chart_results,
        str(result_directory / ENERGY_PLOT),
    )
    plot_attribute_key_scaling_memory(
        parameter_values_by_algorithm,
        {key: (value["means"], value["cis"]) for key, value in memory_results.items()},
        fixed_rsa_key_bits,
        fixed_rsa_decrypt_memory,
        str(result_directory / PEAK_MEMORY_PLOT),
    )
    plot_ciphertext_size_crossover(
        subscriber_counts,
        comparisons["ciphertext"],
        str(result_directory / CIPHERTEXT_SIZE_CROSSOVER_PLOT),
    )
    plot_encrypt_latency_crossover(
        subscriber_counts,
        comparisons["encrypt"],
        str(result_directory / ENCRYPT_LATENCY_CROSSOVER_PLOT),
    )
    plot_decrypt_latency_comparison(
        attribute_counts,
        comparisons["decrypt"],
        str(result_directory / DECRYPT_LATENCY_COMPARISON_PLOT),
    )
    plot_encrypt_decrypt_asymmetry(
        comparisons["asymmetry"],
        str(result_directory / ASYMMETRY_PLOT),
    )

    total_iterations = sum(
        sum(result["iterations"]) for result in case_results.values()
    )
    report_data = {
        "runs": runs,
        "t_multiplier": confidence_interval_multiplier(runs),
        "total_iterations": total_iterations,
        "attribute_counts": attribute_counts,
        "subscriber_counts": subscriber_counts,
        "rsa_key_bits": rsa_key_bits,
        "fixed_rsa_key_bits": fixed_rsa_key_bits,
        "energy_window_start": warmup_duration,
        "energy_window_end": warmup_duration + measurement_duration,
        "cases": case_results,
        "memory": memory_results,
        "baseline_memory_mean": baseline_memory_mean / MEGABYTE,
        "baseline_memory_ci": baseline_memory_ci / MEGABYTE,
        "fixed_rsa_decrypt_memory": fixed_rsa_decrypt_memory,
        "fixed_rsa_decrypt_memory_ci": fixed_rsa_decrypt_memory_ci,
        "memory_changes": memory_changes,
        "regressions": regressions,
        "comparisons": comparisons,
        "plots": {
            "cpabe": CPABE_PLOT,
            "rsa_subscribers": RSA_SUBSCRIBERS_PLOT,
            "rsa_key_bits": RSA_KEY_BITS_PLOT,
            "energy": ENERGY_PLOT,
            "peak_memory": PEAK_MEMORY_PLOT,
            "ciphertext_crossover": CIPHERTEXT_SIZE_CROSSOVER_PLOT,
            "encrypt_crossover": ENCRYPT_LATENCY_CROSSOVER_PLOT,
            "decrypt_comparison": DECRYPT_LATENCY_COMPARISON_PLOT,
            "asymmetry": ASYMMETRY_PLOT,
        },
    }
    write_attribute_key_scaling_report(
        report_data,
        str(template_path),
        str(report_path),
    )


if __name__ == "__main__":
    main()
