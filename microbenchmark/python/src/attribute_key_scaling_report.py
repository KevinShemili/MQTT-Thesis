from reporting.benchmark import (
    CIPHERTEXT_BYTES,
    NS_PER_MICROSECOND,
    NS_PER_MILLISECOND,
    NS_PER_OP,
    STORED_KEY_BYTES,
    TOTAL_CIPHERTEXT_BYTES,
    BenchmarkSummary,
    FeatureSweep,
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
    draw_distribution,
    draw_summary,
    plt,
    save_figure,
    calculate_axis_top,
)
from reporting.environment import Config
from reporting.formatting import (
    format_byte_size,
    format_mean_with_ci,
)
from reporting.html import build_html_generic_data, build_html_report, build_html_table
from reporting.statistics import LinearFit, fit_linear_regression

SCENARIO = "attribute-key-scaling"
ENV_PREFIX = "ATTRIBUTE_KEY_SCALING"
BENCHMARK_PREFIX = "BenchmarkAttributeKeyScaling"
TEMPLATE_NAME = "attribute_key_scaling_template.html"

CPABE_PLOT = "cpabe_attributes.png"
RSA_SUBSCRIBERS_PLOT = "rsa_subscribers.png"
RSA_KEY_BITS_PLOT = "rsa_key_bits.png"
CIPHERTEXT_SIZE_CROSSOVER_PLOT = "ciphertext_size_crossover.png"
ASYMMETRY_PLOT = "encrypt_decrypt_asymmetry.png"
ENCRYPT_LATENCY_CROSSOVER_PLOT = "encrypt_latency_crossover.png"
DECRYPT_LATENCY_CROSSOVER_PLOT = "decrypt_latency_crossover.png"

CPABE_ATTRIBUTES = "CPABEAttributes"
RSA_SUBSCRIBERS = "RSASubscribers"
RSA_KEY_BITS = "RSAKeyBits"

# CP-ABE key issuance is deliberately not measured by the benchmark, it is paid by the
# trusted attribute authority and never by the constrained device, so only the RSA key
# size sweep carries a key generation operation
ENCRYPT_DECRYPT = ["encrypt", "decrypt"]
ENCRYPT_DECRYPT_KEYGEN = ["encrypt", "decrypt", "keygen"]

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


def format_attribute_label(attribute_count: int) -> str:
    if attribute_count == 1:
        return "1 ATTRIBUTE"

    return f"{attribute_count} ATTRIBUTES"


# CP-ABE's cost as a straight line in the policy attribute count
def fit_cpabe_slope(
    results: BenchmarkSummary,
    config: Config,
    operation: str,
    unit: str,
    divisor: float = 1.0,
) -> LinearFit:

    series = results.sweep_features(
        operation,
        CPABE_ATTRIBUTES,
        config.integers("ATTRIBUTE_COUNT"),
        unit,
        divisor,
    )

    return fit_linear_regression(series.sweep_values, series.means)


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
def fit_rsa_encrypt_slope(results: BenchmarkSummary, config: Config) -> LinearFit:

    series = sweep_rsa_encrypt_micros(results, config)

    return fit_linear_regression(series.sweep_values, series.means)


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


# Where RSA's per-subscriber ciphertext growth overtakes CP-ABE's fixed ciphertext
def plot_ciphertext_size_crossover(
    results: BenchmarkSummary,
    config: Config,
) -> None:

    attribute_counts = config.integers("ATTRIBUTE_COUNT")
    subscriber_counts = config.integers("SUBSCRIBER_COUNT")

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


# Where RSA's per-subscriber encrypt cost overtakes CP-ABE's fixed encrypt cost
def plot_encrypt_latency_crossover(
    results: BenchmarkSummary,
    config: Config,
) -> None:

    attribute_counts = config.integers("ATTRIBUTE_COUNT")
    subscriber_counts = config.integers("SUBSCRIBER_COUNT")

    encrypt_fit = fit_rsa_encrypt_slope(results, config)

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


def plot_decrypt_latency_crossover(
    results: BenchmarkSummary,
    config: Config,
) -> None:

    attribute_counts = config.integers("ATTRIBUTE_COUNT")

    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    cpabe_series = results.sweep_features(
        "decrypt",
        CPABE_ATTRIBUTES,
        attribute_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )

    draw_summary(axis, cpabe_series, "CP-ABE", VIOLET, with_ci=True, linewidth=2.0)

    largest_value = calculate_axis_top([cpabe_series])

    for index, rsa_key_bits in enumerate(config.integers("RSA_KEY_SIZES")):

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


def plot_encrypt_decrypt_asymmetry(
    results: BenchmarkSummary,
    config: Config,
) -> None:

    fixed_rsa_key_bits = config.integer("FIXED_RSA_KEY_BITS")
    min_attributes = config.integers("ATTRIBUTE_COUNT")[0]

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


