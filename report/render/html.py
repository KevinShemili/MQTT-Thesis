from typing import Any, Sequence

from .formatting import *

CONFIDENCE_LEVEL = "95%"

# A row is marked where the Raspberry Pi firmware throttled the clock while that case was
# being measured, which makes the measurement a pessimistic bound rather than an invalid
# one.
THERMAL_MARK = "&#9888;"

# A row the rest of the report is quoted against, ex. the fixed RSA key size the
# cross-schema comparisons use, is marked so it can be found among the swept values
REFERENCE_ROW_CLASS = "reference-row"
THERMAL_FLAGGED_NOTE = (
    "Marks a case measured while the Raspberry Pi firmware was throttled."
)
THERMAL_CLEAN_NOTE = "No throttling occurred while these cases were measured."


def build_html_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    throttled: list[bool] | None = None,
    highlighted: list[bool] | None = None,
) -> str:

    lines = ["<table>", "<thead>", "<tr>"]
    lines += [f"<th>{header}</th>" for header in headers]
    lines += ["</tr>", "</thead>", "<tbody>"]

    for index, row in enumerate(rows):

        if highlighted is not None and highlighted[index]:
            lines.append(f'<tr class="{REFERENCE_ROW_CLASS}">')
        else:
            lines.append("<tr>")

        for column_index, cell in enumerate(row):
            if column_index == 0 and throttled is not None and throttled[index]:
                cell = (
                    f'{cell}<span class="thermal-mark" '
                    f'title="Thermally throttled">{THERMAL_MARK}</span>'
                )
            lines.append(f"<td>{cell}</td>")

        lines.append("</tr>")

    lines += ["</tbody>", "</table>"]

    return "\n".join(lines)


def build_thermal_legend(throttled: Sequence[bool]) -> str:
    if any(throttled):
        return (
            '<div class="thermal-status thermal-status-flagged">'
            f'<span class="thermal-symbol">{THERMAL_MARK}</span>'
            f"<span>{THERMAL_FLAGGED_NOTE}</span>"
            "</div>"
        )

    return f'<div class="thermal-status">{THERMAL_CLEAN_NOTE}</div>'


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
    payload_sizes: list[int],
    cases: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    headers = [
        "Payload",
        "Latency (ns/op)",
    ]
    specifications = [
        ("EncryptAesTable", ("AES-GCM", "Encrypt")),
        ("EncryptAsconTable", ("ASCON", "Encrypt")),
        ("DecryptAesTable", ("AES-GCM", "Decrypt")),
        ("DecryptAsconTable", ("ASCON", "Decrypt")),
    ]
    tables = {}
    for placeholder, case in specifications:
        values = cases[case]
        tables[placeholder] = _build_data_table(
            headers,
            [
                [format_byte_size(value, compact=True) for value in payload_sizes],
                _mean_ci_column(
                    values["latency_means"],
                    values["latency_cis"],
                ),
            ],
            values["timing_throttled"],
        )

    return tables


