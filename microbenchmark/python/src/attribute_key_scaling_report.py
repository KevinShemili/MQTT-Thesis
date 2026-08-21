import os
from pathlib import Path

from template_builder.chart import *
from template_builder.formatting import *
from template_builder.html import *
from template_builder.color import *

from model.benchmark_summary import *
from model.case_aggregation import *
from model.case import *
from model.measurement import *
from model.populate_model import *

from config.environment import *

from statistics_tbd.summary import *
from statistics_tbd.linear_regression import *

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

ENCRYPT_DECRYPT = ["Encrypt", "Decrypt"]

OPERATION_COLORS = {"Encrypt": AMBER, "Decrypt": VIOLET}
TOTAL_CIPHERTEXT_COLOR = TEAL

RSA_KEY_BITS_COLORS = [TOTAL_CIPHERTEXT_COLOR, BLUE, AMBER, CRIMSON]

CIPHERTEXT_COLUMN = ("CIPHERTEXT", CIPHERTEXT_BYTES)

FANOUT_LARGEST_DIAMETER_PX = 168.0
FANOUT_SMALLEST_DIAMETER_PX = 22.0

CROSSOVER_FIGURE_SIZE = (8.5, 5.2)

MINIMUM_FIT_POINTS = 3

NOT_AVAILABLE = "&mdash;"
OUT_OF_MEMORY = "Out of memory"

MISSING_CASE_NOTE = (
    '<p class="missing-note">Not available: a case this comparison rests on ran out '
    "of memory. See Out of Memory at the top of the report.</p>"
)


def format_attribute_label(attribute_count: int) -> str:
    if attribute_count == 1:
        return "1 ATTRIBUTE"

    return f"{attribute_count} ATTRIBUTES"


def find_measured_aggregation(
    results: BenchmarkSummary,
    operation: str,
    group: str,
    sweep_value: int,
) -> CaseAggregation | None:
    aggregation = results.find_aggregation(operation, group, sweep_value)

    if aggregation is None or aggregation.out_of_memory:
        return None

    return aggregation


# Whether every case these operations need at these sweep values survived.
def measured(
    results: BenchmarkSummary,
    operations: list[str],
    group: str,
    sweep_values: list[int],
) -> bool:

    return all(
        find_measured_aggregation(results, operation, group, sweep_value) is not None
        for operation in operations
        for sweep_value in sweep_values
    )


def plot_frame(drawn: bool, filename: str, note: str = MISSING_CASE_NOTE) -> str:

    if not drawn:
        return note

    return f'<img src="{filename}">'


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
        aggregation = find_measured_aggregation(results, operation, group, sweep_value)

        if aggregation is None:
            continue

        measured_x.append(sweep_value)
        measured_y.append(aggregation.mean(measurement_name) / divisor)

    if len(measured_x) < MINIMUM_FIT_POINTS:
        return None

    return fit_linear_regression(measured_x, measured_y)


def cpabe_micros(
    results: BenchmarkSummary,
    operation: str,
    attribute_count: int,
) -> float:

    aggregation = find_measured_aggregation(
        results, operation, CPABE_ATTRIBUTES, attribute_count
    )
    assert aggregation is not None
    return aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND


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
    aggregation = find_measured_aggregation(
        summary, operation, RSA_KEY_BITS, fixed_rsa_key_bits
    )

    if aggregation is None or not aggregation.has_measurement(feature_name):
        return None

    return aggregation


def cpabe_ciphertext_bytes(results: BenchmarkSummary, attribute_count: int) -> float:
    aggregation = find_measured_aggregation(
        results, "Encrypt", CPABE_ATTRIBUTES, attribute_count
    )
    assert aggregation is not None
    return aggregation.mean(CIPHERTEXT_BYTES)


# One wrapped session key is the same size at every subscriber count, and RSA's total
# ciphertext grows by exactly that much per additional subscriber
def rsa_bytes_per_subscriber(
    results: BenchmarkSummary, subscriber_counts: list[int]
) -> float:
    aggregation = find_measured_aggregation(
        results, "Encrypt", RSA_SUBSCRIBERS, subscriber_counts[0]
    )
    assert aggregation is not None
    return aggregation.mean(CIPHERTEXT_BYTES)


