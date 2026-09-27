import csv

import report.analysis.shared.load_summary as sut


def _write_csv(filepath, fieldnames, rows):

    with filepath.open("w", encoding="utf-8", newline="") as file:

        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_load_timing_results_groups_cases_and_loads_measurements(tmp_path):

    # Arrange
    filepath = tmp_path / "timing.csv"

    _write_csv(
        filepath,
        [
            "scenario",
            "row_type",
            "algorithm",
            "operation",
            "parameter",
            "parameter_value",
            "run",
            "ns_per_op",
            "mb_per_s",
            "serialized_bytes",
            "raw_bytes",
            "ciphertext_bytes",
            "total_ciphertext_bytes",
            "stored_key_bytes",
            "throttled",
        ],
        [
            {
                "scenario": "aes_ascon",
                "row_type": "workload",
                "algorithm": "AES-GCM",
                "operation": "Encrypt",
                "parameter": "payload_size",
                "parameter_value": 256,
                "run": 1,
                "ns_per_op": 100.0,
                "mb_per_s": 50.0,
                "serialized_bytes": 300,
                "raw_bytes": 256,
                "ciphertext_bytes": 272,
                "total_ciphertext_bytes": 280,
                "stored_key_bytes": 16,
                "throttled": 0,
            },
            {
                "scenario": "aes_ascon",
                "row_type": "workload",
                "algorithm": "AES-GCM",
                "operation": "Encrypt",
                "parameter": "payload_size",
                "parameter_value": 256,
                "run": 2,
                "ns_per_op": 110.0,
                "throttled": 1,
            },
            {
                "scenario": "aes_ascon",
                "row_type": "workload",
                "algorithm": "AES-GCM",
                "operation": "Encrypt",
                "parameter": "payload_size",
                "parameter_value": 512,
                "run": 1,
                "ns_per_op": 200.0,
                "mb_per_s": 100.0,
                "throttled": 0,
            },
        ],
    )

    summary = sut.BenchmarkSummary()

    # Act
    sut._load_timing_results(summary, str(filepath))

    # Assert
    assert len(summary.timing_aggregations) == 2

    aggregation = summary.find_timing_aggregation(
        "AES-GCM", "Encrypt", "payload_size", 256
    )

    assert aggregation is not None
    assert len(aggregation.cases) == 2

    first_case = aggregation.cases[0]
    second_case = aggregation.cases[1]

    assert first_case.run == 1
    assert first_case.measurements[sut.NS_PER_OP] == 100.0
    assert first_case.measurements[sut.MB_PER_SECOND] == 50.0
    assert first_case.measurements[sut.SERIALIZED_BYTES] == 300.0
    assert first_case.measurements[sut.RAW_BYTES] == 256.0
    assert first_case.measurements[sut.CIPHERTEXT_BYTES] == 272.0
    assert first_case.measurements[sut.TOTAL_CIPHERTEXT_BYTES] == 280.0
    assert first_case.measurements[sut.STORED_KEY_BYTES] == 16.0
    assert first_case.measurements[sut.TIMING_THROTTLED] == 0.0

    assert second_case.run == 2
    assert second_case.measurements[sut.NS_PER_OP] == 110.0
    assert second_case.measurements[sut.TIMING_THROTTLED] == 1.0
    assert sut.MB_PER_SECOND not in second_case.measurements


