import os
from pathlib import Path

from template_builder.chart import *
from template_builder.formatting import *
from template_builder.html import *

from model.benchmark_summary import *
from model.case_aggregation import *
from model.measurement import *
from model.populate_model import *

from config.environment import *

from statistics_tbd.linear_regression import *
from statistics_tbd.summary import *

NS_PER_MILLISECOND = 1000000.0
NO_MEASUREMENT = float("nan")

SCENARIO = "attribute-key-scaling"
BENCHMARK_PREFIX = "BenchmarkAttributeKeyScaling"
TEMPLATE_NAME = "attribute_key_scaling_template.html"

CPABE_PLOT = "cpabe_attributes.png"
RSA_SUBSCRIBERS_PLOT = "rsa_subscribers.png"
RSA_KEY_BITS_PLOT = "rsa_key_bits.png"
CIPHERTEXT_SIZE_CROSSOVER_PLOT = "ciphertext_size_crossover.png"
ASYMMETRY_PLOT = "encrypt_decrypt_asymmetry.png"
ENCRYPT_LATENCY_CROSSOVER_PLOT = "encrypt_latency_crossover.png"
DECRYPT_LATENCY_CROSSOVER_PLOT = "decrypt_latency_crossover.png"
PEAK_MEMORY_PLOT = "peak_memory.png"

CPABE_ATTRIBUTES = "CPABEAttributes"
RSA_SUBSCRIBERS = "RSASubscribers"
RSA_KEY_BITS = "RSAKeyBits"

MINIMUM_FIT_POINTS = 3


def fit_measurement(
    results: BenchmarkSummary,
    operation: str,
    group: str,
    sweep_values: list[int],
    measurement_name: str,
    divisor: float = 1.0,
) -> LinearRegression | None:
    measured_x = []
    measured_y = []

    for sweep_value in sweep_values:
        aggregation = results.find_aggregation(operation, group, sweep_value)

        if aggregation is None or aggregation.out_of_memory:
            continue

        measured_x.append(sweep_value)
        measured_y.append(aggregation.mean(measurement_name) / divisor)

    if len(measured_x) < MINIMUM_FIT_POINTS:
        return None

    return fit_linear_regression(measured_x, measured_y)


def measurement_means(
    results: BenchmarkSummary,
    operation: str,
    group: str,
    sweep_values: list[int],
    measurement_name: str,
    divisor: float = 1.0,
) -> list[float | None]:
    values = []

    for sweep_value in sweep_values:
        aggregation = results.find_aggregation(operation, group, sweep_value)
        if aggregation is None or aggregation.out_of_memory:
            values.append(None)
        else:
            values.append(aggregation.mean(measurement_name) / divisor)

    return values


def measurement_confidence_intervals(
    results: BenchmarkSummary,
    operation: str,
    group: str,
    sweep_values: list[int],
    measurement_name: str,
    divisor: float = 1.0,
) -> list[float | None]:
    values = []

    for sweep_value in sweep_values:
        aggregation = results.find_aggregation(operation, group, sweep_value)
        if aggregation is None or aggregation.out_of_memory:
            values.append(None)
        else:
            values.append(aggregation.confidence_interval(measurement_name) / divisor)

    return values


def measurement_iterations(
    results: BenchmarkSummary,
    operation: str,
    group: str,
    sweep_values: list[int],
) -> list[int | None]:
    values = []

    for sweep_value in sweep_values:
        aggregation = results.find_aggregation(operation, group, sweep_value)
        if aggregation is None or aggregation.out_of_memory:
            values.append(None)
        else:
            values.append(aggregation.iterations)

    return values


def plotted(values: list[float | None]) -> list[float]:
    return [NO_MEASUREMENT if value is None else value for value in values]


def required(values: list[float | None]) -> list[float]:
    assert all(value is not None for value in values)
    return [value for value in values if value is not None]


def find_fixed_rsa_aggregation(
    summary: BenchmarkSummary,
    operation: str,
    fixed_rsa_key_bits: int,
    feature_name: str,
) -> CaseAggregation | None:
    aggregation = summary.find_aggregation(operation, RSA_KEY_BITS, fixed_rsa_key_bits)

    if (
        aggregation is None
        or aggregation.out_of_memory
        or not aggregation.has_measurement(feature_name)
    ):
        return None

    return aggregation


def peak_memory_change(
    results: BenchmarkSummary,
    operation: str,
    group: str,
    sweep_values: list[int],
) -> tuple[float | None, float | None, float | None, float | None]:
    first_aggregation = results.find_aggregation(operation, group, sweep_values[0])
    last_aggregation = results.find_aggregation(operation, group, sweep_values[-1])

    if (
        first_aggregation is None
        or first_aggregation.out_of_memory
        or last_aggregation is None
        or last_aggregation.out_of_memory
    ):
        return None, None, None, None

    first = first_aggregation.mean(PEAK_RSS_BYTES) / MEGABYTE
    last = last_aggregation.mean(PEAK_RSS_BYTES) / MEGABYTE
    return first, last, last - first, (last / first - 1) * 100.0


