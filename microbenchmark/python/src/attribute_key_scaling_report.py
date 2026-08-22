import os
from typing import cast
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


def collect_timing_aggregations(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    subscriber_counts: list[int],
    rsa_key_sizes: list[int],
):
    scaling_attribute_encrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Encrypt", CPABE_ATTRIBUTES, attribute_count),
        )
        for attribute_count in attribute_counts
    ]
    scaling_attribute_decrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Decrypt", CPABE_ATTRIBUTES, attribute_count),
        )
        for attribute_count in attribute_counts
    ]
    scaling_subscriber_encrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Encrypt", RSA_SUBSCRIBERS, subscriber_count),
        )
        for subscriber_count in subscriber_counts
    ]
    scaling_key_encrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Encrypt", RSA_KEY_BITS, rsa_key_bits),
        )
        for rsa_key_bits in rsa_key_sizes
    ]
    scaling_key_decrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Decrypt", RSA_KEY_BITS, rsa_key_bits),
        )
        for rsa_key_bits in rsa_key_sizes
    ]
    scaling_key_generation = [
        cast(
            CaseAggregation,
            results.find_aggregation("KeyGen", RSA_KEY_BITS, rsa_key_bits),
        )
        for rsa_key_bits in rsa_key_sizes
    ]

    return (
        scaling_attribute_encrypt,
        scaling_attribute_decrypt,
        scaling_subscriber_encrypt,
        scaling_key_encrypt,
        scaling_key_decrypt,
        scaling_key_generation,
    )


def collect_memory_aggregations(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    subscriber_counts: list[int],
    rsa_key_sizes: list[int],
):
    memory_baseline = cast(
        CaseAggregation,
        results.find_aggregation("MemoryBaseline", "Runtime", 0),
    )
    assert not memory_baseline.out_of_memory

    scaling_attribute_memory_encrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation(
                "MemoryEncrypt", CPABE_ATTRIBUTES, attribute_count
            ),
        )
        for attribute_count in attribute_counts
    ]
    scaling_attribute_memory_decrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation(
                "MemoryDecrypt", CPABE_ATTRIBUTES, attribute_count
            ),
        )
        for attribute_count in attribute_counts
    ]
    scaling_subscriber_memory_encrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation(
                "MemoryEncrypt", RSA_SUBSCRIBERS, subscriber_count
            ),
        )
        for subscriber_count in subscriber_counts
    ]
    scaling_key_memory_encrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("MemoryEncrypt", RSA_KEY_BITS, rsa_key_bits),
        )
        for rsa_key_bits in rsa_key_sizes
    ]
    scaling_key_memory_decrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("MemoryDecrypt", RSA_KEY_BITS, rsa_key_bits),
        )
        for rsa_key_bits in rsa_key_sizes
    ]

    return (
        memory_baseline,
        scaling_attribute_memory_encrypt,
        scaling_attribute_memory_decrypt,
        scaling_subscriber_memory_encrypt,
        scaling_key_memory_encrypt,
        scaling_key_memory_decrypt,
    )


def analyze_timing_aggregations(
    scaling_attribute_encrypt: list[CaseAggregation],
    scaling_attribute_decrypt: list[CaseAggregation],
    scaling_subscriber_encrypt: list[CaseAggregation],
    scaling_key_encrypt: list[CaseAggregation],
    scaling_key_decrypt: list[CaseAggregation],
    scaling_key_generation: list[CaseAggregation],
):
    # Scaling Attribute Calculations
    # 1. Latency of Encrypt and Decrypt
    scaling_attribute_encrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in scaling_attribute_encrypt
    ]
    scaling_attribute_encrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in scaling_attribute_encrypt
    ]
    scaling_attribute_decrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in scaling_attribute_decrypt
    ]
    scaling_attribute_decrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in scaling_attribute_decrypt
    ]
    # 2. Size of Ciphertext
    scaling_attribute_ciphertext_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(CIPHERTEXT_BYTES)
        for aggregation in scaling_attribute_encrypt
    ]
    scaling_attribute_ciphertext_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(CIPHERTEXT_BYTES)
        )
        for aggregation in scaling_attribute_encrypt
    ]
    # 3. Size of Stored Key
    scaling_attribute_stored_key_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(STORED_KEY_BYTES)
        for aggregation in scaling_attribute_decrypt
    ]
    scaling_attribute_stored_key_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(STORED_KEY_BYTES)
        )
        for aggregation in scaling_attribute_decrypt
    ]
    # 4. Iterations of Encrypt and Decrypt
    scaling_attribute_encrypt_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in scaling_attribute_encrypt
    ]
    scaling_attribute_decrypt_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in scaling_attribute_decrypt
    ]

    # Scaling Subscriber Calculations
    # 1. Latency of Encrypt
    scaling_subscriber_encrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in scaling_subscriber_encrypt
    ]
    scaling_subscriber_encrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in scaling_subscriber_encrypt
    ]
    # 2. Size of Ciphertext
    # 2.1. Single ciphertext
    scaling_subscriber_ciphertext_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(CIPHERTEXT_BYTES)
        for aggregation in scaling_subscriber_encrypt
    ]
    scaling_subscriber_ciphertext_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(CIPHERTEXT_BYTES)
        )
        for aggregation in scaling_subscriber_encrypt
    ]
    # 2.2. Total ciphertext size
    scaling_subscriber_total_ciphertext_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(TOTAL_CIPHERTEXT_BYTES)
        for aggregation in scaling_subscriber_encrypt
    ]
    scaling_subscriber_total_ciphertext_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(TOTAL_CIPHERTEXT_BYTES)
        )
        for aggregation in scaling_subscriber_encrypt
    ]
    # 3. Iterations of Encrypt
    scaling_subscriber_encrypt_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in scaling_subscriber_encrypt
    ]

    # Key Scaling Calculations
    # 1. Latency of Encrypt and Decrypt
    scaling_key_encrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in scaling_key_encrypt
    ]
    scaling_key_encrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in scaling_key_encrypt
    ]
    scaling_key_decrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in scaling_key_decrypt
    ]
    scaling_key_decrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in scaling_key_decrypt
    ]
    # 2. Size of Ciphertext
    scaling_key_ciphertext_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(CIPHERTEXT_BYTES)
        for aggregation in scaling_key_encrypt
    ]
    scaling_key_ciphertext_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(CIPHERTEXT_BYTES)
        )
        for aggregation in scaling_key_encrypt
    ]
    # 3. Iterations of Encrypt and Decrypt
    scaling_key_encrypt_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in scaling_key_encrypt
    ]
    scaling_key_decrypt_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in scaling_key_decrypt
    ]

    # Key Generation Calculations
    # 1. Median, Minimum, Maximum, First Quartile, Third Quartile, IQR
    scaling_key_generation_median_list = [
        None if aggregation.out_of_memory else aggregation.median(NS_PER_OP)
        for aggregation in scaling_key_generation
    ]
    scaling_key_generation_minimum_list = [
        None if aggregation.out_of_memory else aggregation.minimum(NS_PER_OP)
        for aggregation in scaling_key_generation
    ]
    scaling_key_generation_maximum_list = [
        None if aggregation.out_of_memory else aggregation.maximum(NS_PER_OP)
        for aggregation in scaling_key_generation
    ]
    scaling_key_generation_first_quartile_list = [
        None if aggregation.out_of_memory else aggregation.first_quartile(NS_PER_OP)
        for aggregation in scaling_key_generation
    ]
    scaling_key_generation_third_quartile_list = [
        None if aggregation.out_of_memory else aggregation.third_quartile(NS_PER_OP)
        for aggregation in scaling_key_generation
    ]
    scaling_key_generation_iqr_list = [
        None if aggregation.out_of_memory else aggregation.iqr(NS_PER_OP)
        for aggregation in scaling_key_generation
    ]
    # 2. Size of Stored Key
    scaling_key_generation_stored_key_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(STORED_KEY_BYTES)
        for aggregation in scaling_key_generation
    ]
    scaling_key_generation_stored_key_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(STORED_KEY_BYTES)
        )
        for aggregation in scaling_key_generation
    ]
    # 3. Sample Count
    scaling_key_generation_sample_count_list = [
        None if aggregation.out_of_memory else aggregation.get_sample_count(NS_PER_OP)
        for aggregation in scaling_key_generation
    ]

    return (
        scaling_attribute_encrypt_latency_list,
        scaling_attribute_encrypt_latency_ci_list,
        scaling_attribute_decrypt_latency_list,
        scaling_attribute_decrypt_latency_ci_list,
        scaling_attribute_ciphertext_size_list,
        scaling_attribute_ciphertext_ci_list,
        scaling_attribute_stored_key_size_list,
        scaling_attribute_stored_key_ci_list,
        scaling_attribute_encrypt_iteration_list,
        scaling_attribute_decrypt_iteration_list,
        scaling_subscriber_encrypt_latency_list,
        scaling_subscriber_encrypt_latency_ci_list,
        scaling_subscriber_ciphertext_size_list,
        scaling_subscriber_ciphertext_ci_list,
        scaling_subscriber_total_ciphertext_size_list,
        scaling_subscriber_total_ciphertext_ci_list,
        scaling_subscriber_encrypt_iteration_list,
        scaling_key_encrypt_latency_list,
        scaling_key_encrypt_latency_ci_list,
        scaling_key_decrypt_latency_list,
        scaling_key_decrypt_latency_ci_list,
        scaling_key_ciphertext_size_list,
        scaling_key_ciphertext_ci_list,
        scaling_key_encrypt_iteration_list,
        scaling_key_decrypt_iteration_list,
        scaling_key_generation_median_list,
        scaling_key_generation_minimum_list,
        scaling_key_generation_maximum_list,
        scaling_key_generation_first_quartile_list,
        scaling_key_generation_third_quartile_list,
        scaling_key_generation_iqr_list,
        scaling_key_generation_stored_key_size_list,
        scaling_key_generation_stored_key_ci_list,
        scaling_key_generation_sample_count_list,
    )


