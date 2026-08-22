import os
from pathlib import Path

from template_builder.chart import *
from template_builder.formatting import *
from template_builder.html import *

from model.benchmark_summary import *
from model.measurement import *
from model.populate_model import *

from config.environment import *
from statistics_tbd.summary import *

SCENARIO = "json-cbor"
HTML_TEMPLATE_NAME = "json_cbor_template.html"

LATENCY_PLOT = "plot.png"
SIZE_PLOT = "size.png"

BENCHMARK_PREFIX = "BenchmarkEnvelope"


def main() -> None:
    runs = parse_int_env("JSON_CBOR_RUNS")
    attribute_counts = parse_int_list_env("JSON_CBOR_ATTRIBUTE_COUNTS")

    result_dir = Path(
        os.environ.get("JSON_CBOR_RESULT_DIR", f"{DEFAULT_RESULT_ROOT}/{SCENARIO}")
    )
    bench_output = result_dir / BENCH_OUTPUT_NAME
    template_path = Path(TEMPLATE_DIR) / HTML_TEMPLATE_NAME
    report_path = result_dir / REPORT_NAME

    results = BenchmarkSummary()
    load_results(results, str(bench_output), BENCHMARK_PREFIX, "Attrs")

    json_serialize = [
        results.find_aggregation("Serialize", "JSON", attribute_count)
        for attribute_count in attribute_counts
    ]
    cbor_serialize = [
        results.find_aggregation("Serialize", "CBOR", attribute_count)
        for attribute_count in attribute_counts
    ]
    cbor_int_serialize = [
        results.find_aggregation("Serialize", "CBORKeyAsInt", attribute_count)
        for attribute_count in attribute_counts
    ]
    json_deserialize = [
        results.find_aggregation("Deserialize", "JSON", attribute_count)
        for attribute_count in attribute_counts
    ]
    cbor_deserialize = [
        results.find_aggregation("Deserialize", "CBOR", attribute_count)
        for attribute_count in attribute_counts
    ]
    cbor_int_deserialize = [
        results.find_aggregation("Deserialize", "CBORKeyAsInt", attribute_count)
        for attribute_count in attribute_counts
    ]
    assert all(aggregation is not None for aggregation in json_serialize)
    assert all(aggregation is not None for aggregation in cbor_serialize)
    assert all(aggregation is not None for aggregation in cbor_int_serialize)
    assert all(aggregation is not None for aggregation in json_deserialize)
    assert all(aggregation is not None for aggregation in cbor_deserialize)
    assert all(aggregation is not None for aggregation in cbor_int_deserialize)

    json_serialize = [
        aggregation for aggregation in json_serialize if aggregation is not None
    ]
    cbor_serialize = [
        aggregation for aggregation in cbor_serialize if aggregation is not None
    ]
    cbor_int_serialize = [
        aggregation for aggregation in cbor_int_serialize if aggregation is not None
    ]
    json_deserialize = [
        aggregation for aggregation in json_deserialize if aggregation is not None
    ]
    cbor_deserialize = [
        aggregation for aggregation in cbor_deserialize if aggregation is not None
    ]
    cbor_int_deserialize = [
        aggregation for aggregation in cbor_int_deserialize if aggregation is not None
    ]

    json_serialize_latency_ns = [
        aggregation.mean(NS_PER_OP) for aggregation in json_serialize
    ]
    json_serialize_latency_cis_ns = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in json_serialize
    ]
    cbor_serialize_latency_ns = [
        aggregation.mean(NS_PER_OP) for aggregation in cbor_serialize
    ]
    cbor_serialize_latency_cis_ns = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in cbor_serialize
    ]
    cbor_int_serialize_latency_ns = [
        aggregation.mean(NS_PER_OP) for aggregation in cbor_int_serialize
    ]
    cbor_int_serialize_latency_cis_ns = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in cbor_int_serialize
    ]
    json_deserialize_latency_ns = [
        aggregation.mean(NS_PER_OP) for aggregation in json_deserialize
    ]
    json_deserialize_latency_cis_ns = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in json_deserialize
    ]
    cbor_deserialize_latency_ns = [
        aggregation.mean(NS_PER_OP) for aggregation in cbor_deserialize
    ]
    cbor_deserialize_latency_cis_ns = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in cbor_deserialize
    ]
    cbor_int_deserialize_latency_ns = [
        aggregation.mean(NS_PER_OP) for aggregation in cbor_int_deserialize
    ]
    cbor_int_deserialize_latency_cis_ns = [
        aggregation.confidence_interval(NS_PER_OP)
        for aggregation in cbor_int_deserialize
    ]

    json_serialize_raw_sizes = [
        aggregation.mean(RAW_BYTES) for aggregation in json_serialize
    ]
    json_serialize_envelope_sizes = [
        aggregation.mean(ENVELOPE_BYTES) for aggregation in json_serialize
    ]
    cbor_serialize_raw_sizes = [
        aggregation.mean(RAW_BYTES) for aggregation in cbor_serialize
    ]
    cbor_serialize_envelope_sizes = [
        aggregation.mean(ENVELOPE_BYTES) for aggregation in cbor_serialize
    ]
    cbor_int_serialize_raw_sizes = [
        aggregation.mean(RAW_BYTES) for aggregation in cbor_int_serialize
    ]
    cbor_int_serialize_envelope_sizes = [
        aggregation.mean(ENVELOPE_BYTES) for aggregation in cbor_int_serialize
    ]
    json_deserialize_raw_sizes = [
        aggregation.mean(RAW_BYTES) for aggregation in json_deserialize
    ]
    json_deserialize_envelope_sizes = [
        aggregation.mean(ENVELOPE_BYTES) for aggregation in json_deserialize
    ]
    cbor_deserialize_raw_sizes = [
        aggregation.mean(RAW_BYTES) for aggregation in cbor_deserialize
    ]
    cbor_deserialize_envelope_sizes = [
        aggregation.mean(ENVELOPE_BYTES) for aggregation in cbor_deserialize
    ]
    cbor_int_deserialize_raw_sizes = [
        aggregation.mean(RAW_BYTES) for aggregation in cbor_int_deserialize
    ]
    cbor_int_deserialize_envelope_sizes = [
        aggregation.mean(ENVELOPE_BYTES) for aggregation in cbor_int_deserialize
    ]

    json_serialize_overhead_bytes = [
        envelope - raw
        for envelope, raw in zip(
            json_serialize_envelope_sizes, json_serialize_raw_sizes, strict=True
        )
    ]
    cbor_serialize_overhead_bytes = [
        envelope - raw
        for envelope, raw in zip(
            cbor_serialize_envelope_sizes, cbor_serialize_raw_sizes, strict=True
        )
    ]
    cbor_int_serialize_overhead_bytes = [
        envelope - raw
        for envelope, raw in zip(
            cbor_int_serialize_envelope_sizes,
            cbor_int_serialize_raw_sizes,
            strict=True,
        )
    ]

    plot_json_cbor_latency(
        attribute_counts,
        [value / NS_PER_MICROSECOND for value in json_serialize_latency_ns],
        [value / NS_PER_MICROSECOND for value in json_serialize_latency_cis_ns],
        [value / NS_PER_MICROSECOND for value in cbor_serialize_latency_ns],
        [value / NS_PER_MICROSECOND for value in cbor_serialize_latency_cis_ns],
        [value / NS_PER_MICROSECOND for value in cbor_int_serialize_latency_ns],
        [value / NS_PER_MICROSECOND for value in cbor_int_serialize_latency_cis_ns],
        [value / NS_PER_MICROSECOND for value in json_deserialize_latency_ns],
        [value / NS_PER_MICROSECOND for value in json_deserialize_latency_cis_ns],
        [value / NS_PER_MICROSECOND for value in cbor_deserialize_latency_ns],
        [value / NS_PER_MICROSECOND for value in cbor_deserialize_latency_cis_ns],
        [value / NS_PER_MICROSECOND for value in cbor_int_deserialize_latency_ns],
        [value / NS_PER_MICROSECOND for value in cbor_int_deserialize_latency_cis_ns],
        str(result_dir / LATENCY_PLOT),
    )
    plot_json_cbor_size(
        attribute_counts,
        json_serialize_envelope_sizes,
        [
            aggregation.confidence_interval(ENVELOPE_BYTES)
            for aggregation in json_serialize
        ],
        json_serialize_overhead_bytes,
        cbor_serialize_envelope_sizes,
        [
            aggregation.confidence_interval(ENVELOPE_BYTES)
            for aggregation in cbor_serialize
        ],
        cbor_serialize_overhead_bytes,
        cbor_int_serialize_envelope_sizes,
        [
            aggregation.confidence_interval(ENVELOPE_BYTES)
            for aggregation in cbor_int_serialize
        ],
        cbor_int_serialize_overhead_bytes,
        str(result_dir / SIZE_PLOT),
    )

    write_json_cbor_report(
        runs=runs,
        t_multiplier=get_student_t_critical_95(runs - 1),
        total_iterations=sum(
            aggregation.iterations for aggregation in results.aggregations
        ),
        attribute_counts=attribute_counts,
        json_serialize_latency_means=json_serialize_latency_ns,
        json_serialize_latency_cis=json_serialize_latency_cis_ns,
        json_serialize_raw_sizes=json_serialize_raw_sizes,
        json_serialize_envelope_sizes=json_serialize_envelope_sizes,
        json_serialize_overhead_percents=[
            overhead / raw * 100.0
            for overhead, raw in zip(
                json_serialize_overhead_bytes, json_serialize_raw_sizes, strict=True
            )
        ],
        json_serialize_iterations=[
            aggregation.iterations for aggregation in json_serialize
        ],
        json_serialize_throttled=results.get_throttle_flags(
            "Serialize", "JSON", attribute_counts
        ),
        cbor_serialize_latency_means=cbor_serialize_latency_ns,
        cbor_serialize_latency_cis=cbor_serialize_latency_cis_ns,
        cbor_serialize_raw_sizes=cbor_serialize_raw_sizes,
        cbor_serialize_envelope_sizes=cbor_serialize_envelope_sizes,
        cbor_serialize_overhead_percents=[
            (envelope - raw) / raw * 100.0
            for envelope, raw in zip(
                cbor_serialize_envelope_sizes, cbor_serialize_raw_sizes, strict=True
            )
        ],
        cbor_serialize_iterations=[
            aggregation.iterations for aggregation in cbor_serialize
        ],
        cbor_serialize_throttled=results.get_throttle_flags(
            "Serialize", "CBOR", attribute_counts
        ),
        cbor_int_serialize_latency_means=cbor_int_serialize_latency_ns,
        cbor_int_serialize_latency_cis=cbor_int_serialize_latency_cis_ns,
        cbor_int_serialize_raw_sizes=cbor_int_serialize_raw_sizes,
        cbor_int_serialize_envelope_sizes=cbor_int_serialize_envelope_sizes,
        cbor_int_serialize_overhead_percents=[
            (envelope - raw) / raw * 100.0
            for envelope, raw in zip(
                cbor_int_serialize_envelope_sizes,
                cbor_int_serialize_raw_sizes,
                strict=True,
            )
        ],
        cbor_int_serialize_iterations=[
            aggregation.iterations for aggregation in cbor_int_serialize
        ],
        cbor_int_serialize_throttled=results.get_throttle_flags(
            "Serialize", "CBORKeyAsInt", attribute_counts
        ),
        json_deserialize_latency_means=json_deserialize_latency_ns,
        json_deserialize_latency_cis=json_deserialize_latency_cis_ns,
        json_deserialize_raw_sizes=json_deserialize_raw_sizes,
        json_deserialize_envelope_sizes=json_deserialize_envelope_sizes,
        json_deserialize_overhead_percents=[
            (envelope - raw) / raw * 100.0
            for envelope, raw in zip(
                json_deserialize_envelope_sizes,
                json_deserialize_raw_sizes,
                strict=True,
            )
        ],
        json_deserialize_iterations=[
            aggregation.iterations for aggregation in json_deserialize
        ],
        json_deserialize_throttled=results.get_throttle_flags(
            "Deserialize", "JSON", attribute_counts
        ),
        cbor_deserialize_latency_means=cbor_deserialize_latency_ns,
        cbor_deserialize_latency_cis=cbor_deserialize_latency_cis_ns,
        cbor_deserialize_raw_sizes=cbor_deserialize_raw_sizes,
        cbor_deserialize_envelope_sizes=cbor_deserialize_envelope_sizes,
        cbor_deserialize_overhead_percents=[
            (envelope - raw) / raw * 100.0
            for envelope, raw in zip(
                cbor_deserialize_envelope_sizes,
                cbor_deserialize_raw_sizes,
                strict=True,
            )
        ],
        cbor_deserialize_iterations=[
            aggregation.iterations for aggregation in cbor_deserialize
        ],
        cbor_deserialize_throttled=results.get_throttle_flags(
            "Deserialize", "CBOR", attribute_counts
        ),
        cbor_int_deserialize_latency_means=cbor_int_deserialize_latency_ns,
        cbor_int_deserialize_latency_cis=cbor_int_deserialize_latency_cis_ns,
        cbor_int_deserialize_raw_sizes=cbor_int_deserialize_raw_sizes,
        cbor_int_deserialize_envelope_sizes=cbor_int_deserialize_envelope_sizes,
        cbor_int_deserialize_overhead_percents=[
            (envelope - raw) / raw * 100.0
            for envelope, raw in zip(
                cbor_int_deserialize_envelope_sizes,
                cbor_int_deserialize_raw_sizes,
                strict=True,
            )
        ],
        cbor_int_deserialize_iterations=[
            aggregation.iterations for aggregation in cbor_int_deserialize
        ],
        cbor_int_deserialize_throttled=results.get_throttle_flags(
            "Deserialize", "CBORKeyAsInt", attribute_counts
        ),
        latency_plot=LATENCY_PLOT,
        size_plot=SIZE_PLOT,
        template_path=str(template_path),
        report_path=str(report_path),
    )


if __name__ == "__main__":
    main()
