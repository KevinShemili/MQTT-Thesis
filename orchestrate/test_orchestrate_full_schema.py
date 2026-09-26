import pytest

import orchestrate.orchestrate_full_schema as sut

# monkeypatch temporarily replaces real functions/objects during a test.
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

    monkeypatch.setattr(
        sut, "MEMORY_RESULT_FILE", tmp_path / "memory.txt", raising=False
    )
    monkeypatch.setattr(sut, "PAYLOAD_SIZES", [256], raising=False)
    monkeypatch.setattr(
        sut,
        "run_memory_case",
        lambda output, operation, algorithm, payload_size: calls.append(
            (operation, algorithm, payload_size)
        ),
    )

    expected = [
        ("MemoryBaseline", "Runtime", 0),
        ("MemoryEncrypt", "PSKStandard", 256),
        ("MemoryDecrypt", "PSKStandard", 256),
        ("MemoryEncrypt", "PSKLightweight", 256),
        ("MemoryDecrypt", "PSKLightweight", 256),
        ("MemoryEncrypt", "RSAStandard", 256),
        ("MemoryDecrypt", "RSAStandard", 256),
        ("MemoryEncrypt", "RSALightweight", 256),
        ("MemoryDecrypt", "RSALightweight", 256),
        ("MemoryEncrypt", "CPABEStandard", 256),
        ("MemoryDecrypt", "CPABEStandard", 256),
        ("MemoryEncrypt", "CPABELightweight", 256),
        ("MemoryDecrypt", "CPABELightweight", 256),
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
        ("PSKStandard", "Encrypt", 256),
        ("PSKStandard", "Decrypt", 256),
        ("PSKLightweight", "Encrypt", 256),
        ("PSKLightweight", "Decrypt", 256),
        ("RSAStandard", "Encrypt", 256),
        ("RSAStandard", "Decrypt", 256),
        ("RSALightweight", "Encrypt", 256),
        ("RSALightweight", "Decrypt", 256),
        ("CPABEStandard", "Encrypt", 256),
        ("CPABEStandard", "Decrypt", 256),
        ("CPABELightweight", "Encrypt", 256),
        ("CPABELightweight", "Decrypt", 256),
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
        ("PSKStandard", "Encrypt", 256),
        ("PSKStandard", "Decrypt", 256),
        ("PSKLightweight", "Encrypt", 256),
        ("PSKLightweight", "Decrypt", 256),
        ("RSAStandard", "Encrypt", 256),
        ("RSAStandard", "Decrypt", 256),
        ("RSALightweight", "Encrypt", 256),
        ("RSALightweight", "Decrypt", 256),
        ("CPABEStandard", "Encrypt", 256),
        ("CPABEStandard", "Decrypt", 256),
        ("CPABELightweight", "Encrypt", 256),
        ("CPABELightweight", "Decrypt", 256),
    ]

    # Act
    sut.orchestrate_timing()

    # Assert
    assert calls == expected
