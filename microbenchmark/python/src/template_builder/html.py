from typing import Sequence

from template_builder.formatting import *

CONFIDENCE_LEVEL = "95%"

# A row is marked where the Raspberry Pi firmware throttled the clock while that case was
# being measured, which makes the measurement a pessimistic bound rather than an invalid
# one. The column is drawn only where something actually throttled, since a column of
# identical marks repeated across every table would bury the rows that matter
THERMAL_MARK = "&#9888;"

# A row the rest of the report is quoted against, ex. the fixed RSA key size the
# cross-schema comparisons use, is marked so it can be found among the swept values
REFERENCE_ROW_CLASS = "reference-row"
THERMAL_FLAGGED_NOTE = (
    "&#9888; marks a case measured while the Raspberry Pi firmware was thermally "
    "throttling. Those measurements are a pessimistic bound, not an invalid one."
)
THERMAL_CLEAN_NOTE = "No thermal throttling occurred while these cases were measured."

OUT_OF_MEMORY_NOTICE_HEADERS = ["OPERATION", "CASE", "RESULT"]
OUT_OF_MEMORY_NOTICE_NOTE = (
    "These timing or key-generation cases ran out of memory. Any partial measurements "
    "they emitted are excluded from the figures and tables below."
)


# Builds HTML table, given header names and row values. The throttle flags are positional,
# one per row, and are left out entirely for a benchmark that carries no throttle readings.
# The highlight flags are positional in the same way
def build_html_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    throttled: list[bool] | None = None,
    thermal_header: str = "Thermal",
    highlighted: list[bool] | None = None,
) -> str:

    flagged = throttled is not None and any(throttled)

    lines = ["<table>", "<thead>", "<tr>"]
    lines += [f"<th>{header}</th>" for header in headers]

    if flagged:
        lines.append(f"<th>{thermal_header}</th>")

    lines += ["</tr>", "</thead>", "<tbody>"]

    for index, row in enumerate(rows):

        if highlighted is not None and highlighted[index]:
            lines.append(f'<tr class="{REFERENCE_ROW_CLASS}">')
        else:
            lines.append("<tr>")

        lines += [f"<td>{cell}</td>" for cell in row]

        if flagged:
            mark = THERMAL_MARK if throttled[index] else ""  # type: ignore
            lines.append(f'<td class="thermal">{mark}</td>')

        lines.append("</tr>")

    lines += ["</tbody>", "</table>"]

    # The note explains the mark where there is one, and confirms the absence of
    # throttling where the column has been left out
    if throttled is not None:
        note = THERMAL_FLAGGED_NOTE if flagged else THERMAL_CLEAN_NOTE
        lines.append(f'<p class="table-note">{note}</p>')

    return "\n".join(lines)


# A run in which every process finished has nothing to report here, so the whole section
# collapses to an empty string and leaves no trace in the page
def build_html_out_of_memory_notice(rows: Sequence[Sequence[str]]) -> str:

    if not rows:
        return ""

    return "\n".join(
        [
            '<section class="section failure-notice">',
            '<div class="section-heading">',
            "<h2>Out of Memory</h2>",
            f"<p>{OUT_OF_MEMORY_NOTICE_NOTE}</p>",
            "</div>",
            '<div class="table-block">',
            '<div class="table-wrapper">',
            build_html_table(OUT_OF_MEMORY_NOTICE_HEADERS, rows),
            "</div>",
            "</div>",
            "</section>",
        ]
    )


# Report values shared by all scenarios:
# 1. runs
# 2. t_critical
# 3. iteration_total
def build_html_generic_data(
    runs: int,
    t_multiplier: float,
    iteration_total: int,
) -> dict[str, str]:

    return {
        "RunCount": str(runs),
        "ConfidenceLevel": CONFIDENCE_LEVEL,
        "TMultiplier": str(t_multiplier),
        "TotalIterations": f"{iteration_total:,}",
    }


# Builds final HTML report by replacing template placeholders with actual values
def build_html_report(
    template_path: str,
    output_path: str,
    placeholders: dict[str, str],
) -> None:

    with open(template_path, "r", encoding="utf-8") as file:
        report = file.read()

    for name, value in placeholders.items():
        report = report.replace(f"{{{{{name}}}}}", value)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(report)

    print(f"Saved -> {output_path}")


def build_aes_ascon_table(
    payload_sizes: list[int],
    latency_means: list[float],
    latency_cis: list[float],
    throughput_means: list[float],
    throughput_cis: list[float],
    overhead_bytes: list[float],
    iterations: list[int],
    throttled: list[bool] | None,
    runs: int,
) -> str:
    rows = [
        [
            format_byte_size(payload_size, compact=True),
            format_mean_with_ci(latency_mean, latency_ci),
            format_mean_with_ci(throughput_mean, throughput_ci, decimals=1),
            f"{overhead:.0f}",
            f"{iteration_count:,}",
        ]
        for (
            payload_size,
            latency_mean,
            latency_ci,
            throughput_mean,
            throughput_ci,
            overhead,
            iteration_count,
        ) in zip(
            payload_sizes,
            latency_means,
            latency_cis,
            throughput_means,
            throughput_cis,
            overhead_bytes,
            iterations,
            strict=True,
        )
    ]

    return build_html_table(
        [
            "Payload",
            "Latency (ns/op)",
            "Throughput (MB/s)",
            "Tag + Nonce (B)",
            f"Iters (Σ{runs} runs)",
        ],
        rows,
        throttled,
    )


