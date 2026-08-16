import os

from reporting.benchmark import (
    CIPHERTEXT_BYTES,
    NS_PER_MICROSECOND,
    NS_PER_MILLISECOND,
    NS_PER_OP,
    OOM_KILLED_EXIT_CODE,
    PEAK_RSS_BYTES,
    STORED_KEY_BYTES,
    TOTAL_CIPHERTEXT_BYTES,
    BenchmarkSummary,
    CaseSummary,
    FeatureSweep,
    Measurement,
    load_invocations,
    load_results,
    throttle_flags,
)
from reporting.charts import (
    AMBER,
    AXIS_HEADROOM,
    BLUE,
    CRIMSON,
    TEAL,
    VIOLET,
    Series,
    mark_crossover,
    apply_value_grid,
    draw_constant,
    draw_distribution,
    draw_summary,
    plt,
    save_figure,
    calculate_axis_top,
)
from reporting.environment import Config
from reporting.formatting import (
    KILOBYTE,
    MEGABYTE,
    format_byte_size,
    format_mean_with_ci,
)
from reporting.html import (
    build_html_failure_notice,
    build_html_generic_data,
    build_html_report,
    build_html_table,
)
from reporting.statistics import LinearFit, fit_linear_regression

SCENARIO = "attribute-key-scaling"
ENV_PREFIX = "ATTRIBUTE_KEY_SCALING"
BENCHMARK_PREFIX = "BenchmarkAttributeKeyScaling"
TEMPLATE_NAME = "attribute_key_scaling_template.html"

# Peak memory is a separate experiment in a separate file, and its benchmarks are named
# so that stripping this longer prefix leaves the same plain operations the timing
# summary is keyed by
MEMORY_PREFIX = BENCHMARK_PREFIX + "Memory"

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

# CP-ABE key issuance is deliberately not measured by the benchmark, it is paid by the
# trusted attribute authority and never by the constrained device, so only the RSA key
# size sweep carries a key generation operation
ENCRYPT_DECRYPT = ["encrypt", "decrypt"]
ENCRYPT_DECRYPT_KEYGEN = ["encrypt", "decrypt", "keygen"]

# The orchestrator records an operation by the benchmark it filtered the process on.
# Timing and memory are read from separate files, so each maps the invocation names it
# owns onto the operations its own summary is keyed by
TIMING_OPERATIONS = {"Encrypt": "encrypt", "Decrypt": "decrypt", "KeyGen": "keygen"}
MEMORY_OPERATIONS = {"MemoryEncrypt": "encrypt", "MemoryDecrypt": "decrypt"}

# The three sweeps the memory experiment covers, keyed by the group Go names them with:
# the environment variable holding the values, the panel title, the axis label, the unit a
# slope through them is quoted per, and the operations that sweep actually measures.
#
# The subscriber sweep measures encrypt alone. Decrypt is the publisher's fan-out turned
# around: a subscriber only ever unwraps its own session key, so there is nothing there
# for a subscriber count to move
MEMORY_SWEEPS = {
    CPABE_ATTRIBUTES: (
        "ATTRIBUTE_COUNT",
        "CP-ABE",
        "Policy Attributes",
        "attribute",
        ENCRYPT_DECRYPT,
    ),
    RSA_SUBSCRIBERS: (
        "SUBSCRIBER_COUNT",
        "RSA Subscribers",
        "Subscribers",
        "subscriber",
        ["encrypt"],
    ),
    RSA_KEY_BITS: (
        "RSA_KEY_SIZES",
        "RSA Key Size",
        "RSA Key Bits",
        "key bit",
        ENCRYPT_DECRYPT,
    ),
}

OPERATION_COLORS = {"encrypt": AMBER, "decrypt": VIOLET, "keygen": CRIMSON}
TOTAL_CIPHERTEXT_COLOR = TEAL

RSA_KEY_BITS_COLORS = [TOTAL_CIPHERTEXT_COLOR, BLUE, AMBER, CRIMSON]

CIPHERTEXT_SERIES = Series("encrypt", CIPHERTEXT_BYTES, "Ciphertext", AMBER)
TOTAL_CIPHERTEXT_SERIES = Series(
    "encrypt", TOTAL_CIPHERTEXT_BYTES, "Ciphertext (TOTAL)", TOTAL_CIPHERTEXT_COLOR
)

# CP-ABE's stored key size is reported by the decrypt benchmark since its issuance is
# not timed, whereas RSA's is reported by the key generation benchmark
CPABE_STORED_KEY_SERIES = Series("decrypt", STORED_KEY_BYTES, "Private Key", CRIMSON)
RSA_STORED_KEY_SERIES = Series("keygen", STORED_KEY_BYTES, "Private Key", CRIMSON)

CIPHERTEXT_COLUMN = ("CIPHERTEXT", CIPHERTEXT_BYTES)
TOTAL_CIPHERTEXT_COLUMN = ("CIPHERTEXT (TOTAL)", TOTAL_CIPHERTEXT_BYTES)
STORED_KEY_COLUMN = ("STORED KEY", STORED_KEY_BYTES)

