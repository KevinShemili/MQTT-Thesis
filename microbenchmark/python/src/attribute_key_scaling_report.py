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

NS_PER_MILLISECOND = 1000000.0

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

CIPHERTEXT_COLUMN = ("CIPHERTEXT", CIPHERTEXT_BYTES)

FANOUT_LARGEST_DIAMETER_PX = 168.0
FANOUT_SMALLEST_DIAMETER_PX = 22.0

MINIMUM_FIT_POINTS = 3

NOT_AVAILABLE = "&mdash;"
OUT_OF_MEMORY = "Out of memory"

MISSING_CASE_NOTE = (
    '<p class="missing-note">Not available: a case this comparison rests on ran out '
    "of memory. See Out of Memory at the top of the report.</p>"
)


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


# Decrypt does not depend on how many subscribers there are, a subscriber only ever
# unwraps its own session key, so it is not swept against subscriber count at all. What
# the subscriber sweep quotes for it is the figure the key size sweep measured at the
# fixed key size, which is the same operation on the same key actually performed
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


def build_latency_table(
    results: BenchmarkSummary,
    runs: int,
    sweep_name: str,
    sweep_values: list[int],
    operation: str,
    value_header: str,
    size_columns: tuple[tuple[str, str], ...] = (),
    highlight_value: int | None = None,
) -> str:

    rows = []

    for sweep_value in sweep_values:

        # The sweep value was configured and attempted, so it keeps its row. What the
        # process managed to print before it died is not a measurement of it
        aggregation = results.find_aggregation(operation, sweep_name, sweep_value)

        if aggregation is None or aggregation.out_of_memory:
            rows.append(
                [str(sweep_value), OUT_OF_MEMORY]
                + [NOT_AVAILABLE] * (len(size_columns) + 1)
            )
            continue

        latency_mean = aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND
        latency_ci = aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND

        rows.append(
            [
                str(sweep_value),
                format_mean_with_ci(latency_mean, latency_ci),
                *[
                    format_byte_size(round(aggregation.mean(measurement_name)))
                    for _, measurement_name in size_columns
                ],
                f"{aggregation.iterations:,}",
            ]
        )

    return build_html_table(
        [
            value_header.upper(),
            "LATENCY (µs/op)",
            *[header for header, _ in size_columns],
            f"ITERS (Σ{runs} RUNS)",
        ],
        rows,
        results.get_throttle_flags(operation, sweep_name, sweep_values),
        thermal_header="THERMAL",
        highlighted=[sweep_value == highlight_value for sweep_value in sweep_values],
    )


# Key generation is reported as the distribution it is. Every run performs exactly one
# generation, so each run contributes one sample and the column n is that sample count.
# The spread between min and max is the point, a single averaged figure would not be
# representative of a probabilistic prime search
def build_keygen_table(results: BenchmarkSummary, rsa_key_sizes: list[int]) -> str:

    rows = []

    for rsa_key_bits in rsa_key_sizes:
        aggregation = results.find_aggregation("KeyGen", RSA_KEY_BITS, rsa_key_bits)

        if aggregation is None or aggregation.out_of_memory:
            rows.append([str(rsa_key_bits), OUT_OF_MEMORY] + [NOT_AVAILABLE] * 5)
            continue

        rows.append(
            [
                str(rsa_key_bits),
                f"{aggregation.median(NS_PER_OP) / NS_PER_MILLISECOND:,.2f}",
                f"{aggregation.minimum(NS_PER_OP) / NS_PER_MILLISECOND:,.2f}",
                f"{aggregation.maximum(NS_PER_OP) / NS_PER_MILLISECOND:,.2f}",
                f"{aggregation.iqr(NS_PER_OP) / NS_PER_MILLISECOND:,.2f}",
                format_byte_size(round(aggregation.mean(STORED_KEY_BYTES))),
                str(aggregation.get_sample_count(NS_PER_OP)),
            ]
        )

    return build_html_table(
        [
            "KEY BITS",
            "MEDIAN (ms)",
            "MIN (ms)",
            "MAX (ms)",
            "IQR (ms)",
            "STORED KEY",
            "n",
        ],
        rows,
        results.get_throttle_flags("KeyGen", RSA_KEY_BITS, rsa_key_sizes),
        thermal_header="THERMAL",
    )