def main() -> None:
    timing_runs = parse_int_env("ATTRIBUTE_KEY_SCALING_RUNS")
    attribute_counts = parse_int_list_env("ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT")
    subscriber_counts = parse_int_list_env("ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT")
    rsa_key_sizes = parse_int_list_env("ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES")
    fixed_rsa_key_bits = parse_int_env("ATTRIBUTE_KEY_SCALING_FIXED_RSA_KEY_SIZE")

    result_dir = Path(
        os.environ.get(
            "ATTRIBUTE_KEY_SCALING_RESULT_DIR", f"{DEFAULT_RESULT_ROOT}/{SCENARIO}"
        )
    )
    bench_output = result_dir / BENCH_OUTPUT_NAME
    memory_output = result_dir / MEMORY_OUTPUT_NAME
    case_status = result_dir / CASE_STATUS_NAME
    template_path = Path(TEMPLATE_DIR) / TEMPLATE_NAME
    report_path = result_dir / REPORT_NAME

    results = BenchmarkSummary()
    load_results(results, str(bench_output), BENCHMARK_PREFIX)
    load_results(results, str(memory_output), BENCHMARK_PREFIX)
    load_out_of_memory_status(results, str(case_status))

    min_attributes = attribute_counts[0]
    max_attributes = attribute_counts[-1]

    cpabe_encrypt_latency = measurement_means(
        results,
        "Encrypt",
        CPABE_ATTRIBUTES,
        attribute_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )
    cpabe_encrypt_latency_cis = measurement_confidence_intervals(
        results,
        "Encrypt",
        CPABE_ATTRIBUTES,
        attribute_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )
    cpabe_decrypt_latency = measurement_means(
        results,
        "Decrypt",
        CPABE_ATTRIBUTES,
        attribute_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )
    cpabe_decrypt_latency_cis = measurement_confidence_intervals(
        results,
        "Decrypt",
        CPABE_ATTRIBUTES,
        attribute_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )
    cpabe_ciphertext_sizes = measurement_means(
        results, "Encrypt", CPABE_ATTRIBUTES, attribute_counts, CIPHERTEXT_BYTES
    )
    cpabe_ciphertext_cis = measurement_confidence_intervals(
        results, "Encrypt", CPABE_ATTRIBUTES, attribute_counts, CIPHERTEXT_BYTES
    )
    cpabe_stored_key_sizes = measurement_means(
        results, "Decrypt", CPABE_ATTRIBUTES, attribute_counts, STORED_KEY_BYTES
    )
    cpabe_stored_key_cis = measurement_confidence_intervals(
        results, "Decrypt", CPABE_ATTRIBUTES, attribute_counts, STORED_KEY_BYTES
    )

    subscriber_encrypt_latency = measurement_means(
        results,
        "Encrypt",
        RSA_SUBSCRIBERS,
        subscriber_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )
    subscriber_encrypt_latency_cis = measurement_confidence_intervals(
        results,
        "Encrypt",
        RSA_SUBSCRIBERS,
        subscriber_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )
    subscriber_ciphertext_sizes = measurement_means(
        results, "Encrypt", RSA_SUBSCRIBERS, subscriber_counts, CIPHERTEXT_BYTES
    )
    subscriber_ciphertext_cis = measurement_confidence_intervals(
        results, "Encrypt", RSA_SUBSCRIBERS, subscriber_counts, CIPHERTEXT_BYTES
    )
    subscriber_total_ciphertext_sizes = measurement_means(
        results, "Encrypt", RSA_SUBSCRIBERS, subscriber_counts, TOTAL_CIPHERTEXT_BYTES
    )
    subscriber_total_ciphertext_cis = measurement_confidence_intervals(
        results, "Encrypt", RSA_SUBSCRIBERS, subscriber_counts, TOTAL_CIPHERTEXT_BYTES
    )

    rsa_encrypt_latency = measurement_means(
        results, "Encrypt", RSA_KEY_BITS, rsa_key_sizes, NS_PER_OP, NS_PER_MICROSECOND
    )
    rsa_encrypt_latency_cis = measurement_confidence_intervals(
        results, "Encrypt", RSA_KEY_BITS, rsa_key_sizes, NS_PER_OP, NS_PER_MICROSECOND
    )
    rsa_decrypt_latency = measurement_means(
        results, "Decrypt", RSA_KEY_BITS, rsa_key_sizes, NS_PER_OP, NS_PER_MICROSECOND
    )
    rsa_decrypt_latency_cis = measurement_confidence_intervals(
        results, "Decrypt", RSA_KEY_BITS, rsa_key_sizes, NS_PER_OP, NS_PER_MICROSECOND
    )
    rsa_ciphertext_sizes = measurement_means(
        results, "Encrypt", RSA_KEY_BITS, rsa_key_sizes, CIPHERTEXT_BYTES
    )
    rsa_ciphertext_cis = measurement_confidence_intervals(
        results, "Encrypt", RSA_KEY_BITS, rsa_key_sizes, CIPHERTEXT_BYTES
    )

    keygen_medians = []
    keygen_minimums = []
    keygen_maximums = []
    keygen_first_quartiles = []
    keygen_third_quartiles = []
    keygen_iqrs = []
    keygen_stored_key_sizes = []
    keygen_stored_key_cis = []
    keygen_sample_counts = []
    for rsa_key_bits in rsa_key_sizes:
        aggregation = results.find_aggregation("KeyGen", RSA_KEY_BITS, rsa_key_bits)
        if aggregation is None or aggregation.out_of_memory:
            keygen_medians.append(None)
            keygen_minimums.append(None)
            keygen_maximums.append(None)
            keygen_first_quartiles.append(None)
            keygen_third_quartiles.append(None)
            keygen_iqrs.append(None)
            keygen_stored_key_sizes.append(None)
            keygen_stored_key_cis.append(None)
            keygen_sample_counts.append(None)
        else:
            keygen_medians.append(aggregation.median(NS_PER_OP) / NS_PER_MILLISECOND)
            keygen_minimums.append(aggregation.minimum(NS_PER_OP) / NS_PER_MILLISECOND)
            keygen_maximums.append(aggregation.maximum(NS_PER_OP) / NS_PER_MILLISECOND)
            keygen_first_quartiles.append(
                aggregation.first_quartile(NS_PER_OP) / NS_PER_MILLISECOND
            )
            keygen_third_quartiles.append(
                aggregation.third_quartile(NS_PER_OP) / NS_PER_MILLISECOND
            )
            keygen_iqrs.append(aggregation.iqr(NS_PER_OP) / NS_PER_MILLISECOND)
            keygen_stored_key_sizes.append(aggregation.mean(STORED_KEY_BYTES))
            keygen_stored_key_cis.append(
                aggregation.confidence_interval(STORED_KEY_BYTES)
            )
            keygen_sample_counts.append(aggregation.get_sample_count(NS_PER_OP))

    decrypt_reference = find_fixed_rsa_aggregation(
        results, "Decrypt", fixed_rsa_key_bits, NS_PER_OP
    )
    decrypt_reference_micros = (
        None
        if decrypt_reference is None
        else decrypt_reference.mean(NS_PER_OP) / NS_PER_MICROSECOND
    )

    cpabe_encrypt_fit = fit_measurement(
        results,
        "Encrypt",
        CPABE_ATTRIBUTES,
        attribute_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )
    cpabe_decrypt_fit = fit_measurement(
        results,
        "Decrypt",
        CPABE_ATTRIBUTES,
        attribute_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )
    cpabe_ciphertext_fit = fit_measurement(
        results, "Encrypt", CPABE_ATTRIBUTES, attribute_counts, CIPHERTEXT_BYTES
    )
    cpabe_stored_key_fit = fit_measurement(
        results, "Decrypt", CPABE_ATTRIBUTES, attribute_counts, STORED_KEY_BYTES
    )
    subscriber_encrypt_fit = fit_measurement(
        results,
        "Encrypt",
        RSA_SUBSCRIBERS,
        subscriber_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )

    rsa_subscriber_reference = results.find_aggregation(
        "Encrypt", RSA_SUBSCRIBERS, subscriber_counts[0]
    )
    if rsa_subscriber_reference is None or rsa_subscriber_reference.out_of_memory:
        bytes_per_subscriber = None
    else:
        bytes_per_subscriber = rsa_subscriber_reference.mean(CIPHERTEXT_BYTES)

    cpabe_low_encrypt = results.find_aggregation(
        "Encrypt", CPABE_ATTRIBUTES, min_attributes
    )
    cpabe_high_encrypt = results.find_aggregation(
        "Encrypt", CPABE_ATTRIBUTES, max_attributes
    )
    cpabe_encrypt_endpoints_available = all(
        aggregation is not None and not aggregation.out_of_memory
        for aggregation in (cpabe_low_encrypt, cpabe_high_encrypt)
    )

    if bytes_per_subscriber is not None and cpabe_encrypt_endpoints_available:
        assert cpabe_low_encrypt is not None and cpabe_high_encrypt is not None
        cpabe_low_ciphertext = cpabe_low_encrypt.mean(CIPHERTEXT_BYTES)
        cpabe_high_ciphertext = cpabe_high_encrypt.mean(CIPHERTEXT_BYTES)
        bytes_crossover_low = cpabe_low_ciphertext / bytes_per_subscriber
        bytes_crossover_high = cpabe_high_ciphertext / bytes_per_subscriber
    else:
        cpabe_low_ciphertext = None
        cpabe_high_ciphertext = None
        bytes_crossover_low = None
        bytes_crossover_high = None

    if subscriber_encrypt_fit is not None and cpabe_encrypt_endpoints_available:
        assert cpabe_low_encrypt is not None and cpabe_high_encrypt is not None
        cpabe_low_encrypt_micros = (
            cpabe_low_encrypt.mean(NS_PER_OP) / NS_PER_MICROSECOND
        )
        cpabe_high_encrypt_micros = (
            cpabe_high_encrypt.mean(NS_PER_OP) / NS_PER_MICROSECOND
        )
        latency_crossover_low = subscriber_encrypt_fit.solve_x_for_y(
            cpabe_low_encrypt_micros
        )
        latency_crossover_high = subscriber_encrypt_fit.solve_x_for_y(
            cpabe_high_encrypt_micros
        )
    else:
        cpabe_low_encrypt_micros = None
        cpabe_high_encrypt_micros = None
        latency_crossover_low = None
        latency_crossover_high = None

    if decrypt_reference_micros is None:
        decrypt_penalty_low = None
        decrypt_penalty_high = None
    else:
        decrypt_penalty_low = (
            None
            if cpabe_decrypt_latency[0] is None
            else cpabe_decrypt_latency[0] / decrypt_reference_micros
        )
        decrypt_penalty_high = (
            None
            if cpabe_decrypt_latency[-1] is None
            else cpabe_decrypt_latency[-1] / decrypt_reference_micros
        )

    cpabe_memory_encrypt_means = required(
        measurement_means(
            results,
            "MemoryEncrypt",
            CPABE_ATTRIBUTES,
            attribute_counts,
            PEAK_RSS_BYTES,
            MEGABYTE,
        )
    )
    cpabe_memory_encrypt_cis = required(
        measurement_confidence_intervals(
            results,
            "MemoryEncrypt",
            CPABE_ATTRIBUTES,
            attribute_counts,
            PEAK_RSS_BYTES,
            MEGABYTE,
        )
    )
    cpabe_memory_decrypt_means = required(
        measurement_means(
            results,
            "MemoryDecrypt",
            CPABE_ATTRIBUTES,
            attribute_counts,
            PEAK_RSS_BYTES,
            MEGABYTE,
        )
    )
    cpabe_memory_decrypt_cis = required(
        measurement_confidence_intervals(
            results,
            "MemoryDecrypt",
            CPABE_ATTRIBUTES,
            attribute_counts,
            PEAK_RSS_BYTES,
            MEGABYTE,
        )
    )
    subscriber_memory_encrypt_means = required(
        measurement_means(
            results,
            "MemoryEncrypt",
            RSA_SUBSCRIBERS,
            subscriber_counts,
            PEAK_RSS_BYTES,
            MEGABYTE,
        )
    )
    subscriber_memory_encrypt_cis = required(
        measurement_confidence_intervals(
            results,
            "MemoryEncrypt",
            RSA_SUBSCRIBERS,
            subscriber_counts,
            PEAK_RSS_BYTES,
            MEGABYTE,
        )
    )
    rsa_memory_encrypt_means = required(
        measurement_means(
            results,
            "MemoryEncrypt",
            RSA_KEY_BITS,
            rsa_key_sizes,
            PEAK_RSS_BYTES,
            MEGABYTE,
        )
    )
    rsa_memory_encrypt_cis = required(
        measurement_confidence_intervals(
            results,
            "MemoryEncrypt",
            RSA_KEY_BITS,
            rsa_key_sizes,
            PEAK_RSS_BYTES,
            MEGABYTE,
        )
    )
    rsa_memory_decrypt_means = required(
        measurement_means(
            results,
            "MemoryDecrypt",
            RSA_KEY_BITS,
            rsa_key_sizes,
            PEAK_RSS_BYTES,
            MEGABYTE,
        )
    )
    rsa_memory_decrypt_cis = required(
        measurement_confidence_intervals(
            results,
            "MemoryDecrypt",
            RSA_KEY_BITS,
            rsa_key_sizes,
            PEAK_RSS_BYTES,
            MEGABYTE,
        )
    )

    memory_decrypt_reference = find_fixed_rsa_aggregation(
        results, "MemoryDecrypt", fixed_rsa_key_bits, PEAK_RSS_BYTES
    )
    if memory_decrypt_reference is None:
        subscriber_memory_decrypt_mean = None
        subscriber_memory_decrypt_ci = None
    else:
        subscriber_memory_decrypt_mean = (
            memory_decrypt_reference.mean(PEAK_RSS_BYTES) / MEGABYTE
        )
        subscriber_memory_decrypt_ci = (
            memory_decrypt_reference.confidence_interval(PEAK_RSS_BYTES) / MEGABYTE
        )

    memory_baseline = results.find_aggregation("MemoryBaseline", "Runtime", 0)
    assert memory_baseline is not None and not memory_baseline.out_of_memory
    baseline_memory_mean = memory_baseline.mean(PEAK_RSS_BYTES) / MEGABYTE
    baseline_memory_ci = memory_baseline.confidence_interval(PEAK_RSS_BYTES) / MEGABYTE

    cpabe_memory_sample_counts = []
    for attribute_count in attribute_counts:
        aggregation = results.find_aggregation(
            "MemoryDecrypt", CPABE_ATTRIBUTES, attribute_count
        )
        assert aggregation is not None and not aggregation.out_of_memory
        cpabe_memory_sample_counts.append(aggregation.get_sample_count(PEAK_RSS_BYTES))

    subscriber_memory_sample_counts = []
    for subscriber_count in subscriber_counts:
        aggregation = results.find_aggregation(
            "MemoryEncrypt", RSA_SUBSCRIBERS, subscriber_count
        )
        assert aggregation is not None and not aggregation.out_of_memory
        subscriber_memory_sample_counts.append(
            aggregation.get_sample_count(PEAK_RSS_BYTES)
        )

    rsa_memory_sample_counts = []
    for rsa_key_bits in rsa_key_sizes:
        aggregation = results.find_aggregation(
            "MemoryDecrypt", RSA_KEY_BITS, rsa_key_bits
        )
        assert aggregation is not None and not aggregation.out_of_memory
        rsa_memory_sample_counts.append(aggregation.get_sample_count(PEAK_RSS_BYTES))

    (
        cpabe_encrypt_memory_first,
        cpabe_encrypt_memory_last,
        cpabe_encrypt_memory_absolute_change,
        cpabe_encrypt_memory_percent_change,
    ) = peak_memory_change(results, "MemoryEncrypt", CPABE_ATTRIBUTES, attribute_counts)
    (
        cpabe_decrypt_memory_first,
        cpabe_decrypt_memory_last,
        cpabe_decrypt_memory_absolute_change,
        cpabe_decrypt_memory_percent_change,
    ) = peak_memory_change(results, "MemoryDecrypt", CPABE_ATTRIBUTES, attribute_counts)
    (
        subscriber_encrypt_memory_first,
        subscriber_encrypt_memory_last,
        subscriber_encrypt_memory_absolute_change,
        subscriber_encrypt_memory_percent_change,
    ) = peak_memory_change(results, "MemoryEncrypt", RSA_SUBSCRIBERS, subscriber_counts)
    (
        rsa_encrypt_memory_first,
        rsa_encrypt_memory_last,
        rsa_encrypt_memory_absolute_change,
        rsa_encrypt_memory_percent_change,
    ) = peak_memory_change(results, "MemoryEncrypt", RSA_KEY_BITS, rsa_key_sizes)
    (
        rsa_decrypt_memory_first,
        rsa_decrypt_memory_last,
        rsa_decrypt_memory_absolute_change,
        rsa_decrypt_memory_percent_change,
    ) = peak_memory_change(results, "MemoryDecrypt", RSA_KEY_BITS, rsa_key_sizes)

    largest_subscriber_aggregation = results.find_aggregation(
        "Encrypt", RSA_SUBSCRIBERS, subscriber_counts[-1]
    )
    if (
        bytes_per_subscriber is None
        or largest_subscriber_aggregation is None
        or largest_subscriber_aggregation.out_of_memory
    ):
        fanout_total_bytes = None
        fanout_multiplier = None
    else:
        fanout_total_bytes = largest_subscriber_aggregation.mean(TOTAL_CIPHERTEXT_BYTES)
        fanout_multiplier = fanout_total_bytes / bytes_per_subscriber

    plot_cpabe_attribute_sweep(
        attribute_counts,
        plotted(cpabe_encrypt_latency),
        plotted(cpabe_encrypt_latency_cis),
        plotted(cpabe_decrypt_latency),
        plotted(cpabe_decrypt_latency_cis),
        plotted(cpabe_ciphertext_sizes),
        plotted(cpabe_ciphertext_cis),
        plotted(cpabe_stored_key_sizes),
        plotted(cpabe_stored_key_cis),
        str(result_dir / CPABE_PLOT),
    )
    plot_rsa_subscriber_sweep(
        subscriber_counts,
        fixed_rsa_key_bits,
        plotted(subscriber_encrypt_latency),
        plotted(subscriber_encrypt_latency_cis),
        decrypt_reference_micros,
        plotted(subscriber_ciphertext_sizes),
        plotted(subscriber_ciphertext_cis),
        plotted(subscriber_total_ciphertext_sizes),
        plotted(subscriber_total_ciphertext_cis),
        str(result_dir / RSA_SUBSCRIBERS_PLOT),
    )
    plot_rsa_key_size_sweep(
        rsa_key_sizes,
        plotted(keygen_medians),
        plotted(keygen_minimums),
        plotted(keygen_maximums),
        plotted(keygen_first_quartiles),
        plotted(keygen_third_quartiles),
        plotted(rsa_encrypt_latency),
        plotted(rsa_encrypt_latency_cis),
        plotted(rsa_decrypt_latency),
        plotted(rsa_decrypt_latency_cis),
        plotted(rsa_ciphertext_sizes),
        plotted(rsa_ciphertext_cis),
        plotted(keygen_stored_key_sizes),
        plotted(keygen_stored_key_cis),
        str(result_dir / RSA_KEY_BITS_PLOT),
    )

    if (
        bytes_crossover_low is not None
        and bytes_crossover_high is not None
        and cpabe_low_ciphertext is not None
        and cpabe_high_ciphertext is not None
    ):
        plot_ciphertext_size_crossover(
            subscriber_counts,
            plotted(subscriber_total_ciphertext_sizes),
            plotted(subscriber_total_ciphertext_cis),
            min_attributes,
            cpabe_low_ciphertext,
            bytes_crossover_low,
            max_attributes,
            cpabe_high_ciphertext,
            bytes_crossover_high,
            str(result_dir / CIPHERTEXT_SIZE_CROSSOVER_PLOT),
        )
        bandwidth_crossover_plot = CIPHERTEXT_SIZE_CROSSOVER_PLOT
    else:
        bandwidth_crossover_plot = None

    if (
        subscriber_encrypt_fit is not None
        and latency_crossover_low is not None
        and latency_crossover_high is not None
        and cpabe_low_encrypt_micros is not None
        and cpabe_high_encrypt_micros is not None
    ):
        projection_start_subscribers = float(subscriber_counts[-1])
        projection_end_subscribers = latency_crossover_high * 1.15
        projection_start_micros = subscriber_encrypt_fit.calculate_y_based_on_x(
            projection_start_subscribers
        )
        projection_end_micros = subscriber_encrypt_fit.calculate_y_based_on_x(
            projection_end_subscribers
        )
        plot_encrypt_latency_crossover(
            subscriber_counts,
            plotted(subscriber_encrypt_latency),
            plotted(subscriber_encrypt_latency_cis),
            projection_start_subscribers,
            projection_start_micros,
            projection_end_subscribers,
            projection_end_micros,
            min_attributes,
            cpabe_low_encrypt_micros,
            latency_crossover_low,
            max_attributes,
            cpabe_high_encrypt_micros,
            latency_crossover_high,
            str(result_dir / ENCRYPT_LATENCY_CROSSOVER_PLOT),
        )
        encrypt_crossover_plot = ENCRYPT_LATENCY_CROSSOVER_PLOT
    else:
        encrypt_crossover_plot = None

    measured_rsa_key_sizes = [
        rsa_key_bits
        for rsa_key_bits, value in zip(rsa_key_sizes, rsa_decrypt_latency, strict=True)
        if value is not None
    ]
    measured_rsa_decrypt_means = [
        value for value in rsa_decrypt_latency if value is not None
    ]
    measured_rsa_decrypt_cis = [
        value for value in rsa_decrypt_latency_cis if value is not None
    ]
    decrypt_crossover_available = bool(measured_rsa_key_sizes) and any(
        value is not None for value in cpabe_decrypt_latency
    )
    if decrypt_crossover_available:
        plot_decrypt_latency_crossover(
            attribute_counts,
            plotted(cpabe_decrypt_latency),
            plotted(cpabe_decrypt_latency_cis),
            measured_rsa_key_sizes,
            measured_rsa_decrypt_means,
            measured_rsa_decrypt_cis,
            str(result_dir / DECRYPT_LATENCY_CROSSOVER_PLOT),
        )
        decrypt_crossover_plot = DECRYPT_LATENCY_CROSSOVER_PLOT
    else:
        decrypt_crossover_plot = None

    rsa_encrypt_reference = find_fixed_rsa_aggregation(
        results, "Encrypt", fixed_rsa_key_bits, NS_PER_OP
    )
    cpabe_min_encrypt = results.find_aggregation(
        "Encrypt", CPABE_ATTRIBUTES, min_attributes
    )
    cpabe_min_decrypt = results.find_aggregation(
        "Decrypt", CPABE_ATTRIBUTES, min_attributes
    )
    asymmetry_available = (
        rsa_encrypt_reference is not None
        and decrypt_reference is not None
        and cpabe_min_encrypt is not None
        and not cpabe_min_encrypt.out_of_memory
        and cpabe_min_decrypt is not None
        and not cpabe_min_decrypt.out_of_memory
    )
    if asymmetry_available:
        assert rsa_encrypt_reference is not None and decrypt_reference is not None
        assert cpabe_min_encrypt is not None and cpabe_min_decrypt is not None
        rsa_encrypt_micros = rsa_encrypt_reference.mean(NS_PER_OP) / NS_PER_MICROSECOND
        rsa_decrypt_micros = decrypt_reference.mean(NS_PER_OP) / NS_PER_MICROSECOND
        cpabe_encrypt_micros = cpabe_min_encrypt.mean(NS_PER_OP) / NS_PER_MICROSECOND
        cpabe_decrypt_micros = cpabe_min_decrypt.mean(NS_PER_OP) / NS_PER_MICROSECOND
        if rsa_encrypt_micros >= rsa_decrypt_micros:
            rsa_slower_operation = "Encrypt"
            rsa_ratio = rsa_encrypt_micros / rsa_decrypt_micros
        else:
            rsa_slower_operation = "Decrypt"
            rsa_ratio = rsa_decrypt_micros / rsa_encrypt_micros
        if cpabe_encrypt_micros >= cpabe_decrypt_micros:
            cpabe_slower_operation = "Encrypt"
            cpabe_ratio = cpabe_encrypt_micros / cpabe_decrypt_micros
        else:
            cpabe_slower_operation = "Decrypt"
            cpabe_ratio = cpabe_decrypt_micros / cpabe_encrypt_micros

        plot_encrypt_decrypt_asymmetry(
            fixed_rsa_key_bits,
            min_attributes,
            rsa_encrypt_micros,
            rsa_decrypt_micros,
            rsa_slower_operation,
            rsa_ratio,
            cpabe_encrypt_micros,
            cpabe_decrypt_micros,
            cpabe_slower_operation,
            cpabe_ratio,
            str(result_dir / ASYMMETRY_PLOT),
        )
        asymmetry_plot = ASYMMETRY_PLOT
    else:
        asymmetry_plot = None

    plot_peak_memory(
        attribute_counts,
        cpabe_memory_encrypt_means,
        cpabe_memory_encrypt_cis,
        cpabe_memory_decrypt_means,
        cpabe_memory_decrypt_cis,
        subscriber_counts,
        subscriber_memory_encrypt_means,
        subscriber_memory_encrypt_cis,
        subscriber_memory_decrypt_mean,
        rsa_key_sizes,
        rsa_memory_encrypt_means,
        rsa_memory_encrypt_cis,
        rsa_memory_decrypt_means,
        rsa_memory_decrypt_cis,
        fixed_rsa_key_bits,
        str(result_dir / PEAK_MEMORY_PLOT),
    )

    timing_iterations = sum(
        aggregation.iterations
        for aggregation in results.aggregations
        if aggregation.operation in ("Encrypt", "Decrypt", "KeyGen")
        and not aggregation.out_of_memory
    )
    out_of_memory_aggregations = [
        aggregation for aggregation in results.aggregations if aggregation.out_of_memory
    ]

    write_attribute_key_scaling_report(
        timing_runs=timing_runs,
        t_multiplier=get_student_t_critical_95(timing_runs - 1),
        timing_iterations=timing_iterations,
        attribute_counts=attribute_counts,
        subscriber_counts=subscriber_counts,
        rsa_key_sizes=rsa_key_sizes,
        fixed_rsa_key_bits=fixed_rsa_key_bits,
        cpabe_encrypt_latency_means=cpabe_encrypt_latency,
        cpabe_encrypt_latency_cis=cpabe_encrypt_latency_cis,
        cpabe_encrypt_ciphertext_sizes=cpabe_ciphertext_sizes,
        cpabe_encrypt_iterations=measurement_iterations(
            results, "Encrypt", CPABE_ATTRIBUTES, attribute_counts
        ),
        cpabe_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", CPABE_ATTRIBUTES, attribute_counts
        ),
        cpabe_decrypt_latency_means=cpabe_decrypt_latency,
        cpabe_decrypt_latency_cis=cpabe_decrypt_latency_cis,
        cpabe_decrypt_stored_key_sizes=cpabe_stored_key_sizes,
        cpabe_decrypt_iterations=measurement_iterations(
            results, "Decrypt", CPABE_ATTRIBUTES, attribute_counts
        ),
        cpabe_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", CPABE_ATTRIBUTES, attribute_counts
        ),
        subscriber_encrypt_latency_means=subscriber_encrypt_latency,
        subscriber_encrypt_latency_cis=subscriber_encrypt_latency_cis,
        subscriber_ciphertext_sizes=subscriber_ciphertext_sizes,
        subscriber_total_ciphertext_sizes=subscriber_total_ciphertext_sizes,
        subscriber_encrypt_iterations=measurement_iterations(
            results, "Encrypt", RSA_SUBSCRIBERS, subscriber_counts
        ),
        subscriber_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", RSA_SUBSCRIBERS, subscriber_counts
        ),
        rsa_encrypt_latency_means=rsa_encrypt_latency,
        rsa_encrypt_latency_cis=rsa_encrypt_latency_cis,
        rsa_ciphertext_sizes=rsa_ciphertext_sizes,
        rsa_encrypt_iterations=measurement_iterations(
            results, "Encrypt", RSA_KEY_BITS, rsa_key_sizes
        ),
        rsa_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", RSA_KEY_BITS, rsa_key_sizes
        ),
        rsa_decrypt_latency_means=rsa_decrypt_latency,
        rsa_decrypt_latency_cis=rsa_decrypt_latency_cis,
        rsa_decrypt_iterations=measurement_iterations(
            results, "Decrypt", RSA_KEY_BITS, rsa_key_sizes
        ),
        rsa_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", RSA_KEY_BITS, rsa_key_sizes
        ),
        keygen_medians=keygen_medians,
        keygen_minimums=keygen_minimums,
        keygen_maximums=keygen_maximums,
        keygen_iqrs=keygen_iqrs,
        keygen_stored_key_sizes=keygen_stored_key_sizes,
        keygen_sample_counts=keygen_sample_counts,
        keygen_throttled=results.get_throttle_flags(
            "KeyGen", RSA_KEY_BITS, rsa_key_sizes
        ),
        baseline_memory_mean=baseline_memory_mean,
        baseline_memory_ci=baseline_memory_ci,
        cpabe_memory_encrypt_means=cpabe_memory_encrypt_means,
        cpabe_memory_encrypt_cis=cpabe_memory_encrypt_cis,
        cpabe_memory_decrypt_means=cpabe_memory_decrypt_means,
        cpabe_memory_decrypt_cis=cpabe_memory_decrypt_cis,
        cpabe_memory_sample_counts=cpabe_memory_sample_counts,
        subscriber_memory_encrypt_means=subscriber_memory_encrypt_means,
        subscriber_memory_encrypt_cis=subscriber_memory_encrypt_cis,
        subscriber_memory_decrypt_mean=subscriber_memory_decrypt_mean,
        subscriber_memory_decrypt_ci=subscriber_memory_decrypt_ci,
        subscriber_memory_sample_counts=subscriber_memory_sample_counts,
        rsa_memory_encrypt_means=rsa_memory_encrypt_means,
        rsa_memory_encrypt_cis=rsa_memory_encrypt_cis,
        rsa_memory_decrypt_means=rsa_memory_decrypt_means,
        rsa_memory_decrypt_cis=rsa_memory_decrypt_cis,
        rsa_memory_sample_counts=rsa_memory_sample_counts,
        cpabe_encrypt_memory_first=cpabe_encrypt_memory_first,
        cpabe_encrypt_memory_last=cpabe_encrypt_memory_last,
        cpabe_encrypt_memory_absolute_change=cpabe_encrypt_memory_absolute_change,
        cpabe_encrypt_memory_percent_change=cpabe_encrypt_memory_percent_change,
        cpabe_decrypt_memory_first=cpabe_decrypt_memory_first,
        cpabe_decrypt_memory_last=cpabe_decrypt_memory_last,
        cpabe_decrypt_memory_absolute_change=cpabe_decrypt_memory_absolute_change,
        cpabe_decrypt_memory_percent_change=cpabe_decrypt_memory_percent_change,
        subscriber_encrypt_memory_first=subscriber_encrypt_memory_first,
        subscriber_encrypt_memory_last=subscriber_encrypt_memory_last,
        subscriber_encrypt_memory_absolute_change=subscriber_encrypt_memory_absolute_change,
        subscriber_encrypt_memory_percent_change=subscriber_encrypt_memory_percent_change,
        rsa_encrypt_memory_first=rsa_encrypt_memory_first,
        rsa_encrypt_memory_last=rsa_encrypt_memory_last,
        rsa_encrypt_memory_absolute_change=rsa_encrypt_memory_absolute_change,
        rsa_encrypt_memory_percent_change=rsa_encrypt_memory_percent_change,
        rsa_decrypt_memory_first=rsa_decrypt_memory_first,
        rsa_decrypt_memory_last=rsa_decrypt_memory_last,
        rsa_decrypt_memory_absolute_change=rsa_decrypt_memory_absolute_change,
        rsa_decrypt_memory_percent_change=rsa_decrypt_memory_percent_change,
        fanout_single_bytes=bytes_per_subscriber,
        fanout_total_bytes=fanout_total_bytes,
        fanout_multiplier=fanout_multiplier,
        out_of_memory_operations=[
            aggregation.operation for aggregation in out_of_memory_aggregations
        ],
        out_of_memory_cases=[
            f"{aggregation.parameter}/{aggregation.parameter_value}"
            for aggregation in out_of_memory_aggregations
        ],
        cpabe_encrypt_slope=(
            None if cpabe_encrypt_fit is None else cpabe_encrypt_fit.slope
        ),
        cpabe_encrypt_slope_ci=(
            None if cpabe_encrypt_fit is None else cpabe_encrypt_fit.slope_ci
        ),
        cpabe_encrypt_r_squared=(
            None if cpabe_encrypt_fit is None else cpabe_encrypt_fit.r_squared
        ),
        cpabe_decrypt_slope=(
            None if cpabe_decrypt_fit is None else cpabe_decrypt_fit.slope
        ),
        cpabe_decrypt_slope_ci=(
            None if cpabe_decrypt_fit is None else cpabe_decrypt_fit.slope_ci
        ),
        cpabe_decrypt_r_squared=(
            None if cpabe_decrypt_fit is None else cpabe_decrypt_fit.r_squared
        ),
        cpabe_ciphertext_slope=(
            None if cpabe_ciphertext_fit is None else cpabe_ciphertext_fit.slope
        ),
        cpabe_ciphertext_slope_ci=(
            None if cpabe_ciphertext_fit is None else cpabe_ciphertext_fit.slope_ci
        ),
        cpabe_ciphertext_r_squared=(
            None if cpabe_ciphertext_fit is None else cpabe_ciphertext_fit.r_squared
        ),
        cpabe_stored_key_slope=(
            None if cpabe_stored_key_fit is None else cpabe_stored_key_fit.slope
        ),
        cpabe_stored_key_slope_ci=(
            None if cpabe_stored_key_fit is None else cpabe_stored_key_fit.slope_ci
        ),
        cpabe_stored_key_r_squared=(
            None if cpabe_stored_key_fit is None else cpabe_stored_key_fit.r_squared
        ),
        subscriber_encrypt_slope=(
            None if subscriber_encrypt_fit is None else subscriber_encrypt_fit.slope
        ),
        subscriber_encrypt_slope_ci=(
            None if subscriber_encrypt_fit is None else subscriber_encrypt_fit.slope_ci
        ),
        subscriber_encrypt_r_squared=(
            None if subscriber_encrypt_fit is None else subscriber_encrypt_fit.r_squared
        ),
        bytes_per_subscriber=bytes_per_subscriber,
        bytes_crossover_low=bytes_crossover_low,
        bytes_crossover_high=bytes_crossover_high,
        latency_crossover_low=latency_crossover_low,
        latency_crossover_high=latency_crossover_high,
        decrypt_penalty_low=decrypt_penalty_low,
        decrypt_penalty_high=decrypt_penalty_high,
        cpabe_plot=CPABE_PLOT,
        rsa_subscribers_plot=RSA_SUBSCRIBERS_PLOT,
        rsa_key_bits_plot=RSA_KEY_BITS_PLOT,
        bandwidth_crossover_plot=bandwidth_crossover_plot,
        encrypt_crossover_plot=encrypt_crossover_plot,
        decrypt_crossover_plot=decrypt_crossover_plot,
        asymmetry_plot=asymmetry_plot,
        peak_memory_plot=PEAK_MEMORY_PLOT,
        template_path=str(template_path),
        report_path=str(report_path),
    )


if __name__ == "__main__":
    main()