FANOUT_LARGEST_DIAMETER_PX = 168.0
FANOUT_SMALLEST_DIAMETER_PX = 22.0

CROSSOVER_FIGURE_SIZE = (8.5, 5.2)
ASYMMETRY_FIGURE_SIZE = (9, 5.5)
PEAK_MEMORY_FIGURE_SIZE = (14, 4.6)

# A straight line needs three points before its slope carries a confidence interval
MINIMUM_FIT_POINTS = 3

NOT_AVAILABLE = "&mdash;"
NOT_COMPLETED = "FAILED"

OOM_KILLED_DIAGNOSIS = "Killed by the kernel out-of-memory killer (SIGKILL)"
RUNTIME_OOM_DIAGNOSIS = "Go runtime could not allocate"
PROCESS_FAILED_DIAGNOSIS = "Process failed"

MISSING_CASE_NOTE = (
    '<p class="missing-note">Not available: a case this comparison rests on did not '
    "complete. See Incomplete Cases at the top of the report.</p>"
)
NO_MEMORY_READING_NOTE = (
    '<p class="missing-note">No peak memory reading is available for this run. The '
    "kernel reports it through <code>/proc</code>, which a host outside Linux does not "
    "provide.</p>"
)


def format_attribute_label(attribute_count: int) -> str:
    if attribute_count == 1:
        return "1 ATTRIBUTE"

    return f"{attribute_count} ATTRIBUTES"


# Whether every case these operations need at these sweep values survived. A comparison
# resting on a case that did not is not a comparison
def measured(
    results: BenchmarkSummary,
    operations: list[str],
    group: str,
    sweep_values: list[int],
) -> bool:

    return all(
        results.has_case(operation, group, sweep_value)
        for operation in operations
        for sweep_value in sweep_values
    )


# Either the figure, or a line saying why it is not there. A run that lost a case still
# produces a report rather than failing on the first thing it cannot compute
def plot_frame(drawn: bool, filename: str, note: str = MISSING_CASE_NOTE) -> str:

    if not drawn:
        return note

    return f'<img src="{filename}">'


# A line fitted through the points that were measured, or nothing where too few of them
# survived to say anything about a trend
def fit_sweep(series: FeatureSweep) -> LinearFit | None:

    measured_series = series.without_gaps()

    if len(measured_series.sweep_values) < MINIMUM_FIT_POINTS:
        return None

    return fit_linear_regression(measured_series.sweep_values, measured_series.means)


# CP-ABE's cost as a straight line in the policy attribute count
def fit_cpabe_slope(
    results: BenchmarkSummary,
    config: Config,
    operation: str,
    unit: str,
    divisor: float = 1.0,
) -> LinearFit | None:

    return fit_sweep(
        results.sweep_features(
            operation,
            CPABE_ATTRIBUTES,
            config.integers("ATTRIBUTE_COUNT"),
            unit,
            divisor,
        )
    )


def sweep_rsa_encrypt_micros(
    results: BenchmarkSummary,
    config: Config,
) -> FeatureSweep:

    return results.sweep_features(
        "encrypt",
        RSA_SUBSCRIBERS,
        config.integers("SUBSCRIBER_COUNT"),
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )


# RSA's publisher cost as a straight line in the subscriber count
def fit_rsa_encrypt_slope(
    results: BenchmarkSummary, config: Config
) -> LinearFit | None:

    return fit_sweep(sweep_rsa_encrypt_micros(results, config))


def cpabe_micros(
    results: BenchmarkSummary,
    operation: str,
    attribute_count: int,
) -> float:

    return (
        results.get_case_summary(operation, CPABE_ATTRIBUTES, attribute_count)
        .latency()
        .mean
    )


# Decrypt does not depend on how many subscribers there are, a subscriber only ever
# unwraps its own session key, so it is not swept against subscriber count at all. What
# the subscriber sweep quotes for it is the figure the key size sweep measured at the
# fixed key size, which is the same operation on the same key actually performed
def fixed_rsa_decrypt(
    summary: BenchmarkSummary,
    config: Config,
    feature_name: str,
    divisor: float = 1.0,
) -> Measurement | None:

    fixed_rsa_key_bits = config.integer("FIXED_RSA_KEY_SIZE")

    if not summary.has_case("decrypt", RSA_KEY_BITS, fixed_rsa_key_bits):
        return None

    case = summary.get_case_summary("decrypt", RSA_KEY_BITS, fixed_rsa_key_bits)

    if feature_name not in case.features:
        return None

    return case.get_feature(feature_name).scale_unit(divisor)


def cpabe_ciphertext_bytes(results: BenchmarkSummary, attribute_count: int) -> float:
    return (
        results.get_case_summary("encrypt", CPABE_ATTRIBUTES, attribute_count)
        .get_feature(CIPHERTEXT_BYTES)
        .mean
    )


# One wrapped session key is the same size at every subscriber count, and RSA's total
# ciphertext grows by exactly that much per additional subscriber
def rsa_bytes_per_subscriber(results: BenchmarkSummary, config: Config) -> float:
    return (
        results.get_case_summary(
            "encrypt", RSA_SUBSCRIBERS, config.integers("SUBSCRIBER_COUNT")[0]
        )
        .get_feature(CIPHERTEXT_BYTES)
        .mean
    )