# Peak memory as it was measured, one row per configured sweep value. All three tables
# keep the same columns so they can be read against one another, and the column a sweep
# did not measure carries the reading of that operation from where it was measured
def build_cpabe_peak_memory_table(
    results: BenchmarkSummary,
    attribute_counts: list[int],
) -> str:
    rows = []

    for attribute_count in attribute_counts:
        encrypt = results.find_aggregation(
            "MemoryEncrypt", CPABE_ATTRIBUTES, attribute_count
        )
        decrypt = results.find_aggregation(
            "MemoryDecrypt", CPABE_ATTRIBUTES, attribute_count
        )
        assert encrypt is not None and decrypt is not None

        rows.append(
            [
                str(attribute_count),
                format_mean_with_ci(
                    encrypt.mean(PEAK_RSS_BYTES) / MEGABYTE,
                    encrypt.confidence_interval(PEAK_RSS_BYTES) / MEGABYTE,
                ),
                format_mean_with_ci(
                    decrypt.mean(PEAK_RSS_BYTES) / MEGABYTE,
                    decrypt.confidence_interval(PEAK_RSS_BYTES) / MEGABYTE,
                ),
                str(decrypt.get_sample_count(PEAK_RSS_BYTES)),
            ]
        )

    return build_html_table(["ATTRIBUTES", "ENCRYPT (MB)", "DECRYPT (MB)", "n"], rows)


def build_rsa_subscriber_peak_memory_table(
    results: BenchmarkSummary,
    subscriber_counts: list[int],
    fixed_rsa_key_bits: int,
) -> str:
    decrypt_reference = find_fixed_rsa_aggregation(
        results, "MemoryDecrypt", fixed_rsa_key_bits, PEAK_RSS_BYTES
    )
    decrypt_value = (
        NOT_AVAILABLE
        if decrypt_reference is None
        else format_mean_with_ci(
            decrypt_reference.mean(PEAK_RSS_BYTES) / MEGABYTE,
            decrypt_reference.confidence_interval(PEAK_RSS_BYTES) / MEGABYTE,
        )
    )
    rows = []

    for subscriber_count in subscriber_counts:
        encrypt = results.find_aggregation(
            "MemoryEncrypt", RSA_SUBSCRIBERS, subscriber_count
        )
        assert encrypt is not None

        rows.append(
            [
                str(subscriber_count),
                format_mean_with_ci(
                    encrypt.mean(PEAK_RSS_BYTES) / MEGABYTE,
                    encrypt.confidence_interval(PEAK_RSS_BYTES) / MEGABYTE,
                ),
                decrypt_value,
                str(encrypt.get_sample_count(PEAK_RSS_BYTES)),
            ]
        )

    return build_html_table(["SUBSCRIBERS", "ENCRYPT (MB)", "DECRYPT (MB)", "n"], rows)


def build_rsa_key_size_peak_memory_table(
    results: BenchmarkSummary,
    rsa_key_sizes: list[int],
) -> str:
    rows = []

    for rsa_key_bits in rsa_key_sizes:
        encrypt = results.find_aggregation("MemoryEncrypt", RSA_KEY_BITS, rsa_key_bits)
        decrypt = results.find_aggregation("MemoryDecrypt", RSA_KEY_BITS, rsa_key_bits)
        assert encrypt is not None and decrypt is not None

        rows.append(
            [
                str(rsa_key_bits),
                format_mean_with_ci(
                    encrypt.mean(PEAK_RSS_BYTES) / MEGABYTE,
                    encrypt.confidence_interval(PEAK_RSS_BYTES) / MEGABYTE,
                ),
                format_mean_with_ci(
                    decrypt.mean(PEAK_RSS_BYTES) / MEGABYTE,
                    decrypt.confidence_interval(PEAK_RSS_BYTES) / MEGABYTE,
                ),
                str(decrypt.get_sample_count(PEAK_RSS_BYTES)),
            ]
        )

    return build_html_table(["KEY BITS", "ENCRYPT (MB)", "DECRYPT (MB)", "n"], rows)