def plot_cpabe_attribute_sweep(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    output_path: str,
) -> None:
    figure, (latency_axis, size_axis) = plt.subplots(1, 2, figsize=(13, 5))
    figure.suptitle("CP-ABE Scaling with Policy Attribute Count", fontsize=13)

    for operation in ENCRYPT_DECRYPT:
        aggregations = [
            results.find_aggregation(operation, CPABE_ATTRIBUTES, attribute_count)
            for attribute_count in attribute_counts
        ]
        means = [
            (
                NO_MEASUREMENT
                if aggregation is None or aggregation.out_of_memory
                else aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND
            )
            for aggregation in aggregations
        ]
        confidence_intervals = [
            (
                NO_MEASUREMENT
                if aggregation is None or aggregation.out_of_memory
                else aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
            )
            for aggregation in aggregations
        ]

        draw_summary(
            latency_axis,
            attribute_counts,
            means,
            confidence_intervals,
            operation,
            OPERATION_COLORS[operation],
            with_ci=True,
        )

    for operation, measurement_name, label, color in (
        ("Encrypt", CIPHERTEXT_BYTES, "Ciphertext", AMBER),
        ("Decrypt", STORED_KEY_BYTES, "Private Key", CRIMSON),
    ):
        aggregations = [
            results.find_aggregation(operation, CPABE_ATTRIBUTES, attribute_count)
            for attribute_count in attribute_counts
        ]
        draw_summary(
            size_axis,
            attribute_counts,
            [
                (
                    NO_MEASUREMENT
                    if aggregation is None or aggregation.out_of_memory
                    else aggregation.mean(measurement_name)
                )
                for aggregation in aggregations
            ],
            [
                (
                    NO_MEASUREMENT
                    if aggregation is None or aggregation.out_of_memory
                    else aggregation.confidence_interval(measurement_name)
                )
                for aggregation in aggregations
            ],
            label,
            color,
        )

    latency_axis.set_title("Latency", fontsize=11)
    latency_axis.set_ylabel("Latency (µs) ± 95% CI")
    latency_axis.set_ylim(bottom=0)
    latency_axis.set_xticks(attribute_counts)
    latency_axis.set_xlabel("Policy Attributes")
    apply_value_grid(latency_axis)
    latency_axis.legend(fontsize=10)

    size_axis.set_title("Sizes", fontsize=11)
    size_axis.set_ylabel("Size (bytes)")
    size_axis.set_xticks(attribute_counts)
    size_axis.set_xlabel("Policy Attributes")
    size_axis.set_ylim(bottom=0)
    apply_value_grid(size_axis)
    size_axis.legend(fontsize=10)

    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    save_figure(figure, output_path)


def plot_rsa_subscriber_sweep(
    results: BenchmarkSummary,
    subscriber_counts: list[int],
    fixed_rsa_key_bits: int,
    output_path: str,
) -> None:
    figure, (latency_axis, size_axis) = plt.subplots(1, 2, figsize=(13, 5))
    figure.suptitle(
        f"RSA Scaling with Subscriber Count (Fixed Key: {fixed_rsa_key_bits} bits)",
        fontsize=13,
    )

    encrypt_aggregations = [
        results.find_aggregation("Encrypt", RSA_SUBSCRIBERS, subscriber_count)
        for subscriber_count in subscriber_counts
    ]
    draw_summary(
        latency_axis,
        subscriber_counts,
        [
            (
                NO_MEASUREMENT
                if aggregation is None or aggregation.out_of_memory
                else aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND
            )
            for aggregation in encrypt_aggregations
        ],
        [
            (
                NO_MEASUREMENT
                if aggregation is None or aggregation.out_of_memory
                else aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
            )
            for aggregation in encrypt_aggregations
        ],
        "Encrypt",
        AMBER,
        with_ci=True,
    )

    decrypt_reference = find_fixed_rsa_aggregation(
        results, "Decrypt", fixed_rsa_key_bits, NS_PER_OP
    )
    if decrypt_reference is not None:
        draw_constant(
            latency_axis,
            decrypt_reference.mean(NS_PER_OP) / NS_PER_MICROSECOND,
            subscriber_counts,
            f"Decrypt (RSA-{fixed_rsa_key_bits}, Constant)",
            VIOLET,
        )

    for measurement_name, label, color in (
        (CIPHERTEXT_BYTES, "Ciphertext", AMBER),
        (TOTAL_CIPHERTEXT_BYTES, "Ciphertext (TOTAL)", TOTAL_CIPHERTEXT_COLOR),
    ):
        draw_summary(
            size_axis,
            subscriber_counts,
            [
                (
                    NO_MEASUREMENT
                    if aggregation is None or aggregation.out_of_memory
                    else aggregation.mean(measurement_name)
                )
                for aggregation in encrypt_aggregations
            ],
            [
                (
                    NO_MEASUREMENT
                    if aggregation is None or aggregation.out_of_memory
                    else aggregation.confidence_interval(measurement_name)
                )
                for aggregation in encrypt_aggregations
            ],
            label,
            color,
        )

    latency_axis.set_title("Latency", fontsize=11)
    latency_axis.set_ylabel("Latency (µs) ± 95% CI")
    latency_axis.set_ylim(bottom=0)
    latency_axis.set_xticks(subscriber_counts)
    latency_axis.set_xlabel("Subscribers")
    apply_value_grid(latency_axis)
    latency_axis.legend(fontsize=10)

    size_axis.set_title("Sizes", fontsize=11)
    size_axis.set_ylabel("Size (bytes)")
    size_axis.set_xticks(subscriber_counts)
    size_axis.set_xlabel("Subscribers")
    size_axis.set_ylim(bottom=0)
    apply_value_grid(size_axis)
    size_axis.legend(fontsize=10)

    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    save_figure(figure, output_path)