def build_latency_table(
    results: BenchmarkSummary,
    config: Config,
    sweep_name: str,
    sweep_values: list[int],
    operation: str,
    value_header: str,
    size_columns: tuple[tuple[str, str], ...] = (),
) -> str:

    rows = []
    cases = []

    for sweep_value in sweep_values:

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
    )


# Key generation is reported as the distribution it is. Every run performs exactly one
# generation, so each run contributes one sample and the column n is that sample count.
# The spread between min and max is the point, a single averaged figure would not be
# representative of a probabilistic prime search
def build_keygen_table(results: BenchmarkSummary, config: Config) -> str:

    rows = []
    cases = []

    for rsa_key_bits in config.integers("RSA_KEY_SIZES"):

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


def build_rsa_circle_visualization(
    results: BenchmarkSummary,
    config: Config,
) -> dict[str, str]:

    single_bytes = rsa_bytes_per_subscriber(results, config)
    total_bytes = (
        results.get_case_summary(
            "encrypt", RSA_SUBSCRIBERS, config.integers("SUBSCRIBER_COUNT")[-1]
        )
        .get_feature(TOTAL_CIPHERTEXT_BYTES)
        .mean
    )

    single_diameter_px = max(
        FANOUT_SMALLEST_DIAMETER_PX,
        FANOUT_LARGEST_DIAMETER_PX * (single_bytes / total_bytes) ** 0.5,
    )

    def circle_style(diameter_px: float) -> str:
        return f'style="width:{diameter_px:.0f}px;height:{diameter_px:.0f}px;"'

    return {
        "FanoutSingleBytes": format_byte_size(round(single_bytes)),
        "FanoutTotalBytes": format_byte_size(round(total_bytes)),
        "FanoutMultiplier": f"{total_bytes / single_bytes:.0f}",
        "FanoutSingleStyle": circle_style(single_diameter_px),
        "FanoutTotalStyle": circle_style(FANOUT_LARGEST_DIAMETER_PX),
    }