def test_load_memory_results_separates_baseline_and_groups_workload_cases(tmp_path):

    # Arrange
    filepath = tmp_path / "memory.csv"

    _write_csv(
        filepath,
        [
            "scenario",
            "row_type",
            "algorithm",
            "operation",
            "parameter",
            "parameter_value",
            "run",
            "peak_rss_bytes",
        ],
        [
            {
                "scenario": "aes_ascon",
                "row_type": "baseline",
                "run": 1,
                "peak_rss_bytes": 1000,
            },
            {
                "scenario": "aes_ascon",
                "row_type": "workload",
                "algorithm": "AES-GCM",
                "operation": "MemoryEncrypt",
                "parameter": "payload_size",
                "parameter_value": 256,
                "run": 1,
                "peak_rss_bytes": 2000,
            },
            {
                "scenario": "aes_ascon",
                "row_type": "workload",
                "algorithm": "AES-GCM",
                "operation": "MemoryEncrypt",
                "parameter": "payload_size",
                "parameter_value": 256,
                "run": 2,
                "peak_rss_bytes": 2100,
            },
        ],
    )

    summary = sut.BenchmarkSummary()

    # Act
    sut._load_memory_results(summary, str(filepath))

    # Assert
    assert len(summary.memory_baseline_cases) == 1
    assert summary.memory_baseline_cases[0].run == 1
    assert summary.memory_baseline_cases[0].measurements[sut.PEAK_RSS_BYTES] == 1000.0

    assert len(summary.memory_aggregations) == 1

    aggregation = summary.find_memory_aggregation(
        "AES-GCM", "MemoryEncrypt", "payload_size", 256
    )

    assert aggregation is not None
    assert len(aggregation.cases) == 2

    assert aggregation.cases[0].run == 1
    assert aggregation.cases[0].measurements[sut.PEAK_RSS_BYTES] == 2000.0

    assert aggregation.cases[1].run == 2
    assert aggregation.cases[1].measurements[sut.PEAK_RSS_BYTES] == 2100.0


def test_load_energy_results_groups_samples_by_aggregation_and_run(tmp_path):

    # Arrange
    filepath = tmp_path / "energy.csv"

    _write_csv(
        filepath,
        [
            "scenario",
            "row_type",
            "algorithm",
            "operation",
            "parameter",
            "parameter_value",
            "run",
            "throttled",
            "elapsed_s",
            "voltage_v",
            "current_a",
            "power_w",
        ],
        [
            {
                "scenario": "aes_ascon",
                "row_type": "baseline",
                "run": 1,
                "elapsed_s": 0.1,
                "voltage_v": 5.0,
                "current_a": 0.1,
                "power_w": 0.5,
            },
            {
                "scenario": "aes_ascon",
                "row_type": "baseline",
                "run": 1,
                "elapsed_s": 0.2,
                "voltage_v": 5.0,
                "current_a": 0.2,
                "power_w": 1.0,
            },
            {
                "scenario": "aes_ascon",
                "row_type": "workload",
                "algorithm": "AES-GCM",
                "operation": "Encrypt",
                "parameter": "payload_size",
                "parameter_value": 256,
                "run": 1,
                "throttled": 0,
                "elapsed_s": 0.1,
                "voltage_v": 5.0,
                "current_a": 0.3,
                "power_w": 1.5,
            },
            {
                "scenario": "aes_ascon",
                "row_type": "workload",
                "algorithm": "AES-GCM",
                "operation": "Encrypt",
                "parameter": "payload_size",
                "parameter_value": 256,
                "run": 1,
                "throttled": 0,
                "elapsed_s": 0.2,
                "voltage_v": 5.0,
                "current_a": 0.4,
                "power_w": 2.0,
            },
            {
                "scenario": "aes_ascon",
                "row_type": "workload",
                "algorithm": "AES-GCM",
                "operation": "Encrypt",
                "parameter": "payload_size",
                "parameter_value": 256,
                "run": 2,
                "throttled": 1,
                "elapsed_s": 0.1,
                "voltage_v": 5.0,
                "current_a": 0.5,
                "power_w": 2.5,
            },
        ],
    )

    summary = sut.BenchmarkSummary()

    # Act
    sut._load_energy_results(summary, str(filepath))

    # Assert
    assert len(summary.energy_baseline_cases) == 1
    assert summary.energy_baseline_cases[0].run == 1
    assert len(summary.energy_baseline_cases[0].samples) == 2

    assert len(summary.energy_aggregations) == 1

    aggregation = summary.find_energy_aggregation(
        "AES-GCM", "Encrypt", "payload_size", 256
    )

    assert aggregation is not None
    assert len(aggregation.cases) == 2

    first_case = aggregation.find_case(1)
    second_case = aggregation.find_case(2)

    assert first_case is not None
    assert second_case is not None

    assert len(first_case.samples) == 2
    assert first_case.measurements[sut.ENERGY_THROTTLED] == 0.0
    assert first_case.samples[0].elapsed_s == 0.1
    assert first_case.samples[0].voltage_v == 5.0
    assert first_case.samples[0].current_a == 0.3
    assert first_case.samples[0].power_w == 1.5
    assert first_case.samples[1].elapsed_s == 0.2
    assert first_case.samples[1].power_w == 2.0

    assert len(second_case.samples) == 1
    assert second_case.measurements[sut.ENERGY_THROTTLED] == 1.0
    assert second_case.samples[0].elapsed_s == 0.1
    assert second_case.samples[0].power_w == 2.5


