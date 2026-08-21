import matplotlib
import matplotlib.pyplot as plt
from template_builder import formatting

matplotlib.use("Agg")

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from math import isnan

from model.benchmark_summary import BenchmarkSummary
from model.measurement import *
from statistics_tbd.linear_regression import LinearRegression
from template_builder.color import *
from template_builder.formatting import KILOBYTE, MEGABYTE, NS_PER_MICROSECOND

FIGURE_DPI = 150
PANEL_FIGURE_SIZE = (13, 5)

# Leaves a little space between the last data point and the right edge of an axis
AXIS_HEADROOM = 1.03
NS_PER_MILLISECOND = 1000000.0
NO_MEASUREMENT = float("nan")
CROSSOVER_FIGURE_SIZE = (8.5, 5.2)
TOTAL_CIPHERTEXT_COLOR = TEAL
RSA_KEY_BITS_COLORS = [TOTAL_CIPHERTEXT_COLOR, BLUE, AMBER, CRIMSON]


# Draws a sweep as its mean at every point. Error bars are opt-in because a size fixed
# by construction, such as a ciphertext length, has no meaningful spread to present.
def draw_summary(
    axis: Axes,
    sweep_values: list[int],
    means: list[float],
    confidence_intervals: list[float],
    label: str,
    color: str,
    with_ci: bool = False,
    linewidth: float = 1.8,
    markersize: float = 5,
    capsize: float = 4,
) -> None:
    axis.errorbar(
        sweep_values,
        means,
        yerr=confidence_intervals if with_ci else None,
        label=label,
        color=color,
        marker="o",
        linewidth=linewidth,
        markersize=markersize,
        capsize=capsize,
    )


# A measurement that does not depend on the swept variable, drawn as the flat line it is.
# Spans the whole sweep rather than carrying a point at every value, since it was measured
# once and repeating it at each tick would read as a sweep that had been performed
def draw_constant(
    axis: Axes,
    value: float,
    sweep_values: list[int],
    label: str,
    color: str,
) -> None:

    axis.hlines(
        value,
        sweep_values[0],
        sweep_values[-1],
        color=color,
        linestyle="--",
        linewidth=1.8,
        label=label,
    )


# Draws a sweep as a distribution rather than as a mean, for a measurement whose
# samples are skewed and where the tail is the point, ex. RSA key generation.
# The median is the line, the box spans the IQR and the thin whiskers reach the
# smallest and largest sample observed
def draw_distribution(
    axis: Axes,
    sweep_values: list[int],
    medians: list[float],
    minimums: list[float],
    maximums: list[float],
    first_quartiles: list[float],
    third_quartiles: list[float],
    label: str,
    color: str,
) -> None:
    axis.vlines(
        sweep_values,
        minimums,
        maximums,
        color=color,
        linewidth=0.9,
        alpha=0.55,
    )

    axis.errorbar(
        sweep_values,
        medians,
        yerr=[
            [
                median_value - lower
                for median_value, lower in zip(medians, first_quartiles)
            ],
            [
                upper - median_value
                for median_value, upper in zip(medians, third_quartiles)
            ],
        ],
        label=label,
        color=color,
        marker="o",
        linewidth=1.8,
        markersize=5,
        capsize=6,
        elinewidth=4.5,
    )


# Adds horizontal grid lines to allow better interpretability of the vertical axis
# linewidth controls how thick those grid lines are.
def apply_value_grid(axis: Axes, linewidth: float = 0.5) -> None:
    axis.grid(True, axis="y", linestyle="-", linewidth=linewidth, alpha=0.18)


# Configures a horizontal axis that measures payload sizes, labelling the ticks
# in compact byte units ex. "16KB" rather than raw byte counts
def configure_byte_axis(axis: Axes, max_byte_size: int, tick_step: int) -> None:

    tick_values = list(range(0, max_byte_size + tick_step, tick_step))

    axis.set_xticks(tick_values)
    axis.set_xticklabels(
        [
            "0" if tick == 0 else formatting.format_byte_size(tick, compact=True)
            for tick in tick_values
        ]
    )
    axis.set_xlim(0, max_byte_size * AXIS_HEADROOM)

    apply_value_grid(axis)


