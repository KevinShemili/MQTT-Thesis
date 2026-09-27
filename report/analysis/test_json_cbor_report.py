import report.analysis.json_cbor_report as sut


def test_main_calls_report_stages_in_expected_order(monkeypatch, tmp_path):

    # Arrange
    calls = []
    render_calls = []

    class FakeTimingCase:
        measurements = {
            sut.SERIALIZED_BYTES: 2,
            sut.RAW_BYTES: 1,
        }

    class FakeTimingAggregation:
        cases = [FakeTimingCase()]

    class FakeSummary:
        energy_baseline_cases = []

        def find_timing_aggregation(
            self, format_name, operation, parameter, parameter_value
        ):
            return FakeTimingAggregation()

        def find_energy_aggregation(
            self, format_name, operation, parameter, parameter_value
        ):
            return "energy"

    def fake_load_summary(*args, **kwargs):
        calls.append("load summary")
        return FakeSummary()

    def fake_analyze_case(*args):
        if "analyze cases" not in calls:
            calls.append("analyze cases")

        return {
            "latency_means": [2.0],
            "latency_cis": [0.1],
            "energy_means": [2.0],
            "energy_cis": [0.1],
            "timing_throttled": [False],
            "energy_throttled": [False],
        }

    def fake_chart(name):
        def chart(*args):
            if "generate charts" not in calls:
                calls.append("generate charts")

            render_calls.append(name)

        return chart

    def fake_write_report(*args):
        calls.append("write html")
        render_calls.append("html")

    monkeypatch.setattr(sut, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sut, "TEMPLATE_DIR", tmp_path)
    monkeypatch.setenv("JSON_CBOR_RESULT_DIR", "results")

    monkeypatch.setattr(sut, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(sut, "parse_int_env", lambda name: 1)
    monkeypatch.setattr(sut, "parse_int_list_env", lambda name: [256])

    monkeypatch.setattr(sut, "load_summary", fake_load_summary)
    monkeypatch.setattr(sut, "analyze_case", fake_analyze_case)

    monkeypatch.setattr(
        sut,
        "plot_json_cbor_latency",
        fake_chart("latency"),
    )
    monkeypatch.setattr(
        sut,
        "plot_json_cbor_latency_speedup",
        fake_chart("latency speedup"),
    )
    monkeypatch.setattr(
        sut,
        "plot_json_cbor_size",
        fake_chart("size"),
    )
    monkeypatch.setattr(
        sut,
        "plot_json_cbor_wire_overhead",
        fake_chart("wire overhead"),
    )
    monkeypatch.setattr(
        sut,
        "plot_json_cbor_energy",
        fake_chart("energy"),
    )
    monkeypatch.setattr(
        sut,
        "plot_json_cbor_energy_reduction",
        fake_chart("energy reduction"),
    )
    monkeypatch.setattr(
        sut,
        "write_json_cbor_report",
        fake_write_report,
    )

    expected_calls = [
        "load summary",
        "analyze cases",
        "generate charts",
        "write html",
    ]

    expected_charts = {
        "latency",
        "latency speedup",
        "size",
        "wire overhead",
        "energy",
        "energy reduction",
    }

    # Act
    sut.main()

    # Assert
    assert calls == expected_calls
    assert set(render_calls[:-1]) == expected_charts
    assert render_calls[-1] == "html"


def test_analyze_case_calls_expected_analysis_functions(monkeypatch):

    # Arrange
    calls = []

    monkeypatch.setattr(
        sut,
        "timing_statistics",
        lambda *args: (
            calls.append("timing statistics"),
            ([1.0], [1.0]),
        )[1],
    )
    monkeypatch.setattr(
        sut,
        "energy_statistics",
        lambda *args: (
            calls.append("energy statistics"),
            ([1.0], [1.0]),
        )[1],
    )

    monkeypatch.setattr(sut, "to_microseconds", lambda values: values)
    monkeypatch.setattr(sut, "to_microjoules", lambda values: values)
    monkeypatch.setattr(sut, "collect_timing_throttle_flags", lambda values: [])
    monkeypatch.setattr(sut, "collect_energy_throttle_flags", lambda values: [])

    expected = {
        "timing statistics",
        "energy statistics",
    }

    # Act
    sut.analyze_case(
        ["timing"],
        ["energy"],
        ["energy baseline"],
    )

    # Assert
    assert set(calls) == expected