def plot_rsa_key_size_sweep(
    results: BenchmarkSummary,
    rsa_key_sizes: list[int],
    output_path: str,
) -> None:
    figure = plt.figure(figsize=(13, 7))
    grid_spec = figure.add_gridspec(
        2,
        2,
        width_ratios=[1.0, 1.0],
        height_ratios=[1.0, 1.0],
        hspace=0.34,
    )
    keygen_latency_axis = figure.add_subplot(grid_spec[0, 0])
    latency_axis = figure.add_subplot(grid_spec[1, 0], sharex=keygen_latency_axis)
    size_axis = figure.add_subplot(grid_spec[:, 1])
    figure.suptitle("RSA Scaling with Key Size (1 Subscriber)", fontsize=13)

    keygen_aggregations = [
        results.find_aggregation("KeyGen", RSA_KEY_BITS, rsa_key_bits)
        for rsa_key_bits in rsa_key_sizes
    ]
    draw_distribution(
        keygen_latency_axis,
        rsa_key_sizes,
        [
            (
                NO_MEASUREMENT
                if aggregation is None or aggregation.out_of_memory
                else aggregation.median(NS_PER_OP) / NS_PER_MILLISECOND
            )
            for aggregation in keygen_aggregations
        ],
        [
            (
                NO_MEASUREMENT
                if aggregation is None or aggregation.out_of_memory
                else aggregation.minimum(NS_PER_OP) / NS_PER_MILLISECOND
            )
            for aggregation in keygen_aggregations
        ],
        [
            (
                NO_MEASUREMENT
                if aggregation is None or aggregation.out_of_memory
                else aggregation.maximum(NS_PER_OP) / NS_PER_MILLISECOND
            )
            for aggregation in keygen_aggregations
        ],
        [
            (
                NO_MEASUREMENT
                if aggregation is None or aggregation.out_of_memory
                else aggregation.first_quartile(NS_PER_OP) / NS_PER_MILLISECOND
            )
            for aggregation in keygen_aggregations
        ],
        [
            (
                NO_MEASUREMENT
                if aggregation is None or aggregation.out_of_memory
                else aggregation.third_quartile(NS_PER_OP) / NS_PER_MILLISECOND
            )
            for aggregation in keygen_aggregations
        ],
        "Keygen",
        CRIMSON,
    )

    for operation in ENCRYPT_DECRYPT:
        aggregations = [
            results.find_aggregation(operation, RSA_KEY_BITS, rsa_key_bits)
            for rsa_key_bits in rsa_key_sizes
        ]
        draw_summary(
            latency_axis,
            rsa_key_sizes,
            [
                (
                    NO_MEASUREMENT
                    if aggregation is None or aggregation.out_of_memory
                    else aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND
                )
                for aggregation in aggregations
            ],
            [
                (
                    NO_MEASUREMENT
                    if aggregation is None or aggregation.out_of_memory
                    else aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
                )
                for aggregation in aggregations
            ],
            operation,
            OPERATION_COLORS[operation],
            with_ci=True,
        )

    for aggregations, measurement_name, label, color in (
        (
            [
                results.find_aggregation("Encrypt", RSA_KEY_BITS, rsa_key_bits)
                for rsa_key_bits in rsa_key_sizes
            ],
            CIPHERTEXT_BYTES,
            "Ciphertext",
            AMBER,
        ),
        (keygen_aggregations, STORED_KEY_BYTES, "Private Key", CRIMSON),
    ):
        draw_summary(
            size_axis,
            rsa_key_sizes,
            [
                (
                    NO_MEASUREMENT
                    if aggregation is None or aggregation.out_of_memory
                    else aggregation.mean(measurement_name)
                )
                for aggregation in aggregations
            ],
            [
                (
                    NO_MEASUREMENT
                    if aggregation is None or aggregation.out_of_memory
                    else aggregation.confidence_interval(measurement_name)
                )
                for aggregation in aggregations
            ],
            label,
            color,
        )

    keygen_latency_axis.set_title("Key Generation Latency", fontsize=11)
    keygen_latency_axis.set_ylabel("Latency (ms), Median + IQR + Min-Max")
    keygen_latency_axis.set_ylim(bottom=0)
    keygen_latency_axis.set_xticks(rsa_key_sizes)
    keygen_latency_axis.tick_params(axis="x", labelbottom=True)
    keygen_latency_axis.set_xlabel("RSA Key Bits")
    apply_value_grid(keygen_latency_axis)
    keygen_latency_axis.legend(fontsize=10)

    latency_axis.set_title("Encrypt + Decrypt Latency", fontsize=11)
    latency_axis.set_ylabel("Latency (µs) ± 95% CI")
    latency_axis.set_ylim(bottom=0)
    latency_axis.set_xticks(rsa_key_sizes)
    latency_axis.set_xlabel("RSA Key Bits")
    apply_value_grid(latency_axis)
    latency_axis.legend(fontsize=10)

    size_axis.set_title("Sizes", fontsize=11)
    size_axis.set_ylabel("Size (bytes)")
    size_axis.set_xticks(rsa_key_sizes)
    size_axis.set_xlabel("RSA Key Bits")
    size_axis.set_ylim(bottom=0)
    apply_value_grid(size_axis)
    size_axis.legend(fontsize=10)

    figure.subplots_adjust(top=0.92)
    save_figure(figure, output_path)


