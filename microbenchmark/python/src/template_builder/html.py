from collections.abc import Callable
from typing import Any, Sequence

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


def _rows_from_columns(columns: Sequence[Sequence[str]]) -> list[list[str]]:
    return [list(row) for row in zip(*columns, strict=True)]


def _mean_ci_column(
    means: Sequence[float],
    confidence_intervals: Sequence[float],
    decimals: int = 2,
) -> list[str]:
    return [
        format_mean_with_ci(mean, confidence_interval, decimals=decimals)
        for mean, confidence_interval in zip(means, confidence_intervals, strict=True)
    ]


def _build_data_table(
    headers: list[str],
    columns: list[Sequence[str]],
    throttled: list[bool] | None = None,
) -> str:
    return build_html_table(headers, _rows_from_columns(columns), throttled)


def _build_aes_ascon_tables(
    payload_sizes: list[int], scope: dict[str, Any], runs: int
) -> dict[str, str]:
    headers = [
        "Payload",
        "Latency (ns/op)",
        "Throughput (MB/s)",
        "Tag + Nonce (B)",
        f"Iters (Σ{runs} runs)",
    ]
    specifications = [
        ("EncryptAesTable", "aes_encrypt"),
        ("EncryptAsconTable", "ascon_encrypt"),
        ("DecryptAesTable", "aes_decrypt"),
        ("DecryptAsconTable", "ascon_decrypt"),
    ]
    return {
        placeholder: _build_data_table(
            headers,
            [
                [format_byte_size(value, compact=True) for value in payload_sizes],
                _mean_ci_column(
                    scope[f"{prefix}_latency_means"],
                    scope[f"{prefix}_latency_cis"],
                ),
                _mean_ci_column(
                    scope[f"{prefix}_throughput_means"],
                    scope[f"{prefix}_throughput_cis"],
                    decimals=1,
                ),
                [f"{value:.0f}" for value in scope[f"{prefix}_overhead_bytes"]],
                [f"{value:,}" for value in scope[f"{prefix}_iterations"]],
            ],
            scope[f"{prefix}_throttled"],
        )
        for placeholder, prefix in specifications
    }


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
        **_build_aes_ascon_tables(payload_sizes, locals(), runs),
        "LatencyPlot": latency_plot,
        "ThroughputPlot": throughput_plot,
    }

    build_html_report(template_path, report_path, placeholders)


def _build_json_cbor_tables(
    attribute_counts: list[int], scope: dict[str, Any], runs: int
) -> dict[str, str]:
    headers = [
        "Attributes",
        "Latency (ns/op)",
        "Raw (B)",
        "Envelope Size (B)",
        "Format Overhead (%)",
        f"Iters (Σ{runs} runs)",
    ]
    specifications = [
        ("SerializeJsonTable", "json_serialize"),
        ("SerializeCborTable", "cbor_serialize"),
        ("SerializeCborKeyAsIntTable", "cbor_int_serialize"),
        ("DeserializeJsonTable", "json_deserialize"),
        ("DeserializeCborTable", "cbor_deserialize"),
        ("DeserializeCborKeyAsIntTable", "cbor_int_deserialize"),
    ]
    return {
        placeholder: _build_data_table(
            headers,
            [
                [str(value) for value in attribute_counts],
                _mean_ci_column(
                    scope[f"{prefix}_latency_means"],
                    scope[f"{prefix}_latency_cis"],
                ),
                [f"{value:,.0f}" for value in scope[f"{prefix}_raw_sizes"]],
                [f"{value:,.0f}" for value in scope[f"{prefix}_envelope_sizes"]],
                [f"{value:.2f}%" for value in scope[f"{prefix}_overhead_percents"]],
                [f"{value:,}" for value in scope[f"{prefix}_iterations"]],
            ],
            scope[f"{prefix}_throttled"],
        )
        for placeholder, prefix in specifications
    }


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
        **_build_json_cbor_tables(attribute_counts, locals(), runs),
        "LatencyPlot": latency_plot,
        "SizePlot": size_plot,
    }

    build_html_report(template_path, report_path, placeholders)