def write_aes_ascon_report(
    *,
    runs: int,
    t_multiplier: float,
    total_iterations: int,
    payload_sizes: list[int],
    aes_encrypt_latency_means: list[float],
    aes_encrypt_latency_cis: list[float],
    aes_encrypt_throughput_means: list[float],
    aes_encrypt_throughput_cis: list[float],
    aes_encrypt_overhead_bytes: list[float],
    aes_encrypt_iterations: list[int],
    aes_encrypt_throttled: list[bool] | None,
    ascon_encrypt_latency_means: list[float],
    ascon_encrypt_latency_cis: list[float],
    ascon_encrypt_throughput_means: list[float],
    ascon_encrypt_throughput_cis: list[float],
    ascon_encrypt_overhead_bytes: list[float],
    ascon_encrypt_iterations: list[int],
    ascon_encrypt_throttled: list[bool] | None,
    aes_decrypt_latency_means: list[float],
    aes_decrypt_latency_cis: list[float],
    aes_decrypt_throughput_means: list[float],
    aes_decrypt_throughput_cis: list[float],
    aes_decrypt_overhead_bytes: list[float],
    aes_decrypt_iterations: list[int],
    aes_decrypt_throttled: list[bool] | None,
    ascon_decrypt_latency_means: list[float],
    ascon_decrypt_latency_cis: list[float],
    ascon_decrypt_throughput_means: list[float],
    ascon_decrypt_throughput_cis: list[float],
    ascon_decrypt_overhead_bytes: list[float],
    ascon_decrypt_iterations: list[int],
    ascon_decrypt_throttled: list[bool] | None,
    latency_plot: str,
    throughput_plot: str,
    template_path: str,
    report_path: str,
) -> None:
    placeholders = {
        **build_html_generic_data(runs, t_multiplier, total_iterations),
        "EncryptAesTable": build_aes_ascon_table(
            payload_sizes,
            aes_encrypt_latency_means,
            aes_encrypt_latency_cis,
            aes_encrypt_throughput_means,
            aes_encrypt_throughput_cis,
            aes_encrypt_overhead_bytes,
            aes_encrypt_iterations,
            aes_encrypt_throttled,
            runs,
        ),
        "EncryptAsconTable": build_aes_ascon_table(
            payload_sizes,
            ascon_encrypt_latency_means,
            ascon_encrypt_latency_cis,
            ascon_encrypt_throughput_means,
            ascon_encrypt_throughput_cis,
            ascon_encrypt_overhead_bytes,
            ascon_encrypt_iterations,
            ascon_encrypt_throttled,
            runs,
        ),
        "DecryptAesTable": build_aes_ascon_table(
            payload_sizes,
            aes_decrypt_latency_means,
            aes_decrypt_latency_cis,
            aes_decrypt_throughput_means,
            aes_decrypt_throughput_cis,
            aes_decrypt_overhead_bytes,
            aes_decrypt_iterations,
            aes_decrypt_throttled,
            runs,
        ),
        "DecryptAsconTable": build_aes_ascon_table(
            payload_sizes,
            ascon_decrypt_latency_means,
            ascon_decrypt_latency_cis,
            ascon_decrypt_throughput_means,
            ascon_decrypt_throughput_cis,
            ascon_decrypt_overhead_bytes,
            ascon_decrypt_iterations,
            ascon_decrypt_throttled,
            runs,
        ),
        "LatencyPlot": latency_plot,
        "ThroughputPlot": throughput_plot,
    }

    build_html_report(template_path, report_path, placeholders)


def build_json_cbor_table(
    attribute_counts: list[int],
    latency_means: list[float],
    latency_cis: list[float],
    raw_sizes: list[float],
    envelope_sizes: list[float],
    overhead_percents: list[float],
    iterations: list[int],
    throttled: list[bool] | None,
    runs: int,
) -> str:
    rows = [
        [
            str(attribute_count),
            format_mean_with_ci(latency_mean, latency_ci),
            f"{raw_size:,.0f}",
            f"{envelope_size:,.0f}",
            f"{overhead_percent:.2f}%",
            f"{iteration_count:,}",
        ]
        for (
            attribute_count,
            latency_mean,
            latency_ci,
            raw_size,
            envelope_size,
            overhead_percent,
            iteration_count,
        ) in zip(
            attribute_counts,
            latency_means,
            latency_cis,
            raw_sizes,
            envelope_sizes,
            overhead_percents,
            iterations,
            strict=True,
        )
    ]

    return build_html_table(
        [
            "Attributes",
            "Latency (ns/op)",
            "Raw (B)",
            "Envelope Size (B)",
            "Format Overhead (%)",
            f"Iters (Σ{runs} runs)",
        ],
        rows,
        throttled,
    )


def write_json_cbor_report(
    *,
    runs: int,
    t_multiplier: float,
    total_iterations: int,
    attribute_counts: list[int],
    json_serialize_latency_means: list[float],
    json_serialize_latency_cis: list[float],
    json_serialize_raw_sizes: list[float],
    json_serialize_envelope_sizes: list[float],
    json_serialize_overhead_percents: list[float],
    json_serialize_iterations: list[int],
    json_serialize_throttled: list[bool] | None,
    cbor_serialize_latency_means: list[float],
    cbor_serialize_latency_cis: list[float],
    cbor_serialize_raw_sizes: list[float],
    cbor_serialize_envelope_sizes: list[float],
    cbor_serialize_overhead_percents: list[float],
    cbor_serialize_iterations: list[int],
    cbor_serialize_throttled: list[bool] | None,
    cbor_int_serialize_latency_means: list[float],
    cbor_int_serialize_latency_cis: list[float],
    cbor_int_serialize_raw_sizes: list[float],
    cbor_int_serialize_envelope_sizes: list[float],
    cbor_int_serialize_overhead_percents: list[float],
    cbor_int_serialize_iterations: list[int],
    cbor_int_serialize_throttled: list[bool] | None,
    json_deserialize_latency_means: list[float],
    json_deserialize_latency_cis: list[float],
    json_deserialize_raw_sizes: list[float],
    json_deserialize_envelope_sizes: list[float],
    json_deserialize_overhead_percents: list[float],
    json_deserialize_iterations: list[int],
    json_deserialize_throttled: list[bool] | None,
    cbor_deserialize_latency_means: list[float],
    cbor_deserialize_latency_cis: list[float],
    cbor_deserialize_raw_sizes: list[float],
    cbor_deserialize_envelope_sizes: list[float],
    cbor_deserialize_overhead_percents: list[float],
    cbor_deserialize_iterations: list[int],
    cbor_deserialize_throttled: list[bool] | None,
    cbor_int_deserialize_latency_means: list[float],
    cbor_int_deserialize_latency_cis: list[float],
    cbor_int_deserialize_raw_sizes: list[float],
    cbor_int_deserialize_envelope_sizes: list[float],
    cbor_int_deserialize_overhead_percents: list[float],
    cbor_int_deserialize_iterations: list[int],
    cbor_int_deserialize_throttled: list[bool] | None,
    latency_plot: str,
    size_plot: str,
    template_path: str,
    report_path: str,
) -> None:
    placeholders = {
        **build_html_generic_data(runs, t_multiplier, total_iterations),
        "SerializeJsonTable": build_json_cbor_table(
            attribute_counts,
            json_serialize_latency_means,
            json_serialize_latency_cis,
            json_serialize_raw_sizes,
            json_serialize_envelope_sizes,
            json_serialize_overhead_percents,
            json_serialize_iterations,
            json_serialize_throttled,
            runs,
        ),
        "SerializeCborTable": build_json_cbor_table(
            attribute_counts,
            cbor_serialize_latency_means,
            cbor_serialize_latency_cis,
            cbor_serialize_raw_sizes,
            cbor_serialize_envelope_sizes,
            cbor_serialize_overhead_percents,
            cbor_serialize_iterations,
            cbor_serialize_throttled,
            runs,
        ),
        "SerializeCborKeyAsIntTable": build_json_cbor_table(
            attribute_counts,
            cbor_int_serialize_latency_means,
            cbor_int_serialize_latency_cis,
            cbor_int_serialize_raw_sizes,
            cbor_int_serialize_envelope_sizes,
            cbor_int_serialize_overhead_percents,
            cbor_int_serialize_iterations,
            cbor_int_serialize_throttled,
            runs,
        ),
        "DeserializeJsonTable": build_json_cbor_table(
            attribute_counts,
            json_deserialize_latency_means,
            json_deserialize_latency_cis,
            json_deserialize_raw_sizes,
            json_deserialize_envelope_sizes,
            json_deserialize_overhead_percents,
            json_deserialize_iterations,
            json_deserialize_throttled,
            runs,
        ),
        "DeserializeCborTable": build_json_cbor_table(
            attribute_counts,
            cbor_deserialize_latency_means,
            cbor_deserialize_latency_cis,
            cbor_deserialize_raw_sizes,
            cbor_deserialize_envelope_sizes,
            cbor_deserialize_overhead_percents,
            cbor_deserialize_iterations,
            cbor_deserialize_throttled,
            runs,
        ),
        "DeserializeCborKeyAsIntTable": build_json_cbor_table(
            attribute_counts,
            cbor_int_deserialize_latency_means,
            cbor_int_deserialize_latency_cis,
            cbor_int_deserialize_raw_sizes,
            cbor_int_deserialize_envelope_sizes,
            cbor_int_deserialize_overhead_percents,
            cbor_int_deserialize_iterations,
            cbor_int_deserialize_throttled,
            runs,
        ),
        "LatencyPlot": latency_plot,
        "SizePlot": size_plot,
    }

    build_html_report(template_path, report_path, placeholders)