# The change across the two ends of each sweep. Peak memory is a runtime floor plus
# whatever an operation had to touch, not a quantity that follows a slope, so the two ends
# are quoted as they were measured and nothing is fitted through what lies between them
def build_peak_memory_deltas(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    subscriber_counts: list[int],
    rsa_key_sizes: list[int],
) -> str:

    # The ends are the ones the experiment was configured with. If either did not complete
    # there is no such change, and the ends that did survive are not a substitute for it
    def endpoints_change(group: str, operation: str, sweep_values: list[int]) -> str:
        first_aggregation = results.find_aggregation(operation, group, sweep_values[0])
        last_aggregation = results.find_aggregation(operation, group, sweep_values[-1])

        if (
            first_aggregation is None
            or first_aggregation.out_of_memory
            or last_aggregation is None
            or last_aggregation.out_of_memory
        ):
            return NOT_AVAILABLE

        first = first_aggregation.mean(PEAK_RSS_BYTES) / MEGABYTE
        last = last_aggregation.mean(PEAK_RSS_BYTES) / MEGABYTE

        return (
            f"{first:,.2f} &rarr; {last:,.2f} MB &middot; {last - first:+,.2f} MB "
            f"({(last / first - 1) * 100:+,.1f}%)"
        )

    # Only what each sweep moved. The subscriber sweep's borrowed decrypt reading is not
    # presented as a change of its own.
    items = [
        '<span class="delta-item"><strong>CP-ABE Encrypt</strong> '
        f"{attribute_counts[0]} &rarr; {attribute_counts[-1]} attributes &middot; "
        f'{endpoints_change(CPABE_ATTRIBUTES, "MemoryEncrypt", attribute_counts)}</span>',
        '<span class="delta-item"><strong>CP-ABE Decrypt</strong> '
        f"{attribute_counts[0]} &rarr; {attribute_counts[-1]} attributes &middot; "
        f'{endpoints_change(CPABE_ATTRIBUTES, "MemoryDecrypt", attribute_counts)}</span>',
        '<span class="delta-item"><strong>RSA Subscribers Encrypt</strong> '
        f"{subscriber_counts[0]} &rarr; {subscriber_counts[-1]} subscribers &middot; "
        f'{endpoints_change(RSA_SUBSCRIBERS, "MemoryEncrypt", subscriber_counts)}</span>',
        '<span class="delta-item"><strong>RSA Key Size Encrypt</strong> '
        f"{rsa_key_sizes[0]} &rarr; {rsa_key_sizes[-1]} key bits &middot; "
        f'{endpoints_change(RSA_KEY_BITS, "MemoryEncrypt", rsa_key_sizes)}</span>',
        '<span class="delta-item"><strong>RSA Key Size Decrypt</strong> '
        f"{rsa_key_sizes[0]} &rarr; {rsa_key_sizes[-1]} key bits &middot; "
        f'{endpoints_change(RSA_KEY_BITS, "MemoryDecrypt", rsa_key_sizes)}</span>',
    ]

    return f'<div class="delta-strip">{"".join(items)}</div>'