def test_load_macro_summary_combines_publisher_and_subscriber_data(tmp_path):

    # Arrange
    publisher_filepath = tmp_path / "publisher.csv"
    subscriber_filepath = tmp_path / "subscriber.csv"

    _write_csv(
        publisher_filepath,
        [
            "payload_size",
            "repetition",
            "message_id",
            "publisher_started_unix_ns",
            "publisher_cycles",
        ],
        [
            {
                "payload_size": 256,
                "repetition": 1,
                "message_id": "message-1",
                "publisher_started_unix_ns": 100,
                "publisher_cycles": 1000,
            },
            {
                "payload_size": 256,
                "repetition": 1,
                "message_id": "message-2",
                "publisher_started_unix_ns": 200,
                "publisher_cycles": 1000,
            },
            {
                "payload_size": 256,
                "repetition": 2,
                "message_id": "message-1",
                "publisher_started_unix_ns": 300,
                "publisher_cycles": 1100,
            },
            {
                "payload_size": 512,
                "repetition": 1,
                "message_id": "message-1",
                "publisher_started_unix_ns": 400,
                "publisher_cycles": 1200,
            },
        ],
    )

    _write_csv(
        subscriber_filepath,
        [
            "payload_size",
            "repetition",
            "message_id",
            "subscriber_arrived_unix_ns",
            "subscriber_cycles",
        ],
        [
            {
                "payload_size": 256,
                "repetition": 1,
                "message_id": "message-1",
                "subscriber_arrived_unix_ns": 150,
                "subscriber_cycles": 2000,
            },
            {
                "payload_size": 256,
                "repetition": 1,
                "message_id": "message-2",
                "subscriber_arrived_unix_ns": 250,
                "subscriber_cycles": 2000,
            },
            {
                "payload_size": 256,
                "repetition": 2,
                "message_id": "message-1",
                "subscriber_arrived_unix_ns": 350,
                "subscriber_cycles": 2100,
            },
            {
                "payload_size": 512,
                "repetition": 1,
                "message_id": "message-1",
                "subscriber_arrived_unix_ns": 450,
                "subscriber_cycles": 2200,
            },
        ],
    )

    # Act
    summary = sut.load_macro_summary(str(publisher_filepath), str(subscriber_filepath))

    # Assert
    assert len(summary.macro_aggregations) == 2

    aggregation = summary.find_macro_aggregation("MQTT-TLS", 256)

    assert aggregation is not None
    assert len(aggregation.cases) == 2

    first_case = aggregation.find_case(1)
    second_case = aggregation.find_case(2)

    assert first_case is not None
    assert second_case is not None

    assert first_case.publisher_cycles == 1000
    assert first_case.subscriber_cycles == 2000
    assert first_case.publisher_timestamps == {
        "message-1": 100,
        "message-2": 200,
    }
    assert first_case.subscriber_timestamps == {
        "message-1": 150,
        "message-2": 250,
    }

    assert second_case.publisher_cycles == 1100
    assert second_case.subscriber_cycles == 2100
    assert second_case.publisher_timestamps == {
        "message-1": 300,
    }
    assert second_case.subscriber_timestamps == {
        "message-1": 350,
    }

    second_aggregation = summary.find_macro_aggregation("MQTT-TLS", 512)

    assert second_aggregation is not None
    assert len(second_aggregation.cases) == 1

    case = second_aggregation.find_case(1)

    assert case is not None
    assert case.publisher_cycles == 1200
    assert case.subscriber_cycles == 2200
    assert case.publisher_timestamps == {
        "message-1": 400,
    }
    assert case.subscriber_timestamps == {
        "message-1": 450,
    }