def _build_payload_tables(
    payload_sizes: list[int], scope: dict[str, Any], runs: int
) -> dict[str, str]:
    headers = [
        "Raw Size",
        "Latency (µs/op)",
        "Throughput (MB/s)",
        "Wire Size",
        "Overhead (%)",
        f"Iters (Σ{runs} runs)",
    ]
    specifications = [
        ("EncryptPskTable", "psk_encrypt", "psk"),
        ("EncryptRsaTable", "rsa_encrypt", "rsa"),
        ("EncryptCpabeTable", "cpabe_encrypt", "cpabe"),
        ("DecryptPskTable", "psk_decrypt", "psk"),
        ("DecryptRsaTable", "rsa_decrypt", "rsa"),
        ("DecryptCpabeTable", "cpabe_decrypt", "cpabe"),
    ]
    return {
        placeholder: _build_data_table(
            headers,
            [
                [format_byte_size(value) for value in payload_sizes],
                _mean_ci_column(
                    scope[f"{case}_latency_means"], scope[f"{case}_latency_cis"]
                ),
                _mean_ci_column(
                    scope[f"{case}_throughput_means"],
                    scope[f"{case}_throughput_cis"],
                    decimals=1,
                ),
                [format_byte_size(value) for value in scope[f"{scheme}_wire_sizes"]],
                [
                    f"{value:.2f}%" if value >= 0.01 else "&lt;0.01%"
                    for value in scope[f"{scheme}_overhead_percents"]
                ],
                [f"{value:,}" for value in scope[f"{case}_iterations"]],
            ],
            scope[f"{case}_throttled"],
        )
        for placeholder, case, scheme in specifications
    }


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
        **_build_payload_tables(payload_sizes, locals(), runs),
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
ExtraColumn = tuple[str, list[float | None], Callable[[float], str]]


def _build_optional_latency_table(
    index_header: str,
    index_values: list[int],
    latency_means: list[float | None],
    latency_cis: list[float | None],
    extra_columns: list[ExtraColumn],
    iterations: list[int | None],
    throttled: list[bool] | None,
    runs: int,
    highlighted: list[bool] | None = None,
) -> str:
    rows = []
    columns = [index_values, latency_means, latency_cis]
    columns.extend(values for _, values, _ in extra_columns)
    columns.append(iterations)
    for values in zip(*columns, strict=True):
        index_value, latency_mean, latency_ci, *remaining = values
        measurement_values = remaining[:-1]
        iteration_count = remaining[-1]

        if latency_mean is None or latency_ci is None:
            rows.append(
                [str(index_value), OUT_OF_MEMORY]
                + [NOT_AVAILABLE] * (len(extra_columns) + 1)
            )
            continue

        assert iteration_count is not None
        assert all(value is not None for value in measurement_values)
        rows.append(
            [str(index_value), format_mean_with_ci(latency_mean, latency_ci)]
            + [
                formatter(value)  # type: ignore
                for value, (_, _, formatter) in zip(
                    measurement_values, extra_columns, strict=True
                )
            ]
            + [f"{iteration_count:,}"]
        )

    return build_html_table(
        [
            index_header,
            "LATENCY (µs/op)",
            *[header for header, _, _ in extra_columns],
            f"ITERS (Σ{runs} RUNS)",
        ],
        rows,
        throttled,
        thermal_header="THERMAL",
        highlighted=highlighted,
    )


def _format_byte_size(value: float) -> str:
    return format_byte_size(round(value))