def build_rsa_circle_visualization(
    results: BenchmarkSummary,
    subscriber_counts: list[int],
    bytes_per_subscriber: float | None,
) -> dict[str, str]:

    def circle_style(diameter_px: float) -> str:
        return f'style="width:{diameter_px:.0f}px;height:{diameter_px:.0f}px;"'

    largest_aggregation = results.find_aggregation(
        "Encrypt", RSA_SUBSCRIBERS, subscriber_counts[-1]
    )
    if (
        bytes_per_subscriber is None
        or largest_aggregation is None
        or largest_aggregation.out_of_memory
    ):
        return {
            "FanoutSingleBytes": NOT_AVAILABLE,
            "FanoutTotalBytes": NOT_AVAILABLE,
            "FanoutMultiplier": NOT_AVAILABLE,
            "FanoutSingleStyle": circle_style(FANOUT_SMALLEST_DIAMETER_PX),
            "FanoutTotalStyle": circle_style(FANOUT_SMALLEST_DIAMETER_PX),
        }

    single_bytes = bytes_per_subscriber
    total_bytes = largest_aggregation.mean(TOTAL_CIPHERTEXT_BYTES)

    single_diameter_px = max(
        FANOUT_SMALLEST_DIAMETER_PX,
        FANOUT_LARGEST_DIAMETER_PX * (single_bytes / total_bytes) ** 0.5,
    )

    return {
        "FanoutSingleBytes": format_byte_size(round(single_bytes)),
        "FanoutTotalBytes": format_byte_size(round(total_bytes)),
        "FanoutMultiplier": f"{total_bytes / single_bytes:.0f}",
        "FanoutSingleStyle": circle_style(single_diameter_px),
        "FanoutTotalStyle": circle_style(FANOUT_LARGEST_DIAMETER_PX),
    }


def out_of_memory_rows(results: BenchmarkSummary) -> list[list[str]]:
    return [
        [
            aggregation.operation,
            f"{aggregation.parameter}/{aggregation.parameter_value}",
            OUT_OF_MEMORY,
        ]
        for aggregation in results.aggregations
        if aggregation.out_of_memory
    ]