def build_payload_scaling_table(
    payload_sizes: list[int],
    latency_means: list[float],
    latency_cis: list[float],
    throughput_means: list[float],
    throughput_cis: list[float],
    wire_sizes: list[int],
    overhead_percents: list[float],
    iterations: list[int],
    throttled: list[bool] | None,
    runs: int,
) -> str:
    rows = [
        [
            format_byte_size(payload_size),
            format_mean_with_ci(latency_mean, latency_ci),
            format_mean_with_ci(throughput_mean, throughput_ci, decimals=1),
            format_byte_size(wire_size),
            (f"{overhead_percent:.2f}%" if overhead_percent >= 0.01 else "&lt;0.01%"),
            f"{iteration_count:,}",
        ]
        for (
            payload_size,
            latency_mean,
            latency_ci,
            throughput_mean,
            throughput_ci,
            wire_size,
            overhead_percent,
            iteration_count,
        ) in zip(
            payload_sizes,
            latency_means,
            latency_cis,
            throughput_means,
            throughput_cis,
            wire_sizes,
            overhead_percents,
            iterations,
            strict=True,
        )
    ]

    return build_html_table(
        [
            "Raw Size",
            "Latency (µs/op)",
            "Throughput (MB/s)",
            "Wire Size",
            "Overhead (%)",
            f"Iters (Σ{runs} runs)",
        ],
        rows,
        throttled,
    )


def write_payload_scaling_report(
    *,
    runs: int,
    t_multiplier: float,
    total_iterations: int,
    payload_sizes: list[int],
    psk_wire_sizes: list[int],
    psk_overhead_percents: list[float],
    rsa_wire_sizes: list[int],
    rsa_overhead_percents: list[float],
    cpabe_wire_sizes: list[int],
    cpabe_overhead_percents: list[float],
    psk_encrypt_latency_means: list[float],
    psk_encrypt_latency_cis: list[float],
    psk_encrypt_throughput_means: list[float],
    psk_encrypt_throughput_cis: list[float],
    psk_encrypt_iterations: list[int],
    psk_encrypt_throttled: list[bool] | None,
    rsa_encrypt_latency_means: list[float],
    rsa_encrypt_latency_cis: list[float],
    rsa_encrypt_throughput_means: list[float],
    rsa_encrypt_throughput_cis: list[float],
    rsa_encrypt_iterations: list[int],
    rsa_encrypt_throttled: list[bool] | None,
    cpabe_encrypt_latency_means: list[float],
    cpabe_encrypt_latency_cis: list[float],
    cpabe_encrypt_throughput_means: list[float],
    cpabe_encrypt_throughput_cis: list[float],
    cpabe_encrypt_iterations: list[int],
    cpabe_encrypt_throttled: list[bool] | None,
    psk_decrypt_latency_means: list[float],
    psk_decrypt_latency_cis: list[float],
    psk_decrypt_throughput_means: list[float],
    psk_decrypt_throughput_cis: list[float],
    psk_decrypt_iterations: list[int],
    psk_decrypt_throttled: list[bool] | None,
    rsa_decrypt_latency_means: list[float],
    rsa_decrypt_latency_cis: list[float],
    rsa_decrypt_throughput_means: list[float],
    rsa_decrypt_throughput_cis: list[float],
    rsa_decrypt_iterations: list[int],
    rsa_decrypt_throttled: list[bool] | None,
    cpabe_decrypt_latency_means: list[float],
    cpabe_decrypt_latency_cis: list[float],
    cpabe_decrypt_throughput_means: list[float],
    cpabe_decrypt_throughput_cis: list[float],
    cpabe_decrypt_iterations: list[int],
    cpabe_decrypt_throttled: list[bool] | None,
    latency_plot: str,
    throughput_plot: str,
    template_path: str,
    report_path: str,
) -> None:
    placeholders = {
        **build_html_generic_data(runs, t_multiplier, total_iterations),
        "EncryptPskTable": build_payload_scaling_table(
            payload_sizes,
            psk_encrypt_latency_means,
            psk_encrypt_latency_cis,
            psk_encrypt_throughput_means,
            psk_encrypt_throughput_cis,
            psk_wire_sizes,
            psk_overhead_percents,
            psk_encrypt_iterations,
            psk_encrypt_throttled,
            runs,
        ),
        "EncryptRsaTable": build_payload_scaling_table(
            payload_sizes,
            rsa_encrypt_latency_means,
            rsa_encrypt_latency_cis,
            rsa_encrypt_throughput_means,
            rsa_encrypt_throughput_cis,
            rsa_wire_sizes,
            rsa_overhead_percents,
            rsa_encrypt_iterations,
            rsa_encrypt_throttled,
            runs,
        ),
        "EncryptCpabeTable": build_payload_scaling_table(
            payload_sizes,
            cpabe_encrypt_latency_means,
            cpabe_encrypt_latency_cis,
            cpabe_encrypt_throughput_means,
            cpabe_encrypt_throughput_cis,
            cpabe_wire_sizes,
            cpabe_overhead_percents,
            cpabe_encrypt_iterations,
            cpabe_encrypt_throttled,
            runs,
        ),
        "DecryptPskTable": build_payload_scaling_table(
            payload_sizes,
            psk_decrypt_latency_means,
            psk_decrypt_latency_cis,
            psk_decrypt_throughput_means,
            psk_decrypt_throughput_cis,
            psk_wire_sizes,
            psk_overhead_percents,
            psk_decrypt_iterations,
            psk_decrypt_throttled,
            runs,
        ),
        "DecryptRsaTable": build_payload_scaling_table(
            payload_sizes,
            rsa_decrypt_latency_means,
            rsa_decrypt_latency_cis,
            rsa_decrypt_throughput_means,
            rsa_decrypt_throughput_cis,
            rsa_wire_sizes,
            rsa_overhead_percents,
            rsa_decrypt_iterations,
            rsa_decrypt_throttled,
            runs,
        ),
        "DecryptCpabeTable": build_payload_scaling_table(
            payload_sizes,
            cpabe_decrypt_latency_means,
            cpabe_decrypt_latency_cis,
            cpabe_decrypt_throughput_means,
            cpabe_decrypt_throughput_cis,
            cpabe_wire_sizes,
            cpabe_overhead_percents,
            cpabe_decrypt_iterations,
            cpabe_decrypt_throttled,
            runs,
        ),
        "LatencyPlot": latency_plot,
        "ThroughputPlot": throughput_plot,
    }

    build_html_report(template_path, report_path, placeholders)