# Peak resident memory of one isolated operation across the three sweeps. The panels
# share a vertical axis so the three can be read against one another directly
def plot_peak_memory(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    subscriber_counts: list[int],
    rsa_key_sizes: list[int],
    fixed_rsa_key_bits: int,
    output_path: str,
) -> bool:
    figure, axes = plt.subplots(1, 3, figsize=(14, 4.6), sharey=True)
    figure.suptitle("Peak Process Memory of a Single Operation", fontsize=13)

    cpabe_axis, subscriber_axis, key_size_axis = axes

    for operation, label, color in (
        ("MemoryEncrypt", "Encrypt", AMBER),
        ("MemoryDecrypt", "Decrypt", VIOLET),
    ):
        aggregations = [
            results.find_aggregation(operation, CPABE_ATTRIBUTES, attribute_count)
            for attribute_count in attribute_counts
        ]
        assert all(aggregation is not None for aggregation in aggregations)
        draw_summary(
            cpabe_axis,
            attribute_counts,
            [
                aggregation.mean(PEAK_RSS_BYTES) / MEGABYTE
                for aggregation in aggregations
                if aggregation is not None
            ],
            [
                aggregation.confidence_interval(PEAK_RSS_BYTES) / MEGABYTE
                for aggregation in aggregations
                if aggregation is not None
            ],
            label,
            color,
            with_ci=True,
        )

    subscriber_encrypt_aggregations = [
        results.find_aggregation("MemoryEncrypt", RSA_SUBSCRIBERS, subscriber_count)
        for subscriber_count in subscriber_counts
    ]
    assert all(
        aggregation is not None for aggregation in subscriber_encrypt_aggregations
    )
    draw_summary(
        subscriber_axis,
        subscriber_counts,
        [
            aggregation.mean(PEAK_RSS_BYTES) / MEGABYTE
            for aggregation in subscriber_encrypt_aggregations
            if aggregation is not None
        ],
        [
            aggregation.confidence_interval(PEAK_RSS_BYTES) / MEGABYTE
            for aggregation in subscriber_encrypt_aggregations
            if aggregation is not None
        ],
        "Encrypt",
        AMBER,
        with_ci=True,
    )

    # Subscriber count does not move decrypt, so quote the fixed-key measurement from
    # the RSA key-size sweep rather than presenting an empty half-panel.
    decrypt_reference = find_fixed_rsa_aggregation(
        results, "MemoryDecrypt", fixed_rsa_key_bits, PEAK_RSS_BYTES
    )
    if decrypt_reference is not None:
        draw_constant(
            subscriber_axis,
            decrypt_reference.mean(PEAK_RSS_BYTES) / MEGABYTE,
            subscriber_counts,
            f"Decrypt (RSA-{fixed_rsa_key_bits})",
            VIOLET,
        )

    for operation, label, color in (
        ("MemoryEncrypt", "Encrypt", AMBER),
        ("MemoryDecrypt", "Decrypt", VIOLET),
    ):
        aggregations = [
            results.find_aggregation(operation, RSA_KEY_BITS, rsa_key_bits)
            for rsa_key_bits in rsa_key_sizes
        ]
        assert all(aggregation is not None for aggregation in aggregations)
        draw_summary(
            key_size_axis,
            rsa_key_sizes,
            [
                aggregation.mean(PEAK_RSS_BYTES) / MEGABYTE
                for aggregation in aggregations
                if aggregation is not None
            ],
            [
                aggregation.confidence_interval(PEAK_RSS_BYTES) / MEGABYTE
                for aggregation in aggregations
                if aggregation is not None
            ],
            label,
            color,
            with_ci=True,
        )

    cpabe_axis.set_title("CP-ABE", fontsize=11)
    cpabe_axis.set_xlabel("Policy Attributes")
    cpabe_axis.set_xticks(attribute_counts)

    subscriber_axis.set_title("RSA Subscribers", fontsize=11)
    subscriber_axis.set_xlabel("Subscribers")
    subscriber_axis.set_xticks(subscriber_counts)

    key_size_axis.set_title("RSA Key Size", fontsize=11)
    key_size_axis.set_xlabel("RSA Key Bits")
    key_size_axis.set_xticks(rsa_key_sizes)

    for axis in axes:
        apply_value_grid(axis)
        axis.legend(fontsize=9)

    # The only axis in this report not anchored at zero. Peak RSS is measured against a
    # runtime floor of several megabytes that no operation can go below, so zero is not a
    # reference the differences can be read against. The shared axis keeps the three
    # panels comparable with one another instead
    axes[0].set_ylabel("Peak RSS (MB) ± 95% CI")

    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.93))
    save_figure(figure, output_path)

    return True