def _build_aes_ascon_memory_tables(
    payload_sizes: list[int],
    memory: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    specifications = [
        ("EncryptAesMemoryTable", ("AES-GCM", "Encrypt")),
        ("EncryptAsconMemoryTable", ("ASCON", "Encrypt")),
        ("DecryptAesMemoryTable", ("AES-GCM", "Decrypt")),
        ("DecryptAsconMemoryTable", ("ASCON", "Decrypt")),
    ]
    tables = {}
    for placeholder, case in specifications:
        values = memory[case]
        tables[placeholder] = _build_data_table(
            ["Payload", "Peak RSS (MB)"],
            [
                [format_byte_size(value, compact=True) for value in payload_sizes],
                _mean_ci_column(values["means"], values["cis"]),
            ],
        )

    return tables


def _build_aes_ascon_energy_tables(
    payload_sizes: list[int],
    cases: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    headers = ["Payload", "Energy (µJ/op)"]
    specifications = [
        ("EncryptAesEnergyTable", ("AES-GCM", "Encrypt")),
        ("EncryptAsconEnergyTable", ("ASCON", "Encrypt")),
        ("DecryptAesEnergyTable", ("AES-GCM", "Decrypt")),
        ("DecryptAsconEnergyTable", ("ASCON", "Decrypt")),
    ]
    tables = {}
    for placeholder, case in specifications:
        values = cases[case]
        tables[placeholder] = _build_data_table(
            headers,
            [
                [format_byte_size(value, compact=True) for value in payload_sizes],
                _mean_ci_column(
                    values["energy_means"],
                    values["energy_cis"],
                ),
            ],
            values["energy_throttled"],
        )

    return tables


def write_aes_ascon_report(
    report_data: dict[str, Any],
    template_path: str,
    report_path: str,
) -> None:
    payload_sizes = report_data["payload_sizes"]
    cases = report_data["cases"]
    plots = report_data["plots"]
    interpretations = report_data["interpretations"]
    latency_speedup = interpretations["latency_speedup"]
    energy_reduction = interpretations["energy_reduction"]
    timing_throttled = [
        flag for values in cases.values() for flag in values["timing_throttled"]
    ]
    energy_throttled = [
        flag for values in cases.values() for flag in values["energy_throttled"]
    ]

    placeholders = {
        "RunCount": str(report_data["runs"]),
        "ConfidenceLevel": CONFIDENCE_LEVEL,
        **_build_aes_ascon_tables(payload_sizes, cases),
        **_build_aes_ascon_energy_tables(payload_sizes, cases),
        **_build_aes_ascon_memory_tables(payload_sizes, report_data["memory"]),
        "TimingThermalLegend": build_thermal_legend(timing_throttled),
        "EnergyThermalLegend": build_thermal_legend(energy_throttled),
        "EnergyBaseline": f'{format_mean_with_ci(report_data["energy_baseline_mean"], report_data["energy_baseline_ci"])} J',
        "EnergyBaselineDuration": f'{report_data["energy_baseline_duration"]:g}',
        "BaselineRss": f'{format_mean_with_ci(report_data["baseline_memory_mean"], report_data["baseline_memory_ci"])} MB',
        "EnergyWindowStart": f'{report_data["energy_window_start"]:g}',
        "EnergyWindowEnd": f'{report_data["energy_window_end"]:g}',
        "LatencyPlot": plots["latency"],
        "LatencySpeedupPlot": plots["latency_speedup"],
        "LatencySpeedupEncryptMin": f'{latency_speedup["encrypt_min"]:.1f}',
        "LatencySpeedupEncryptMax": f'{latency_speedup["encrypt_max"]:.1f}',
        "LatencySpeedupDecryptMin": f'{latency_speedup["decrypt_min"]:.1f}',
        "LatencySpeedupDecryptMax": f'{latency_speedup["decrypt_max"]:.1f}',
        "ThroughputPlot": plots["throughput"],
        "EnergyPlot": plots["energy"],
        "EnergyReductionPlot": plots["energy_reduction"],
        "EnergyReductionEncryptMin": f'{energy_reduction["encrypt_min"]:.1f}',
        "EnergyReductionEncryptMax": f'{energy_reduction["encrypt_max"]:.1f}',
        "EnergyReductionDecryptMin": f'{energy_reduction["decrypt_min"]:.1f}',
        "EnergyReductionDecryptMax": f'{energy_reduction["decrypt_max"]:.1f}',
        "MemoryPlot": plots["memory"],
    }

    build_html_report(template_path, report_path, placeholders)


def _build_json_cbor_timing_tables(
    attribute_counts: list[int],
    cases: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    headers = [
        "Attributes",
        "Latency (µs/op)",
    ]
    specifications = [
        ("SerializeJsonTable", ("JSON", "Serialize")),
        ("SerializeCborTable", ("CBOR", "Serialize")),
        ("SerializeCborKeyAsIntTable", ("CBORKeyAsInt", "Serialize")),
        ("DeserializeJsonTable", ("JSON", "Deserialize")),
        ("DeserializeCborTable", ("CBOR", "Deserialize")),
        ("DeserializeCborKeyAsIntTable", ("CBORKeyAsInt", "Deserialize")),
    ]
    tables = {}
    for placeholder, case in specifications:
        values = cases[case]
        tables[placeholder] = _build_data_table(
            headers,
            [
                [str(value) for value in attribute_counts],
                _mean_ci_column(
                    values["latency_means"],
                    values["latency_cis"],
                ),
            ],
            values["timing_throttled"],
        )

    return tables


def _build_json_cbor_size_tables(
    attribute_counts: list[int],
    sizes: dict[str, list[int]],
) -> dict[str, str]:
    specifications = [
        ("JsonSizeTable", "JSON"),
        ("CborSizeTable", "CBOR"),
        ("CborKeyAsIntSizeTable", "CBORKeyAsInt"),
    ]
    tables = {}
    for placeholder, format_name in specifications:
        tables[placeholder] = _build_data_table(
            ["Attributes", "Envelope Size (B)"],
            [
                [str(value) for value in attribute_counts],
                [f"{value:,}" for value in sizes[format_name]],
            ],
        )

    return tables


def _build_json_cbor_energy_tables(
    attribute_counts: list[int],
    cases: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    headers = ["Attributes", "Energy (µJ/op)"]
    specifications = [
        ("SerializeJsonEnergyTable", ("JSON", "Serialize")),
        ("SerializeCborEnergyTable", ("CBOR", "Serialize")),
        ("SerializeCborKeyAsIntEnergyTable", ("CBORKeyAsInt", "Serialize")),
        ("DeserializeJsonEnergyTable", ("JSON", "Deserialize")),
        ("DeserializeCborEnergyTable", ("CBOR", "Deserialize")),
        ("DeserializeCborKeyAsIntEnergyTable", ("CBORKeyAsInt", "Deserialize")),
    ]
    tables = {}
    for placeholder, case in specifications:
        values = cases[case]
        tables[placeholder] = _build_data_table(
            headers,
            [
                [str(value) for value in attribute_counts],
                _mean_ci_column(
                    values["energy_means"],
                    values["energy_cis"],
                ),
            ],
            values["energy_throttled"],
        )

    return tables


def write_json_cbor_report(
    report_data: dict[str, Any],
    template_path: str,
    report_path: str,
) -> None:
    attribute_counts = report_data["attribute_counts"]
    cases = report_data["cases"]
    plots = report_data["plots"]
    interpretations = report_data["interpretations"]
    latency_speedup = interpretations["latency_speedup"]
    size_reduction = interpretations["size_reduction"]
    integer_key_size_reduction = interpretations["integer_key_size_reduction"]
    energy_reduction = interpretations["energy_reduction"]
    timing_throttled = [
        flag for values in cases.values() for flag in values["timing_throttled"]
    ]
    energy_throttled = [
        flag for values in cases.values() for flag in values["energy_throttled"]
    ]

    placeholders = {
        "RunCount": str(report_data["runs"]),
        "ConfidenceLevel": CONFIDENCE_LEVEL,
        **_build_json_cbor_timing_tables(attribute_counts, cases),
        **_build_json_cbor_size_tables(attribute_counts, report_data["sizes"]),
        **_build_json_cbor_energy_tables(attribute_counts, cases),
        "TimingThermalLegend": build_thermal_legend(timing_throttled),
        "EnergyThermalLegend": build_thermal_legend(energy_throttled),
        "EnergyBaseline": f'{format_mean_with_ci(report_data["energy_baseline_mean"], report_data["energy_baseline_ci"])} J',
        "EnergyBaselineDuration": f'{report_data["energy_baseline_duration"]:g}',
        "EnergyWindowStart": f'{report_data["energy_window_start"]:g}',
        "EnergyWindowEnd": f'{report_data["energy_window_end"]:g}',
        "LatencyPlot": plots["latency"],
        "LatencySpeedupPlot": plots["latency_speedup"],
        "LatencySpeedupSerializeCborMin": f'{latency_speedup["serialize_cbor_min"]:.1f}',
        "LatencySpeedupSerializeCborMax": f'{latency_speedup["serialize_cbor_max"]:.1f}',
        "LatencySpeedupSerializeCborIntMin": f'{latency_speedup["serialize_cbor_int_min"]:.1f}',
        "LatencySpeedupSerializeCborIntMax": f'{latency_speedup["serialize_cbor_int_max"]:.1f}',
        "LatencySpeedupDeserializeCborMin": f'{latency_speedup["deserialize_cbor_min"]:.1f}',
        "LatencySpeedupDeserializeCborMax": f'{latency_speedup["deserialize_cbor_max"]:.1f}',
        "LatencySpeedupDeserializeCborIntMin": f'{latency_speedup["deserialize_cbor_int_min"]:.1f}',
        "LatencySpeedupDeserializeCborIntMax": f'{latency_speedup["deserialize_cbor_int_max"]:.1f}',
        "SizePlot": plots["size"],
        "SizeReductionPlot": plots["size_reduction"],
        "SizeReductionCborMin": f'{size_reduction["cbor_min"]:.1f}',
        "SizeReductionCborMax": f'{size_reduction["cbor_max"]:.1f}',
        "SizeReductionCborIntMin": f'{size_reduction["cbor_int_min"]:.1f}',
        "SizeReductionCborIntMax": f'{size_reduction["cbor_int_max"]:.1f}',
        "IntegerKeySizeSavingBytes": f'{integer_key_size_reduction["additional_bytes"]:,}',
        "IntegerKeySizeReductionFirst": f'{integer_key_size_reduction["first"]:.2f}',
        "IntegerKeySizeReductionLast": f'{integer_key_size_reduction["last"]:.2f}',
        "EnergyPlot": plots["energy"],
        "EnergyReductionPlot": plots["energy_reduction"],
        "EnergyReductionSerializeCborMin": f'{energy_reduction["serialize_cbor_min"]:.1f}',
        "EnergyReductionSerializeCborMax": f'{energy_reduction["serialize_cbor_max"]:.1f}',
        "EnergyReductionSerializeCborIntMin": f'{energy_reduction["serialize_cbor_int_min"]:.1f}',
        "EnergyReductionSerializeCborIntMax": f'{energy_reduction["serialize_cbor_int_max"]:.1f}',
        "EnergyReductionDeserializeCborMin": f'{energy_reduction["deserialize_cbor_min"]:.1f}',
        "EnergyReductionDeserializeCborMax": f'{energy_reduction["deserialize_cbor_max"]:.1f}',
        "EnergyReductionDeserializeCborIntMin": f'{energy_reduction["deserialize_cbor_int_min"]:.1f}',
        "EnergyReductionDeserializeCborIntMax": f'{energy_reduction["deserialize_cbor_int_max"]:.1f}',
    }

    build_html_report(template_path, report_path, placeholders)


def _build_payload_scaling_tables(
    payload_sizes: list[int],
    cases: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    headers = [
        "Payload",
        "Latency (µs/op)",
    ]
    specifications = [
        ("EncryptPskTable", ("PSK", "Encrypt")),
        ("EncryptRsaTable", ("RSA", "Encrypt")),
        ("EncryptCpabeTable", ("CPABE", "Encrypt")),
        ("DecryptPskTable", ("PSK", "Decrypt")),
        ("DecryptRsaTable", ("RSA", "Decrypt")),
        ("DecryptCpabeTable", ("CPABE", "Decrypt")),
    ]
    tables = {}
    for placeholder, case in specifications:
        values = cases[case]
        tables[placeholder] = _build_data_table(
            headers,
            [
                [format_byte_size(value) for value in payload_sizes],
                _mean_ci_column(
                    values["latency_means"],
                    values["latency_cis"],
                ),
            ],
            values["timing_throttled"],
        )

    return tables


def _build_payload_scaling_wire_size_table(
    payload_sizes: list[int],
    wire_sizes: dict[str, list[float]],
) -> str:
    return _build_data_table(
        ["Payload", "PSK Wire Size", "RSA Wire Size", "CP-ABE Wire Size"],
        [
            [format_byte_size(value) for value in payload_sizes],
            [format_byte_size(round(value)) for value in wire_sizes["PSK"]],
            [format_byte_size(round(value)) for value in wire_sizes["RSA"]],
            [format_byte_size(round(value)) for value in wire_sizes["CPABE"]],
        ],
    )


def _build_payload_scaling_energy_tables(
    payload_sizes: list[int],
    cases: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    headers = ["Raw Size", "Energy (µJ/op)"]
    specifications = [
        ("EncryptPskEnergyTable", ("PSK", "Encrypt")),
        ("EncryptRsaEnergyTable", ("RSA", "Encrypt")),
        ("EncryptCpabeEnergyTable", ("CPABE", "Encrypt")),
        ("DecryptPskEnergyTable", ("PSK", "Decrypt")),
        ("DecryptRsaEnergyTable", ("RSA", "Decrypt")),
        ("DecryptCpabeEnergyTable", ("CPABE", "Decrypt")),
    ]
    tables = {}
    for placeholder, case in specifications:
        values = cases[case]
        tables[placeholder] = _build_data_table(
            headers,
            [
                [format_byte_size(value) for value in payload_sizes],
                _mean_ci_column(
                    values["energy_means"],
                    values["energy_cis"],
                ),
            ],
            values["energy_throttled"],
        )

    return tables


def _build_payload_scaling_memory_tables(
    payload_sizes: list[int],
    memory: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    specifications = [
        ("EncryptPskMemoryTable", ("PSK", "Encrypt")),
        ("EncryptRsaMemoryTable", ("RSA", "Encrypt")),
        ("EncryptCpabeMemoryTable", ("CPABE", "Encrypt")),
        ("DecryptPskMemoryTable", ("PSK", "Decrypt")),
        ("DecryptRsaMemoryTable", ("RSA", "Decrypt")),
        ("DecryptCpabeMemoryTable", ("CPABE", "Decrypt")),
    ]
    tables = {}
    for placeholder, case in specifications:
        values = memory[case]
        tables[placeholder] = _build_data_table(
            ["Payload", "Peak RSS (MB)"],
            [
                [format_byte_size(value) for value in payload_sizes],
                _mean_ci_column(values["means"], values["cis"]),
            ],
        )

    return tables


def write_payload_scaling_report(
    report_data: dict[str, Any],
    template_path: str,
    report_path: str,
) -> None:
    payload_sizes = report_data["payload_sizes"]
    cases = report_data["cases"]
    plots = report_data["plots"]
    timing_throttled = [
        flag for values in cases.values() for flag in values["timing_throttled"]
    ]
    energy_throttled = [
        flag for values in cases.values() for flag in values["energy_throttled"]
    ]

    placeholders = {
        "RunCount": str(report_data["runs"]),
        "ConfidenceLevel": CONFIDENCE_LEVEL,
        **_build_payload_scaling_tables(
            payload_sizes,
            cases,
        ),
        "WireSizeTable": _build_payload_scaling_wire_size_table(
            payload_sizes,
            report_data["wire_sizes"],
        ),
        **_build_payload_scaling_energy_tables(payload_sizes, cases),
        **_build_payload_scaling_memory_tables(
            payload_sizes,
            report_data["memory"],
        ),
        "TimingThermalLegend": build_thermal_legend(timing_throttled),
        "EnergyThermalLegend": build_thermal_legend(energy_throttled),
        "EnergyBaseline": f'{format_mean_with_ci(report_data["energy_baseline_mean"], report_data["energy_baseline_ci"])} J',
        "EnergyBaselineDuration": f'{report_data["energy_baseline_duration"]:g}',
        "BaselineRss": f'{format_mean_with_ci(report_data["baseline_memory_mean"], report_data["baseline_memory_ci"])} MB',
        "EnergyWindowStart": f'{report_data["energy_window_start"]:g}',
        "EnergyWindowEnd": f'{report_data["energy_window_end"]:g}',
        "LatencyPlot": plots["latency"],
        "LatencyOverheadSharePlot": plots["latency_overhead_share"],
        "ThroughputPlot": plots["throughput"],
        "WireExpansionPlot": plots["wire_expansion"],
        "EnergyPlot": plots["energy"],
        "AdditionalEnergyPlot": plots["additional_energy"],
        "MemoryPlot": plots["memory"],
    }

    build_html_report(template_path, report_path, placeholders)


FANOUT_LARGEST_DIAMETER_PX = 168.0
FANOUT_SMALLEST_DIAMETER_PX = 22.0


def _format_byte_size(value: float) -> str:
    return format_byte_size(round(value))


def format_peak_memory_change(
    first: float,
    last: float,
    absolute_change: float,
    percent_change: float,
) -> str:
    return (
        f"{first:,.2f} &rarr; {last:,.2f} MB &middot; "
        f"{absolute_change:+,.2f} MB ({percent_change:+,.1f}%)"
    )


def build_rsa_circle_visualization(
    single_bytes: float,
    total_bytes: float,
    multiplier: float,
) -> dict[str, str]:
    def circle_style(diameter_px: float) -> str:
        return f'style="width:{diameter_px:.0f}px;height:{diameter_px:.0f}px;"'

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


def build_plot_frame(filename: str) -> str:
    return f'<img src="{filename}">'


def format_slope(
    slope: float,
    slope_ci: float,
    unit: str,
    decimals: int = 0,
    thousands: bool = True,
) -> str:
    return (
        f"+{format_mean_with_ci(slope, slope_ci, decimals=decimals, thousands=thousands)} "
        f"{unit}"
    )


def _build_attribute_timing_table(
    index_header: str,
    index_values: list[int],
    values: dict,
    runs: int,
    extra_columns: list[tuple[str, str]],
    highlighted: list[bool] | None = None,
) -> str:
    headers = [index_header, "LATENCY (µs/op)"]
    columns = [
        [str(value) for value in index_values],
        _mean_ci_column(values["latency_means"], values["latency_cis"]),
    ]
    for header, name in extra_columns:
        headers.append(header)
        columns.append([_format_byte_size(value) for value in values[name]])
    headers.append(f"ITERS (Σ{runs} RUNS)")
    columns.append([f"{value:,}" for value in values["iterations"]])
    return build_html_table(
        headers,
        _rows_from_columns(columns),
        values["timing_throttled"],
        highlighted=highlighted,
    )


def _build_attribute_timing_report_tables(
    report_data: dict[str, Any],
) -> dict[str, str]:
    cases = report_data["cases"]
    attributes = report_data["attribute_counts"]
    subscribers = report_data["subscriber_counts"]
    rsa_key_bits = report_data["rsa_key_bits"]
    runs = report_data["runs"]

    return {
        "CpabeEncryptTable": _build_attribute_timing_table(
            "ATTRIBUTES",
            attributes,
            cases[("CPABEAttributes", "Encrypt")],
            runs,
            [("CIPHERTEXT", "ciphertext_means")],
        ),
        "CpabeDecryptTable": _build_attribute_timing_table(
            "ATTRIBUTES",
            attributes,
            cases[("CPABEAttributes", "Decrypt")],
            runs,
            [("STORED KEY", "stored_key_means")],
        ),
        "RsaSubscribersEncryptTable": _build_attribute_timing_table(
            "SUBSCRIBERS",
            subscribers,
            cases[("RSASubscribers", "Encrypt")],
            runs,
            [
                ("CIPHERTEXT", "ciphertext_means"),
                ("CIPHERTEXT (TOTAL)", "total_ciphertext_means"),
            ],
        ),
        "RsaKeyBitsEncryptTable": _build_attribute_timing_table(
            "KEY BITS",
            rsa_key_bits,
            cases[("RSAKeyBits", "Encrypt")],
            runs,
            [("CIPHERTEXT", "ciphertext_means")],
        ),
        "RsaKeyBitsDecryptTable": _build_attribute_timing_table(
            "KEY BITS",
            rsa_key_bits,
            cases[("RSAKeyBits", "Decrypt")],
            runs,
            [],
            [value == report_data["fixed_rsa_key_bits"] for value in rsa_key_bits],
        ),
    }


def _build_attribute_keygen_table(report_data: dict[str, Any]) -> str:
    values = report_data["cases"][("RSAKeyBits", "KeyGen")]
    rows = []
    for index, rsa_key_bits in enumerate(report_data["rsa_key_bits"]):
        rows.append(
            [
                str(rsa_key_bits),
                f'{values["medians"][index]:,.2f}',
                f'{values["minimums"][index]:,.2f}',
                f'{values["maximums"][index]:,.2f}',
                f'{values["iqrs"][index]:,.2f}',
                _format_byte_size(values["stored_key_means"][index]),
                str(values["sample_counts"][index]),
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
        values["timing_throttled"],
    )


def _build_attribute_energy_tables(report_data: dict[str, Any]) -> dict[str, str]:
    cases = report_data["cases"]
    specifications = (
        (
            "CpabeEncryptEnergyTable",
            "ATTRIBUTES",
            report_data["attribute_counts"],
            "CPABEAttributes",
            "Encrypt",
        ),
        (
            "CpabeDecryptEnergyTable",
            "ATTRIBUTES",
            report_data["attribute_counts"],
            "CPABEAttributes",
            "Decrypt",
        ),
        (
            "RsaSubscribersEncryptEnergyTable",
            "SUBSCRIBERS",
            report_data["subscriber_counts"],
            "RSASubscribers",
            "Encrypt",
        ),
        (
            "RsaKeyBitsEncryptEnergyTable",
            "KEY BITS",
            report_data["rsa_key_bits"],
            "RSAKeyBits",
            "Encrypt",
        ),
        (
            "RsaKeyBitsDecryptEnergyTable",
            "KEY BITS",
            report_data["rsa_key_bits"],
            "RSAKeyBits",
            "Decrypt",
        ),
        (
            "RsaKeyBitsKeygenEnergyTable",
            "KEY BITS",
            report_data["rsa_key_bits"],
            "RSAKeyBits",
            "KeyGen",
        ),
    )
    tables = {}
    for placeholder, header, parameter_values, algorithm, operation in specifications:
        values = cases[(algorithm, operation)]
        tables[placeholder] = _build_data_table(
            [header, "ENERGY (µJ/op)"],
            [
                [str(parameter_value) for parameter_value in parameter_values],
                _mean_ci_column(values["energy_means"], values["energy_cis"]),
            ],
            values["energy_throttled"],
        )
    return tables


def _build_attribute_memory_report_tables(
    report_data: dict[str, Any],
) -> dict[str, str]:
    memory = report_data["memory"]

    def table(index_header, index_values, encrypt, decrypt):
        return build_html_table(
            [index_header, "ENCRYPT (MB)", "DECRYPT (MB)", "n"],
            _rows_from_columns(
                [
                    [str(value) for value in index_values],
                    _mean_ci_column(encrypt["means"], encrypt["cis"]),
                    _mean_ci_column(decrypt["means"], decrypt["cis"]),
                    [str(value) for value in encrypt["sample_counts"]],
                ]
            ),
        )

    cpabe_encrypt = memory[("CPABEAttributes", "Encrypt")]
    cpabe_decrypt = memory[("CPABEAttributes", "Decrypt")]
    rsa_encrypt = memory[("RSAKeyBits", "Encrypt")]
    rsa_decrypt = memory[("RSAKeyBits", "Decrypt")]
    subscriber_encrypt = memory[("RSASubscribers", "Encrypt")]
    decrypt_reference = format_mean_with_ci(
        report_data["fixed_rsa_decrypt_memory"],
        report_data["fixed_rsa_decrypt_memory_ci"],
    )
    subscriber_rows = _rows_from_columns(
        [
            [str(value) for value in report_data["subscriber_counts"]],
            _mean_ci_column(subscriber_encrypt["means"], subscriber_encrypt["cis"]),
            [decrypt_reference] * len(report_data["subscriber_counts"]),
            [str(value) for value in subscriber_encrypt["sample_counts"]],
        ]
    )

    return {
        "PeakMemoryCpabeTable": table(
            "ATTRIBUTES", report_data["attribute_counts"], cpabe_encrypt, cpabe_decrypt
        ),
        "PeakMemoryRsaSubscribersTable": build_html_table(
            ["SUBSCRIBERS", "ENCRYPT (MB)", "DECRYPT (MB)", "n"], subscriber_rows
        ),
        "PeakMemoryRsaKeyBitsTable": table(
            "KEY BITS", report_data["rsa_key_bits"], rsa_encrypt, rsa_decrypt
        ),
    }


def _build_memory_delta_strip(report_data: dict[str, Any]) -> str:
    labels = (
        (
            "CP-ABE Encrypt",
            report_data["attribute_counts"],
            "attributes",
            "cpabe_encrypt",
        ),
        (
            "CP-ABE Decrypt",
            report_data["attribute_counts"],
            "attributes",
            "cpabe_decrypt",
        ),
        (
            "RSA Subscribers Encrypt",
            report_data["subscriber_counts"],
            "subscribers",
            "subscriber_encrypt",
        ),
        (
            "RSA Key Size Encrypt",
            report_data["rsa_key_bits"],
            "key bits",
            "rsa_encrypt",
        ),
        (
            "RSA Key Size Decrypt",
            report_data["rsa_key_bits"],
            "key bits",
            "rsa_decrypt",
        ),
    )
    items = []
    for label, values, unit, name in labels:
        change = report_data["memory_changes"][name]
        text = format_peak_memory_change(
            change["first"],
            change["last"],
            change["absolute_change"],
            change["percent_change"],
        )
        items.append(
            f'<span class="delta-item"><strong>{label}</strong> '
            f"{values[0]} &rarr; {values[-1]} {unit} &middot; {text}</span>"
        )
    return f'<div class="delta-strip">{"".join(items)}</div>'


def write_attribute_key_scaling_report(
    report_data: dict[str, Any],
    template_path: str,
    report_path: str,
) -> None:
    comparisons = report_data["comparisons"]
    regressions = report_data["regressions"]
    plots = report_data["plots"]
    attributes = report_data["attribute_counts"]
    subscribers = report_data["subscriber_counts"]
    timing_throttled = [
        flag
        for values in report_data["cases"].values()
        for flag in values["timing_throttled"]
    ]
    energy_throttled = [
        flag
        for values in report_data["cases"].values()
        for flag in values["energy_throttled"]
    ]

    fanout = build_rsa_circle_visualization(
        comparisons["bytes_per_subscriber"],
        report_data["cases"][("RSASubscribers", "Encrypt")]["total_ciphertext_means"][
            -1
        ],
        subscribers[-1],
    )
    placeholders = {
        **build_html_generic_data(
            report_data["runs"],
            report_data["t_multiplier"],
            report_data["total_iterations"],
        ),
        **fanout,
        **_build_attribute_timing_report_tables(report_data),
        "RsaKeyBitsKeygenTable": _build_attribute_keygen_table(report_data),
        **_build_attribute_energy_tables(report_data),
        **_build_attribute_memory_report_tables(report_data),
        "TimingThermalLegend": build_thermal_legend(timing_throttled),
        "EnergyThermalLegend": build_thermal_legend(energy_throttled),
        "EnergyBaseline": f'{format_mean_with_ci(report_data["energy_baseline_mean"], report_data["energy_baseline_ci"])} J',
        "EnergyBaselineDuration": f'{report_data["energy_baseline_duration"]:g}',
        "PeakMemoryDeltas": _build_memory_delta_strip(report_data),
        "BaselineRss": f'{format_mean_with_ci(report_data["baseline_memory_mean"], report_data["baseline_memory_ci"])} MB',
        "MinAttributeLabel": format_attribute_label(attributes[0]),
        "MaxAttributeLabel": format_attribute_label(attributes[-1]),
        "MaxSubscriberCount": str(subscribers[-1]),
        "FixedRsaKeyBits": str(report_data["fixed_rsa_key_bits"]),
        "EnergyWindowStart": f'{report_data["energy_window_start"]:g}',
        "EnergyWindowEnd": f'{report_data["energy_window_end"]:g}',
        "CpabePlot": plots["cpabe"],
        "RsaSubscribersPlot": plots["rsa_subscribers"],
        "RsaKeyBitsPlot": plots["rsa_key_bits"],
        "EnergyPlot": plots["energy"],
        "BandwidthCrossoverFrame": build_plot_frame(plots["ciphertext_crossover"]),
        "EncryptCpuCrossoverFrame": build_plot_frame(plots["encrypt_crossover"]),
        "DecryptCpuComparisonFrame": build_plot_frame(plots["decrypt_comparison"]),
        "AsymmetryFrame": build_plot_frame(plots["asymmetry"]),
        "PeakMemoryFrame": build_plot_frame(plots["peak_memory"]),
        "RsaSubscriberTotalCiphertextSlope": f'+{comparisons["bytes_per_subscriber"]:.0f} B',
        "BytesCrossoverLow": f'{comparisons["bytes_crossover_low"]:,.1f}',
        "BytesCrossoverHigh": f'{comparisons["bytes_crossover_high"]:,.1f}',
        "BytesRsaThroughMin": f'{int(comparisons["bytes_crossover_low"]):,}',
        "BytesRsaThroughMax": f'{int(comparisons["bytes_crossover_high"]):,}',
        "EncryptCpuCrossoverLow": f'{comparisons["latency_crossover_low"]:,.0f}',
        "EncryptCpuCrossoverHigh": f'{comparisons["latency_crossover_high"]:,.0f}',
        "CpuRsaThroughMin": f'{int(comparisons["latency_crossover_low"]):,}',
        "CpuRsaThroughMax": f'{int(comparisons["latency_crossover_high"]):,}',
        "DecryptPenaltyMin": f'{comparisons["decrypt_penalty_low"]:,.1f}',
        "DecryptPenaltyMax": f'{comparisons["decrypt_penalty_high"]:,.1f}',
    }

    regression_placeholders = (
        ("CpabeEncrypt", "cpabe_encrypt", "µs", 0, True),
        ("CpabeDecrypt", "cpabe_decrypt", "µs", 0, True),
        ("CpabeCiphertext", "cpabe_ciphertext", "B", 0, False),
        ("CpabeStoredKey", "cpabe_stored_key", "B", 0, False),
        ("RsaSubscriberEncrypt", "subscriber_encrypt", "µs", 2, True),
    )
    for placeholder, name, unit, decimals, thousands in regression_placeholders:
        slope, _, r_squared, slope_ci = regressions[name]
        placeholders[f"{placeholder}Slope"] = format_slope(
            slope, slope_ci, unit, decimals=decimals, thousands=thousands
        )
        placeholders[f"{placeholder}RSquared"] = f"{r_squared:.6f}"

    build_html_report(template_path, report_path, placeholders)