NOT_AVAILABLE = "&mdash;"
OUT_OF_MEMORY = "Out of memory"
MISSING_CASE_NOTE = (
    '<p class="missing-note">Not available: a case this comparison rests on ran out '
    "of memory. See Out of Memory at the top of the report.</p>"
)
FANOUT_LARGEST_DIAMETER_PX = 168.0
FANOUT_SMALLEST_DIAMETER_PX = 22.0


def format_optional_mean_with_ci(
    mean_value: float | None,
    ci: float | None,
    suffix: str = "",
) -> str:
    if mean_value is None or ci is None:
        return NOT_AVAILABLE

    return f"{format_mean_with_ci(mean_value, ci)}{suffix}"


def build_cpabe_encrypt_table(
    attribute_counts: list[int],
    latency_means: list[float | None],
    latency_cis: list[float | None],
    ciphertext_sizes: list[float | None],
    iterations: list[int | None],
    throttled: list[bool] | None,
    runs: int,
) -> str:
    rows = []
    for (
        attribute_count,
        latency_mean,
        latency_ci,
        ciphertext_size,
        iteration_count,
    ) in zip(
        attribute_counts,
        latency_means,
        latency_cis,
        ciphertext_sizes,
        iterations,
        strict=True,
    ):
        if latency_mean is None or latency_ci is None:
            rows.append(
                [str(attribute_count), OUT_OF_MEMORY, NOT_AVAILABLE, NOT_AVAILABLE]
            )
        else:
            assert ciphertext_size is not None and iteration_count is not None
            rows.append(
                [
                    str(attribute_count),
                    format_mean_with_ci(latency_mean, latency_ci),
                    format_byte_size(round(ciphertext_size)),
                    f"{iteration_count:,}",
                ]
            )

    return build_html_table(
        ["ATTRIBUTES", "LATENCY (µs/op)", "CIPHERTEXT", f"ITERS (Σ{runs} RUNS)"],
        rows,
        throttled,
        thermal_header="THERMAL",
        highlighted=[False] * len(attribute_counts),
    )


def build_cpabe_decrypt_table(
    attribute_counts: list[int],
    latency_means: list[float | None],
    latency_cis: list[float | None],
    stored_key_sizes: list[float | None],
    iterations: list[int | None],
    throttled: list[bool] | None,
    runs: int,
) -> str:
    rows = []
    for (
        attribute_count,
        latency_mean,
        latency_ci,
        stored_key_size,
        iteration_count,
    ) in zip(
        attribute_counts,
        latency_means,
        latency_cis,
        stored_key_sizes,
        iterations,
        strict=True,
    ):
        if latency_mean is None or latency_ci is None:
            rows.append(
                [str(attribute_count), OUT_OF_MEMORY, NOT_AVAILABLE, NOT_AVAILABLE]
            )
        else:
            assert stored_key_size is not None and iteration_count is not None
            rows.append(
                [
                    str(attribute_count),
                    format_mean_with_ci(latency_mean, latency_ci),
                    format_byte_size(round(stored_key_size)),
                    f"{iteration_count:,}",
                ]
            )

    return build_html_table(
        ["ATTRIBUTES", "LATENCY (µs/op)", "STORED KEY", f"ITERS (Σ{runs} RUNS)"],
        rows,
        throttled,
        thermal_header="THERMAL",
        highlighted=[False] * len(attribute_counts),
    )


def build_rsa_subscriber_encrypt_table(
    subscriber_counts: list[int],
    latency_means: list[float | None],
    latency_cis: list[float | None],
    ciphertext_sizes: list[float | None],
    total_ciphertext_sizes: list[float | None],
    iterations: list[int | None],
    throttled: list[bool] | None,
    runs: int,
) -> str:
    rows = []
    for (
        subscriber_count,
        latency_mean,
        latency_ci,
        ciphertext_size,
        total_size,
        iteration_count,
    ) in zip(
        subscriber_counts,
        latency_means,
        latency_cis,
        ciphertext_sizes,
        total_ciphertext_sizes,
        iterations,
        strict=True,
    ):
        if latency_mean is None or latency_ci is None:
            rows.append(
                [
                    str(subscriber_count),
                    OUT_OF_MEMORY,
                    NOT_AVAILABLE,
                    NOT_AVAILABLE,
                    NOT_AVAILABLE,
                ]
            )
        else:
            assert ciphertext_size is not None and total_size is not None
            assert iteration_count is not None
            rows.append(
                [
                    str(subscriber_count),
                    format_mean_with_ci(latency_mean, latency_ci),
                    format_byte_size(round(ciphertext_size)),
                    format_byte_size(round(total_size)),
                    f"{iteration_count:,}",
                ]
            )

    return build_html_table(
        [
            "SUBSCRIBERS",
            "LATENCY (µs/op)",
            "CIPHERTEXT",
            "CIPHERTEXT (TOTAL)",
            f"ITERS (Σ{runs} RUNS)",
        ],
        rows,
        throttled,
        thermal_header="THERMAL",
        highlighted=[False] * len(subscriber_counts),
    )