def _build_attribute_timing_tables(
    scope: dict[str, Any],
    attribute_counts: list[int],
    subscriber_counts: list[int],
    rsa_key_sizes: list[int],
    fixed_rsa_key_bits: int,
    runs: int,
) -> dict[str, str]:
    indexes = {
        "cpabe": ("ATTRIBUTES", attribute_counts),
        "subscriber": ("SUBSCRIBERS", subscriber_counts),
        "rsa": ("KEY BITS", rsa_key_sizes),
    }
    specifications = [
        (
            "CpabeEncryptTable",
            "cpabe_encrypt",
            [("CIPHERTEXT", "cpabe_encrypt_ciphertext_sizes")],
        ),
        (
            "CpabeDecryptTable",
            "cpabe_decrypt",
            [("STORED KEY", "cpabe_decrypt_stored_key_sizes")],
        ),
        (
            "RsaSubscribersEncryptTable",
            "subscriber_encrypt",
            [
                ("CIPHERTEXT", "subscriber_ciphertext_sizes"),
                ("CIPHERTEXT (TOTAL)", "subscriber_total_ciphertext_sizes"),
            ],
        ),
        (
            "RsaKeyBitsEncryptTable",
            "rsa_encrypt",
            [("CIPHERTEXT", "rsa_ciphertext_sizes")],
        ),
        ("RsaKeyBitsDecryptTable", "rsa_decrypt", []),
    ]
    tables = {}
    for placeholder, prefix, extra_columns in specifications:
        index_header, index_values = indexes[prefix.partition("_")[0]]
        highlighted = None
        if prefix == "rsa_decrypt":
            highlighted = [value == fixed_rsa_key_bits for value in rsa_key_sizes]
        tables[placeholder] = _build_optional_latency_table(
            index_header,
            index_values,
            scope[f"{prefix}_latency_means"],
            scope[f"{prefix}_latency_cis"],
            [
                (header, scope[value_name], _format_byte_size)
                for header, value_name in extra_columns
            ],
            scope[f"{prefix}_iterations"],
            scope[f"{prefix}_throttled"],
            runs,
            highlighted,
        )
    return tables


def _build_rsa_keygen_table(scope: dict[str, Any], rsa_key_sizes: list[int]) -> str:
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
        scope["keygen_medians"],
        scope["keygen_minimums"],
        scope["keygen_maximums"],
        scope["keygen_iqrs"],
        scope["keygen_stored_key_sizes"],
        scope["keygen_sample_counts"],
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
        scope["keygen_throttled"],
        thermal_header="THERMAL",
    )


def _build_peak_memory_table(
    index_header: str,
    index_values: list[int],
    encrypt_means: list[float],
    encrypt_cis: list[float],
    decrypt_values: list[str],
    sample_counts: list[int],
) -> str:
    return build_html_table(
        [index_header, "ENCRYPT (MB)", "DECRYPT (MB)", "n"],
        _rows_from_columns(
            [
                [str(value) for value in index_values],
                _mean_ci_column(encrypt_means, encrypt_cis),
                decrypt_values,
                [str(value) for value in sample_counts],
            ]
        ),
    )


def _build_attribute_memory_tables(
    scope: dict[str, Any],
    attribute_counts: list[int],
    subscriber_counts: list[int],
    rsa_key_sizes: list[int],
) -> dict[str, str]:
    specifications = [
        (
            "PeakMemoryCpabeTable",
            "ATTRIBUTES",
            attribute_counts,
            "cpabe_memory",
            False,
        ),
        (
            "PeakMemoryRsaKeyBitsTable",
            "KEY BITS",
            rsa_key_sizes,
            "rsa_memory",
            False,
        ),
        (
            "PeakMemoryRsaSubscribersTable",
            "SUBSCRIBERS",
            subscriber_counts,
            "subscriber_memory",
            True,
        ),
    ]
    tables = {}
    for placeholder, header, values, prefix, constant_decrypt in specifications:
        if constant_decrypt:
            mean = scope[f"{prefix}_decrypt_mean"]
            ci = scope[f"{prefix}_decrypt_ci"]
            decrypt_value = (
                NOT_AVAILABLE
                if mean is None or ci is None
                else format_mean_with_ci(mean, ci)
            )
            decrypt_values = [decrypt_value] * len(values)
        else:
            decrypt_values = _mean_ci_column(
                scope[f"{prefix}_decrypt_means"], scope[f"{prefix}_decrypt_cis"]
            )
        tables[placeholder] = _build_peak_memory_table(
            header,
            values,
            scope[f"{prefix}_encrypt_means"],
            scope[f"{prefix}_encrypt_cis"],
            decrypt_values,
            scope[f"{prefix}_sample_counts"],
        )
    return tables


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
    scope: dict[str, Any],
    attribute_counts: list[int],
    subscriber_counts: list[int],
    rsa_key_sizes: list[int],
) -> str:
    specifications = [
        ("CP-ABE Encrypt", attribute_counts, "attributes", "cpabe_encrypt"),
        ("CP-ABE Decrypt", attribute_counts, "attributes", "cpabe_decrypt"),
        (
            "RSA Subscribers Encrypt",
            subscriber_counts,
            "subscribers",
            "subscriber_encrypt",
        ),
        ("RSA Key Size Encrypt", rsa_key_sizes, "key bits", "rsa_encrypt"),
        ("RSA Key Size Decrypt", rsa_key_sizes, "key bits", "rsa_decrypt"),
    ]
    items = []
    for label, counts, unit, prefix in specifications:
        change = format_peak_memory_change(
            scope[f"{prefix}_memory_first"],
            scope[f"{prefix}_memory_last"],
            scope[f"{prefix}_memory_absolute_change"],
            scope[f"{prefix}_memory_percent_change"],
        )
        items.append(
            f'<span class="delta-item"><strong>{label}</strong> '
            f"{counts[0]} &rarr; {counts[-1]} {unit} &middot; {change}</span>"
        )
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