# Where RSA's per-subscriber ciphertext growth overtakes CP-ABE's fixed ciphertext
def plot_ciphertext_size_crossover(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    subscriber_counts: list[int],
    output_path: str,
) -> bool:
    if not measured(
        results, ["Encrypt"], RSA_SUBSCRIBERS, [subscriber_counts[0]]
    ) or not measured(
        results,
        ["Encrypt"],
        CPABE_ATTRIBUTES,
        [attribute_counts[0], attribute_counts[-1]],
    ):
        return False

    bytes_per_subscriber = rsa_bytes_per_subscriber(results, subscriber_counts)
    x_limit = subscriber_counts[-1]

    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    rsa_aggregations = [
        find_measured_aggregation(results, "Encrypt", RSA_SUBSCRIBERS, count)
        for count in subscriber_counts
    ]

    draw_summary(
        axis,
        subscriber_counts,
        [
            (
                NO_MEASUREMENT
                if aggregation is None
                else aggregation.mean(TOTAL_CIPHERTEXT_BYTES)
            )
            for aggregation in rsa_aggregations
        ],
        [
            (
                NO_MEASUREMENT
                if aggregation is None
                else aggregation.confidence_interval(TOTAL_CIPHERTEXT_BYTES)
            )
            for aggregation in rsa_aggregations
        ],
        "RSA Scaling Subs",
        TOTAL_CIPHERTEXT_COLOR,
    )

    for attribute_count, color in (
        (attribute_counts[0], AMBER),
        (attribute_counts[-1], CRIMSON),
    ):
        level = cpabe_ciphertext_bytes(results, attribute_count)

        axis.hlines(
            level,
            1,
            x_limit,
            color=color,
            linewidth=1.8,
            label=f"CP-ABE, {format_attribute_label(attribute_count)}",
        )

        # Subscriber count at which RSA's wrapped keys add up to CP-ABE's one ciphertext
        crossover = level / bytes_per_subscriber

        mark_crossover(axis, crossover, level, f"≈{crossover:,.1f}")

    linear_tick_values = [subscriber_counts[0]] + [
        count for count in subscriber_counts if count >= 8
    ]

    axis.set_xticks(linear_tick_values)
    axis.set_xlim(0.0, float(x_limit) * AXIS_HEADROOM)
    axis.set_xlabel("Subscribers")
    axis.set_ylabel("Ciphertext Bytes")
    axis.set_ylim(bottom=0.0)
    apply_value_grid(axis)
    axis.legend(fontsize=9, loc="upper left")

    figure.tight_layout()
    save_figure(figure, output_path)

    return True