def analyze_memory_aggregations(
    memory_baseline: CaseAggregation,
    scaling_attribute_memory_encrypt: list[CaseAggregation],
    scaling_attribute_memory_decrypt: list[CaseAggregation],
    scaling_subscriber_memory_encrypt: list[CaseAggregation],
    scaling_key_memory_encrypt: list[CaseAggregation],
    scaling_key_memory_decrypt: list[CaseAggregation],
    fixed_rsa_key_index: int,
):
    # Baseline Memory Calculations
    baseline_memory = memory_baseline.mean(PEAK_RSS_BYTES)
    baseline_memory_ci = memory_baseline.confidence_interval(PEAK_RSS_BYTES)

    # Attribute Scaling Memory Calculations
    # 1. Peak Memory of Encrypt and Decrypt
    scaling_attribute_memory_encrypt_list = [
        aggregation.mean(PEAK_RSS_BYTES)
        for aggregation in scaling_attribute_memory_encrypt
    ]
    scaling_attribute_memory_encrypt_ci_list = [
        aggregation.confidence_interval(PEAK_RSS_BYTES)
        for aggregation in scaling_attribute_memory_encrypt
    ]
    scaling_attribute_memory_decrypt_list = [
        aggregation.mean(PEAK_RSS_BYTES)
        for aggregation in scaling_attribute_memory_decrypt
    ]
    scaling_attribute_memory_decrypt_ci_list = [
        aggregation.confidence_interval(PEAK_RSS_BYTES)
        for aggregation in scaling_attribute_memory_decrypt
    ]
    # 2. Sample Count
    scaling_attribute_memory_sample_count_list = [
        aggregation.get_sample_count(PEAK_RSS_BYTES)
        for aggregation in scaling_attribute_memory_decrypt
    ]

    # Subscriber Scaling Memory Calculations
    # 1. Peak Memory of Encrypt
    scaling_subscriber_memory_encrypt_list = [
        aggregation.mean(PEAK_RSS_BYTES)
        for aggregation in scaling_subscriber_memory_encrypt
    ]
    scaling_subscriber_memory_encrypt_ci_list = [
        aggregation.confidence_interval(PEAK_RSS_BYTES)
        for aggregation in scaling_subscriber_memory_encrypt
    ]
    # 2. Sample Count
    scaling_subscriber_memory_sample_count_list = [
        aggregation.get_sample_count(PEAK_RSS_BYTES)
        for aggregation in scaling_subscriber_memory_encrypt
    ]

    # Key Scaling Memory Calculations
    # 1. Peak Memory of Encrypt and Decrypt
    scaling_key_memory_encrypt_list = [
        aggregation.mean(PEAK_RSS_BYTES) for aggregation in scaling_key_memory_encrypt
    ]
    scaling_key_memory_encrypt_ci_list = [
        aggregation.confidence_interval(PEAK_RSS_BYTES)
        for aggregation in scaling_key_memory_encrypt
    ]
    scaling_key_memory_decrypt_list = [
        aggregation.mean(PEAK_RSS_BYTES) for aggregation in scaling_key_memory_decrypt
    ]
    scaling_key_memory_decrypt_ci_list = [
        aggregation.confidence_interval(PEAK_RSS_BYTES)
        for aggregation in scaling_key_memory_decrypt
    ]
    # 2. Sample Count
    scaling_key_memory_sample_count_list = [
        aggregation.get_sample_count(PEAK_RSS_BYTES)
        for aggregation in scaling_key_memory_decrypt
    ]

    # TBD ----
    scaling_subscriber_fixed_memory_decrypt = scaling_key_memory_decrypt[
        fixed_rsa_key_index
    ]
    scaling_subscriber_memory_decrypt = (
        None
        if scaling_subscriber_fixed_memory_decrypt.out_of_memory
        else scaling_subscriber_fixed_memory_decrypt.mean(PEAK_RSS_BYTES)
    )
    scaling_subscriber_memory_decrypt_ci = (
        None
        if scaling_subscriber_fixed_memory_decrypt.out_of_memory
        else scaling_subscriber_fixed_memory_decrypt.confidence_interval(PEAK_RSS_BYTES)
    )
    # ----

    return (
        baseline_memory,
        baseline_memory_ci,
        scaling_attribute_memory_encrypt_list,
        scaling_attribute_memory_encrypt_ci_list,
        scaling_attribute_memory_decrypt_list,
        scaling_attribute_memory_decrypt_ci_list,
        scaling_attribute_memory_sample_count_list,
        scaling_subscriber_memory_encrypt_list,
        scaling_subscriber_memory_encrypt_ci_list,
        scaling_subscriber_memory_sample_count_list,
        scaling_key_memory_encrypt_list,
        scaling_key_memory_encrypt_ci_list,
        scaling_key_memory_decrypt_list,
        scaling_key_memory_decrypt_ci_list,
        scaling_key_memory_sample_count_list,
        scaling_subscriber_memory_decrypt,
        scaling_subscriber_memory_decrypt_ci,
    )