def build_rsa_key_bits_encrypt_table(
    rsa_key_sizes: list[int],
    latency_means: list[float | None],
    latency_cis: list[float | None],
    ciphertext_sizes: list[float | None],
    iterations: list[int | None],
    throttled: list[bool] | None,
    runs: int,
) -> str:
    rows = []
    for rsa_key_bits, latency_mean, latency_ci, ciphertext_size, iteration_count in zip(
        rsa_key_sizes,
        latency_means,
        latency_cis,
        ciphertext_sizes,
        iterations,
        strict=True,
    ):
        if latency_mean is None or latency_ci is None:
            rows.append(
                [str(rsa_key_bits), OUT_OF_MEMORY, NOT_AVAILABLE, NOT_AVAILABLE]
            )
        else:
            assert ciphertext_size is not None and iteration_count is not None
            rows.append(
                [
                    str(rsa_key_bits),
                    format_mean_with_ci(latency_mean, latency_ci),
                    format_byte_size(round(ciphertext_size)),
                    f"{iteration_count:,}",
                ]
            )

    return build_html_table(
        ["KEY BITS", "LATENCY (µs/op)", "CIPHERTEXT", f"ITERS (Σ{runs} RUNS)"],
        rows,
        throttled,
        thermal_header="THERMAL",
        highlighted=[False] * len(rsa_key_sizes),
    )


def build_rsa_key_bits_decrypt_table(
    rsa_key_sizes: list[int],
    latency_means: list[float | None],
    latency_cis: list[float | None],
    iterations: list[int | None],
    throttled: list[bool] | None,
    runs: int,
    fixed_rsa_key_bits: int,
) -> str:
    rows = []
    for rsa_key_bits, latency_mean, latency_ci, iteration_count in zip(
        rsa_key_sizes, latency_means, latency_cis, iterations, strict=True
    ):
        if latency_mean is None or latency_ci is None:
            rows.append([str(rsa_key_bits), OUT_OF_MEMORY, NOT_AVAILABLE])
        else:
            assert iteration_count is not None
            rows.append(
                [
                    str(rsa_key_bits),
                    format_mean_with_ci(latency_mean, latency_ci),
                    f"{iteration_count:,}",
                ]
            )

    return build_html_table(
        ["KEY BITS", "LATENCY (µs/op)", f"ITERS (Σ{runs} RUNS)"],
        rows,
        throttled,
        thermal_header="THERMAL",
        highlighted=[
            rsa_key_bits == fixed_rsa_key_bits for rsa_key_bits in rsa_key_sizes
        ],
    )