def format_optional_number(
    value: float | None, decimals: int = 0, truncate: bool = False
) -> str:
    if value is None:
        return NOT_AVAILABLE

    if truncate:
        return f"{int(value):,}"

    return f"{value:,.{decimals}f}"


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
        **_build_attribute_timing_tables(
            locals(),
            attribute_counts,
            subscriber_counts,
            rsa_key_sizes,
            fixed_rsa_key_bits,
            timing_runs,
        ),
        "RsaKeyBitsKeygenTable": _build_rsa_keygen_table(locals(), rsa_key_sizes),
        "BaselineRss": f"{format_mean_with_ci(baseline_memory_mean, baseline_memory_ci)} MB",
        **_build_attribute_memory_tables(
            locals(), attribute_counts, subscriber_counts, rsa_key_sizes
        ),
        "PeakMemoryDeltas": build_peak_memory_deltas(
            locals(), attribute_counts, subscriber_counts, rsa_key_sizes
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
        "CpabeEncryptRSquared": format_optional_number(cpabe_encrypt_r_squared, 6),
        "CpabeDecryptRSquared": format_optional_number(cpabe_decrypt_r_squared, 6),
        "CpabeCiphertextRSquared": format_optional_number(
            cpabe_ciphertext_r_squared, 6
        ),
        "CpabeStoredKeyRSquared": format_optional_number(cpabe_stored_key_r_squared, 6),
        "RsaSubscriberEncryptSlope": format_slope(
            subscriber_encrypt_slope,
            subscriber_encrypt_slope_ci,
            "µs",
            decimals=2,
        ),
        "RsaSubscriberEncryptRSquared": format_optional_number(
            subscriber_encrypt_r_squared, 6
        ),
        "RsaSubscriberTotalCiphertextSlope": (
            NOT_AVAILABLE
            if bytes_per_subscriber is None
            else f"+{bytes_per_subscriber:.0f} B"
        ),
        "BytesCrossoverLow": format_optional_number(bytes_crossover_low, 1),
        "BytesCrossoverHigh": format_optional_number(bytes_crossover_high, 1),
        "BytesRsaThroughMin": format_optional_number(
            bytes_crossover_low, truncate=True
        ),
        "BytesRsaThroughMax": format_optional_number(
            bytes_crossover_high, truncate=True
        ),
        "EncryptCpuCrossoverLow": format_optional_number(latency_crossover_low),
        "EncryptCpuCrossoverHigh": format_optional_number(latency_crossover_high),
        "CpuRsaThroughMin": format_optional_number(
            latency_crossover_low, truncate=True
        ),
        "CpuRsaThroughMax": format_optional_number(
            latency_crossover_high, truncate=True
        ),
        "DecryptPenaltyMin": format_optional_number(decrypt_penalty_low, 1),
        "DecryptPenaltyMax": format_optional_number(decrypt_penalty_high, 1),
    }

    build_html_report(template_path, report_path, placeholders)