def obtain_fits(
    attribute_counts: list[int],
    subscriber_counts: list[int],
    scaling_attribute_encrypt_latency_list: list[float | None],
    scaling_attribute_decrypt_latency_list: list[float | None],
    scaling_attribute_ciphertext_size_list: list[float | None],
    scaling_attribute_stored_key_size_list: list[float | None],
    scaling_subscriber_encrypt_latency_list: list[float | None],
):
    # CP-ABE Encrypt Latency Fit
    cpabe_encrypt_fit_x = [
        attribute_count
        for attribute_count, latency in zip(
            attribute_counts,
            scaling_attribute_encrypt_latency_list,
            strict=True,
        )
        if latency is not None
    ]
    cpabe_encrypt_fit_y = [
        latency
        for latency in scaling_attribute_encrypt_latency_list
        if latency is not None
    ]
    cpabe_encrypt_fit = (
        None
        if len(cpabe_encrypt_fit_x) < MINIMUM_FIT_POINTS
        else fit_linear_regression(cpabe_encrypt_fit_x, cpabe_encrypt_fit_y)
    )

    # CP-ABE Decrypt Latency Fit
    cpabe_decrypt_fit_x = [
        attribute_count
        for attribute_count, latency in zip(
            attribute_counts,
            scaling_attribute_decrypt_latency_list,
            strict=True,
        )
        if latency is not None
    ]
    cpabe_decrypt_fit_y = [
        latency
        for latency in scaling_attribute_decrypt_latency_list
        if latency is not None
    ]
    cpabe_decrypt_fit = (
        None
        if len(cpabe_decrypt_fit_x) < MINIMUM_FIT_POINTS
        else fit_linear_regression(cpabe_decrypt_fit_x, cpabe_decrypt_fit_y)
    )

    # CP-ABE Ciphertext Size Fit
    cpabe_ciphertext_fit_x = [
        attribute_count
        for attribute_count, ciphertext_size in zip(
            attribute_counts,
            scaling_attribute_ciphertext_size_list,
            strict=True,
        )
        if ciphertext_size is not None
    ]
    cpabe_ciphertext_fit_y = [
        ciphertext_size
        for ciphertext_size in scaling_attribute_ciphertext_size_list
        if ciphertext_size is not None
    ]
    cpabe_ciphertext_fit = (
        None
        if len(cpabe_ciphertext_fit_x) < MINIMUM_FIT_POINTS
        else fit_linear_regression(cpabe_ciphertext_fit_x, cpabe_ciphertext_fit_y)
    )

    # CP-ABE Stored Key Size Fit
    cpabe_stored_key_fit_x = [
        attribute_count
        for attribute_count, stored_key_size in zip(
            attribute_counts,
            scaling_attribute_stored_key_size_list,
            strict=True,
        )
        if stored_key_size is not None
    ]
    cpabe_stored_key_fit_y = [
        stored_key_size
        for stored_key_size in scaling_attribute_stored_key_size_list
        if stored_key_size is not None
    ]
    cpabe_stored_key_fit = (
        None
        if len(cpabe_stored_key_fit_x) < MINIMUM_FIT_POINTS
        else fit_linear_regression(cpabe_stored_key_fit_x, cpabe_stored_key_fit_y)
    )

    # RSA Subscriber Encrypt Latency Fit
    subscriber_encrypt_fit_x = [
        subscriber_count
        for subscriber_count, latency in zip(
            subscriber_counts,
            scaling_subscriber_encrypt_latency_list,
            strict=True,
        )
        if latency is not None
    ]
    subscriber_encrypt_fit_y = [
        latency
        for latency in scaling_subscriber_encrypt_latency_list
        if latency is not None
    ]
    subscriber_encrypt_fit = (
        None
        if len(subscriber_encrypt_fit_x) < MINIMUM_FIT_POINTS
        else fit_linear_regression(
            subscriber_encrypt_fit_x,
            subscriber_encrypt_fit_y,
        )
    )

    return (
        cpabe_encrypt_fit,
        cpabe_decrypt_fit,
        cpabe_ciphertext_fit,
        cpabe_stored_key_fit,
        subscriber_encrypt_fit,
    )