# Where RSA's per-subscriber encrypt cost overtakes CP-ABE's fixed encrypt cost
def plot_encrypt_latency_crossover(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    subscriber_counts: list[int],
    output_path: str,
) -> bool:
    encrypt_fit = fit_measurement(
        results,
        "Encrypt",
        RSA_SUBSCRIBERS,
        subscriber_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )

    if encrypt_fit is None or not measured(
        results,
        ["Encrypt"],
        CPABE_ATTRIBUTES,
        [attribute_counts[0], attribute_counts[-1]],
    ):
        return False

    # Subscriber count at which RSA's fitted encrypt line reaches CP-ABE's fixed cost
    x_limit = (
        encrypt_fit.solve_x_for_y(
            cpabe_micros(results, "Encrypt", attribute_counts[-1])
        )
        * 1.15
    )

    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    projection_start_subscribers = float(subscriber_counts[-1])
    projection_end_micros = encrypt_fit.calculate_y_based_on_x(x_limit)

    axis.plot(
        [projection_start_subscribers, x_limit],
        [
            encrypt_fit.calculate_y_based_on_x(projection_start_subscribers),
            projection_end_micros,
        ],
        color=TOTAL_CIPHERTEXT_COLOR,
        linewidth=1.8,
        linestyle=":",
        label="RSA Linear Fit (Projected Beyond Sample)",
    )

    rsa_aggregations = [
        find_measured_aggregation(results, "Encrypt", RSA_SUBSCRIBERS, count)
        for count in subscriber_counts
    ]
    rsa_statistics = [
        (
            (NO_MEASUREMENT, NO_MEASUREMENT)
            if aggregation is None
            else (
                aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND,
                aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND,
            )
        )
        for aggregation in rsa_aggregations
    ]

    draw_summary(
        axis,
        subscriber_counts,
        [mean_value for mean_value, _ in rsa_statistics],
        [ci for _, ci in rsa_statistics],
        "RSA Scaling Subs (Measured)",
        TOTAL_CIPHERTEXT_COLOR,
        linewidth=2.6,
    )

    largest_value = projection_end_micros

    for attribute_count, color in (
        (attribute_counts[0], AMBER),
        (attribute_counts[-1], CRIMSON),
    ):
        level = cpabe_micros(results, "Encrypt", attribute_count)

        axis.hlines(
            level,
            0.0,
            x_limit,
            color=color,
            linewidth=1.8,
            label=f"CP-ABE, {format_attribute_label(attribute_count)}",
        )

        crossover = encrypt_fit.solve_x_for_y(level)

        mark_crossover(axis, crossover, level, f"≈{crossover:,.0f}")

        largest_value = max(largest_value, level)

    axis.set_xlim(0.0, x_limit)
    axis.set_ylim(0.0, largest_value * 1.12)
    axis.set_xlabel("Subscribers")
    axis.set_ylabel("Publisher Encrypt Latency (µs)")
    apply_value_grid(axis)
    axis.legend(fontsize=9, loc="upper left")

    figure.tight_layout()
    save_figure(figure, output_path)

    return True


def plot_decrypt_latency_crossover(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    rsa_key_sizes: list[int],
    output_path: str,
) -> bool:
    rsa_key_bits_values = [
        rsa_key_bits
        for rsa_key_bits in rsa_key_sizes
        if find_measured_aggregation(results, "Decrypt", RSA_KEY_BITS, rsa_key_bits)
        is not None
    ]

    cpabe_aggregations = [
        find_measured_aggregation(results, "Decrypt", CPABE_ATTRIBUTES, attribute_count)
        for attribute_count in attribute_counts
    ]

    if not rsa_key_bits_values or not any(cpabe_aggregations):
        return False

    cpabe_statistics = [
        (
            (NO_MEASUREMENT, NO_MEASUREMENT)
            if aggregation is None
            else (
                aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND,
                aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND,
            )
        )
        for aggregation in cpabe_aggregations
    ]
    cpabe_means = [mean_value for mean_value, _ in cpabe_statistics]
    cpabe_cis = [ci for _, ci in cpabe_statistics]

    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    draw_summary(
        axis,
        attribute_counts,
        cpabe_means,
        cpabe_cis,
        "CP-ABE",
        VIOLET,
        with_ci=True,
        linewidth=2.0,
    )

    largest_value = calculate_axis_top(cpabe_means, cpabe_cis)

    for index, rsa_key_bits in enumerate(rsa_key_bits_values):

        rsa_aggregation = find_measured_aggregation(
            results, "Decrypt", RSA_KEY_BITS, rsa_key_bits
        )
        assert rsa_aggregation is not None
        rsa_mean = rsa_aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND
        rsa_ci = rsa_aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND

        rsa_color = RSA_KEY_BITS_COLORS[index % len(RSA_KEY_BITS_COLORS)]

        axis.hlines(
            rsa_mean,
            attribute_counts[0],
            attribute_counts[-1],
            color=rsa_color,
            linestyle="--",
            linewidth=1.6,
            label=f"RSA-{rsa_key_bits}",
        )

        axis.errorbar(
            [attribute_counts[-1]],
            [rsa_mean],
            yerr=[rsa_ci],
            color=rsa_color,
            fmt="none",
            capsize=4,
        )

        largest_value = max(largest_value, rsa_mean + rsa_ci)

    axis.set_xticks(attribute_counts)
    axis.set_xlim(0.0, float(attribute_counts[-1]) * AXIS_HEADROOM)
    axis.set_ylim(0.0, largest_value * 1.15)
    axis.set_xlabel("Policy Attributes")
    axis.set_ylabel("Decrypt Latency (µs) ± 95% CI")
    apply_value_grid(axis)
    axis.legend(fontsize=9, loc="upper left")

    figure.tight_layout()
    save_figure(figure, output_path)

    return True


