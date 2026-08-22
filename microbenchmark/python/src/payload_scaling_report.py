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

SCENARIO = "payload-scaling"
HTML_TEMPLATE_NAME = "payload_scaling_template.html"

LATENCY_PLOT = "plot.png"
THROUGHPUT_PLOT = "throughput.png"

BENCHMARK_PREFIX = "BenchmarkPayloadScaling"


# A scheme's wire overhead does not depend on payload size, so it is averaged over every
# payload size measured for that scheme.
def scheme_overhead_bytes(
    results: BenchmarkSummary,
    payload_sizes: list[int],
    scheme_name: str,
) -> float:
    values = []

    for payload_size in payload_sizes:
        aggregation = results.find_aggregation("Encrypt", scheme_name, payload_size)
        assert aggregation is not None
        values.append(aggregation.mean(WIRE_OVERHEAD_BYTES))

    return mean(values)


def main() -> None:
    runs = parse_int_env("PAYLOAD_SCALING_RUNS")
    payload_sizes = parse_int_list_env("PAYLOAD_SCALING_PAYLOAD_SIZES")

    result_dir = Path(
        os.environ.get(
            "PAYLOAD_SCALING_RESULT_DIR", f"{DEFAULT_RESULT_ROOT}/{SCENARIO}"
        )
    )
    bench_output = result_dir / BENCH_OUTPUT_NAME
    template_path = Path(TEMPLATE_DIR) / HTML_TEMPLATE_NAME
    report_path = result_dir / REPORT_NAME

    results = BenchmarkSummary()
    load_results(results, str(bench_output), BENCHMARK_PREFIX, "B")

    psk_encrypt = [
        results.find_aggregation("Encrypt", "PSK", payload_size)
        for payload_size in payload_sizes
    ]
    rsa_encrypt = [
        results.find_aggregation("Encrypt", "RSA", payload_size)
        for payload_size in payload_sizes
    ]
    cpabe_encrypt = [
        results.find_aggregation("Encrypt", "CPABE", payload_size)
        for payload_size in payload_sizes
    ]
    psk_decrypt = [
        results.find_aggregation("Decrypt", "PSK", payload_size)
        for payload_size in payload_sizes
    ]
    rsa_decrypt = [
        results.find_aggregation("Decrypt", "RSA", payload_size)
        for payload_size in payload_sizes
    ]
    cpabe_decrypt = [
        results.find_aggregation("Decrypt", "CPABE", payload_size)
        for payload_size in payload_sizes
    ]
    assert all(aggregation is not None for aggregation in psk_encrypt)
    assert all(aggregation is not None for aggregation in rsa_encrypt)
    assert all(aggregation is not None for aggregation in cpabe_encrypt)
    assert all(aggregation is not None for aggregation in psk_decrypt)
    assert all(aggregation is not None for aggregation in rsa_decrypt)
    assert all(aggregation is not None for aggregation in cpabe_decrypt)

    psk_encrypt = [
        aggregation for aggregation in psk_encrypt if aggregation is not None
    ]
    rsa_encrypt = [
        aggregation for aggregation in rsa_encrypt if aggregation is not None
    ]
    cpabe_encrypt = [
        aggregation for aggregation in cpabe_encrypt if aggregation is not None
    ]
    psk_decrypt = [
        aggregation for aggregation in psk_decrypt if aggregation is not None
    ]
    rsa_decrypt = [
        aggregation for aggregation in rsa_decrypt if aggregation is not None
    ]
    cpabe_decrypt = [
        aggregation for aggregation in cpabe_decrypt if aggregation is not None
    ]

    psk_encrypt_latency = [
        aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND for aggregation in psk_encrypt
    ]
    psk_encrypt_latency_cis = [
        aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in psk_encrypt
    ]
    rsa_encrypt_latency = [
        aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND for aggregation in rsa_encrypt
    ]
    rsa_encrypt_latency_cis = [
        aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in rsa_encrypt
    ]
    cpabe_encrypt_latency = [
        aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in cpabe_encrypt
    ]
    cpabe_encrypt_latency_cis = [
        aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in cpabe_encrypt
    ]
    psk_decrypt_latency = [
        aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND for aggregation in psk_decrypt
    ]
    psk_decrypt_latency_cis = [
        aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in psk_decrypt
    ]
    rsa_decrypt_latency = [
        aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND for aggregation in rsa_decrypt
    ]
    rsa_decrypt_latency_cis = [
        aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in rsa_decrypt
    ]
    cpabe_decrypt_latency = [
        aggregation.mean(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in cpabe_decrypt
    ]
    cpabe_decrypt_latency_cis = [
        aggregation.confidence_interval(NS_PER_OP) / NS_PER_MICROSECOND
        for aggregation in cpabe_decrypt
    ]

    psk_encrypt_throughput = [
        aggregation.mean(MB_PER_SECOND) for aggregation in psk_encrypt
    ]
    psk_encrypt_throughput_cis = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in psk_encrypt
    ]
    rsa_encrypt_throughput = [
        aggregation.mean(MB_PER_SECOND) for aggregation in rsa_encrypt
    ]
    rsa_encrypt_throughput_cis = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in rsa_encrypt
    ]
    cpabe_encrypt_throughput = [
        aggregation.mean(MB_PER_SECOND) for aggregation in cpabe_encrypt
    ]
    cpabe_encrypt_throughput_cis = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in cpabe_encrypt
    ]
    psk_decrypt_throughput = [
        aggregation.mean(MB_PER_SECOND) for aggregation in psk_decrypt
    ]
    psk_decrypt_throughput_cis = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in psk_decrypt
    ]
    rsa_decrypt_throughput = [
        aggregation.mean(MB_PER_SECOND) for aggregation in rsa_decrypt
    ]
    rsa_decrypt_throughput_cis = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in rsa_decrypt
    ]
    cpabe_decrypt_throughput = [
        aggregation.mean(MB_PER_SECOND) for aggregation in cpabe_decrypt
    ]
    cpabe_decrypt_throughput_cis = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in cpabe_decrypt
    ]

    psk_overhead_bytes = int(
        round(scheme_overhead_bytes(results, payload_sizes, "PSK"))
    )
    rsa_overhead_bytes = int(
        round(scheme_overhead_bytes(results, payload_sizes, "RSA"))
    )
    cpabe_overhead_bytes = int(
        round(scheme_overhead_bytes(results, payload_sizes, "CPABE"))
    )
    psk_wire_sizes = [
        payload_size + psk_overhead_bytes for payload_size in payload_sizes
    ]
    rsa_wire_sizes = [
        payload_size + rsa_overhead_bytes for payload_size in payload_sizes
    ]
    cpabe_wire_sizes = [
        payload_size + cpabe_overhead_bytes for payload_size in payload_sizes
    ]
    psk_overhead_percents = [
        psk_overhead_bytes / payload_size * 100.0 for payload_size in payload_sizes
    ]
    rsa_overhead_percents = [
        rsa_overhead_bytes / payload_size * 100.0 for payload_size in payload_sizes
    ]
    cpabe_overhead_percents = [
        cpabe_overhead_bytes / payload_size * 100.0 for payload_size in payload_sizes
    ]

    plot_payload_scaling_latency(
        payload_sizes,
        psk_encrypt_latency,
        psk_encrypt_latency_cis,
        rsa_encrypt_latency,
        rsa_encrypt_latency_cis,
        cpabe_encrypt_latency,
        cpabe_encrypt_latency_cis,
        psk_decrypt_latency,
        psk_decrypt_latency_cis,
        rsa_decrypt_latency,
        rsa_decrypt_latency_cis,
        cpabe_decrypt_latency,
        cpabe_decrypt_latency_cis,
        str(result_dir / LATENCY_PLOT),
    )
    plot_payload_scaling_throughput(
        payload_sizes,
        psk_encrypt_throughput,
        psk_encrypt_throughput_cis,
        rsa_encrypt_throughput,
        rsa_encrypt_throughput_cis,
        cpabe_encrypt_throughput,
        cpabe_encrypt_throughput_cis,
        psk_decrypt_throughput,
        psk_decrypt_throughput_cis,
        rsa_decrypt_throughput,
        rsa_decrypt_throughput_cis,
        cpabe_decrypt_throughput,
        cpabe_decrypt_throughput_cis,
        str(result_dir / THROUGHPUT_PLOT),
    )

    write_payload_scaling_report(
        runs=runs,
        t_multiplier=get_student_t_critical_95(runs - 1),
        total_iterations=sum(
            aggregation.iterations for aggregation in results.aggregations
        ),
        payload_sizes=payload_sizes,
        psk_wire_sizes=psk_wire_sizes,
        psk_overhead_percents=psk_overhead_percents,
        rsa_wire_sizes=rsa_wire_sizes,
        rsa_overhead_percents=rsa_overhead_percents,
        cpabe_wire_sizes=cpabe_wire_sizes,
        cpabe_overhead_percents=cpabe_overhead_percents,
        psk_encrypt_latency_means=psk_encrypt_latency,
        psk_encrypt_latency_cis=psk_encrypt_latency_cis,
        psk_encrypt_throughput_means=psk_encrypt_throughput,
        psk_encrypt_throughput_cis=psk_encrypt_throughput_cis,
        psk_encrypt_iterations=[aggregation.iterations for aggregation in psk_encrypt],
        psk_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", "PSK", payload_sizes
        ),
        rsa_encrypt_latency_means=rsa_encrypt_latency,
        rsa_encrypt_latency_cis=rsa_encrypt_latency_cis,
        rsa_encrypt_throughput_means=rsa_encrypt_throughput,
        rsa_encrypt_throughput_cis=rsa_encrypt_throughput_cis,
        rsa_encrypt_iterations=[aggregation.iterations for aggregation in rsa_encrypt],
        rsa_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", "RSA", payload_sizes
        ),
        cpabe_encrypt_latency_means=cpabe_encrypt_latency,
        cpabe_encrypt_latency_cis=cpabe_encrypt_latency_cis,
        cpabe_encrypt_throughput_means=cpabe_encrypt_throughput,
        cpabe_encrypt_throughput_cis=cpabe_encrypt_throughput_cis,
        cpabe_encrypt_iterations=[
            aggregation.iterations for aggregation in cpabe_encrypt
        ],
        cpabe_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", "CPABE", payload_sizes
        ),
        psk_decrypt_latency_means=psk_decrypt_latency,
        psk_decrypt_latency_cis=psk_decrypt_latency_cis,
        psk_decrypt_throughput_means=psk_decrypt_throughput,
        psk_decrypt_throughput_cis=psk_decrypt_throughput_cis,
        psk_decrypt_iterations=[aggregation.iterations for aggregation in psk_decrypt],
        psk_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", "PSK", payload_sizes
        ),
        rsa_decrypt_latency_means=rsa_decrypt_latency,
        rsa_decrypt_latency_cis=rsa_decrypt_latency_cis,
        rsa_decrypt_throughput_means=rsa_decrypt_throughput,
        rsa_decrypt_throughput_cis=rsa_decrypt_throughput_cis,
        rsa_decrypt_iterations=[aggregation.iterations for aggregation in rsa_decrypt],
        rsa_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", "RSA", payload_sizes
        ),
        cpabe_decrypt_latency_means=cpabe_decrypt_latency,
        cpabe_decrypt_latency_cis=cpabe_decrypt_latency_cis,
        cpabe_decrypt_throughput_means=cpabe_decrypt_throughput,
        cpabe_decrypt_throughput_cis=cpabe_decrypt_throughput_cis,
        cpabe_decrypt_iterations=[
            aggregation.iterations for aggregation in cpabe_decrypt
        ],
        cpabe_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", "CPABE", payload_sizes
        ),
        latency_plot=LATENCY_PLOT,
        throughput_plot=THROUGHPUT_PLOT,
        template_path=str(template_path),
        report_path=str(report_path),
    )


if __name__ == "__main__":
    main()