def obtain_crossovers(
    scaling_attribute_ciphertext_size_list: list[float | None],
    scaling_subscriber_ciphertext_size_list: list[float | None],
    scaling_attribute_encrypt_latency_list: list[float | None],
    scaling_attribute_decrypt_latency_list: list[float | None],
    scaling_subscriber_fixed_decrypt_latency: float | None,
    subscriber_encrypt_fit: LinearRegression | None,
):
    # Calculate Ciphertext Crossover
    # 1. Take any ciphertext size from the subscriber sweep, since it is constant across all subscriber counts
    bytes_per_subscriber = scaling_subscriber_ciphertext_size_list[0]

    # 2. Take the lowest and highest ciphertext sizes from the attribute sweep
    cpabe_low_ciphertext = scaling_attribute_ciphertext_size_list[0]
    cpabe_high_ciphertext = scaling_attribute_ciphertext_size_list[-1]

    # 3. Check we do not have null values due to OOM
    if (
        bytes_per_subscriber is not None
        and cpabe_low_ciphertext is not None
        and cpabe_high_ciphertext is not None
    ):
        # 4. How many equal sized RSA ciphertexts fit into the CP-ABE ciphertext?
        # - Lower Bound
        ciphertext_crossover_low = cpabe_low_ciphertext / bytes_per_subscriber

        # - Upper Bound
        ciphertext_crossover_high = cpabe_high_ciphertext / bytes_per_subscriber
    else:
        ciphertext_crossover_low = None
        ciphertext_crossover_high = None

    # Calculate Encrypt Latency Crossover
    # 1. Take lowest and highest encrypt latencies from the attribute sweep
    cpabe_low_encrypt_latency = scaling_attribute_encrypt_latency_list[0]
    cpabe_high_encrypt_latency = scaling_attribute_encrypt_latency_list[-1]

    # 2. Check we do not have null values due to OOM
    if (
        subscriber_encrypt_fit is not None
        and cpabe_low_encrypt_latency is not None
        and cpabe_high_encrypt_latency is not None
    ):
        # 3. At what subscriber count does RSA latency equal this CP-ABE latency?
        # - Lower Bound
        latency_crossover_low = subscriber_encrypt_fit.solve_x_for_y(
            cpabe_low_encrypt_latency
        )

        # - Upper Bound
        latency_crossover_high = subscriber_encrypt_fit.solve_x_for_y(
            cpabe_high_encrypt_latency
        )
    else:
        latency_crossover_low = None
        latency_crossover_high = None

    # Calculate Decrypt Latency Penalty
    # 1. Take lowest and highest decrypt latencies from the attribute sweep
    cpabe_low_decrypt_latency = scaling_attribute_decrypt_latency_list[0]
    cpabe_high_decrypt_latency = scaling_attribute_decrypt_latency_list[-1]

    # 2. Check we do not have null values due to OOM
    if scaling_subscriber_fixed_decrypt_latency is None:
        decrypt_penalty_low = None
        decrypt_penalty_high = None
    else:
        # 3. How many times slower is CP-ABE decrypt than RSA decrypt?
        # - Lower Bound
        decrypt_penalty_low = (
            None
            if cpabe_low_decrypt_latency is None
            else cpabe_low_decrypt_latency / scaling_subscriber_fixed_decrypt_latency
        )

        # - Upper Bound
        decrypt_penalty_high = (
            None
            if cpabe_high_decrypt_latency is None
            else cpabe_high_decrypt_latency / scaling_subscriber_fixed_decrypt_latency
        )

    return (
        bytes_per_subscriber,
        cpabe_low_ciphertext,
        cpabe_high_ciphertext,
        ciphertext_crossover_low,
        ciphertext_crossover_high,
        cpabe_low_encrypt_latency,
        cpabe_high_encrypt_latency,
        latency_crossover_low,
        latency_crossover_high,
        decrypt_penalty_low,
        decrypt_penalty_high,
    )


def obtain_rss_change(
    scaling_attribute_memory_encrypt_list: list[float],
    scaling_attribute_memory_decrypt_list: list[float],
    scaling_subscriber_memory_encrypt_list: list[float],
    scaling_key_memory_encrypt_list: list[float],
    scaling_key_memory_decrypt_list: list[float],
):
    # Peak Memory Change Calculations

    # CP-ABE Encrypt
    cpabe_encrypt_memory_first = scaling_attribute_memory_encrypt_list[0]
    cpabe_encrypt_memory_last = scaling_attribute_memory_encrypt_list[-1]
    cpabe_encrypt_memory_absolute_change = (
        cpabe_encrypt_memory_last - cpabe_encrypt_memory_first
    )
    cpabe_encrypt_memory_percent_change = (
        cpabe_encrypt_memory_last / cpabe_encrypt_memory_first - 1
    ) * 100.0

    # CP-ABE Decrypt
    cpabe_decrypt_memory_first = scaling_attribute_memory_decrypt_list[0]
    cpabe_decrypt_memory_last = scaling_attribute_memory_decrypt_list[-1]
    cpabe_decrypt_memory_absolute_change = (
        cpabe_decrypt_memory_last - cpabe_decrypt_memory_first
    )
    cpabe_decrypt_memory_percent_change = (
        cpabe_decrypt_memory_last / cpabe_decrypt_memory_first - 1
    ) * 100.0

    # RSA Subscriber Encrypt
    subscriber_encrypt_memory_first = scaling_subscriber_memory_encrypt_list[0]
    subscriber_encrypt_memory_last = scaling_subscriber_memory_encrypt_list[-1]
    subscriber_encrypt_memory_absolute_change = (
        subscriber_encrypt_memory_last - subscriber_encrypt_memory_first
    )
    subscriber_encrypt_memory_percent_change = (
        subscriber_encrypt_memory_last / subscriber_encrypt_memory_first - 1
    ) * 100.0

    # RSA Key Size Encrypt
    rsa_encrypt_memory_first = scaling_key_memory_encrypt_list[0]
    rsa_encrypt_memory_last = scaling_key_memory_encrypt_list[-1]
    rsa_encrypt_memory_absolute_change = (
        rsa_encrypt_memory_last - rsa_encrypt_memory_first
    )
    rsa_encrypt_memory_percent_change = (
        rsa_encrypt_memory_last / rsa_encrypt_memory_first - 1
    ) * 100.0

    # RSA Key Size Decrypt
    rsa_decrypt_memory_first = scaling_key_memory_decrypt_list[0]
    rsa_decrypt_memory_last = scaling_key_memory_decrypt_list[-1]
    rsa_decrypt_memory_absolute_change = (
        rsa_decrypt_memory_last - rsa_decrypt_memory_first
    )
    rsa_decrypt_memory_percent_change = (
        rsa_decrypt_memory_last / rsa_decrypt_memory_first - 1
    ) * 100.0

    return (
        cpabe_encrypt_memory_first,
        cpabe_encrypt_memory_last,
        cpabe_encrypt_memory_absolute_change,
        cpabe_encrypt_memory_percent_change,
        cpabe_decrypt_memory_first,
        cpabe_decrypt_memory_last,
        cpabe_decrypt_memory_absolute_change,
        cpabe_decrypt_memory_percent_change,
        subscriber_encrypt_memory_first,
        subscriber_encrypt_memory_last,
        subscriber_encrypt_memory_absolute_change,
        subscriber_encrypt_memory_percent_change,
        rsa_encrypt_memory_first,
        rsa_encrypt_memory_last,
        rsa_encrypt_memory_absolute_change,
        rsa_encrypt_memory_percent_change,
        rsa_decrypt_memory_first,
        rsa_decrypt_memory_last,
        rsa_decrypt_memory_absolute_change,
        rsa_decrypt_memory_percent_change,
    )


