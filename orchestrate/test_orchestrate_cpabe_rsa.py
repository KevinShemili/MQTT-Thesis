import pytest

import orchestrate.orchestrate_cpabe_rsa as sut


def test_main_calls_stages_in_expected_order(monkeypatch):

    # Arrange
    calls = []

    class FakeResultDirectory:
        def mkdir(self, parents, exist_ok):
            calls.append("create result directory")

    monkeypatch.setattr(
        sut, "load_environment_variables", lambda: calls.append("load environment")
    )
    monkeypatch.setattr(sut, "RESULT_DIRECTORY", FakeResultDirectory(), raising=False)
    monkeypatch.setattr(sut, "build_binaries", lambda: calls.append("build binaries"))
    monkeypatch.setattr(sut, "orchestrate_provision", lambda: calls.append("provision"))
    monkeypatch.setattr(sut, "orchestrate_memory", lambda: calls.append("memory"))
    monkeypatch.setattr(sut, "orchestrate_energy", lambda: calls.append("energy"))
    monkeypatch.setattr(sut, "orchestrate_timing", lambda: calls.append("timing"))
    monkeypatch.setattr(sut, "generate_report", lambda: calls.append("report"))
    monkeypatch.setattr(
        sut.time, "sleep", lambda seconds: calls.append(f"sleep {seconds}")
    )

    expected = [
        "load environment",
        "create result directory",
        "build binaries",
        "provision",
        "sleep 5",
        "memory",
        "sleep 5",
        "energy",
        "timing",
        "report",
    ]

    # Act
    sut.main()

    # Assert
    assert calls == expected


def test_orchestrate_memory_runs_cases_in_expected_order(monkeypatch, tmp_path):

    # Arrange
    calls = []

    def fake_convert_memory_results(filepath, scenario):
        calls.append("convert memory results")
        return tmp_path / "memory.csv"

    monkeypatch.setattr(
        sut, "MEMORY_RESULT_FILE", tmp_path / "memory.txt", raising=False
    )
    monkeypatch.setattr(sut, "ATTRIBUTE_COUNTS", [5], raising=False)
    monkeypatch.setattr(sut, "SUBSCRIBER_COUNTS", [10], raising=False)
    monkeypatch.setattr(sut, "FIXED_RSA_KEY_BITS", 2048, raising=False)

    # Replace the real benchmark runner so only experiment order is observed.
    monkeypatch.setattr(
        sut,
        "run_memory_case",
        lambda output, operation, algorithm, parameter_value: calls.append(
            (operation, algorithm, parameter_value)
        ),
    )
    monkeypatch.setattr(sut, "convert_memory_results", fake_convert_memory_results)

    expected = [
        ("MemoryBaseline", "Runtime", 0),
        ("MemoryEncrypt", "CPABEAttributes", 5),
        ("MemoryDecrypt", "CPABEAttributes", 5),
        ("MemoryEncrypt", "RSASubscribers", 10),
        ("MemoryDecrypt", "RSAKeyBits", 2048),
        "convert memory results",
    ]

    # Act
    sut.orchestrate_memory()

    # Assert
    assert calls == expected


def test_orchestrate_energy_runs_baseline_before_cases(monkeypatch, tmp_path):

    # Arrange
    calls = []

    class FakeUM24C:
        MAC_ADDRESS = "fake"

        def close(self):
            pass

    def fake_read_um24c(meter, duration):
        calls.append("read baseline")
        return []

    def fake_write_samples(writer, samples, metadata):
        calls.append("write baseline")

    def fake_run_energy_case(meter, writer, algorithm, operation, parameter_value):
        calls.append((algorithm, operation, parameter_value))

    monkeypatch.setattr(sut, "UM24C", FakeUM24C)
    monkeypatch.setattr(
        sut, "ENERGY_RESULT_FILE", tmp_path / "energy.csv", raising=False
    )
    monkeypatch.setattr(sut, "RUNS", 1, raising=False)
    monkeypatch.setattr(sut, "BASELINE_DURATION", 5, raising=False)
    monkeypatch.setattr(sut, "ATTRIBUTE_COUNTS", [5], raising=False)
    monkeypatch.setattr(sut, "SUBSCRIBER_COUNTS", [10], raising=False)
    monkeypatch.setattr(sut, "FIXED_RSA_KEY_BITS", 2048, raising=False)
    monkeypatch.setattr(sut, "read_um24c", fake_read_um24c)
    monkeypatch.setattr(sut, "write_samples", fake_write_samples)
    monkeypatch.setattr(sut, "run_energy_case", fake_run_energy_case)

    expected = [
        "read baseline",
        "write baseline",
        ("CPABEAttributes", "Encrypt", 5),
        ("CPABEAttributes", "Decrypt", 5),
        ("RSASubscribers", "Encrypt", 10),
        ("RSAKeyBits", "Decrypt", 2048),
    ]

    # Act
    sut.orchestrate_energy()

    # Assert
    assert calls == expected


def test_orchestrate_timing_runs_cases_in_expected_order(monkeypatch, tmp_path):

    # Arrange
    calls = []

    def fake_run_timing_case(
        output, algorithm, operation, parameter_value, benchmark_time, runs
    ):
        calls.append((algorithm, operation, parameter_value))

    def fake_convert_timing_results(filepath, scenario):
        calls.append("convert timing results")
        return tmp_path / "timing.csv"

    monkeypatch.setattr(
        sut, "TIMING_RESULT_FILE", tmp_path / "timing.txt", raising=False
    )
    monkeypatch.setattr(sut, "ATTRIBUTE_COUNTS", [5], raising=False)
    monkeypatch.setattr(sut, "SUBSCRIBER_COUNTS", [10], raising=False)
    monkeypatch.setattr(sut, "RSA_KEY_BITS", [2048], raising=False)
    monkeypatch.setattr(sut, "TIMING_DURATION", 5, raising=False)
    monkeypatch.setattr(sut, "RUNS", 2, raising=False)
    monkeypatch.setattr(sut, "run_timing_case", fake_run_timing_case)
    monkeypatch.setattr(sut, "convert_timing_results", fake_convert_timing_results)

    expected = [
        ("CPABEAttributes", "Encrypt", 5),
        ("CPABEAttributes", "Decrypt", 5),
        ("RSASubscribers", "Encrypt", 10),
        ("RSAKeyBits", "Encrypt", 2048),
        ("RSAKeyBits", "Decrypt", 2048),
        "convert timing results",
    ]

    # Act
    sut.orchestrate_timing()

    # Assert
    assert calls == expected