def plot_encrypt_decrypt_asymmetry(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    fixed_rsa_key_bits: int,
    output_path: str,
) -> bool:
    min_attributes = attribute_counts[0]

    if not measured(
        results, ENCRYPT_DECRYPT, RSA_KEY_BITS, [fixed_rsa_key_bits]
    ) or not measured(results, ENCRYPT_DECRYPT, CPABE_ATTRIBUTES, [min_attributes]):
        return False

    def rsa_micros(operation: str) -> float:
        aggregation = find_measured_aggregation(
            results, operation, RSA_KEY_BITS, fixed_rsa_key_bits
        )
        assert aggregation is not None
        return aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND

    scheme_labels = [
        f"RSA-{fixed_rsa_key_bits}",
        f"CP-ABE ({format_attribute_label(min_attributes)})",
    ]
    encrypt_values = [
        rsa_micros("Encrypt"),
        cpabe_micros(results, "Encrypt", min_attributes),
    ]
    decrypt_values = [
        rsa_micros("Decrypt"),
        cpabe_micros(results, "Decrypt", min_attributes),
    ]

    figure, axis = plt.subplots(figsize=(9, 5.5))

    positions = [0.0, 1.25]
    bar_width = 0.34

    encrypt_positions = [position - bar_width / 2.0 for position in positions]
    decrypt_positions = [position + bar_width / 2.0 for position in positions]

    axis.bar(
        encrypt_positions, encrypt_values, width=bar_width, color=AMBER, label="Encrypt"
    )
    axis.bar(
        decrypt_positions,
        decrypt_values,
        width=bar_width,
        color=VIOLET,
        label="Decrypt",
    )

    largest_value = max(max(encrypt_values), max(decrypt_values))

    for index, position in enumerate(positions):

        for bar_position, value in (
            (encrypt_positions[index], encrypt_values[index]),
            (decrypt_positions[index], decrypt_values[index]),
        ):
            axis.annotate(
                f"{value:,.1f} µs",
                (bar_position, value),
                textcoords="offset points",
                xytext=(0, 5),
                ha="center",
                fontsize=9,
            )

        if encrypt_values[index] >= decrypt_values[index]:
            ratio_text = f"Encrypt is {encrypt_values[index] / decrypt_values[index]:.0f}× Slower"
        else:
            ratio_text = f"Decrypt is {decrypt_values[index] / encrypt_values[index]:.0f}× Slower"

        tallest_value = max(encrypt_values[index], decrypt_values[index])

        axis.text(
            position,
            tallest_value + largest_value * 0.10,
            ratio_text,
            ha="center",
            fontsize=10,
            fontweight="bold",
        )

    axis.set_ylim(0.0, largest_value * 1.24)
    axis.set_xticks(positions)
    axis.set_xticklabels(scheme_labels)
    axis.set_ylabel("Latency (µs)")
    axis.set_title("Encrypt vs Decrypt Asymmetry", fontsize=12)
    axis.grid(False)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.legend(loc="upper center", ncol=2, frameon=False, fontsize=10)

    figure.tight_layout()
    save_figure(figure, output_path)

    return True


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

        if not measured(
            results, [operation], group, [sweep_values[0], sweep_values[-1]]
        ):
            return NOT_AVAILABLE

        first_aggregation = find_measured_aggregation(
            results, operation, group, sweep_values[0]
        )
        last_aggregation = find_measured_aggregation(
            results, operation, group, sweep_values[-1]
        )
        assert first_aggregation is not None and last_aggregation is not None

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
) -> dict[str, str]:

    def circle_style(diameter_px: float) -> str:
        return f'style="width:{diameter_px:.0f}px;height:{diameter_px:.0f}px;"'

    if not measured(
        results,
        ["Encrypt"],
        RSA_SUBSCRIBERS,
        [subscriber_counts[0], subscriber_counts[-1]],
    ):
        return {
            "FanoutSingleBytes": NOT_AVAILABLE,
            "FanoutTotalBytes": NOT_AVAILABLE,
            "FanoutMultiplier": NOT_AVAILABLE,
            "FanoutSingleStyle": circle_style(FANOUT_SMALLEST_DIAMETER_PX),
            "FanoutTotalStyle": circle_style(FANOUT_SMALLEST_DIAMETER_PX),
        }

    single_bytes = rsa_bytes_per_subscriber(results, subscriber_counts)
    largest_aggregation = find_measured_aggregation(
        results, "Encrypt", RSA_SUBSCRIBERS, subscriber_counts[-1]
    )
    assert largest_aggregation is not None
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
    frames: dict[str, str],
    template_path: str,
    report_path: str,
) -> None:
    min_attributes = attribute_counts[0]
    max_attributes = attribute_counts[-1]

    encrypt_fit = fit_measurement(
        results,
        "Encrypt",
        RSA_SUBSCRIBERS,
        subscriber_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )
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

    cpabe_encrypt_measured = measured(
        results, ["Encrypt"], CPABE_ATTRIBUTES, [min_attributes, max_attributes]
    )
    bytes_measured = cpabe_encrypt_measured and measured(
        results, ["Encrypt"], RSA_SUBSCRIBERS, [subscriber_counts[0]]
    )
    decrypt_penalty_measured = measured(
        results, ["Decrypt"], CPABE_ATTRIBUTES, [min_attributes, max_attributes]
    ) and measured(results, ["Decrypt"], RSA_KEY_BITS, [fixed_rsa_key_bits])

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

    # Subscriber count at which RSA's wrapped keys add up to CP-ABE's one ciphertext
    def bytes_crossover(attribute_count: int) -> float | None:
        if not bytes_measured:
            return None

        return cpabe_ciphertext_bytes(
            results, attribute_count
        ) / rsa_bytes_per_subscriber(results, subscriber_counts)

    # Subscriber count at which RSA's fitted encrypt line reaches CP-ABE's fixed cost
    def latency_crossover(attribute_count: int) -> float | None:
        if encrypt_fit is None or not cpabe_encrypt_measured:
            return None

        return encrypt_fit.solve_x_for_y(
            cpabe_micros(results, "Encrypt", attribute_count)
        )

    # How much more decrypt latency CP-ABE asks of the subscriber than RSA does
    def decrypt_penalty(attribute_count: int) -> float | None:
        if not decrypt_penalty_measured:
            return None

        rsa_decrypt = find_measured_aggregation(
            results, "Decrypt", RSA_KEY_BITS, fixed_rsa_key_bits
        )
        assert rsa_decrypt is not None
        rsa_decrypt_micros = rsa_decrypt.mean(NS_PER_OP) / NS_PER_MICROSECOND

        return cpabe_micros(results, "Decrypt", attribute_count) / rsa_decrypt_micros

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
    memory_baseline = find_measured_aggregation(results, "MemoryBaseline", "Runtime", 0)
    assert memory_baseline is not None
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
            get_student_t_critical_95(timing_runs - 1),
            timing_iterations,
        ),
        **build_rsa_circle_visualization(results, subscriber_counts),
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
            if not bytes_measured
            else f"+{rsa_bytes_per_subscriber(results, subscriber_counts):.0f} B"
        ),
        "BytesCrossoverLow": rounded(bytes_crossover(min_attributes), 1),
        "BytesCrossoverHigh": rounded(bytes_crossover(max_attributes), 1),
        "BytesRsaThroughMin": truncated(bytes_crossover(min_attributes)),
        "BytesRsaThroughMax": truncated(bytes_crossover(max_attributes)),
        "EncryptCpuCrossoverLow": rounded(latency_crossover(min_attributes)),
        "EncryptCpuCrossoverHigh": rounded(latency_crossover(max_attributes)),
        "CpuRsaThroughMin": truncated(latency_crossover(min_attributes)),
        "CpuRsaThroughMax": truncated(latency_crossover(max_attributes)),
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

    frames = {
        "BandwidthCrossoverFrame": plot_frame(
            plot_ciphertext_size_crossover(
                results,
                attribute_counts,
                subscriber_counts,
                str(result_dir / CIPHERTEXT_SIZE_CROSSOVER_PLOT),
            ),
            CIPHERTEXT_SIZE_CROSSOVER_PLOT,
        ),
        "EncryptCpuCrossoverFrame": plot_frame(
            plot_encrypt_latency_crossover(
                results,
                attribute_counts,
                subscriber_counts,
                str(result_dir / ENCRYPT_LATENCY_CROSSOVER_PLOT),
            ),
            ENCRYPT_LATENCY_CROSSOVER_PLOT,
        ),
        "DecryptCpuCrossoverFrame": plot_frame(
            plot_decrypt_latency_crossover(
                results,
                attribute_counts,
                rsa_key_sizes,
                str(result_dir / DECRYPT_LATENCY_CROSSOVER_PLOT),
            ),
            DECRYPT_LATENCY_CROSSOVER_PLOT,
        ),
        "AsymmetryFrame": plot_frame(
            plot_encrypt_decrypt_asymmetry(
                results,
                attribute_counts,
                fixed_rsa_key_bits,
                str(result_dir / ASYMMETRY_PLOT),
            ),
            ASYMMETRY_PLOT,
        ),
        "PeakMemoryFrame": plot_frame(
            plot_peak_memory(
                results,
                attribute_counts,
                subscriber_counts,
                rsa_key_sizes,
                fixed_rsa_key_bits,
                str(result_dir / PEAK_MEMORY_PLOT),
            ),
            PEAK_MEMORY_PLOT,
        ),
    }

    write_html_report(
        results,
        timing_runs,
        attribute_counts,
        subscriber_counts,
        rsa_key_sizes,
        fixed_rsa_key_bits,
        frames,
        str(template_path),
        str(report_path),
    )


if __name__ == "__main__":
    main()