def plot_sweep(
    results: BenchmarkSummary,
    sweep_name: str,
    sweep_values: list[int],
    sweep_operations: list[str],
    size_series: tuple[Series, ...],
    x_label: str,
    figure_title: str,
    output_path: str,
    reference_latency: Measurement | None = None,
    reference_label: str = "",
) -> None:

    # Key generation is orders of magnitude slower than encrypt and decrypt, so it gets
    # its own panel wherever the sweep measures it
    keygen_on_own_axis = "keygen" in sweep_operations

    if keygen_on_own_axis:
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
    else:
        figure = plt.figure(figsize=(13, 5))
        grid_spec = figure.add_gridspec(1, 2)

        latency_axis = figure.add_subplot(grid_spec[0, 0])
        keygen_latency_axis = latency_axis
        size_axis = figure.add_subplot(grid_spec[0, 1])

    figure.suptitle(figure_title, fontsize=13)

    for operation in sweep_operations:

        # Key generation is a probabilistic prime search, so its samples are skewed with
        # a long right tail and a mean would hide it. It is drawn as a distribution, in
        # milliseconds because it is far slower than the operations it sits above
        if operation == "keygen":
            draw_distribution(
                keygen_latency_axis,
                results.sweep_features(
                    operation, sweep_name, sweep_values, NS_PER_OP, NS_PER_MILLISECOND
                ),
                "Keygen",
                OPERATION_COLORS[operation],
            )
            continue

        draw_summary(
            latency_axis,
            results.sweep_features(
                operation, sweep_name, sweep_values, NS_PER_OP, NS_PER_MICROSECOND
            ),
            operation.capitalize(),
            OPERATION_COLORS[operation],
            with_ci=True,
        )

    # An operation this sweep does not move, quoted from where it was measured
    if reference_latency is not None:
        draw_constant(
            latency_axis,
            reference_latency.mean,
            sweep_values,
            reference_label,
            OPERATION_COLORS["decrypt"],
        )

    if keygen_on_own_axis:
        keygen_latency_axis.set_title("Key Generation Latency", fontsize=11)
        keygen_latency_axis.set_ylabel("Latency (ms), Median + IQR + Min-Max")
        keygen_latency_axis.set_ylim(bottom=0)
        keygen_latency_axis.set_xticks(sweep_values)

        keygen_latency_axis.tick_params(axis="x", labelbottom=True)
        keygen_latency_axis.set_xlabel(x_label)

        apply_value_grid(keygen_latency_axis)
        keygen_latency_axis.legend(fontsize=10)

        latency_axis.set_title("Encrypt + Decrypt Latency", fontsize=11)
    else:
        latency_axis.set_title("Latency", fontsize=11)

    latency_axis.set_ylabel("Latency (µs) ± 95% CI")
    latency_axis.set_ylim(bottom=0)

    latency_axis.set_xticks(sweep_values)
    latency_axis.set_xlabel(x_label)
    apply_value_grid(latency_axis)
    latency_axis.legend(fontsize=10)

    for size in size_series:
        size.draw(size_axis, results, sweep_name, sweep_values)

    size_axis.set_title("Sizes", fontsize=11)
    size_axis.set_ylabel("Size (bytes)")
    size_axis.set_xticks(sweep_values)
    size_axis.set_xlabel(x_label)
    apply_value_grid(size_axis)
    size_axis.legend(fontsize=10)
    size_axis.set_ylim(bottom=0)

    if keygen_on_own_axis:
        figure.subplots_adjust(top=0.92)
    else:
        figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))

    save_figure(figure, output_path)


# Peak resident memory of one isolated operation across the three sweeps. The panels
# share a vertical axis so the three can be read against one another directly
def plot_peak_memory(memory: BenchmarkSummary, config: Config) -> bool:

    if not memory.measures(PEAK_RSS_BYTES):
        return False

    figure, axes = plt.subplots(1, 3, figsize=PEAK_MEMORY_FIGURE_SIZE, sharey=True)
    figure.suptitle("Peak Process Memory of a Single Operation", fontsize=13)

    fixed_rsa_key_bits = config.integer("FIXED_RSA_KEY_SIZE")

    for axis, (group, sweep) in zip(axes, MEMORY_SWEEPS.items()):

        environment_name, panel_title, x_label, _, operations = sweep
        sweep_values = config.integers(environment_name)

        for operation in operations:
            draw_summary(
                axis,
                memory.sweep_features(
                    operation, group, sweep_values, PEAK_RSS_BYTES, MEGABYTE
                ),
                operation.capitalize(),
                OPERATION_COLORS[operation],
                with_ci=True,
            )

        # A sweep that does not move decrypt still sits beside two that do, so it carries
        # the reading of the operation it did not sweep rather than an empty half-panel
        decrypt_reference = (
            None
            if "decrypt" in operations
            else fixed_rsa_decrypt(memory, config, PEAK_RSS_BYTES, MEGABYTE)
        )

        if decrypt_reference is not None:
            draw_constant(
                axis,
                decrypt_reference.mean,
                sweep_values,
                f"Decrypt (RSA-{fixed_rsa_key_bits})",
                OPERATION_COLORS["decrypt"],
            )

        axis.set_title(panel_title, fontsize=11)
        axis.set_xlabel(x_label)
        axis.set_xticks(sweep_values)
        apply_value_grid(axis)
        axis.legend(fontsize=9)

    # The only axis in this report not anchored at zero. Peak RSS is measured against a
    # runtime floor of several megabytes that no operation can go below, so zero is not a
    # reference the differences can be read against. The shared axis keeps the three
    # panels comparable with one another instead
    axes[0].set_ylabel("Peak RSS (MB) ± 95% CI")

    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.93))
    save_figure(figure, config.figure(PEAK_MEMORY_PLOT))

    return True