# Adds a grid in both directions
def apply_mesh_grid(axis: Axes) -> None:
    axis.grid(
        True,
        which="both",
        color="#ded9d2",
        linestyle="--",
        linewidth=0.5,
        alpha=0.7,
    )


# Marks the crossover point of two lines on a plot with an X marker and a label
def mark_crossover(axis: Axes, x_value: float, y_value: float, label: str) -> None:
    axis.plot(
        [x_value],
        [y_value],
        marker="X",
        color="black",
        markersize=9,
        linestyle="none",
        zorder=5,
    )
    axis.annotate(
        label,
        (x_value, y_value),
        textcoords="offset points",
        xytext=(6, 8),
        fontsize=9,
        fontweight="bold",
    )


# Finds the highest visible mean plus CI without introducing a plot-data object.
def calculate_axis_top(means: list[float], confidence_intervals: list[float]) -> float:
    return max(
        (
            mean_value + ci_half
            for mean_value, ci_half in zip(means, confidence_intervals)
            if not isnan(mean_value)
        ),
        default=0.0,
    )


# Persists created image
def save_figure(figure: Figure, output_path: str) -> None:
    figure.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"Saved -> {output_path}")


def plot_aes_ascon_latency(
    results: BenchmarkSummary,
    payload_sizes: list[int],
    output_path: str,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle("AES-GCM vs. ASCON: Latency vs. Payload Size", fontsize=13)

    for axis, operation in zip(axes, ["Encrypt", "Decrypt"]):
        for algorithm, color in (("AES-GCM", AMBER), ("ASCON", VIOLET)):
            aggregations = [
                results.find_aggregation(operation, algorithm, payload_size)
                for payload_size in payload_sizes
            ]
            assert all(aggregation is not None for aggregation in aggregations)

            means = [
                aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND
                for aggregation in aggregations
                if aggregation is not None
            ]
            confidence_intervals = [
                aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
                for aggregation in aggregations
                if aggregation is not None
            ]

            draw_summary(
                axis,
                payload_sizes,
                means,
                confidence_intervals,
                algorithm,
                color,
                with_ci=True,
            )

        axis.set_title(operation, fontsize=11)
        axis.set_xlabel("Payload size")
        axis.set_ylabel("Latency (µs) ± 95% CI")
        axis.set_ylim(bottom=0)
        configure_byte_axis(axis, payload_sizes[-1], 16 * KILOBYTE)
        axis.legend(fontsize=10)

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_aes_ascon_throughput(
    results: BenchmarkSummary,
    payload_sizes: list[int],
    output_path: str,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle("AES-GCM vs. ASCON: Throughput vs. Payload Size", fontsize=13)

    for axis, operation in zip(axes, ["Encrypt", "Decrypt"]):
        for algorithm, color in (("AES-GCM", AMBER), ("ASCON", VIOLET)):
            aggregations = [
                results.find_aggregation(operation, algorithm, payload_size)
                for payload_size in payload_sizes
            ]
            assert all(aggregation is not None for aggregation in aggregations)

            means = [
                aggregation.mean(MB_PER_SECOND)
                for aggregation in aggregations
                if aggregation is not None
            ]
            confidence_intervals = [
                aggregation.confidence_interval(MB_PER_SECOND)
                for aggregation in aggregations
                if aggregation is not None
            ]

            draw_summary(
                axis,
                payload_sizes,
                means,
                confidence_intervals,
                algorithm,
                color,
                with_ci=True,
            )

        axis.set_title(operation, fontsize=11)
        axis.set_xlabel("Payload size")
        axis.set_ylabel("Throughput (MB/s) ± 95% CI")
        axis.set_ylim(bottom=0)
        configure_byte_axis(axis, payload_sizes[-1], 16 * KILOBYTE)
        axis.legend(fontsize=10)

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_payload_scaling_latency(
    results: BenchmarkSummary,
    payload_sizes: list[int],
    output_path: str,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle("PSK vs. RSA vs. CP-ABE: Latency vs. Payload Size", fontsize=13)

    for axis, operation in zip(axes, ["Encrypt", "Decrypt"]):
        drawn = []

        for scheme_name, color in (("PSK", TEAL), ("RSA", VIOLET), ("CPABE", CRIMSON)):
            aggregations = [
                results.find_aggregation(operation, scheme_name, payload_size)
                for payload_size in payload_sizes
            ]
            assert all(aggregation is not None for aggregation in aggregations)

            means = [
                aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND
                for aggregation in aggregations
                if aggregation is not None
            ]
            confidence_intervals = [
                aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
                for aggregation in aggregations
                if aggregation is not None
            ]

            draw_summary(
                axis,
                payload_sizes,
                means,
                confidence_intervals,
                scheme_name,
                color,
                with_ci=True,
            )
            drawn.append((scheme_name, means, confidence_intervals, color))

        axis.set_title(operation, fontsize=11)
        axis.set_xlabel("Payload Size")
        axis.set_ylabel("Latency (µs) ± 95% CI")
        axis.set_ylim(bottom=0)
        configure_byte_axis(axis, payload_sizes[-1], 4 * MEGABYTE)
        axis.legend(fontsize=10, loc="upper left")

        if operation == "Encrypt":
            zoom_axis = axis.inset_axes([0.08, 0.08, 0.47, 0.32])  # type: ignore
            zoomed = [entry for entry in drawn if entry[0] != "CPABE"]

            for scheme_name, means, confidence_intervals, color in zoomed:
                draw_summary(
                    zoom_axis,
                    payload_sizes,
                    means,
                    confidence_intervals,
                    scheme_name,
                    color,
                    linewidth=1.6,
                    markersize=4,
                    capsize=3,
                )

            zoom_axis.set_ylim(
                0.0,
                max(
                    calculate_axis_top(means, confidence_intervals)
                    for _, means, confidence_intervals, _ in zoomed
                )
                * 1.10,
            )
            zoom_axis.set_xlim(0, payload_sizes[-1] * AXIS_HEADROOM)
            zoom_axis.set_xticks([])
            zoom_axis.set_title("PSK + RSA Zoom", fontsize=9)
            zoom_axis.set_ylabel("µs", fontsize=8)
            zoom_axis.tick_params(axis="both", labelsize=8)
            apply_value_grid(zoom_axis, linewidth=0.4)
            zoom_axis.legend(fontsize=8, loc="upper left")

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_payload_scaling_throughput(
    results: BenchmarkSummary,
    payload_sizes: list[int],
    output_path: str,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle("PSK vs. RSA vs. CP-ABE: Throughput vs. Payload Size", fontsize=13)

    for axis, operation in zip(axes, ["Encrypt", "Decrypt"]):
        for scheme_name, color in (("PSK", TEAL), ("RSA", VIOLET), ("CPABE", CRIMSON)):
            aggregations = [
                results.find_aggregation(operation, scheme_name, payload_size)
                for payload_size in payload_sizes
            ]
            assert all(aggregation is not None for aggregation in aggregations)

            draw_summary(
                axis,
                payload_sizes,
                [
                    aggregation.mean(MB_PER_SECOND)
                    for aggregation in aggregations
                    if aggregation is not None
                ],
                [
                    aggregation.confidence_interval(MB_PER_SECOND)
                    for aggregation in aggregations
                    if aggregation is not None
                ],
                scheme_name,
                color,
                with_ci=True,
            )

        axis.set_title(operation, fontsize=11)
        axis.set_xlabel("Payload Size")
        axis.set_ylabel("Throughput (MB/s) ± 95% CI")
        axis.set_ylim(bottom=0)
        configure_byte_axis(axis, payload_sizes[-1], 4 * MEGABYTE)
        axis.legend(fontsize=10, loc="upper left")

    figure.tight_layout()
    save_figure(figure, output_path)


def configure_attribute_axis(attribute_counts: list[int], axis: Axes) -> None:
    axis.set_xticks(attribute_counts)
    apply_mesh_grid(axis)


def plot_json_cbor_latency(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    output_path: str,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(
        "JSON vs. CBOR vs. CBOR (Int Keys): Latency vs. Policy Attributes",
        fontsize=13,
    )

    for axis, operation in zip(axes, ["Serialize", "Deserialize"]):
        for format_name, label, color in (
            ("JSON", "JSON", AMBER),
            ("CBOR", "CBOR", VIOLET),
            ("CBORKeyAsInt", "CBOR (int keys)", TEAL),
        ):
            aggregations = [
                results.find_aggregation(operation, format_name, attribute_count)
                for attribute_count in attribute_counts
            ]
            assert all(aggregation is not None for aggregation in aggregations)

            means = [
                aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND
                for aggregation in aggregations
                if aggregation is not None
            ]
            confidence_intervals = [
                aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
                for aggregation in aggregations
                if aggregation is not None
            ]

            draw_summary(
                axis,
                attribute_counts,
                means,
                confidence_intervals,
                label,
                color,
                with_ci=True,
            )

        axis.set_title(operation, fontsize=11)
        axis.set_xlabel("Attribute Count")
        axis.set_ylabel("Latency (µs) ± 95% CI")
        axis.set_ylim(bottom=0)
        configure_attribute_axis(attribute_counts, axis)
        axis.legend(fontsize=10)

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_json_cbor_size(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    output_path: str,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(
        "JSON vs. CBOR vs. CBOR (Int Keys): Envelope Size vs. Attribute Count",
        fontsize=13,
    )

    for format_name, label, color in (
        ("JSON", "JSON", AMBER),
        ("CBOR", "CBOR", VIOLET),
        ("CBORKeyAsInt", "CBOR (int keys)", TEAL),
    ):
        aggregations = [
            results.find_aggregation("Serialize", format_name, attribute_count)
            for attribute_count in attribute_counts
        ]
        assert all(aggregation is not None for aggregation in aggregations)

        envelope_means = [
            aggregation.mean(ENVELOPE_BYTES)
            for aggregation in aggregations
            if aggregation is not None
        ]
        envelope_cis = [
            aggregation.confidence_interval(ENVELOPE_BYTES)
            for aggregation in aggregations
            if aggregation is not None
        ]
        raw_means = [
            aggregation.mean(RAW_BYTES)
            for aggregation in aggregations
            if aggregation is not None
        ]

        draw_summary(
            axes[0],
            attribute_counts,
            envelope_means,
            envelope_cis,
            label,
            color,
        )

        axes[1].plot(
            attribute_counts,
            [envelope - raw for envelope, raw in zip(envelope_means, raw_means)],
            label=label,
            color=color,
            marker="o",
            linewidth=1.8,
            markersize=5,
        )

    for axis, title, y_label in (
        (axes[0], "Absolute Size", "Envelope size (bytes)"),
        (axes[1], "Format Tax", "Bytes added over raw payload"),
    ):
        axis.set_title(title, fontsize=11)
        axis.set_xlabel("Attribute Count")
        axis.set_ylabel(y_label)
        axis.set_ylim(bottom=0)
        configure_attribute_axis(attribute_counts, axis)
        axis.legend(fontsize=10)

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_cpabe_attribute_sweep(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    output_path: str,
) -> None:
    figure, (latency_axis, size_axis) = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle("CP-ABE Scaling with Policy Attribute Count", fontsize=13)

    for operation, color in (("Encrypt", AMBER), ("Decrypt", VIOLET)):
        aggregations = [
            results.find_aggregation(operation, "CPABEAttributes", attribute_count)
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
            color,
            with_ci=True,
        )

    for operation, measurement_name, label, color in (
        ("Encrypt", CIPHERTEXT_BYTES, "Ciphertext", AMBER),
        ("Decrypt", STORED_KEY_BYTES, "Private Key", CRIMSON),
    ):
        aggregations = [
            results.find_aggregation(operation, "CPABEAttributes", attribute_count)
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
    figure, (latency_axis, size_axis) = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(
        f"RSA Scaling with Subscriber Count (Fixed Key: {fixed_rsa_key_bits} bits)",
        fontsize=13,
    )

    encrypt_aggregations = [
        results.find_aggregation("Encrypt", "RSASubscribers", subscriber_count)
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

    decrypt_reference = results.find_aggregation(
        "Decrypt", "RSAKeyBits", fixed_rsa_key_bits
    )
    if (
        decrypt_reference is not None
        and not decrypt_reference.out_of_memory
        and decrypt_reference.has_measurement(NS_PER_OP)
    ):
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
    grid_spec = figure.add_gridspec(2, 2, hspace=0.34)
    keygen_latency_axis = figure.add_subplot(grid_spec[0, 0])
    latency_axis = figure.add_subplot(grid_spec[1, 0], sharex=keygen_latency_axis)
    size_axis = figure.add_subplot(grid_spec[:, 1])
    figure.suptitle("RSA Scaling with Key Size (1 Subscriber)", fontsize=13)

    keygen_aggregations = [
        results.find_aggregation("KeyGen", "RSAKeyBits", rsa_key_bits)
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

    for operation, color in (("Encrypt", AMBER), ("Decrypt", VIOLET)):
        aggregations = [
            results.find_aggregation(operation, "RSAKeyBits", rsa_key_bits)
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
            color,
            with_ci=True,
        )

    encrypt_aggregations = [
        results.find_aggregation("Encrypt", "RSAKeyBits", rsa_key_bits)
        for rsa_key_bits in rsa_key_sizes
    ]
    for aggregations, measurement_name, label, color in (
        (encrypt_aggregations, CIPHERTEXT_BYTES, "Ciphertext", AMBER),
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


def plot_peak_memory(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    subscriber_counts: list[int],
    rsa_key_sizes: list[int],
    fixed_rsa_key_bits: int,
    output_path: str,
) -> None:
    figure, axes = plt.subplots(1, 3, figsize=(14, 4.6), sharey=True)
    figure.suptitle("Peak Process Memory of a Single Operation", fontsize=13)

    cpabe_axis, subscriber_axis, key_size_axis = axes

    for operation, label, color in (
        ("MemoryEncrypt", "Encrypt", AMBER),
        ("MemoryDecrypt", "Decrypt", VIOLET),
    ):
        aggregations = [
            results.find_aggregation(operation, "CPABEAttributes", attribute_count)
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
        results.find_aggregation("MemoryEncrypt", "RSASubscribers", subscriber_count)
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

    decrypt_reference = results.find_aggregation(
        "MemoryDecrypt", "RSAKeyBits", fixed_rsa_key_bits
    )
    if (
        decrypt_reference is not None
        and not decrypt_reference.out_of_memory
        and decrypt_reference.has_measurement(PEAK_RSS_BYTES)
    ):
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
            results.find_aggregation(operation, "RSAKeyBits", rsa_key_bits)
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

    axes[0].set_ylabel("Peak RSS (MB) ± 95% CI")

    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.93))
    save_figure(figure, output_path)


def plot_ciphertext_size_crossover(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    subscriber_counts: list[int],
    low_crossover: float,
    high_crossover: float,
    output_path: str,
) -> None:
    x_limit = subscriber_counts[-1]
    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    rsa_aggregations = [
        results.find_aggregation("Encrypt", "RSASubscribers", count)
        for count in subscriber_counts
    ]
    draw_summary(
        axis,
        subscriber_counts,
        [
            (
                NO_MEASUREMENT
                if aggregation is None or aggregation.out_of_memory
                else aggregation.mean(TOTAL_CIPHERTEXT_BYTES)
            )
            for aggregation in rsa_aggregations
        ],
        [
            (
                NO_MEASUREMENT
                if aggregation is None or aggregation.out_of_memory
                else aggregation.confidence_interval(TOTAL_CIPHERTEXT_BYTES)
            )
            for aggregation in rsa_aggregations
        ],
        "RSA Scaling Subs",
        TOTAL_CIPHERTEXT_COLOR,
    )

    for attribute_count, crossover, color in (
        (attribute_counts[0], low_crossover, AMBER),
        (attribute_counts[-1], high_crossover, CRIMSON),
    ):
        aggregation = results.find_aggregation(
            "Encrypt", "CPABEAttributes", attribute_count
        )
        assert aggregation is not None and not aggregation.out_of_memory
        level = aggregation.mean(CIPHERTEXT_BYTES)

        axis.hlines(
            level,
            1,
            x_limit,
            color=color,
            linewidth=1.8,
            label=(f"CP-ABE, {formatting.format_attribute_label(attribute_count)}"),
        )
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


def plot_encrypt_latency_crossover(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    subscriber_counts: list[int],
    encrypt_fit: LinearRegression,
    low_crossover: float,
    high_crossover: float,
    output_path: str,
) -> None:
    x_limit = high_crossover * 1.15
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
        results.find_aggregation("Encrypt", "RSASubscribers", count)
        for count in subscriber_counts
    ]
    rsa_statistics = [
        (
            (NO_MEASUREMENT, NO_MEASUREMENT)
            if aggregation is None or aggregation.out_of_memory
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

    for attribute_count, crossover, color in (
        (attribute_counts[0], low_crossover, AMBER),
        (attribute_counts[-1], high_crossover, CRIMSON),
    ):
        aggregation = results.find_aggregation(
            "Encrypt", "CPABEAttributes", attribute_count
        )
        assert aggregation is not None and not aggregation.out_of_memory
        level = aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND

        axis.hlines(
            level,
            0.0,
            x_limit,
            color=color,
            linewidth=1.8,
            label=(f"CP-ABE, {formatting.format_attribute_label(attribute_count)}"),
        )
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


def plot_decrypt_latency_crossover(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    rsa_key_sizes: list[int],
    output_path: str,
) -> None:
    rsa_key_bits_values = []
    for rsa_key_bits in rsa_key_sizes:
        aggregation = results.find_aggregation("Decrypt", "RSAKeyBits", rsa_key_bits)
        if aggregation is not None and not aggregation.out_of_memory:
            rsa_key_bits_values.append(rsa_key_bits)
    cpabe_aggregations = [
        results.find_aggregation("Decrypt", "CPABEAttributes", attribute_count)
        for attribute_count in attribute_counts
    ]
    cpabe_statistics = [
        (
            (NO_MEASUREMENT, NO_MEASUREMENT)
            if aggregation is None or aggregation.out_of_memory
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
        rsa_aggregation = results.find_aggregation(
            "Decrypt", "RSAKeyBits", rsa_key_bits
        )
        assert rsa_aggregation is not None and not rsa_aggregation.out_of_memory
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


def plot_encrypt_decrypt_asymmetry(
    results: BenchmarkSummary,
    attribute_counts: list[int],
    fixed_rsa_key_bits: int,
    output_path: str,
) -> None:
    min_attributes = attribute_counts[0]
    rsa_encrypt = results.find_aggregation("Encrypt", "RSAKeyBits", fixed_rsa_key_bits)
    rsa_decrypt = results.find_aggregation("Decrypt", "RSAKeyBits", fixed_rsa_key_bits)
    cpabe_encrypt = results.find_aggregation(
        "Encrypt", "CPABEAttributes", min_attributes
    )
    cpabe_decrypt = results.find_aggregation(
        "Decrypt", "CPABEAttributes", min_attributes
    )
    assert rsa_encrypt is not None and not rsa_encrypt.out_of_memory
    assert rsa_decrypt is not None and not rsa_decrypt.out_of_memory
    assert cpabe_encrypt is not None and not cpabe_encrypt.out_of_memory
    assert cpabe_decrypt is not None and not cpabe_decrypt.out_of_memory

    encrypt_values = [
        rsa_encrypt.mean(NS_PER_OP) / NS_PER_MICROSECOND,
        cpabe_encrypt.mean(NS_PER_OP) / NS_PER_MICROSECOND,
    ]
    decrypt_values = [
        rsa_decrypt.mean(NS_PER_OP) / NS_PER_MICROSECOND,
        cpabe_decrypt.mean(NS_PER_OP) / NS_PER_MICROSECOND,
    ]
    scheme_labels = [
        f"RSA-{fixed_rsa_key_bits}",
        f"CP-ABE ({formatting.format_attribute_label(min_attributes)})",
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
