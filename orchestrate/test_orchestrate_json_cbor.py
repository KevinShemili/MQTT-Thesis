import pytest

import orchestrate.orchestrate_json_cbor as sut

# monkeypatch temporarily replaces real functions or objects during a test.
# Pytest automatically restores the originals after the test finishes.
# This lets us test orchestration without SSH, sleeping, UM24C hardware,
# or actually running benchmarks.


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
    monkeypatch.setattr(
        sut, "build_benchmark_binary", lambda: calls.append("build binary")
    )
    monkeypatch.setattr(sut, "orchestrate_energy", lambda: calls.append("energy"))
    monkeypatch.setattr(sut, "orchestrate_timing", lambda: calls.append("timing"))
    monkeypatch.setattr(sut, "generate_report", lambda: calls.append("report"))
    monkeypatch.setattr(
        sut.time, "sleep", lambda seconds: calls.append(f"sleep {seconds}")
    )

    expected = [
        "load environment",
        "create result directory",
        "build binary",
        "sleep 5",
        "energy",
        "timing",
        "report",
    ]

    # Act
    sut.main()

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

    def fake_write_to_file(output, samples):
        calls.append("write baseline")

    def fake_run_energy_case(meter, output, algorithm, operation, payload_size):
        calls.append((algorithm, operation, payload_size))

    monkeypatch.setattr(sut, "UM24C", FakeUM24C)
    monkeypatch.setattr(
        sut, "ENERGY_RESULT_FILE", tmp_path / "energy.txt", raising=False
    )
    monkeypatch.setattr(sut, "RUNS", 1, raising=False)
    monkeypatch.setattr(sut, "BASELINE_DURATION", 5, raising=False)
    monkeypatch.setattr(sut, "PAYLOAD_SIZES", [256], raising=False)
    monkeypatch.setattr(sut, "read_um24c", fake_read_um24c)
    monkeypatch.setattr(sut, "write_to_file", fake_write_to_file)
    monkeypatch.setattr(sut, "run_energy_case", fake_run_energy_case)

    expected = [
        "read baseline",
        "write baseline",
        ("JSON", "Serialize", 256),
        ("JSON", "Deserialize", 256),
        ("CBOR", "Serialize", 256),
        ("CBOR", "Deserialize", 256),
        ("CBORKeyAsInt", "Serialize", 256),
        ("CBORKeyAsInt", "Deserialize", 256),
    ]

    # Act
    sut.orchestrate_energy()

    # Assert
    assert calls == expected


def test_orchestrate_timing_runs_cases_in_expected_order(monkeypatch, tmp_path):

    # Arrange
    calls = []

    monkeypatch.setattr(
        sut, "TIMING_RESULT_FILE", tmp_path / "timing.txt", raising=False
    )
    monkeypatch.setattr(sut, "PAYLOAD_SIZES", [256], raising=False)
    monkeypatch.setattr(
        sut,
        "run_timing_case",
        lambda output, algorithm, operation, payload_size: calls.append(
            (algorithm, operation, payload_size)
        ),
    )

    expected = [
        ("JSON", "Serialize", 256),
        ("JSON", "Deserialize", 256),
        ("CBOR", "Serialize", 256),
        ("CBOR", "Deserialize", 256),
        ("CBORKeyAsInt", "Serialize", 256),
        ("CBORKeyAsInt", "Deserialize", 256),
    ]

    # Act
    sut.orchestrate_timing()

    # Assert
    assert calls == expected