def main() -> None:
    timing_runs = parse_int_env("ATTRIBUTE_KEY_SCALING_RUNS")
    attribute_counts = parse_int_list_env("ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT")
    subscriber_counts = parse_int_list_env("ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT")
    rsa_key_sizes = parse_int_list_env("ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES")
    fixed_rsa_key_size = parse_int_env("ATTRIBUTE_KEY_SCALING_FIXED_RSA_KEY_SIZE")

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

    # Timing Aggregations
    (
        scaling_attribute_encrypt,
        scaling_attribute_decrypt,
        scaling_subscriber_encrypt,
        scaling_key_encrypt,
        scaling_key_decrypt,
        scaling_key_generation,
    ) = collect_timing_aggregations(
        results,
        attribute_counts,
        subscriber_counts,
        rsa_key_sizes,
    )

    # Memory Aggregations
    (
        memory_baseline,
        scaling_attribute_memory_encrypt,
        scaling_attribute_memory_decrypt,
        scaling_subscriber_memory_encrypt,
        scaling_key_memory_encrypt,
        scaling_key_memory_decrypt,
    ) = collect_memory_aggregations(
        results,
        attribute_counts,
        subscriber_counts,
        rsa_key_sizes,
    )

    # If OOM happened in Memory Aggregations, halt report
    assert not any(
        aggregation.out_of_memory
        for aggregations in (
            scaling_attribute_memory_encrypt,
            scaling_attribute_memory_decrypt,
            scaling_subscriber_memory_encrypt,
            scaling_key_memory_encrypt,
            scaling_key_memory_decrypt,
        )
        for aggregation in aggregations
    )

    # Obtain Timing Aggregation Analysis
    (
        scaling_attribute_encrypt_latency_list,
        scaling_attribute_encrypt_latency_ci_list,
        scaling_attribute_decrypt_latency_list,
        scaling_attribute_decrypt_latency_ci_list,
        scaling_attribute_ciphertext_size_list,
        scaling_attribute_ciphertext_ci_list,
        scaling_attribute_stored_key_size_list,
        scaling_attribute_stored_key_ci_list,
        scaling_attribute_encrypt_iteration_list,
        scaling_attribute_decrypt_iteration_list,
        scaling_subscriber_encrypt_latency_list,
        scaling_subscriber_encrypt_latency_ci_list,
        scaling_subscriber_ciphertext_size_list,
        scaling_subscriber_ciphertext_ci_list,
        scaling_subscriber_total_ciphertext_size_list,
        scaling_subscriber_total_ciphertext_ci_list,
        scaling_subscriber_encrypt_iteration_list,
        scaling_key_encrypt_latency_list,
        scaling_key_encrypt_latency_ci_list,
        scaling_key_decrypt_latency_list,
        scaling_key_decrypt_latency_ci_list,
        scaling_key_ciphertext_size_list,
        scaling_key_ciphertext_ci_list,
        scaling_key_encrypt_iteration_list,
        scaling_key_decrypt_iteration_list,
        scaling_key_generation_median_list,
        scaling_key_generation_minimum_list,
        scaling_key_generation_maximum_list,
        scaling_key_generation_first_quartile_list,
        scaling_key_generation_third_quartile_list,
        scaling_key_generation_iqr_list,
        scaling_key_generation_stored_key_size_list,
        scaling_key_generation_stored_key_ci_list,
        scaling_key_generation_sample_count_list,
    ) = analyze_timing_aggregations(
        scaling_attribute_encrypt,
        scaling_attribute_decrypt,
        scaling_subscriber_encrypt,
        scaling_key_encrypt,
        scaling_key_decrypt,
        scaling_key_generation,
    )

    # Instead of having a decrypt sweep based on subscriber count in RSA,
    # we use the already calculated decrypt latency from the key scaling sweep
    fixed_rsa_key_index = rsa_key_sizes.index(fixed_rsa_key_size)
    rsa_decrypt_reference = scaling_key_decrypt[fixed_rsa_key_index]
    scaling_subscriber_fixed_decrypt_latency = (
        None
        if rsa_decrypt_reference.out_of_memory
        else rsa_decrypt_reference.mean(NS_PER_OP)
    )

    # Fit Linear Regression
    (
        cpabe_encrypt_fit,
        cpabe_decrypt_fit,
        cpabe_ciphertext_fit,
        cpabe_stored_key_fit,
        subscriber_encrypt_fit,
    ) = obtain_fits(
        attribute_counts,
        subscriber_counts,
        scaling_attribute_encrypt_latency_list,
        scaling_attribute_decrypt_latency_list,
        scaling_attribute_ciphertext_size_list,
        scaling_attribute_stored_key_size_list,
        scaling_subscriber_encrypt_latency_list,
    )

    # Obtain Crossovers and Penalties
    (
        bytes_per_subscriber,
        cpabe_low_ciphertext,
        cpabe_high_ciphertext,
        ciphertext_crossover_low,
        ciphertext_crossover_high,
        cpabe_low_encrypt_latency,
        cpabe_high_encrypt_latency,
        latency_crossover_low,
        latency_crossover_high,
        decrypt_penalty_low,
        decrypt_penalty_high,
    ) = obtain_crossovers(
        scaling_attribute_ciphertext_size_list,
        scaling_subscriber_ciphertext_size_list,
        scaling_attribute_encrypt_latency_list,
        scaling_attribute_decrypt_latency_list,
        scaling_subscriber_fixed_decrypt_latency,
        subscriber_encrypt_fit,
    )

    # Analyze Memory Aggregations
    (
        baseline_memory,
        baseline_memory_ci,
        scaling_attribute_memory_encrypt_list,
        scaling_attribute_memory_encrypt_ci_list,
        scaling_attribute_memory_decrypt_list,
        scaling_attribute_memory_decrypt_ci_list,
        scaling_attribute_memory_sample_count_list,
        scaling_subscriber_memory_encrypt_list,
        scaling_subscriber_memory_encrypt_ci_list,
        scaling_subscriber_memory_sample_count_list,
        scaling_key_memory_encrypt_list,
        scaling_key_memory_encrypt_ci_list,
        scaling_key_memory_decrypt_list,
        scaling_key_memory_decrypt_ci_list,
        scaling_key_memory_sample_count_list,
        scaling_subscriber_memory_decrypt,
        scaling_subscriber_memory_decrypt_ci,
    ) = analyze_memory_aggregations(
        memory_baseline,
        scaling_attribute_memory_encrypt,
        scaling_attribute_memory_decrypt,
        scaling_subscriber_memory_encrypt,
        scaling_key_memory_encrypt,
        scaling_key_memory_decrypt,
        fixed_rsa_key_index,
    )

    # Calculate RSS Change
    (
        cpabe_encrypt_memory_first,
        cpabe_encrypt_memory_last,
        cpabe_encrypt_memory_absolute_change,
        cpabe_encrypt_memory_percent_change,
        cpabe_decrypt_memory_first,
        cpabe_decrypt_memory_last,
        cpabe_decrypt_memory_absolute_change,
        cpabe_decrypt_memory_percent_change,
        subscriber_encrypt_memory_first,
        subscriber_encrypt_memory_last,
        subscriber_encrypt_memory_absolute_change,
        subscriber_encrypt_memory_percent_change,
        rsa_encrypt_memory_first,
        rsa_encrypt_memory_last,
        rsa_encrypt_memory_absolute_change,
        rsa_encrypt_memory_percent_change,
        rsa_decrypt_memory_first,
        rsa_decrypt_memory_last,
        rsa_decrypt_memory_absolute_change,
        rsa_decrypt_memory_percent_change,
    ) = obtain_rss_change(
        scaling_attribute_memory_encrypt_list,
        scaling_attribute_memory_decrypt_list,
        scaling_subscriber_memory_encrypt_list,
        scaling_key_memory_encrypt_list,
        scaling_key_memory_decrypt_list,
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

    # Draw Scaling Attribute Plots
    plot_cpabe_attribute_sweep(
        attribute_counts,
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in scaling_attribute_encrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in scaling_attribute_encrypt_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in scaling_attribute_decrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in scaling_attribute_decrypt_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in scaling_attribute_ciphertext_size_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in scaling_attribute_ciphertext_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in scaling_attribute_stored_key_size_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in scaling_attribute_stored_key_ci_list
        ],
        str(result_dir / CPABE_PLOT),
    )

    # Draw Scaling Subscriber Plots
    plot_rsa_subscriber_sweep(
        subscriber_counts,
        fixed_rsa_key_size,
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in scaling_subscriber_encrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in scaling_subscriber_encrypt_latency_ci_list
        ],
        (
            None
            if scaling_subscriber_fixed_decrypt_latency is None
            else scaling_subscriber_fixed_decrypt_latency / NS_PER_MICROSECOND
        ),
        [
            NO_MEASUREMENT if value is None else value
            for value in scaling_subscriber_ciphertext_size_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in scaling_subscriber_ciphertext_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in scaling_subscriber_total_ciphertext_size_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in scaling_subscriber_total_ciphertext_ci_list
        ],
        str(result_dir / RSA_SUBSCRIBERS_PLOT),
    )

    # Draw Scaling Key Size Plots
    plot_rsa_key_size_sweep(
        rsa_key_sizes,
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MILLISECOND
            for value in scaling_key_generation_median_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MILLISECOND
            for value in scaling_key_generation_minimum_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MILLISECOND
            for value in scaling_key_generation_maximum_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MILLISECOND
            for value in scaling_key_generation_first_quartile_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MILLISECOND
            for value in scaling_key_generation_third_quartile_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in scaling_key_encrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in scaling_key_encrypt_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in scaling_key_decrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in scaling_key_decrypt_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in scaling_key_ciphertext_size_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in scaling_key_ciphertext_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in scaling_key_generation_stored_key_size_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in scaling_key_generation_stored_key_ci_list
        ],
        str(result_dir / RSA_KEY_BITS_PLOT),
    )

    # Draw Ciphertext Crossover Plot
    if (
        ciphertext_crossover_low is not None
        and ciphertext_crossover_high is not None
        and cpabe_low_ciphertext is not None
        and cpabe_high_ciphertext is not None
    ):
        plot_ciphertext_size_crossover(
            subscriber_counts,
            [
                NO_MEASUREMENT if value is None else value
                for value in scaling_subscriber_total_ciphertext_size_list
            ],
            [
                NO_MEASUREMENT if value is None else value
                for value in scaling_subscriber_total_ciphertext_ci_list
            ],
            min_attributes,
            cpabe_low_ciphertext,
            ciphertext_crossover_low,
            max_attributes,
            cpabe_high_ciphertext,
            ciphertext_crossover_high,
            str(result_dir / CIPHERTEXT_SIZE_CROSSOVER_PLOT),
        )
        bandwidth_crossover_plot = CIPHERTEXT_SIZE_CROSSOVER_PLOT
    else:
        bandwidth_crossover_plot = None

    # Encrypt latency crossover plot
    if (
        subscriber_encrypt_fit is not None
        and latency_crossover_low is not None
        and latency_crossover_high is not None
        and cpabe_low_encrypt_latency is not None
        and cpabe_high_encrypt_latency is not None
    ):
        projection_start_subscribers = float(subscriber_counts[-1])
        projection_end_subscribers = latency_crossover_high * 1.15
        projection_start_latency = subscriber_encrypt_fit.calculate_y_based_on_x(
            projection_start_subscribers
        )
        projection_end_latency = subscriber_encrypt_fit.calculate_y_based_on_x(
            projection_end_subscribers
        )
        plot_encrypt_latency_crossover(
            subscriber_counts,
            [
                NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
                for value in scaling_subscriber_encrypt_latency_list
            ],
            [
                NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
                for value in scaling_subscriber_encrypt_latency_ci_list
            ],
            projection_start_subscribers,
            projection_start_latency / NS_PER_MICROSECOND,
            projection_end_subscribers,
            projection_end_latency / NS_PER_MICROSECOND,
            min_attributes,
            cpabe_low_encrypt_latency / NS_PER_MICROSECOND,
            latency_crossover_low,
            max_attributes,
            cpabe_high_encrypt_latency / NS_PER_MICROSECOND,
            latency_crossover_high,
            str(result_dir / ENCRYPT_LATENCY_CROSSOVER_PLOT),
        )
        encrypt_crossover_plot = ENCRYPT_LATENCY_CROSSOVER_PLOT
    else:
        encrypt_crossover_plot = None

    decrypt_crossover_available = any(
        value is not None for value in scaling_key_decrypt_latency_list
    ) and any(value is not None for value in scaling_attribute_decrypt_latency_list)
    if decrypt_crossover_available:
        plot_decrypt_latency_crossover(
            attribute_counts,
            [
                NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
                for value in scaling_attribute_decrypt_latency_list
            ],
            [
                NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
                for value in scaling_attribute_decrypt_latency_ci_list
            ],
            rsa_key_sizes,
            [
                NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
                for value in scaling_key_decrypt_latency_list
            ],
            [
                NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
                for value in scaling_key_decrypt_latency_ci_list
            ],
            str(result_dir / DECRYPT_LATENCY_CROSSOVER_PLOT),
        )

        decrypt_crossover_plot = DECRYPT_LATENCY_CROSSOVER_PLOT
    else:
        decrypt_crossover_plot = None

    # Encrypt/decrypt asymmetry plot
    rsa_encrypt_reference = scaling_key_encrypt[fixed_rsa_key_index]
    cpabe_min_encrypt = scaling_attribute_encrypt[0]
    cpabe_min_decrypt = scaling_attribute_decrypt[0]

    asymmetry_available = not any(
        aggregation.out_of_memory
        for aggregation in (
            rsa_encrypt_reference,
            rsa_decrypt_reference,
            cpabe_min_encrypt,
            cpabe_min_decrypt,
        )
    )

    if asymmetry_available:
        rsa_encrypt_micros = rsa_encrypt_reference.mean(NS_PER_OP) / NS_PER_MICROSECOND
        rsa_decrypt_micros = rsa_decrypt_reference.mean(NS_PER_OP) / NS_PER_MICROSECOND
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
            fixed_rsa_key_size,
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

    # Peak-memory plot
    plot_peak_memory(
        attribute_counts,
        [value / MEGABYTE for value in scaling_attribute_memory_encrypt_list],
        [value / MEGABYTE for value in scaling_attribute_memory_encrypt_ci_list],
        [value / MEGABYTE for value in scaling_attribute_memory_decrypt_list],
        [value / MEGABYTE for value in scaling_attribute_memory_decrypt_ci_list],
        subscriber_counts,
        [value / MEGABYTE for value in scaling_subscriber_memory_encrypt_list],
        [value / MEGABYTE for value in scaling_subscriber_memory_encrypt_ci_list],
        (
            None
            if scaling_subscriber_memory_decrypt is None
            else scaling_subscriber_memory_decrypt / MEGABYTE
        ),
        rsa_key_sizes,
        [value / MEGABYTE for value in scaling_key_memory_encrypt_list],
        [value / MEGABYTE for value in scaling_key_memory_encrypt_ci_list],
        [value / MEGABYTE for value in scaling_key_memory_decrypt_list],
        [value / MEGABYTE for value in scaling_key_memory_decrypt_ci_list],
        fixed_rsa_key_size,
        str(result_dir / PEAK_MEMORY_PLOT),
    )

    write_attribute_key_scaling_report(
        timing_runs=timing_runs,
        t_multiplier=get_student_t_critical_95(timing_runs - 1),
        timing_iterations=timing_iterations,
        attribute_counts=attribute_counts,
        subscriber_counts=subscriber_counts,
        rsa_key_sizes=rsa_key_sizes,
        fixed_rsa_key_bits=fixed_rsa_key_size,
        cpabe_encrypt_latency_means=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in scaling_attribute_encrypt_latency_list
        ],
        cpabe_encrypt_latency_cis=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in scaling_attribute_encrypt_latency_ci_list
        ],
        cpabe_encrypt_ciphertext_sizes=scaling_attribute_ciphertext_size_list,
        cpabe_encrypt_iterations=scaling_attribute_encrypt_iteration_list,
        cpabe_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", CPABE_ATTRIBUTES, attribute_counts
        ),
        cpabe_decrypt_latency_means=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in scaling_attribute_decrypt_latency_list
        ],
        cpabe_decrypt_latency_cis=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in scaling_attribute_decrypt_latency_ci_list
        ],
        cpabe_decrypt_stored_key_sizes=scaling_attribute_stored_key_size_list,
        cpabe_decrypt_iterations=scaling_attribute_decrypt_iteration_list,
        cpabe_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", CPABE_ATTRIBUTES, attribute_counts
        ),
        subscriber_encrypt_latency_means=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in scaling_subscriber_encrypt_latency_list
        ],
        subscriber_encrypt_latency_cis=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in scaling_subscriber_encrypt_latency_ci_list
        ],
        subscriber_ciphertext_sizes=scaling_subscriber_ciphertext_size_list,
        subscriber_total_ciphertext_sizes=scaling_subscriber_total_ciphertext_size_list,
        subscriber_encrypt_iterations=scaling_subscriber_encrypt_iteration_list,
        subscriber_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", RSA_SUBSCRIBERS, subscriber_counts
        ),
        rsa_encrypt_latency_means=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in scaling_key_encrypt_latency_list
        ],
        rsa_encrypt_latency_cis=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in scaling_key_encrypt_latency_ci_list
        ],
        rsa_ciphertext_sizes=scaling_key_ciphertext_size_list,
        rsa_encrypt_iterations=scaling_key_encrypt_iteration_list,
        rsa_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", RSA_KEY_BITS, rsa_key_sizes
        ),
        rsa_decrypt_latency_means=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in scaling_key_decrypt_latency_list
        ],
        rsa_decrypt_latency_cis=[
            None if value is None else value / NS_PER_MICROSECOND
            for value in scaling_key_decrypt_latency_ci_list
        ],
        rsa_decrypt_iterations=scaling_key_decrypt_iteration_list,
        rsa_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", RSA_KEY_BITS, rsa_key_sizes
        ),
        keygen_medians=[
            None if value is None else value / NS_PER_MILLISECOND
            for value in scaling_key_generation_median_list
        ],
        keygen_minimums=[
            None if value is None else value / NS_PER_MILLISECOND
            for value in scaling_key_generation_minimum_list
        ],
        keygen_maximums=[
            None if value is None else value / NS_PER_MILLISECOND
            for value in scaling_key_generation_maximum_list
        ],
        keygen_iqrs=[
            None if value is None else value / NS_PER_MILLISECOND
            for value in scaling_key_generation_iqr_list
        ],
        keygen_stored_key_sizes=scaling_key_generation_stored_key_size_list,
        keygen_sample_counts=scaling_key_generation_sample_count_list,
        keygen_throttled=results.get_throttle_flags(
            "KeyGen", RSA_KEY_BITS, rsa_key_sizes
        ),
        baseline_memory_mean=baseline_memory / MEGABYTE,
        baseline_memory_ci=baseline_memory_ci / MEGABYTE,
        cpabe_memory_encrypt_means=[
            value / MEGABYTE for value in scaling_attribute_memory_encrypt_list
        ],
        cpabe_memory_encrypt_cis=[
            value / MEGABYTE for value in scaling_attribute_memory_encrypt_ci_list
        ],
        cpabe_memory_decrypt_means=[
            value / MEGABYTE for value in scaling_attribute_memory_decrypt_list
        ],
        cpabe_memory_decrypt_cis=[
            value / MEGABYTE for value in scaling_attribute_memory_decrypt_ci_list
        ],
        cpabe_memory_sample_counts=scaling_attribute_memory_sample_count_list,
        subscriber_memory_encrypt_means=[
            value / MEGABYTE for value in scaling_subscriber_memory_encrypt_list
        ],
        subscriber_memory_encrypt_cis=[
            value / MEGABYTE for value in scaling_subscriber_memory_encrypt_ci_list
        ],
        subscriber_memory_decrypt_mean=(
            None
            if scaling_subscriber_memory_decrypt is None
            else scaling_subscriber_memory_decrypt / MEGABYTE
        ),
        subscriber_memory_decrypt_ci=(
            None
            if scaling_subscriber_memory_decrypt_ci is None
            else scaling_subscriber_memory_decrypt_ci / MEGABYTE
        ),
        subscriber_memory_sample_counts=scaling_subscriber_memory_sample_count_list,
        rsa_memory_encrypt_means=[
            value / MEGABYTE for value in scaling_key_memory_encrypt_list
        ],
        rsa_memory_encrypt_cis=[
            value / MEGABYTE for value in scaling_key_memory_encrypt_ci_list
        ],
        rsa_memory_decrypt_means=[
            value / MEGABYTE for value in scaling_key_memory_decrypt_list
        ],
        rsa_memory_decrypt_cis=[
            value / MEGABYTE for value in scaling_key_memory_decrypt_ci_list
        ],
        rsa_memory_sample_counts=scaling_key_memory_sample_count_list,
        cpabe_encrypt_memory_first=cpabe_encrypt_memory_first / MEGABYTE,
        cpabe_encrypt_memory_last=cpabe_encrypt_memory_last / MEGABYTE,
        cpabe_encrypt_memory_absolute_change=(
            cpabe_encrypt_memory_absolute_change / MEGABYTE
        ),
        cpabe_encrypt_memory_percent_change=cpabe_encrypt_memory_percent_change,
        cpabe_decrypt_memory_first=cpabe_decrypt_memory_first / MEGABYTE,
        cpabe_decrypt_memory_last=cpabe_decrypt_memory_last / MEGABYTE,
        cpabe_decrypt_memory_absolute_change=(
            cpabe_decrypt_memory_absolute_change / MEGABYTE
        ),
        cpabe_decrypt_memory_percent_change=cpabe_decrypt_memory_percent_change,
        subscriber_encrypt_memory_first=(subscriber_encrypt_memory_first / MEGABYTE),
        subscriber_encrypt_memory_last=(subscriber_encrypt_memory_last / MEGABYTE),
        subscriber_encrypt_memory_absolute_change=(
            subscriber_encrypt_memory_absolute_change / MEGABYTE
        ),
        subscriber_encrypt_memory_percent_change=(
            subscriber_encrypt_memory_percent_change
        ),
        rsa_encrypt_memory_first=rsa_encrypt_memory_first / MEGABYTE,
        rsa_encrypt_memory_last=rsa_encrypt_memory_last / MEGABYTE,
        rsa_encrypt_memory_absolute_change=(
            rsa_encrypt_memory_absolute_change / MEGABYTE
        ),
        rsa_encrypt_memory_percent_change=rsa_encrypt_memory_percent_change,
        rsa_decrypt_memory_first=rsa_decrypt_memory_first / MEGABYTE,
        rsa_decrypt_memory_last=rsa_decrypt_memory_last / MEGABYTE,
        rsa_decrypt_memory_absolute_change=(
            rsa_decrypt_memory_absolute_change / MEGABYTE
        ),
        rsa_decrypt_memory_percent_change=rsa_decrypt_memory_percent_change,
        fanout_single_bytes=bytes_per_subscriber,
        fanout_total_bytes=scaling_subscriber_total_ciphertext_size_list[-1],
        fanout_multiplier=subscriber_counts[-1],
        out_of_memory_operations=[
            aggregation.operation for aggregation in out_of_memory_aggregations
        ],
        out_of_memory_cases=[
            f"{aggregation.parameter}/{aggregation.parameter_value}"
            for aggregation in out_of_memory_aggregations
        ],
        cpabe_encrypt_slope=(
            None
            if cpabe_encrypt_fit is None
            else cpabe_encrypt_fit.slope / NS_PER_MICROSECOND
        ),
        cpabe_encrypt_slope_ci=(
            None
            if cpabe_encrypt_fit is None
            else cpabe_encrypt_fit.slope_ci / NS_PER_MICROSECOND
        ),
        cpabe_encrypt_r_squared=(
            None if cpabe_encrypt_fit is None else cpabe_encrypt_fit.r_squared
        ),
        cpabe_decrypt_slope=(
            None
            if cpabe_decrypt_fit is None
            else cpabe_decrypt_fit.slope / NS_PER_MICROSECOND
        ),
        cpabe_decrypt_slope_ci=(
            None
            if cpabe_decrypt_fit is None
            else cpabe_decrypt_fit.slope_ci / NS_PER_MICROSECOND
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
            None
            if subscriber_encrypt_fit is None
            else subscriber_encrypt_fit.slope / NS_PER_MICROSECOND
        ),
        subscriber_encrypt_slope_ci=(
            None
            if subscriber_encrypt_fit is None
            else subscriber_encrypt_fit.slope_ci / NS_PER_MICROSECOND
        ),
        subscriber_encrypt_r_squared=(
            None if subscriber_encrypt_fit is None else subscriber_encrypt_fit.r_squared
        ),
        bytes_per_subscriber=bytes_per_subscriber,
        bytes_crossover_low=ciphertext_crossover_low,
        bytes_crossover_high=ciphertext_crossover_high,
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