def write_html_report(
    results: BenchmarkSummary,
    timing_runs: int,
    attribute_counts: list[int],
    subscriber_counts: list[int],
    rsa_key_sizes: list[int],
    fixed_rsa_key_bits: int,
    encrypt_fit: LinearRegression | None,
    bytes_per_subscriber: float | None,
    bytes_crossover_low: float | None,
    bytes_crossover_high: float | None,
    latency_crossover_low: float | None,
    latency_crossover_high: float | None,
    frames: dict[str, str],
    template_path: str,
    report_path: str,
) -> None:
    min_attributes = attribute_counts[0]
    max_attributes = attribute_counts[-1]

    cpabe_encrypt = fit_measurement(
        results,
        "Encrypt",
        CPABE_ATTRIBUTES,
        attribute_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )
    cpabe_decrypt = fit_measurement(
        results,
        "Decrypt",
        CPABE_ATTRIBUTES,
        attribute_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )
    cpabe_ciphertext = fit_measurement(
        results, "Encrypt", CPABE_ATTRIBUTES, attribute_counts, CIPHERTEXT_BYTES
    )
    cpabe_stored_key = fit_measurement(
        results, "Decrypt", CPABE_ATTRIBUTES, attribute_counts, STORED_KEY_BYTES
    )

    def micros_slope(fit: LinearRegression | None) -> str:
        if fit is None:
            return NOT_AVAILABLE

        return f"+{format_mean_with_ci(fit.slope, fit.slope_ci, decimals=0)} µs"

    def bytes_slope(fit: LinearRegression | None) -> str:
        if fit is None:
            return NOT_AVAILABLE

        return f"+{format_mean_with_ci(fit.slope, fit.slope_ci, decimals=0, thousands=False)} B"

    def fit_quality(fit: LinearRegression | None) -> str:
        if fit is None:
            return NOT_AVAILABLE

        return f"{fit.r_squared:.6f}"

    # How much more decrypt latency CP-ABE asks of the subscriber than RSA does
    def decrypt_penalty(attribute_count: int) -> float | None:
        cpabe_decrypt = results.find_aggregation(
            "Decrypt", CPABE_ATTRIBUTES, attribute_count
        )
        rsa_decrypt = results.find_aggregation(
            "Decrypt", RSA_KEY_BITS, fixed_rsa_key_bits
        )
        if (
            cpabe_decrypt is None
            or cpabe_decrypt.out_of_memory
            or rsa_decrypt is None
            or rsa_decrypt.out_of_memory
        ):
            return None

        rsa_decrypt_micros = rsa_decrypt.mean(NS_PER_OP) / NS_PER_MICROSECOND
        cpabe_decrypt_micros = cpabe_decrypt.mean(NS_PER_OP) / NS_PER_MICROSECOND

        return cpabe_decrypt_micros / rsa_decrypt_micros

    # A crossover the report could not compute reads as absent rather than as a zero
    def rounded(value: float | None, decimals: int = 0) -> str:
        if value is None:
            return NOT_AVAILABLE

        return f"{value:,.{decimals}f}"

    # The whole subscribers RSA gets through before it reaches CP-ABE, so truncated
    def truncated(value: float | None) -> str:
        if value is None:
            return NOT_AVAILABLE

        return f"{int(value):,}"

    # The runtime with nothing restored or performed is the floor every memory case was
    # measured on top of.
    memory_baseline = results.find_aggregation("MemoryBaseline", "Runtime", 0)
    assert memory_baseline is not None and not memory_baseline.out_of_memory
    baseline_mean = memory_baseline.mean(PEAK_RSS_BYTES) / MEGABYTE
    baseline_ci = memory_baseline.confidence_interval(PEAK_RSS_BYTES) / MEGABYTE

    timing_iterations = sum(
        aggregation.iterations
        for aggregation in results.aggregations
        if aggregation.operation in ("Encrypt", "Decrypt", "KeyGen")
        and not aggregation.out_of_memory
    )

    placeholders = {
        **build_html_generic_data(
            timing_runs,
            timing_iterations,
        ),
        **build_rsa_circle_visualization(
            results, subscriber_counts, bytes_per_subscriber
        ),
        **frames,
        "PeakMemoryDeltas": build_peak_memory_deltas(
            results, attribute_counts, subscriber_counts, rsa_key_sizes
        ),
        "PeakMemoryCpabeTable": build_cpabe_peak_memory_table(
            results, attribute_counts
        ),
        "PeakMemoryRsaSubscribersTable": build_rsa_subscriber_peak_memory_table(
            results, subscriber_counts, fixed_rsa_key_bits
        ),
        "PeakMemoryRsaKeyBitsTable": build_rsa_key_size_peak_memory_table(
            results, rsa_key_sizes
        ),
        "OutOfMemoryNotice": build_html_out_of_memory_notice(
            out_of_memory_rows(results)
        ),
        "BaselineRss": f"{format_mean_with_ci(baseline_mean, baseline_ci)} MB",
        "CpabeEncryptTable": build_latency_table(
            results,
            timing_runs,
            CPABE_ATTRIBUTES,
            attribute_counts,
            "Encrypt",
            "Attributes",
            (CIPHERTEXT_COLUMN,),
        ),
        "CpabeDecryptTable": build_latency_table(
            results,
            timing_runs,
            CPABE_ATTRIBUTES,
            attribute_counts,
            "Decrypt",
            "Attributes",
            (("STORED KEY", STORED_KEY_BYTES),),
        ),
        "RsaSubscribersEncryptTable": build_latency_table(
            results,
            timing_runs,
            RSA_SUBSCRIBERS,
            subscriber_counts,
            "Encrypt",
            "Subscribers",
            (
                CIPHERTEXT_COLUMN,
                ("CIPHERTEXT (TOTAL)", TOTAL_CIPHERTEXT_BYTES),
            ),
        ),
        "RsaKeyBitsEncryptTable": build_latency_table(
            results,
            timing_runs,
            RSA_KEY_BITS,
            rsa_key_sizes,
            "Encrypt",
            "Key Bits",
            (CIPHERTEXT_COLUMN,),
        ),
        # The row the cross-schema comparisons and the subscriber sweep are quoted
        # against, marked so it can be found among the key sizes around it
        "RsaKeyBitsDecryptTable": build_latency_table(
            results,
            timing_runs,
            RSA_KEY_BITS,
            rsa_key_sizes,
            "Decrypt",
            "Key Bits",
            highlight_value=fixed_rsa_key_bits,
        ),
        "RsaKeyBitsKeygenTable": build_keygen_table(results, rsa_key_sizes),
        "MinAttributeLabel": format_attribute_label(min_attributes),
        "MaxAttributeLabel": format_attribute_label(max_attributes),
        "MaxSubscriberCount": str(subscriber_counts[-1]),
        "FixedRsaKeyBits": str(fixed_rsa_key_bits),
        "CpabePlot": CPABE_PLOT,
        "RsaSubscribersPlot": RSA_SUBSCRIBERS_PLOT,
        "RsaKeyBitsPlot": RSA_KEY_BITS_PLOT,
        "CpabeEncryptSlope": micros_slope(cpabe_encrypt),
        "CpabeDecryptSlope": micros_slope(cpabe_decrypt),
        "CpabeCiphertextSlope": bytes_slope(cpabe_ciphertext),
        "CpabeStoredKeySlope": bytes_slope(cpabe_stored_key),
        "CpabeEncryptRSquared": fit_quality(cpabe_encrypt),
        "CpabeDecryptRSquared": fit_quality(cpabe_decrypt),
        "CpabeCiphertextRSquared": fit_quality(cpabe_ciphertext),
        "CpabeStoredKeyRSquared": fit_quality(cpabe_stored_key),
        "RsaSubscriberEncryptSlope": (
            NOT_AVAILABLE
            if encrypt_fit is None
            else f"+{format_mean_with_ci(encrypt_fit.slope, encrypt_fit.slope_ci)} µs"
        ),
        "RsaSubscriberEncryptRSquared": fit_quality(encrypt_fit),
        "RsaSubscriberTotalCiphertextSlope": (
            NOT_AVAILABLE
            if bytes_per_subscriber is None
            else f"+{bytes_per_subscriber:.0f} B"
        ),
        "BytesCrossoverLow": rounded(bytes_crossover_low, 1),
        "BytesCrossoverHigh": rounded(bytes_crossover_high, 1),
        "BytesRsaThroughMin": truncated(bytes_crossover_low),
        "BytesRsaThroughMax": truncated(bytes_crossover_high),
        "EncryptCpuCrossoverLow": rounded(latency_crossover_low),
        "EncryptCpuCrossoverHigh": rounded(latency_crossover_high),
        "CpuRsaThroughMin": truncated(latency_crossover_low),
        "CpuRsaThroughMax": truncated(latency_crossover_high),
        "DecryptPenaltyMin": rounded(decrypt_penalty(min_attributes), 1),
        "DecryptPenaltyMax": rounded(decrypt_penalty(max_attributes), 1),
    }

    build_html_report(template_path, report_path, placeholders)


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
        bytes_crossover_low = (
            cpabe_low_encrypt.mean(CIPHERTEXT_BYTES) / bytes_per_subscriber
        )
        bytes_crossover_high = (
            cpabe_high_encrypt.mean(CIPHERTEXT_BYTES) / bytes_per_subscriber
        )
    else:
        bytes_crossover_low = None
        bytes_crossover_high = None

    encrypt_fit = fit_measurement(
        results,
        "Encrypt",
        RSA_SUBSCRIBERS,
        subscriber_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )
    if encrypt_fit is not None and cpabe_encrypt_endpoints_available:
        assert cpabe_low_encrypt is not None and cpabe_high_encrypt is not None
        latency_crossover_low = encrypt_fit.solve_x_for_y(
            cpabe_low_encrypt.mean(NS_PER_OP) / NS_PER_MICROSECOND
        )
        latency_crossover_high = encrypt_fit.solve_x_for_y(
            cpabe_high_encrypt.mean(NS_PER_OP) / NS_PER_MICROSECOND
        )
    else:
        latency_crossover_low = None
        latency_crossover_high = None

    plot_cpabe_attribute_sweep(
        results,
        attribute_counts,
        str(result_dir / CPABE_PLOT),
    )

    plot_rsa_subscriber_sweep(
        results,
        subscriber_counts,
        fixed_rsa_key_bits,
        str(result_dir / RSA_SUBSCRIBERS_PLOT),
    )

    plot_rsa_key_size_sweep(
        results,
        rsa_key_sizes,
        str(result_dir / RSA_KEY_BITS_PLOT),
    )

    if bytes_crossover_low is not None and bytes_crossover_high is not None:
        plot_ciphertext_size_crossover(
            results,
            attribute_counts,
            subscriber_counts,
            bytes_crossover_low,
            bytes_crossover_high,
            str(result_dir / CIPHERTEXT_SIZE_CROSSOVER_PLOT),
        )
        bandwidth_crossover_frame = f'<img src="{CIPHERTEXT_SIZE_CROSSOVER_PLOT}">'
    else:
        bandwidth_crossover_frame = MISSING_CASE_NOTE

    if (
        encrypt_fit is not None
        and latency_crossover_low is not None
        and latency_crossover_high is not None
    ):
        plot_encrypt_latency_crossover(
            results,
            attribute_counts,
            subscriber_counts,
            encrypt_fit,
            latency_crossover_low,
            latency_crossover_high,
            str(result_dir / ENCRYPT_LATENCY_CROSSOVER_PLOT),
        )
        encrypt_crossover_frame = f'<img src="{ENCRYPT_LATENCY_CROSSOVER_PLOT}">'
    else:
        encrypt_crossover_frame = MISSING_CASE_NOTE

    rsa_decrypt_aggregations = [
        results.find_aggregation("Decrypt", RSA_KEY_BITS, rsa_key_bits)
        for rsa_key_bits in rsa_key_sizes
    ]
    cpabe_decrypt_aggregations = [
        results.find_aggregation("Decrypt", CPABE_ATTRIBUTES, attribute_count)
        for attribute_count in attribute_counts
    ]
    decrypt_crossover_available = any(
        aggregation is not None and not aggregation.out_of_memory
        for aggregation in rsa_decrypt_aggregations
    ) and any(
        aggregation is not None and not aggregation.out_of_memory
        for aggregation in cpabe_decrypt_aggregations
    )
    if decrypt_crossover_available:
        plot_decrypt_latency_crossover(
            results,
            attribute_counts,
            rsa_key_sizes,
            str(result_dir / DECRYPT_LATENCY_CROSSOVER_PLOT),
        )
        decrypt_crossover_frame = f'<img src="{DECRYPT_LATENCY_CROSSOVER_PLOT}">'
    else:
        decrypt_crossover_frame = MISSING_CASE_NOTE

    asymmetry_aggregations = [
        results.find_aggregation("Encrypt", RSA_KEY_BITS, fixed_rsa_key_bits),
        results.find_aggregation("Decrypt", RSA_KEY_BITS, fixed_rsa_key_bits),
        results.find_aggregation("Encrypt", CPABE_ATTRIBUTES, min_attributes),
        results.find_aggregation("Decrypt", CPABE_ATTRIBUTES, min_attributes),
    ]
    asymmetry_available = all(
        aggregation is not None and not aggregation.out_of_memory
        for aggregation in asymmetry_aggregations
    )
    if asymmetry_available:
        plot_encrypt_decrypt_asymmetry(
            results,
            attribute_counts,
            fixed_rsa_key_bits,
            str(result_dir / ASYMMETRY_PLOT),
        )
        asymmetry_frame = f'<img src="{ASYMMETRY_PLOT}">'
    else:
        asymmetry_frame = MISSING_CASE_NOTE

    plot_peak_memory(
        results,
        attribute_counts,
        subscriber_counts,
        rsa_key_sizes,
        fixed_rsa_key_bits,
        str(result_dir / PEAK_MEMORY_PLOT),
    )

    frames = {
        "BandwidthCrossoverFrame": bandwidth_crossover_frame,
        "EncryptCpuCrossoverFrame": encrypt_crossover_frame,
        "DecryptCpuCrossoverFrame": decrypt_crossover_frame,
        "AsymmetryFrame": asymmetry_frame,
        "PeakMemoryFrame": f'<img src="{PEAK_MEMORY_PLOT}">',
    }

    write_html_report(
        results,
        timing_runs,
        attribute_counts,
        subscriber_counts,
        rsa_key_sizes,
        fixed_rsa_key_bits,
        encrypt_fit,
        bytes_per_subscriber,
        bytes_crossover_low,
        bytes_crossover_high,
        latency_crossover_low,
        latency_crossover_high,
        frames,
        str(template_path),
        str(report_path),
    )


if __name__ == "__main__":
    main()