# Where RSA's per-subscriber ciphertext growth overtakes CP-ABE's fixed ciphertext
def plot_ciphertext_size_crossover(
    results: BenchmarkSummary,
    config: Config,
) -> bool:

    attribute_counts = config.integers("ATTRIBUTE_COUNT")
    subscriber_counts = config.integers("SUBSCRIBER_COUNT")

    if not measured(
        results, ["encrypt"], RSA_SUBSCRIBERS, [subscriber_counts[0]]
    ) or not measured(
        results,
        ["encrypt"],
        CPABE_ATTRIBUTES,
        [attribute_counts[0], attribute_counts[-1]],
    ):
        return False

    bytes_per_subscriber = rsa_bytes_per_subscriber(results, config)
    x_limit = subscriber_counts[-1]

    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    draw_summary(
        axis,
        results.sweep_features(
            "encrypt",
            RSA_SUBSCRIBERS,
            subscriber_counts,
            TOTAL_CIPHERTEXT_BYTES,
        ),
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
    save_figure(figure, config.figure(CIPHERTEXT_SIZE_CROSSOVER_PLOT))

    return True


# Where RSA's per-subscriber encrypt cost overtakes CP-ABE's fixed encrypt cost
def plot_encrypt_latency_crossover(
    results: BenchmarkSummary,
    config: Config,
) -> bool:

    attribute_counts = config.integers("ATTRIBUTE_COUNT")
    subscriber_counts = config.integers("SUBSCRIBER_COUNT")

    encrypt_fit = fit_rsa_encrypt_slope(results, config)

    if encrypt_fit is None or not measured(
        results,
        ["encrypt"],
        CPABE_ATTRIBUTES,
        [attribute_counts[0], attribute_counts[-1]],
    ):
        return False

    # Subscriber count at which RSA's fitted encrypt line reaches CP-ABE's fixed cost
    x_limit = (
        encrypt_fit.solve_x_for_y(
            cpabe_micros(results, "encrypt", attribute_counts[-1])
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

    draw_summary(
        axis,
        sweep_rsa_encrypt_micros(results, config),
        "RSA Scaling Subs (Measured)",
        TOTAL_CIPHERTEXT_COLOR,
        linewidth=2.6,
    )

    largest_value = projection_end_micros

    for attribute_count, color in (
        (attribute_counts[0], AMBER),
        (attribute_counts[-1], CRIMSON),
    ):
        level = cpabe_micros(results, "encrypt", attribute_count)

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
    save_figure(figure, config.figure(ENCRYPT_LATENCY_CROSSOVER_PLOT))

    return True


def plot_decrypt_latency_crossover(
    results: BenchmarkSummary,
    config: Config,
) -> bool:

    attribute_counts = config.integers("ATTRIBUTE_COUNT")
    rsa_key_bits_values = [
        rsa_key_bits
        for rsa_key_bits in config.integers("RSA_KEY_SIZES")
        if results.has_case("decrypt", RSA_KEY_BITS, rsa_key_bits)
    ]

    cpabe_series = results.sweep_features(
        "decrypt",
        CPABE_ATTRIBUTES,
        attribute_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )

    if not rsa_key_bits_values or not cpabe_series.without_gaps().sweep_values:
        return False

    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    draw_summary(axis, cpabe_series, "CP-ABE", VIOLET, with_ci=True, linewidth=2.0)

    largest_value = calculate_axis_top([cpabe_series])

    for index, rsa_key_bits in enumerate(rsa_key_bits_values):

        rsa_latency = results.get_case_summary(
            "decrypt", RSA_KEY_BITS, rsa_key_bits
        ).latency()

        rsa_color = RSA_KEY_BITS_COLORS[index % len(RSA_KEY_BITS_COLORS)]

        axis.hlines(
            rsa_latency.mean,
            attribute_counts[0],
            attribute_counts[-1],
            color=rsa_color,
            linestyle="--",
            linewidth=1.6,
            label=f"RSA-{rsa_key_bits}",
        )

        axis.errorbar(
            [attribute_counts[-1]],
            [rsa_latency.mean],
            yerr=[rsa_latency.ci],
            color=rsa_color,
            fmt="none",
            capsize=4,
        )

        largest_value = max(largest_value, rsa_latency.mean + rsa_latency.ci)

    axis.set_xticks(attribute_counts)
    axis.set_xlim(0.0, float(attribute_counts[-1]) * AXIS_HEADROOM)
    axis.set_ylim(0.0, largest_value * 1.15)
    axis.set_xlabel("Policy Attributes")
    axis.set_ylabel("Decrypt Latency (µs) ± 95% CI")
    apply_value_grid(axis)
    axis.legend(fontsize=9, loc="upper left")

    figure.tight_layout()
    save_figure(figure, config.figure(DECRYPT_LATENCY_CROSSOVER_PLOT))

    return True


def plot_encrypt_decrypt_asymmetry(
    results: BenchmarkSummary,
    config: Config,
) -> bool:

    fixed_rsa_key_bits = config.integer("FIXED_RSA_KEY_SIZE")
    min_attributes = config.integers("ATTRIBUTE_COUNT")[0]

    if not measured(
        results, ENCRYPT_DECRYPT, RSA_KEY_BITS, [fixed_rsa_key_bits]
    ) or not measured(results, ENCRYPT_DECRYPT, CPABE_ATTRIBUTES, [min_attributes]):
        return False

    def rsa_micros(operation: str) -> float:
        return (
            results.get_case_summary(operation, RSA_KEY_BITS, fixed_rsa_key_bits)
            .latency()
            .mean
        )

    scheme_labels = [
        f"RSA-{fixed_rsa_key_bits}",
        f"CP-ABE ({format_attribute_label(min_attributes)})",
    ]
    encrypt_values = [
        rsa_micros("encrypt"),
        cpabe_micros(results, "encrypt", min_attributes),
    ]
    decrypt_values = [
        rsa_micros("decrypt"),
        cpabe_micros(results, "decrypt", min_attributes),
    ]

    figure, axis = plt.subplots(figsize=ASYMMETRY_FIGURE_SIZE)

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
    save_figure(figure, config.figure(ASYMMETRY_PLOT))

    return True


def build_latency_table(
    results: BenchmarkSummary,
    config: Config,
    sweep_name: str,
    sweep_values: list[int],
    operation: str,
    value_header: str,
    size_columns: tuple[tuple[str, str], ...] = (),
    highlight_value: int | None = None,
) -> str:

    rows = []
    cases: list[CaseSummary | None] = []

    for sweep_value in sweep_values:

        # The sweep value was configured and attempted, so it keeps its row. What the
        # process managed to print before it died is not a measurement of it
        if not results.has_case(operation, sweep_name, sweep_value):
            cases.append(None)
            rows.append(
                [str(sweep_value), NOT_COMPLETED]
                + [NOT_AVAILABLE] * (len(size_columns) + 1)
            )
            continue

        case = results.get_case_summary(operation, sweep_name, sweep_value)
        cases.append(case)

        latency = case.latency()

        rows.append(
            [
                str(sweep_value),
                format_mean_with_ci(latency.mean, latency.ci),
                *[
                    format_byte_size(round(case.get_feature(unit).mean))
                    for _, unit in size_columns
                ],
                f"{case.iterations:,}",
            ]
        )

    return build_html_table(
        [
            value_header.upper(),
            "LATENCY (µs/op)",
            *[header for header, _ in size_columns],
            f"ITERS (Σ{config.runs} RUNS)",
        ],
        rows,
        throttle_flags(cases),
        thermal_header="THERMAL",
        highlighted=[sweep_value == highlight_value for sweep_value in sweep_values],
    )


# Key generation is reported as the distribution it is. Every run performs exactly one
# generation, so each run contributes one sample and the column n is that sample count.
# The spread between min and max is the point, a single averaged figure would not be
# representative of a probabilistic prime search
def build_keygen_table(results: BenchmarkSummary, config: Config) -> str:

    rows = []
    cases: list[CaseSummary | None] = []

    for rsa_key_bits in config.integers("RSA_KEY_SIZES"):

        if not results.has_case("keygen", RSA_KEY_BITS, rsa_key_bits):
            cases.append(None)
            rows.append([str(rsa_key_bits), NOT_COMPLETED] + [NOT_AVAILABLE] * 5)
            continue

        case = results.get_case_summary("keygen", RSA_KEY_BITS, rsa_key_bits)
        cases.append(case)

        latency = case.latency(NS_PER_MILLISECOND)

        rows.append(
            [
                str(rsa_key_bits),
                f"{latency.median:,.2f}",
                f"{latency.minimum:,.2f}",
                f"{latency.maximum:,.2f}",
                f"{latency.iqr:,.2f}",
                format_byte_size(round(case.get_feature(STORED_KEY_BYTES).mean)),
                str(latency.count),
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
        throttle_flags(cases),
        thermal_header="THERMAL",
    )


# Peak memory as it was measured, one row per configured sweep value. All three tables
# keep the same columns so they can be read against one another, and the column a sweep
# did not measure carries the reading of that operation from where it was measured
def build_peak_memory_table(
    memory: BenchmarkSummary,
    config: Config,
    group: str,
    value_header: str,
) -> str:

    environment_name, _, _, _, operations = MEMORY_SWEEPS[group]

    decrypt_reference = (
        None
        if "decrypt" in operations
        else fixed_rsa_decrypt(memory, config, PEAK_RSS_BYTES)
    )

    rows = []

    for sweep_value in config.integers(environment_name):

        row = [str(sweep_value)]
        sample_count = NOT_AVAILABLE

        for operation in ENCRYPT_DECRYPT:

            if operation not in operations:
                row.append(
                    NOT_AVAILABLE
                    if decrypt_reference is None
                    else format_byte_size(round(decrypt_reference.mean))
                )
                continue

            if not memory.has_case(operation, group, sweep_value):
                row.append(NOT_COMPLETED)
                continue

            peak = memory.get_case_summary(operation, group, sweep_value).get_feature(
                PEAK_RSS_BYTES
            )

            row.append(format_byte_size(round(peak.mean)))

            # Counted from what this sweep measured, never from a borrowed reading
            sample_count = str(peak.count)

        rows.append(row + [sample_count])

    return build_html_table([value_header.upper(), "ENCRYPT", "DECRYPT", "n"], rows)


# How peak memory tracks each swept variable, put the same way for all three so that the
# numbers rather than the framing say whether and how far it moves
def build_peak_memory_trend_table(memory: BenchmarkSummary, config: Config) -> str:

    def slope_and_fit_quality(series: FeatureSweep, unit: str) -> tuple[str, str]:

        fit = fit_sweep(series)

        if fit is None:
            return NOT_AVAILABLE, NOT_AVAILABLE

        return (
            f"{fit.slope:+,.2f} ± {fit.slope_ci:,.2f} KB / {unit}",
            f"{fit.r_squared:.4f}",
        )

    def spread(values: list[float]) -> str:

        if not values:
            return NOT_AVAILABLE

        return f"{max(values) - min(values):,.1f} KB"

    def change(values: list[float]) -> str:

        if len(values) < 2:
            return NOT_AVAILABLE

        return f"{values[0]:,.1f} &rarr; {values[-1]:,.1f} KB ({values[-1] / values[0]:.2f}×)"

    rows = []

    for group, sweep in MEMORY_SWEEPS.items():

        environment_name, panel_title, _, slope_unit, operations = sweep
        sweep_values = config.integers(environment_name)

        # Only what this sweep moved. An operation it holds fixed has no trend of its own,
        # and a borrowed reading quoted as a flat line here would read as a measured one
        for operation in operations:

            series = memory.sweep_features(
                operation, group, sweep_values, PEAK_RSS_BYTES, KILOBYTE
            )
            measured_means = series.without_gaps().means

            slope_text, fit_quality = slope_and_fit_quality(series, slope_unit)

            rows.append(
                [
                    panel_title,
                    operation.capitalize(),
                    slope_text,
                    fit_quality,
                    spread(measured_means),
                    change(measured_means),
                ]
            )

    return build_html_table(
        ["SWEEP", "OPERATION", "SLOPE", "R²", "MIN-MAX SPREAD", "FIRST &rarr; LAST"],
        rows,
    )


def build_rsa_circle_visualization(
    results: BenchmarkSummary,
    config: Config,
) -> dict[str, str]:

    subscriber_counts = config.integers("SUBSCRIBER_COUNT")

    def circle_style(diameter_px: float) -> str:
        return f'style="width:{diameter_px:.0f}px;height:{diameter_px:.0f}px;"'

    if not measured(
        results,
        ["encrypt"],
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

    single_bytes = rsa_bytes_per_subscriber(results, config)
    total_bytes = (
        results.get_case_summary("encrypt", RSA_SUBSCRIBERS, subscriber_counts[-1])
        .get_feature(TOTAL_CIPHERTEXT_BYTES)
        .mean
    )

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


# The orchestrator's record of every process it launched, turned into the two things the
# report needs of it: the cases it must forget, and the rows of the failure notice
def apply_case_outcomes(
    results: BenchmarkSummary,
    memory: BenchmarkSummary,
    config: Config,
) -> list[list[str]]:

    def diagnose(exit_code: int, out_of_memory: bool) -> str:

        if exit_code == OOM_KILLED_EXIT_CODE:
            return OOM_KILLED_DIAGNOSIS

        if out_of_memory:
            return RUNTIME_OOM_DIAGNOSIS

        return PROCESS_FAILED_DIAGNOSIS

    rows = []

    for invocation in load_invocations(config.case_status, config.case_logs):

        if invocation.completed:
            continue

        for summary, operations in (
            (results, TIMING_OPERATIONS),
            (memory, MEMORY_OPERATIONS),
        ):
            operation = operations.get(invocation.operation)

            if operation is not None:
                summary.drop_case(operation, invocation.group, invocation.sweep_value)

        rows.append(
            [
                invocation.operation,
                f"{invocation.group}/{invocation.sweep_value}",
                str(invocation.sample),
                str(invocation.exit_code),
                diagnose(invocation.exit_code, invocation.out_of_memory),
            ]
        )

    # A memory case that exited cleanly without the readings the experiment asked for
    # measured less than was configured. A confidence interval quietly computed from the
    # rest would describe a smaller experiment than the one that was run
    if memory.measures(PEAK_RSS_BYTES):

        for case in memory.incomplete_cases(PEAK_RSS_BYTES, config.runs):

            rows.append(
                [
                    f"Memory{case.operation.capitalize()}",
                    f"{case.group}/{case.sweep_value}",
                    NOT_AVAILABLE,
                    "0",
                    f"Only {case.sample_count(PEAK_RSS_BYTES)} of {config.runs} "
                    "samples produced a peak reading",
                ]
            )

            memory.drop_case(case.operation, case.group, case.sweep_value)

    return rows


def write_html_report(
    results: BenchmarkSummary,
    memory: BenchmarkSummary,
    config: Config,
    failures: list[list[str]],
    frames: dict[str, str],
) -> None:

    attribute_counts = config.integers("ATTRIBUTE_COUNT")
    subscriber_counts = config.integers("SUBSCRIBER_COUNT")
    rsa_key_bits = config.integers("RSA_KEY_SIZES")
    fixed_rsa_key_bits = config.integer("FIXED_RSA_KEY_SIZE")

    min_attributes = attribute_counts[0]
    max_attributes = attribute_counts[-1]

    encrypt_fit = fit_rsa_encrypt_slope(results, config)

    cpabe_encrypt = fit_cpabe_slope(
        results, config, "encrypt", NS_PER_OP, NS_PER_MICROSECOND
    )
    cpabe_decrypt = fit_cpabe_slope(
        results, config, "decrypt", NS_PER_OP, NS_PER_MICROSECOND
    )
    cpabe_ciphertext = fit_cpabe_slope(results, config, "encrypt", CIPHERTEXT_BYTES)
    cpabe_stored_key = fit_cpabe_slope(results, config, "decrypt", STORED_KEY_BYTES)

    cpabe_encrypt_measured = measured(
        results, ["encrypt"], CPABE_ATTRIBUTES, [min_attributes, max_attributes]
    )
    bytes_measured = cpabe_encrypt_measured and measured(
        results, ["encrypt"], RSA_SUBSCRIBERS, [subscriber_counts[0]]
    )
    decrypt_penalty_measured = measured(
        results, ["decrypt"], CPABE_ATTRIBUTES, [min_attributes, max_attributes]
    ) and measured(results, ["decrypt"], RSA_KEY_BITS, [fixed_rsa_key_bits])

    def micros_slope(fit: LinearFit | None) -> str:
        if fit is None:
            return NOT_AVAILABLE

        return f"+{format_mean_with_ci(fit.slope, fit.slope_ci, decimals=0)} µs"

    def bytes_slope(fit: LinearFit | None) -> str:
        if fit is None:
            return NOT_AVAILABLE

        return f"+{format_mean_with_ci(fit.slope, fit.slope_ci, decimals=0, thousands=False)} B"

    def fit_quality(fit: LinearFit | None) -> str:
        if fit is None:
            return NOT_AVAILABLE

        return f"{fit.r_squared:.6f}"

    # Subscriber count at which RSA's wrapped keys add up to CP-ABE's one ciphertext
    def bytes_crossover(attribute_count: int) -> float | None:
        if not bytes_measured:
            return None

        return cpabe_ciphertext_bytes(
            results, attribute_count
        ) / rsa_bytes_per_subscriber(results, config)

    # Subscriber count at which RSA's fitted encrypt line reaches CP-ABE's fixed cost
    def latency_crossover(attribute_count: int) -> float | None:
        if encrypt_fit is None or not cpabe_encrypt_measured:
            return None

        return encrypt_fit.solve_x_for_y(
            cpabe_micros(results, "encrypt", attribute_count)
        )

    # How much more decrypt latency CP-ABE asks of the subscriber than RSA does
    def decrypt_penalty(attribute_count: int) -> float | None:
        if not decrypt_penalty_measured:
            return None

        rsa_decrypt_micros = (
            results.get_case_summary("decrypt", RSA_KEY_BITS, fixed_rsa_key_bits)
            .latency()
            .mean
        )

        return cpabe_micros(results, "decrypt", attribute_count) / rsa_decrypt_micros

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

    def table(
        sweep_name,
        sweep_values,
        operation,
        value_header,
        *size_columns,
        highlight_value=None,
    ) -> str:
        return build_latency_table(
            results,
            config,
            sweep_name,
            sweep_values,
            operation,
            value_header,
            size_columns,
            highlight_value,
        )

    memory_tables = {
        "PeakMemoryTrendTable": "",
        "PeakMemoryCpabeTable": "",
        "PeakMemoryRsaSubscribersTable": "",
        "PeakMemoryRsaKeyBitsTable": "",
    }

    if memory.measures(PEAK_RSS_BYTES):
        memory_tables = {
            "PeakMemoryTrendTable": build_peak_memory_trend_table(memory, config),
            "PeakMemoryCpabeTable": build_peak_memory_table(
                memory, config, CPABE_ATTRIBUTES, "Attributes"
            ),
            "PeakMemoryRsaSubscribersTable": build_peak_memory_table(
                memory, config, RSA_SUBSCRIBERS, "Subscribers"
            ),
            "PeakMemoryRsaKeyBitsTable": build_peak_memory_table(
                memory, config, RSA_KEY_BITS, "Key Bits"
            ),
        }

    placeholders = {
        **build_html_generic_data(
            config.runs, config.t_critical, results.total_iterations
        ),
        **build_rsa_circle_visualization(results, config),
        **frames,
        **memory_tables,
        "OutOfMemoryNotice": build_html_failure_notice(failures),
        "CpabeEncryptTable": table(
            CPABE_ATTRIBUTES,
            attribute_counts,
            "encrypt",
            "Attributes",
            CIPHERTEXT_COLUMN,
        ),
        "CpabeDecryptTable": table(
            CPABE_ATTRIBUTES,
            attribute_counts,
            "decrypt",
            "Attributes",
            STORED_KEY_COLUMN,
        ),
        "RsaSubscribersEncryptTable": table(
            RSA_SUBSCRIBERS,
            subscriber_counts,
            "encrypt",
            "Subscribers",
            CIPHERTEXT_COLUMN,
            TOTAL_CIPHERTEXT_COLUMN,
        ),
        "RsaKeyBitsEncryptTable": table(
            RSA_KEY_BITS,
            rsa_key_bits,
            "encrypt",
            "Key Bits",
            CIPHERTEXT_COLUMN,
        ),
        # The row the cross-schema comparisons and the subscriber sweep are quoted
        # against, marked so it can be found among the key sizes around it
        "RsaKeyBitsDecryptTable": table(
            RSA_KEY_BITS,
            rsa_key_bits,
            "decrypt",
            "Key Bits",
            highlight_value=fixed_rsa_key_bits,
        ),
        "RsaKeyBitsKeygenTable": build_keygen_table(results, config),
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
            else f"+{rsa_bytes_per_subscriber(results, config):.0f} B"
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

    build_html_report(config.template, config.report, placeholders)


def main() -> None:
    config = Config(SCENARIO, TEMPLATE_NAME, ENV_PREFIX)

    results = load_results(config.bench_output, BENCHMARK_PREFIX)

    # A result set produced before the memory experiment existed simply has no such file
    memory = (
        load_results(config.memory_output, MEMORY_PREFIX)
        if os.path.exists(config.memory_output)
        else BenchmarkSummary({})
    )

    failures = apply_case_outcomes(results, memory, config)

    plot_sweep(
        results,
        CPABE_ATTRIBUTES,
        config.integers("ATTRIBUTE_COUNT"),
        ENCRYPT_DECRYPT,
        (CIPHERTEXT_SERIES, CPABE_STORED_KEY_SERIES),
        "Policy Attributes",
        "CP-ABE Scaling with Policy Attribute Count",
        config.figure(CPABE_PLOT),
    )

    fixed_rsa_key_bits = config.integer("FIXED_RSA_KEY_SIZE")

    plot_sweep(
        results,
        RSA_SUBSCRIBERS,
        config.integers("SUBSCRIBER_COUNT"),
        ["encrypt"],
        (CIPHERTEXT_SERIES, TOTAL_CIPHERTEXT_SERIES),
        "Subscribers",
        f"RSA Scaling with Subscriber Count (Fixed Key: {fixed_rsa_key_bits} bits)",
        config.figure(RSA_SUBSCRIBERS_PLOT),
        fixed_rsa_decrypt(results, config, NS_PER_OP, NS_PER_MICROSECOND),
        f"Decrypt (RSA-{fixed_rsa_key_bits}, Constant)",
    )

    plot_sweep(
        results,
        RSA_KEY_BITS,
        config.integers("RSA_KEY_SIZES"),
        ENCRYPT_DECRYPT_KEYGEN,
        (CIPHERTEXT_SERIES, RSA_STORED_KEY_SERIES),
        "RSA Key Bits",
        "RSA Scaling with Key Size (1 Subscriber)",
        config.figure(RSA_KEY_BITS_PLOT),
    )

    frames = {
        "BandwidthCrossoverFrame": plot_frame(
            plot_ciphertext_size_crossover(results, config),
            CIPHERTEXT_SIZE_CROSSOVER_PLOT,
        ),
        "EncryptCpuCrossoverFrame": plot_frame(
            plot_encrypt_latency_crossover(results, config),
            ENCRYPT_LATENCY_CROSSOVER_PLOT,
        ),
        "DecryptCpuCrossoverFrame": plot_frame(
            plot_decrypt_latency_crossover(results, config),
            DECRYPT_LATENCY_CROSSOVER_PLOT,
        ),
        "AsymmetryFrame": plot_frame(
            plot_encrypt_decrypt_asymmetry(results, config), ASYMMETRY_PLOT
        ),
        "PeakMemoryFrame": plot_frame(
            plot_peak_memory(memory, config),
            PEAK_MEMORY_PLOT,
            NO_MEMORY_READING_NOTE,
        ),
    }

    write_html_report(results, memory, config, failures, frames)


if __name__ == "__main__":
    main()