def write_html_report(results: BenchmarkSummary, config: Config) -> None:

    attribute_counts = config.integers("ATTRIBUTE_COUNT")
    subscriber_counts = config.integers("SUBSCRIBER_COUNT")
    rsa_key_bits = config.integers("RSA_KEY_SIZES")
    fixed_rsa_key_bits = config.integer("FIXED_RSA_KEY_BITS")

    min_attributes = attribute_counts[0]
    max_attributes = attribute_counts[-1]

    encrypt_fit = fit_rsa_encrypt_slope(results, config)
    bytes_per_subscriber = rsa_bytes_per_subscriber(results, config)

    cpabe_encrypt = fit_cpabe_slope(
        results, config, "encrypt", NS_PER_OP, NS_PER_MICROSECOND
    )
    cpabe_decrypt = fit_cpabe_slope(
        results, config, "decrypt", NS_PER_OP, NS_PER_MICROSECOND
    )
    cpabe_ciphertext = fit_cpabe_slope(results, config, "encrypt", CIPHERTEXT_BYTES)
    cpabe_stored_key = fit_cpabe_slope(results, config, "decrypt", STORED_KEY_BYTES)

    rsa_decrypt_micros = (
        results.get_case_summary("decrypt", RSA_KEY_BITS, fixed_rsa_key_bits)
        .latency()
        .mean
    )

    def micros_slope(fit: LinearFit) -> str:
        return f"+{format_mean_with_ci(fit.slope, fit.slope_ci, decimals=0)} µs"

    def bytes_slope(fit: LinearFit) -> str:
        return f"+{format_mean_with_ci(fit.slope, fit.slope_ci, decimals=0, thousands=False)} B"

    # Subscriber count at which RSA's wrapped keys add up to CP-ABE's one ciphertext
    def bytes_crossover(attribute_count: int) -> float:
        return cpabe_ciphertext_bytes(results, attribute_count) / bytes_per_subscriber

    # Subscriber count at which RSA's fitted encrypt line reaches CP-ABE's fixed cost
    def latency_crossover(attribute_count: int) -> float:
        return encrypt_fit.solve_x_for_y(
            cpabe_micros(results, "encrypt", attribute_count)
        )

    # How much more decrypt latency CP-ABE asks of the subscriber than RSA does
    def decrypt_penalty(attribute_count: int) -> float:
        return cpabe_micros(results, "decrypt", attribute_count) / rsa_decrypt_micros

    def table(sweep_name, sweep_values, operation, value_header, *size_columns) -> str:
        return build_latency_table(
            results,
            config,
            sweep_name,
            sweep_values,
            operation,
            value_header,
            size_columns,
        )

    placeholders = {
        **build_html_generic_data(
            config.runs, config.t_critical, results.total_iterations
        ),
        **build_rsa_circle_visualization(results, config),
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
        "RsaSubscribersDecryptTable": table(
            RSA_SUBSCRIBERS,
            subscriber_counts,
            "decrypt",
            "Subscribers",
        ),
        "RsaKeyBitsEncryptTable": table(
            RSA_KEY_BITS,
            rsa_key_bits,
            "encrypt",
            "Key Bits",
            CIPHERTEXT_COLUMN,
        ),
        "RsaKeyBitsDecryptTable": table(
            RSA_KEY_BITS,
            rsa_key_bits,
            "decrypt",
            "Key Bits",
        ),
        "RsaKeyBitsKeygenTable": build_keygen_table(results, config),
        "MinAttributeLabel": format_attribute_label(min_attributes),
        "MaxAttributeLabel": format_attribute_label(max_attributes),
        "MaxSubscriberCount": str(subscriber_counts[-1]),
        "FixedRsaKeyBits": str(fixed_rsa_key_bits),
        "CpabePlot": CPABE_PLOT,
        "RsaSubscribersPlot": RSA_SUBSCRIBERS_PLOT,
        "RsaKeyBitsPlot": RSA_KEY_BITS_PLOT,
        "BandwidthCrossoverPlot": CIPHERTEXT_SIZE_CROSSOVER_PLOT,
        "AsymmetryPlot": ASYMMETRY_PLOT,
        "EncryptCpuCrossoverPlot": ENCRYPT_LATENCY_CROSSOVER_PLOT,
        "DecryptCpuCrossoverPlot": DECRYPT_LATENCY_CROSSOVER_PLOT,
        "CpabeEncryptSlope": micros_slope(cpabe_encrypt),
        "CpabeDecryptSlope": micros_slope(cpabe_decrypt),
        "CpabeCiphertextSlope": bytes_slope(cpabe_ciphertext),
        "CpabeStoredKeySlope": bytes_slope(cpabe_stored_key),
        "CpabeEncryptRSquared": f"{cpabe_encrypt.r_squared:.6f}",
        "CpabeDecryptRSquared": f"{cpabe_decrypt.r_squared:.6f}",
        "CpabeCiphertextRSquared": f"{cpabe_ciphertext.r_squared:.6f}",
        "CpabeStoredKeyRSquared": f"{cpabe_stored_key.r_squared:.6f}",
        "RsaSubscriberEncryptSlope": (
            f"+{format_mean_with_ci(encrypt_fit.slope, encrypt_fit.slope_ci)} µs"
        ),
        "RsaSubscriberEncryptRSquared": f"{encrypt_fit.r_squared:.6f}",
        "RsaSubscriberTotalCiphertextSlope": f"+{bytes_per_subscriber:.0f} B",
        "BytesCrossoverLow": f"{bytes_crossover(min_attributes):,.1f}",
        "BytesCrossoverHigh": f"{bytes_crossover(max_attributes):,.1f}",
        "BytesRsaThroughMin": f"{int(bytes_crossover(min_attributes)):,}",
        "BytesRsaThroughMax": f"{int(bytes_crossover(max_attributes)):,}",
        "EncryptCpuCrossoverLow": f"{latency_crossover(min_attributes):,.0f}",
        "EncryptCpuCrossoverHigh": f"{latency_crossover(max_attributes):,.0f}",
        "CpuRsaThroughMin": f"{int(latency_crossover(min_attributes)):,}",
        "CpuRsaThroughMax": f"{int(latency_crossover(max_attributes)):,}",
        "DecryptPenaltyMin": f"{decrypt_penalty(min_attributes):,.1f}",
        "DecryptPenaltyMax": f"{decrypt_penalty(max_attributes):,.1f}",
    }

    build_html_report(config.template, config.report, placeholders)


def main() -> None:
    config = Config(SCENARIO, TEMPLATE_NAME, ENV_PREFIX)
    results = load_results(config.bench_output, BENCHMARK_PREFIX)

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

    plot_sweep(
        results,
        RSA_SUBSCRIBERS,
        config.integers("SUBSCRIBER_COUNT"),
        ENCRYPT_DECRYPT,
        (CIPHERTEXT_SERIES, TOTAL_CIPHERTEXT_SERIES),
        "Subscribers",
        f"RSA Scaling with Subscriber Count (Fixed Key: {config.integer('FIXED_RSA_KEY_BITS')} bits)",
        config.figure(RSA_SUBSCRIBERS_PLOT),
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

    plot_ciphertext_size_crossover(results, config)
    plot_encrypt_latency_crossover(results, config)
    plot_decrypt_latency_crossover(results, config)
    plot_encrypt_decrypt_asymmetry(results, config)

    write_html_report(results, config)


if __name__ == "__main__":
    main()