def build_rsa_keygen_table(
    rsa_key_sizes: list[int],
    medians: list[float | None],
    minimums: list[float | None],
    maximums: list[float | None],
    iqrs: list[float | None],
    stored_key_sizes: list[float | None],
    sample_counts: list[int | None],
    throttled: list[bool] | None,
) -> str:
    rows = []
    for (
        rsa_key_bits,
        median,
        minimum,
        maximum,
        iqr,
        stored_key_size,
        sample_count,
    ) in zip(
        rsa_key_sizes,
        medians,
        minimums,
        maximums,
        iqrs,
        stored_key_sizes,
        sample_counts,
        strict=True,
    ):
        if median is None:
            rows.append([str(rsa_key_bits), OUT_OF_MEMORY] + [NOT_AVAILABLE] * 5)
        else:
            assert minimum is not None and maximum is not None and iqr is not None
            assert stored_key_size is not None and sample_count is not None
            rows.append(
                [
                    str(rsa_key_bits),
                    f"{median:,.2f}",
                    f"{minimum:,.2f}",
                    f"{maximum:,.2f}",
                    f"{iqr:,.2f}",
                    format_byte_size(round(stored_key_size)),
                    str(sample_count),
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
        throttled,
        thermal_header="THERMAL",
    )


def build_cpabe_peak_memory_table(
    attribute_counts: list[int],
    encrypt_means: list[float],
    encrypt_cis: list[float],
    decrypt_means: list[float],
    decrypt_cis: list[float],
    sample_counts: list[int],
) -> str:
    rows = [
        [
            str(attribute_count),
            format_mean_with_ci(encrypt_mean, encrypt_ci),
            format_mean_with_ci(decrypt_mean, decrypt_ci),
            str(sample_count),
        ]
        for attribute_count, encrypt_mean, encrypt_ci, decrypt_mean, decrypt_ci, sample_count in zip(
            attribute_counts,
            encrypt_means,
            encrypt_cis,
            decrypt_means,
            decrypt_cis,
            sample_counts,
            strict=True,
        )
    ]
    return build_html_table(["ATTRIBUTES", "ENCRYPT (MB)", "DECRYPT (MB)", "n"], rows)


def build_rsa_subscriber_peak_memory_table(
    subscriber_counts: list[int],
    encrypt_means: list[float],
    encrypt_cis: list[float],
    decrypt_mean: float | None,
    decrypt_ci: float | None,
    sample_counts: list[int],
) -> str:
    decrypt_value = format_optional_mean_with_ci(decrypt_mean, decrypt_ci)
    rows = [
        [
            str(subscriber_count),
            format_mean_with_ci(encrypt_mean, encrypt_ci),
            decrypt_value,
            str(sample_count),
        ]
        for subscriber_count, encrypt_mean, encrypt_ci, sample_count in zip(
            subscriber_counts,
            encrypt_means,
            encrypt_cis,
            sample_counts,
            strict=True,
        )
    ]
    return build_html_table(["SUBSCRIBERS", "ENCRYPT (MB)", "DECRYPT (MB)", "n"], rows)


def build_rsa_key_size_peak_memory_table(
    rsa_key_sizes: list[int],
    encrypt_means: list[float],
    encrypt_cis: list[float],
    decrypt_means: list[float],
    decrypt_cis: list[float],
    sample_counts: list[int],
) -> str:
    rows = [
        [
            str(rsa_key_bits),
            format_mean_with_ci(encrypt_mean, encrypt_ci),
            format_mean_with_ci(decrypt_mean, decrypt_ci),
            str(sample_count),
        ]
        for rsa_key_bits, encrypt_mean, encrypt_ci, decrypt_mean, decrypt_ci, sample_count in zip(
            rsa_key_sizes,
            encrypt_means,
            encrypt_cis,
            decrypt_means,
            decrypt_cis,
            sample_counts,
            strict=True,
        )
    ]
    return build_html_table(["KEY BITS", "ENCRYPT (MB)", "DECRYPT (MB)", "n"], rows)


def format_peak_memory_change(
    first: float | None,
    last: float | None,
    absolute_change: float | None,
    percent_change: float | None,
) -> str:
    if (
        first is None
        or last is None
        or absolute_change is None
        or percent_change is None
    ):
        return NOT_AVAILABLE

    return (
        f"{first:,.2f} &rarr; {last:,.2f} MB &middot; "
        f"{absolute_change:+,.2f} MB ({percent_change:+,.1f}%)"
    )


def build_peak_memory_deltas(
    attribute_counts: list[int],
    subscriber_counts: list[int],
    rsa_key_sizes: list[int],
    cpabe_encrypt_first: float | None,
    cpabe_encrypt_last: float | None,
    cpabe_encrypt_absolute_change: float | None,
    cpabe_encrypt_percent_change: float | None,
    cpabe_decrypt_first: float | None,
    cpabe_decrypt_last: float | None,
    cpabe_decrypt_absolute_change: float | None,
    cpabe_decrypt_percent_change: float | None,
    subscriber_encrypt_first: float | None,
    subscriber_encrypt_last: float | None,
    subscriber_encrypt_absolute_change: float | None,
    subscriber_encrypt_percent_change: float | None,
    rsa_encrypt_first: float | None,
    rsa_encrypt_last: float | None,
    rsa_encrypt_absolute_change: float | None,
    rsa_encrypt_percent_change: float | None,
    rsa_decrypt_first: float | None,
    rsa_decrypt_last: float | None,
    rsa_decrypt_absolute_change: float | None,
    rsa_decrypt_percent_change: float | None,
) -> str:
    items = [
        '<span class="delta-item"><strong>CP-ABE Encrypt</strong> '
        f"{attribute_counts[0]} &rarr; {attribute_counts[-1]} attributes &middot; "
        f"{format_peak_memory_change(cpabe_encrypt_first, cpabe_encrypt_last, cpabe_encrypt_absolute_change, cpabe_encrypt_percent_change)}</span>",
        '<span class="delta-item"><strong>CP-ABE Decrypt</strong> '
        f"{attribute_counts[0]} &rarr; {attribute_counts[-1]} attributes &middot; "
        f"{format_peak_memory_change(cpabe_decrypt_first, cpabe_decrypt_last, cpabe_decrypt_absolute_change, cpabe_decrypt_percent_change)}</span>",
        '<span class="delta-item"><strong>RSA Subscribers Encrypt</strong> '
        f"{subscriber_counts[0]} &rarr; {subscriber_counts[-1]} subscribers &middot; "
        f"{format_peak_memory_change(subscriber_encrypt_first, subscriber_encrypt_last, subscriber_encrypt_absolute_change, subscriber_encrypt_percent_change)}</span>",
        '<span class="delta-item"><strong>RSA Key Size Encrypt</strong> '
        f"{rsa_key_sizes[0]} &rarr; {rsa_key_sizes[-1]} key bits &middot; "
        f"{format_peak_memory_change(rsa_encrypt_first, rsa_encrypt_last, rsa_encrypt_absolute_change, rsa_encrypt_percent_change)}</span>",
        '<span class="delta-item"><strong>RSA Key Size Decrypt</strong> '
        f"{rsa_key_sizes[0]} &rarr; {rsa_key_sizes[-1]} key bits &middot; "
        f"{format_peak_memory_change(rsa_decrypt_first, rsa_decrypt_last, rsa_decrypt_absolute_change, rsa_decrypt_percent_change)}</span>",
    ]
    return f'<div class="delta-strip">{"".join(items)}</div>'


def build_rsa_circle_visualization(
    single_bytes: float | None,
    total_bytes: float | None,
    multiplier: float | None,
) -> dict[str, str]:
    def circle_style(diameter_px: float) -> str:
        return f'style="width:{diameter_px:.0f}px;height:{diameter_px:.0f}px;"'

    if single_bytes is None or total_bytes is None or multiplier is None:
        return {
            "FanoutSingleBytes": NOT_AVAILABLE,
            "FanoutTotalBytes": NOT_AVAILABLE,
            "FanoutMultiplier": NOT_AVAILABLE,
            "FanoutSingleStyle": circle_style(FANOUT_SMALLEST_DIAMETER_PX),
            "FanoutTotalStyle": circle_style(FANOUT_SMALLEST_DIAMETER_PX),
        }

    single_diameter_px = max(
        FANOUT_SMALLEST_DIAMETER_PX,
        FANOUT_LARGEST_DIAMETER_PX * (single_bytes / total_bytes) ** 0.5,
    )
    return {
        "FanoutSingleBytes": format_byte_size(round(single_bytes)),
        "FanoutTotalBytes": format_byte_size(round(total_bytes)),
        "FanoutMultiplier": f"{multiplier:.0f}",
        "FanoutSingleStyle": circle_style(single_diameter_px),
        "FanoutTotalStyle": circle_style(FANOUT_LARGEST_DIAMETER_PX),
    }


def build_plot_frame(filename: str | None) -> str:
    if filename is None:
        return MISSING_CASE_NOTE

    return f'<img src="{filename}">'


def format_optional_number(value: float | None, decimals: int = 0) -> str:
    if value is None:
        return NOT_AVAILABLE

    return f"{value:,.{decimals}f}"


def format_optional_truncated_number(value: float | None) -> str:
    if value is None:
        return NOT_AVAILABLE

    return f"{int(value):,}"


def format_slope(
    slope: float | None,
    slope_ci: float | None,
    unit: str,
    decimals: int = 0,
    thousands: bool = True,
) -> str:
    if slope is None or slope_ci is None:
        return NOT_AVAILABLE

    return (
        f"+{format_mean_with_ci(slope, slope_ci, decimals=decimals, thousands=thousands)} "
        f"{unit}"
    )


def format_r_squared(value: float | None) -> str:
    if value is None:
        return NOT_AVAILABLE

    return f"{value:.6f}"


def write_attribute_key_scaling_report(
    *,
    timing_runs: int,
    t_multiplier: float,
    timing_iterations: int,
    attribute_counts: list[int],
    subscriber_counts: list[int],
    rsa_key_sizes: list[int],
    fixed_rsa_key_bits: int,
    cpabe_encrypt_latency_means: list[float | None],
    cpabe_encrypt_latency_cis: list[float | None],
    cpabe_encrypt_ciphertext_sizes: list[float | None],
    cpabe_encrypt_iterations: list[int | None],
    cpabe_encrypt_throttled: list[bool] | None,
    cpabe_decrypt_latency_means: list[float | None],
    cpabe_decrypt_latency_cis: list[float | None],
    cpabe_decrypt_stored_key_sizes: list[float | None],
    cpabe_decrypt_iterations: list[int | None],
    cpabe_decrypt_throttled: list[bool] | None,
    subscriber_encrypt_latency_means: list[float | None],
    subscriber_encrypt_latency_cis: list[float | None],
    subscriber_ciphertext_sizes: list[float | None],
    subscriber_total_ciphertext_sizes: list[float | None],
    subscriber_encrypt_iterations: list[int | None],
    subscriber_encrypt_throttled: list[bool] | None,
    rsa_encrypt_latency_means: list[float | None],
    rsa_encrypt_latency_cis: list[float | None],
    rsa_ciphertext_sizes: list[float | None],
    rsa_encrypt_iterations: list[int | None],
    rsa_encrypt_throttled: list[bool] | None,
    rsa_decrypt_latency_means: list[float | None],
    rsa_decrypt_latency_cis: list[float | None],
    rsa_decrypt_iterations: list[int | None],
    rsa_decrypt_throttled: list[bool] | None,
    keygen_medians: list[float | None],
    keygen_minimums: list[float | None],
    keygen_maximums: list[float | None],
    keygen_iqrs: list[float | None],
    keygen_stored_key_sizes: list[float | None],
    keygen_sample_counts: list[int | None],
    keygen_throttled: list[bool] | None,
    baseline_memory_mean: float,
    baseline_memory_ci: float,
    cpabe_memory_encrypt_means: list[float],
    cpabe_memory_encrypt_cis: list[float],
    cpabe_memory_decrypt_means: list[float],
    cpabe_memory_decrypt_cis: list[float],
    cpabe_memory_sample_counts: list[int],
    subscriber_memory_encrypt_means: list[float],
    subscriber_memory_encrypt_cis: list[float],
    subscriber_memory_decrypt_mean: float | None,
    subscriber_memory_decrypt_ci: float | None,
    subscriber_memory_sample_counts: list[int],
    rsa_memory_encrypt_means: list[float],
    rsa_memory_encrypt_cis: list[float],
    rsa_memory_decrypt_means: list[float],
    rsa_memory_decrypt_cis: list[float],
    rsa_memory_sample_counts: list[int],
    cpabe_encrypt_memory_first: float | None,
    cpabe_encrypt_memory_last: float | None,
    cpabe_encrypt_memory_absolute_change: float | None,
    cpabe_encrypt_memory_percent_change: float | None,
    cpabe_decrypt_memory_first: float | None,
    cpabe_decrypt_memory_last: float | None,
    cpabe_decrypt_memory_absolute_change: float | None,
    cpabe_decrypt_memory_percent_change: float | None,
    subscriber_encrypt_memory_first: float | None,
    subscriber_encrypt_memory_last: float | None,
    subscriber_encrypt_memory_absolute_change: float | None,
    subscriber_encrypt_memory_percent_change: float | None,
    rsa_encrypt_memory_first: float | None,
    rsa_encrypt_memory_last: float | None,
    rsa_encrypt_memory_absolute_change: float | None,
    rsa_encrypt_memory_percent_change: float | None,
    rsa_decrypt_memory_first: float | None,
    rsa_decrypt_memory_last: float | None,
    rsa_decrypt_memory_absolute_change: float | None,
    rsa_decrypt_memory_percent_change: float | None,
    fanout_single_bytes: float | None,
    fanout_total_bytes: float | None,
    fanout_multiplier: float | None,
    out_of_memory_operations: list[str],
    out_of_memory_cases: list[str],
    cpabe_encrypt_slope: float | None,
    cpabe_encrypt_slope_ci: float | None,
    cpabe_encrypt_r_squared: float | None,
    cpabe_decrypt_slope: float | None,
    cpabe_decrypt_slope_ci: float | None,
    cpabe_decrypt_r_squared: float | None,
    cpabe_ciphertext_slope: float | None,
    cpabe_ciphertext_slope_ci: float | None,
    cpabe_ciphertext_r_squared: float | None,
    cpabe_stored_key_slope: float | None,
    cpabe_stored_key_slope_ci: float | None,
    cpabe_stored_key_r_squared: float | None,
    subscriber_encrypt_slope: float | None,
    subscriber_encrypt_slope_ci: float | None,
    subscriber_encrypt_r_squared: float | None,
    bytes_per_subscriber: float | None,
    bytes_crossover_low: float | None,
    bytes_crossover_high: float | None,
    latency_crossover_low: float | None,
    latency_crossover_high: float | None,
    decrypt_penalty_low: float | None,
    decrypt_penalty_high: float | None,
    cpabe_plot: str,
    rsa_subscribers_plot: str,
    rsa_key_bits_plot: str,
    bandwidth_crossover_plot: str | None,
    encrypt_crossover_plot: str | None,
    decrypt_crossover_plot: str | None,
    asymmetry_plot: str | None,
    peak_memory_plot: str,
    template_path: str,
    report_path: str,
) -> None:
    placeholders = {
        **build_html_generic_data(timing_runs, t_multiplier, timing_iterations),
        **build_rsa_circle_visualization(
            fanout_single_bytes, fanout_total_bytes, fanout_multiplier
        ),
        "OutOfMemoryNotice": build_html_out_of_memory_notice(
            [
                [operation, case_name, OUT_OF_MEMORY]
                for operation, case_name in zip(
                    out_of_memory_operations, out_of_memory_cases, strict=True
                )
            ]
        ),
        "CpabeEncryptTable": build_cpabe_encrypt_table(
            attribute_counts,
            cpabe_encrypt_latency_means,
            cpabe_encrypt_latency_cis,
            cpabe_encrypt_ciphertext_sizes,
            cpabe_encrypt_iterations,
            cpabe_encrypt_throttled,
            timing_runs,
        ),
        "CpabeDecryptTable": build_cpabe_decrypt_table(
            attribute_counts,
            cpabe_decrypt_latency_means,
            cpabe_decrypt_latency_cis,
            cpabe_decrypt_stored_key_sizes,
            cpabe_decrypt_iterations,
            cpabe_decrypt_throttled,
            timing_runs,
        ),
        "RsaSubscribersEncryptTable": build_rsa_subscriber_encrypt_table(
            subscriber_counts,
            subscriber_encrypt_latency_means,
            subscriber_encrypt_latency_cis,
            subscriber_ciphertext_sizes,
            subscriber_total_ciphertext_sizes,
            subscriber_encrypt_iterations,
            subscriber_encrypt_throttled,
            timing_runs,
        ),
        "RsaKeyBitsEncryptTable": build_rsa_key_bits_encrypt_table(
            rsa_key_sizes,
            rsa_encrypt_latency_means,
            rsa_encrypt_latency_cis,
            rsa_ciphertext_sizes,
            rsa_encrypt_iterations,
            rsa_encrypt_throttled,
            timing_runs,
        ),
        "RsaKeyBitsDecryptTable": build_rsa_key_bits_decrypt_table(
            rsa_key_sizes,
            rsa_decrypt_latency_means,
            rsa_decrypt_latency_cis,
            rsa_decrypt_iterations,
            rsa_decrypt_throttled,
            timing_runs,
            fixed_rsa_key_bits,
        ),
        "RsaKeyBitsKeygenTable": build_rsa_keygen_table(
            rsa_key_sizes,
            keygen_medians,
            keygen_minimums,
            keygen_maximums,
            keygen_iqrs,
            keygen_stored_key_sizes,
            keygen_sample_counts,
            keygen_throttled,
        ),
        "BaselineRss": f"{format_mean_with_ci(baseline_memory_mean, baseline_memory_ci)} MB",
        "PeakMemoryCpabeTable": build_cpabe_peak_memory_table(
            attribute_counts,
            cpabe_memory_encrypt_means,
            cpabe_memory_encrypt_cis,
            cpabe_memory_decrypt_means,
            cpabe_memory_decrypt_cis,
            cpabe_memory_sample_counts,
        ),
        "PeakMemoryRsaSubscribersTable": build_rsa_subscriber_peak_memory_table(
            subscriber_counts,
            subscriber_memory_encrypt_means,
            subscriber_memory_encrypt_cis,
            subscriber_memory_decrypt_mean,
            subscriber_memory_decrypt_ci,
            subscriber_memory_sample_counts,
        ),
        "PeakMemoryRsaKeyBitsTable": build_rsa_key_size_peak_memory_table(
            rsa_key_sizes,
            rsa_memory_encrypt_means,
            rsa_memory_encrypt_cis,
            rsa_memory_decrypt_means,
            rsa_memory_decrypt_cis,
            rsa_memory_sample_counts,
        ),
        "PeakMemoryDeltas": build_peak_memory_deltas(
            attribute_counts,
            subscriber_counts,
            rsa_key_sizes,
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
        ),
        "MinAttributeLabel": format_attribute_label(attribute_counts[0]),
        "MaxAttributeLabel": format_attribute_label(attribute_counts[-1]),
        "MaxSubscriberCount": str(subscriber_counts[-1]),
        "FixedRsaKeyBits": str(fixed_rsa_key_bits),
        "CpabePlot": cpabe_plot,
        "RsaSubscribersPlot": rsa_subscribers_plot,
        "RsaKeyBitsPlot": rsa_key_bits_plot,
        "BandwidthCrossoverFrame": build_plot_frame(bandwidth_crossover_plot),
        "EncryptCpuCrossoverFrame": build_plot_frame(encrypt_crossover_plot),
        "DecryptCpuCrossoverFrame": build_plot_frame(decrypt_crossover_plot),
        "AsymmetryFrame": build_plot_frame(asymmetry_plot),
        "PeakMemoryFrame": build_plot_frame(peak_memory_plot),
        "CpabeEncryptSlope": format_slope(
            cpabe_encrypt_slope, cpabe_encrypt_slope_ci, "µs"
        ),
        "CpabeDecryptSlope": format_slope(
            cpabe_decrypt_slope, cpabe_decrypt_slope_ci, "µs"
        ),
        "CpabeCiphertextSlope": format_slope(
            cpabe_ciphertext_slope,
            cpabe_ciphertext_slope_ci,
            "B",
            thousands=False,
        ),
        "CpabeStoredKeySlope": format_slope(
            cpabe_stored_key_slope,
            cpabe_stored_key_slope_ci,
            "B",
            thousands=False,
        ),
        "CpabeEncryptRSquared": format_r_squared(cpabe_encrypt_r_squared),
        "CpabeDecryptRSquared": format_r_squared(cpabe_decrypt_r_squared),
        "CpabeCiphertextRSquared": format_r_squared(cpabe_ciphertext_r_squared),
        "CpabeStoredKeyRSquared": format_r_squared(cpabe_stored_key_r_squared),
        "RsaSubscriberEncryptSlope": format_slope(
            subscriber_encrypt_slope,
            subscriber_encrypt_slope_ci,
            "µs",
            decimals=2,
        ),
        "RsaSubscriberEncryptRSquared": format_r_squared(subscriber_encrypt_r_squared),
        "RsaSubscriberTotalCiphertextSlope": (
            NOT_AVAILABLE
            if bytes_per_subscriber is None
            else f"+{bytes_per_subscriber:.0f} B"
        ),
        "BytesCrossoverLow": format_optional_number(bytes_crossover_low, 1),
        "BytesCrossoverHigh": format_optional_number(bytes_crossover_high, 1),
        "BytesRsaThroughMin": format_optional_truncated_number(bytes_crossover_low),
        "BytesRsaThroughMax": format_optional_truncated_number(bytes_crossover_high),
        "EncryptCpuCrossoverLow": format_optional_number(latency_crossover_low),
        "EncryptCpuCrossoverHigh": format_optional_number(latency_crossover_high),
        "CpuRsaThroughMin": format_optional_truncated_number(latency_crossover_low),
        "CpuRsaThroughMax": format_optional_truncated_number(latency_crossover_high),
        "DecryptPenaltyMin": format_optional_number(decrypt_penalty_low, 1),
        "DecryptPenaltyMax": format_optional_number(decrypt_penalty_high, 1),
    }

    build_html_report(template_path, report_path, placeholders)
