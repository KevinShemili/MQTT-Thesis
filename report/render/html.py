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


def _append_thermal_mark(cell: str) -> str:
    return (
        f'{cell}<span class="thermal-mark" '
        f'title="Thermally throttled">{THERMAL_MARK}</span>'
    )


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
                cell = _append_thermal_mark(cell)
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


def _mark_throttled_cells(cells: list[str], throttled: list[bool]) -> list[str]:
    return [
        _append_thermal_mark(cell) if is_throttled else cell
        for cell, is_throttled in zip(cells, throttled, strict=True)
    ]


def _byte_column(values: Sequence[int]) -> list[str]:
    return [f"{value:,} B" for value in values]


def _build_data_table(
    headers: list[str],
    columns: list[Sequence[str]],
    throttled: list[bool] | None = None,
) -> str:
    return build_html_table(headers, _rows_from_columns(columns), throttled)


def _build_aes_ascon_timing_tables(
    payload_sizes: list[int],
    cases: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    return {
        f"{operation}TimingTable": _build_aes_ascon_measurement_table(
            payload_sizes,
            cases,
            operation,
            "latency_means",
            "latency_cis",
            "timing_throttled",
        )
        for operation in ("Encrypt", "Decrypt")
    }


def _build_aes_ascon_measurement_table(
    payload_sizes: list[int],
    results: dict[tuple[str, str], dict[str, Any]],
    operation: str,
    mean_key: str,
    confidence_interval_key: str,
    throttled_key: str | None = None,
) -> str:
    columns = [_byte_column(payload_sizes)]

    for algorithm in ("AES-GCM", "ASCON"):
        values = results[(algorithm, operation)]
        cells = _mean_ci_column(
            values[mean_key],
            values[confidence_interval_key],
        )

        if throttled_key is not None:
            cells = _mark_throttled_cells(cells, values[throttled_key])

        columns.append(cells)

    return _build_data_table(
        ["Payload", "AES-GCM", "ASCON"],
        columns,
    )


def _build_aes_ascon_memory_tables(
    payload_sizes: list[int],
    memory: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    return {
        f"{operation}MemoryTable": _build_aes_ascon_measurement_table(
            payload_sizes,
            memory,
            operation,
            "means",
            "cis",
        )
        for operation in ("Encrypt", "Decrypt")
    }


def _build_aes_ascon_energy_tables(
    payload_sizes: list[int],
    cases: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    return {
        f"{operation}EnergyTable": _build_aes_ascon_measurement_table(
            payload_sizes,
            cases,
            operation,
            "energy_means",
            "energy_cis",
            "energy_throttled",
        )
        for operation in ("Encrypt", "Decrypt")
    }


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
        **_build_aes_ascon_timing_tables(payload_sizes, cases),
        **_build_aes_ascon_energy_tables(payload_sizes, cases),
        **_build_aes_ascon_memory_tables(payload_sizes, report_data["memory"]),
        "TimingThermalLegend": build_thermal_legend(timing_throttled),
        "EnergyThermalLegend": build_thermal_legend(energy_throttled),
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
    payload_sizes: list[int],
    cases: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    return {
        f"{operation}TimingTable": _build_json_cbor_measurement_table(
            payload_sizes,
            cases,
            operation,
            "latency_means",
            "latency_cis",
            "timing_throttled",
        )
        for operation in ("Serialize", "Deserialize")
    }


def _build_json_cbor_measurement_table(
    payload_sizes: list[int],
    cases: dict[tuple[str, str], dict[str, Any]],
    operation: str,
    mean_key: str,
    confidence_interval_key: str,
    throttled_key: str,
) -> str:
    columns = [_byte_column(payload_sizes)]

    for format_name in ("JSON", "CBOR", "CBORKeyAsInt"):
        values = cases[(format_name, operation)]
        columns.append(
            _mark_throttled_cells(
                _mean_ci_column(
                    values[mean_key],
                    values[confidence_interval_key],
                ),
                values[throttled_key],
            )
        )

    return _build_data_table(
        ["Payload", "JSON", "CBOR", "CBOR integer"],
        columns,
    )


def _build_json_cbor_size_table(
    payload_sizes: list[int],
    raw_sizes: list[int],
    sizes: dict[str, list[int]],
) -> str:
    return _build_data_table(
        ["Payload", "Raw binary", "JSON", "CBOR", "CBOR integer"],
        [
            _byte_column(payload_sizes),
            _byte_column(raw_sizes),
            _byte_column(sizes["JSON"]),
            _byte_column(sizes["CBOR"]),
            _byte_column(sizes["CBORKeyAsInt"]),
        ],
    )


def _build_json_cbor_energy_tables(
    payload_sizes: list[int],
    cases: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    return {
        f"{operation}EnergyTable": _build_json_cbor_measurement_table(
            payload_sizes,
            cases,
            operation,
            "energy_means",
            "energy_cis",
            "energy_throttled",
        )
        for operation in ("Serialize", "Deserialize")
    }


def write_json_cbor_report(
    report_data: dict[str, Any],
    template_path: str,
    report_path: str,
) -> None:
    payload_sizes = report_data["payload_sizes"]
    cases = report_data["cases"]
    plots = report_data["plots"]
    interpretations = report_data["interpretations"]
    latency_speedup = interpretations["latency_speedup"]
    wire_overhead = interpretations["wire_overhead"]
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
        **_build_json_cbor_timing_tables(payload_sizes, cases),
        "SizeComparisonTable": _build_json_cbor_size_table(
            payload_sizes,
            report_data["raw_sizes"],
            report_data["sizes"],
        ),
        **_build_json_cbor_energy_tables(payload_sizes, cases),
        "TimingThermalLegend": build_thermal_legend(timing_throttled),
        "EnergyThermalLegend": build_thermal_legend(energy_throttled),
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
        "WireOverheadPlot": plots["wire_overhead"],
        "JsonWireOverheadFirst": f'{wire_overhead["json_first"]:,}',
        "JsonWireOverheadLast": f'{wire_overhead["json_last"]:,}',
        "CborWireOverheadMin": f'{wire_overhead["cbor_min"]:,}',
        "CborWireOverheadMax": f'{wire_overhead["cbor_max"]:,}',
        "CborIntWireOverheadMin": f'{wire_overhead["cbor_int_min"]:,}',
        "CborIntWireOverheadMax": f'{wire_overhead["cbor_int_max"]:,}',
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


def _build_full_schema_tables(
    payload_sizes: list[int],
    cases: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    headers = [
        "Payload Size (B)",
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
                [f"{value:,}" for value in payload_sizes],
                _mean_ci_column(
                    values["latency_means"],
                    values["latency_cis"],
                ),
            ],
            values["timing_throttled"],
        )

    return tables


def _build_full_schema_wire_size_table(
    payload_sizes: list[int],
    wire_sizes: dict[str, list[float]],
) -> str:
    return _build_data_table(
        [
            "Payload Size (B)",
            "PSK Wire Size (B)",
            "RSA Wire Size (B)",
            "CP-ABE Wire Size (B)",
        ],
        [
            [f"{value:,}" for value in payload_sizes],
            [f"{round(value):,}" for value in wire_sizes["PSK"]],
            [f"{round(value):,}" for value in wire_sizes["RSA"]],
            [f"{round(value):,}" for value in wire_sizes["CPABE"]],
        ],
    )


def _build_full_schema_energy_tables(
    payload_sizes: list[int],
    cases: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    headers = ["Payload Size (B)", "Energy (µJ/op)"]
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
                [f"{value:,}" for value in payload_sizes],
                _mean_ci_column(
                    values["energy_means"],
                    values["energy_cis"],
                ),
            ],
            values["energy_throttled"],
        )

    return tables


def _build_full_schema_memory_tables(
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
            ["Payload Size (B)", "Peak RSS (MB)"],
            [
                [f"{value:,}" for value in payload_sizes],
                _mean_ci_column(values["means"], values["cis"]),
            ],
        )

    return tables


def write_full_schema_report(
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
        **_build_full_schema_tables(
            payload_sizes,
            cases,
        ),
        "WireSizeTable": _build_full_schema_wire_size_table(
            payload_sizes,
            report_data["wire_sizes"],
        ),
        **_build_full_schema_energy_tables(payload_sizes, cases),
        **_build_full_schema_memory_tables(
            payload_sizes,
            report_data["memory"],
        ),
        "TimingThermalLegend": build_thermal_legend(timing_throttled),
        "EnergyThermalLegend": build_thermal_legend(energy_throttled),
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
    return f"{round(value):,}"


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


def _build_cpabe_rsa_timing_table(
    index_header: str,
    index_values: list[int],
    values: dict,
    extra_columns: list[tuple[str, str]],
    highlighted: list[bool] | None = None,
) -> str:
    headers = [index_header, "Latency (µs/op)"]
    columns = [
        [str(value) for value in index_values],
        _mean_ci_column(values["latency_means"], values["latency_cis"]),
    ]
    for header, name in extra_columns:
        headers.append(header)
        columns.append([_format_byte_size(value) for value in values[name]])
    return build_html_table(
        headers,
        _rows_from_columns(columns),
        values["timing_throttled"],
        highlighted=highlighted,
    )


def _build_cpabe_rsa_timing_report_tables(
    report_data: dict[str, Any],
) -> dict[str, str]:
    timing = report_data["timing"]
    attributes = report_data["attribute_counts"]
    subscribers = report_data["subscriber_counts"]
    rsa_key_bits = report_data["rsa_key_bits"]

    return {
        "CpabeEncryptTable": _build_cpabe_rsa_timing_table(
            "Policy Attributes",
            attributes,
            timing[("CPABEAttributes", "Encrypt")],
            [("Ciphertext (B)", "ciphertext_means")],
        ),
        "CpabeDecryptTable": _build_cpabe_rsa_timing_table(
            "Policy Attributes",
            attributes,
            timing[("CPABEAttributes", "Decrypt")],
            [("Stored Key (B)", "stored_key_means")],
        ),
        "RsaSubscribersEncryptTable": _build_cpabe_rsa_timing_table(
            "Subscribers",
            subscribers,
            timing[("RSASubscribers", "Encrypt")],
            [
                ("Ciphertext (B)", "ciphertext_means"),
                ("Total Ciphertext (B)", "total_ciphertext_means"),
            ],
        ),
        "RsaKeySizeSensitivityTable": build_html_table(
            [
                "RSA Key Bits",
                "Encrypt Latency (µs/op)",
                "Decrypt Latency (µs/op)",
                "Ciphertext (B)",
            ],
            _rows_from_columns(
                [
                    [str(value) for value in rsa_key_bits],
                    _mean_ci_column(
                        timing[("RSAKeyBits", "Encrypt")]["latency_means"],
                        timing[("RSAKeyBits", "Encrypt")]["latency_cis"],
                    ),
                    _mean_ci_column(
                        timing[("RSAKeyBits", "Decrypt")]["latency_means"],
                        timing[("RSAKeyBits", "Decrypt")]["latency_cis"],
                    ),
                    [
                        _format_byte_size(value)
                        for value in timing[("RSAKeyBits", "Encrypt")][
                            "ciphertext_means"
                        ]
                    ],
                ]
            ),
            [
                encrypt_throttled or decrypt_throttled
                for encrypt_throttled, decrypt_throttled in zip(
                    timing[("RSAKeyBits", "Encrypt")]["timing_throttled"],
                    timing[("RSAKeyBits", "Decrypt")]["timing_throttled"],
                    strict=True,
                )
            ],
            highlighted=[
                value == report_data["fixed_rsa_key_bits"] for value in rsa_key_bits
            ],
        ),
    }


def _build_cpabe_rsa_energy_tables(report_data: dict[str, Any]) -> dict[str, str]:
    energy = report_data["energy"]
    specifications = (
        (
            "CpabeEncryptEnergyTable",
            "Policy Attributes",
            report_data["attribute_counts"],
            "CPABEAttributes",
            "Encrypt",
        ),
        (
            "CpabeDecryptEnergyTable",
            "Policy Attributes",
            report_data["attribute_counts"],
            "CPABEAttributes",
            "Decrypt",
        ),
        (
            "RsaSubscribersEncryptEnergyTable",
            "Subscribers",
            report_data["subscriber_counts"],
            "RSASubscribers",
            "Encrypt",
        ),
        (
            "RsaFixedDecryptEnergyTable",
            "RSA Key Bits",
            [report_data["fixed_rsa_key_bits"]],
            "RSAKeyBits",
            "Decrypt",
        ),
    )
    tables = {}
    for placeholder, header, parameter_values, algorithm, operation in specifications:
        values = energy[(algorithm, operation)]
        tables[placeholder] = _build_data_table(
            [header, "Energy (µJ/op)"],
            [
                [str(parameter_value) for parameter_value in parameter_values],
                _mean_ci_column(values["energy_means"], values["energy_cis"]),
            ],
            values["energy_throttled"],
        )
    return tables


def _build_cpabe_rsa_memory_report_tables(
    report_data: dict[str, Any],
) -> dict[str, str]:
    memory = report_data["memory"]

    def table(index_header, index_values, values):
        return build_html_table(
            [index_header, "Peak RSS (MB)"],
            _rows_from_columns(
                [
                    [str(value) for value in index_values],
                    _mean_ci_column(values["means"], values["cis"]),
                ]
            ),
        )

    cpabe_encrypt = memory[("CPABEAttributes", "Encrypt")]
    cpabe_decrypt = memory[("CPABEAttributes", "Decrypt")]
    subscriber_encrypt = memory[("RSASubscribers", "Encrypt")]
    rsa_decrypt = memory[("RSAKeyBits", "Decrypt")]

    return {
        "PeakMemoryCpabeEncryptTable": table(
            "Policy Attributes", report_data["attribute_counts"], cpabe_encrypt
        ),
        "PeakMemoryCpabeDecryptTable": table(
            "Policy Attributes", report_data["attribute_counts"], cpabe_decrypt
        ),
        "PeakMemoryRsaSubscribersEncryptTable": table(
            "Subscribers", report_data["subscriber_counts"], subscriber_encrypt
        ),
        "PeakMemoryRsaFixedDecryptTable": table(
            "RSA Key Bits", [report_data["fixed_rsa_key_bits"]], rsa_decrypt
        ),
    }


def write_cpabe_rsa_report(
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
        for values in report_data["timing"].values()
        for flag in values["timing_throttled"]
    ]
    energy_throttled = [
        flag
        for values in report_data["energy"].values()
        for flag in values["energy_throttled"]
    ]

    fanout = build_rsa_circle_visualization(
        comparisons["bytes_per_subscriber"],
        report_data["timing"][("RSASubscribers", "Encrypt")]["total_ciphertext_means"][
            -1
        ],
        subscribers[-1],
    )
    placeholders = {
        "RunCount": str(report_data["runs"]),
        "ConfidenceLevel": CONFIDENCE_LEVEL,
        **fanout,
        **_build_cpabe_rsa_timing_report_tables(report_data),
        **_build_cpabe_rsa_energy_tables(report_data),
        **_build_cpabe_rsa_memory_report_tables(report_data),
        "TimingThermalLegend": build_thermal_legend(timing_throttled),
        "EnergyThermalLegend": build_thermal_legend(energy_throttled),
        "BaselineRss": f'{format_mean_with_ci(report_data["baseline_memory_mean"], report_data["baseline_memory_ci"])} MB',
        "MinAttributeLabel": format_attribute_label(attributes[0]),
        "MaxAttributeLabel": format_attribute_label(attributes[-1]),
        "MaxSubscriberCount": str(subscribers[-1]),
        "FixedRsaKeyBits": str(report_data["fixed_rsa_key_bits"]),
        "EnergyWindowStart": f'{report_data["energy_window_start"]:g}',
        "EnergyWindowEnd": f'{report_data["energy_window_end"]:g}',
        "CpabePlot": plots["cpabe"],
        "RsaSubscribersPlot": plots["rsa_subscribers"],
        "RsaKeySizeSensitivityPlot": plots["rsa_key_size_sensitivity"],
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
        slope, _, _, slope_ci = regressions[name]
        placeholders[f"{placeholder}Slope"] = format_slope(
            slope, slope_ci, unit, decimals=decimals, thousands=thousands
        )

    build_html_report(template_path, report_path, placeholders)
