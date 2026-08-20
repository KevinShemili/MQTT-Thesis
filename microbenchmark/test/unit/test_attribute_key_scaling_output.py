import importlib.util
import io
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

MICROBENCHMARK_DIRECTORY = Path(__file__).resolve().parents[2]
PYTHON_SOURCE_DIRECTORY = MICROBENCHMARK_DIRECTORY / "python" / "src"
sys.path.insert(0, str(PYTHON_SOURCE_DIRECTORY))

# The tests exercise parsing and validation, not plotting or environment loading. Keep
# them runnable with the standard library when the optional report dependencies are not
# installed in the current interpreter.
try:
    import matplotlib  # noqa: F401
except ModuleNotFoundError:
    matplotlib = types.ModuleType("matplotlib")
    matplotlib.use = lambda *_: None
    pyplot = types.ModuleType("matplotlib.pyplot")
    axes = types.ModuleType("matplotlib.axes")
    figure = types.ModuleType("matplotlib.figure")
    axes.Axes = type("Axes", (), {})
    figure.Figure = type("Figure", (), {})
    matplotlib.pyplot = pyplot
    sys.modules.update(
        {
            "matplotlib": matplotlib,
            "matplotlib.pyplot": pyplot,
            "matplotlib.axes": axes,
            "matplotlib.figure": figure,
        }
    )

try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *_args, **_kwargs: None
    sys.modules["dotenv"] = dotenv

import attribute_key_scaling_report as report
from reporting.benchmark import (
    NS_PER_OP,
    PEAK_RSS_BYTES,
    BenchmarkSummary,
    CaseSummary,
    OutOfMemoryCase,
    load_out_of_memory_cases,
)
from reporting.html import build_html_out_of_memory_notice

ORCHESTRATOR_PATH = (
    MICROBENCHMARK_DIRECTORY
    / "orchestration"
    / "linux"
    / "orchestrate_attribute_key_scaling.py"
)
spec = importlib.util.spec_from_file_location(
    "attribute_orchestrator", ORCHESTRATOR_PATH
)
orchestrator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(orchestrator)


class TestConfig:
    runs = 2
    bench_output = "bench_output.txt"
    memory_output = "memory_output.txt"
    case_status = "case_status.txt"

    def integers(self, name):
        return {
            "ATTRIBUTE_COUNT": [1],
            "SUBSCRIBER_COUNT": [1],
            "RSA_KEY_SIZES": [2048],
        }[name]

    def integer(self, name):
        return {"KEYGEN_RUNS": 3}[name]


def build_summary(case_counts, feature_name):
    cases = {}

    for (operation, group, sweep_value), count in case_counts.items():
        case = CaseSummary(operation, group, sweep_value)

        for _ in range(count):
            case.add_run(1, {feature_name: 1.0})

        case.summarize()
        cases[f"{operation}/{group}/{sweep_value}"] = case

    return BenchmarkSummary(cases)


def complete_timing_summary():
    return build_summary(
        {
            ("encrypt", report.CPABE_ATTRIBUTES, 1): 2,
            ("decrypt", report.CPABE_ATTRIBUTES, 1): 2,
            ("encrypt", report.RSA_SUBSCRIBERS, 1): 2,
            ("encrypt", report.RSA_KEY_BITS, 2048): 2,
            ("decrypt", report.RSA_KEY_BITS, 2048): 2,
            ("keygen", report.RSA_KEY_BITS, 2048): 3,
        },
        NS_PER_OP,
    )


def complete_memory_summary():
    return build_summary(
        {
            ("baseline", report.BASELINE_GROUP, report.BASELINE_SWEEP_VALUE): 2,
            ("encrypt", report.CPABE_ATTRIBUTES, 1): 2,
            ("decrypt", report.CPABE_ATTRIBUTES, 1): 2,
            ("encrypt", report.RSA_SUBSCRIBERS, 1): 2,
            ("encrypt", report.RSA_KEY_BITS, 2048): 2,
            ("decrypt", report.RSA_KEY_BITS, 2048): 2,
        },
        PEAK_RSS_BYTES,
    )


class OrchestratorOomTests(unittest.TestCase):
    def test_controlled_oom_rules(self):
        self.assertTrue(orchestrator.is_out_of_memory(137, ""))
        self.assertTrue(orchestrator.is_out_of_memory(-9, ""))
        self.assertTrue(orchestrator.is_out_of_memory(2, "fatal error: out of memory"))
        self.assertFalse(orchestrator.is_out_of_memory(2, "ordinary panic"))
        self.assertFalse(orchestrator.is_out_of_memory(0, "out of memory"))

    def test_status_contains_only_the_whole_case(self):
        with tempfile.TemporaryDirectory() as directory:
            status_path = Path(directory) / "case_status.txt"
            status_path.write_text(
                "# operation group sweep_value out_of_memory\n", encoding="utf-8"
            )

            with patch.object(orchestrator, "STATUS_FILE", status_path):
                orchestrator.record_out_of_memory("Encrypt", "CPABEAttributes", 32)

            self.assertEqual(
                status_path.read_text(encoding="utf-8").splitlines(),
                [
                    "# operation group sweep_value out_of_memory",
                    "Encrypt CPABEAttributes 32 true",
                ],
            )

    def test_memory_and_provisioning_do_not_record_oom(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "memory_output.txt"
            status_path = Path(directory) / "case_status.txt"
            output_path.write_text("", encoding="utf-8")
            status_path.write_text(
                "# operation group sweep_value out_of_memory\n", encoding="utf-8"
            )

            completed = orchestrator.subprocess.CompletedProcess([], -9)

            with (
                patch.object(orchestrator, "STATUS_FILE", status_path),
                patch.object(orchestrator.subprocess, "run", return_value=completed),
            ):
                orchestrator.run_benchmark(
                    "MemoryEncrypt",
                    "CPABEAttributes",
                    32,
                    1,
                    output_path,
                    "1x",
                    1,
                )
                orchestrator.run_provision("CPABEAttributes", 32)

            self.assertEqual(
                status_path.read_text(encoding="utf-8"),
                "# operation group sweep_value out_of_memory\n",
            )
            self.assertFalse((Path(directory) / "case_logs").exists())

    def test_ordinary_timing_failures_do_not_create_status_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "bench_output.txt"
            status_path = Path(directory) / "case_status.txt"
            output_path.write_text("", encoding="utf-8")
            status_path.write_text(
                "# operation group sweep_value out_of_memory\n", encoding="utf-8"
            )

            for return_code in (0, 2):
                completed = orchestrator.subprocess.CompletedProcess(
                    [], return_code, stderr="ordinary panic"
                )

                with (
                    patch.object(orchestrator, "STATUS_FILE", status_path),
                    patch.object(
                        orchestrator.subprocess, "run", return_value=completed
                    ),
                ):
                    orchestrator.run_benchmark(
                        "Encrypt",
                        "CPABEAttributes",
                        32,
                        None,
                        output_path,
                        "5s",
                        2,
                        record_oom=True,
                    )

            self.assertEqual(
                status_path.read_text(encoding="utf-8"),
                "# operation group sweep_value out_of_memory\n",
            )


class ReportingTests(unittest.TestCase):
    def test_loads_four_field_oom_records(self):
        with tempfile.TemporaryDirectory() as directory:
            status_path = Path(directory) / "case_status.txt"
            status_path.write_text(
                "# operation group sweep_value out_of_memory\n"
                "Encrypt CPABEAttributes 32 true\n"
                "KeyGen RSAKeyBits 5120 true\n",
                encoding="utf-8",
            )

            cases = load_out_of_memory_cases(str(status_path))

            self.assertEqual(
                [(case.operation, case.group, case.sweep_value) for case in cases],
                [
                    ("Encrypt", "CPABEAttributes", 32),
                    ("KeyGen", "RSAKeyBits", 5120),
                ],
            )

    def test_complete_measurements_are_valid(self):
        self.assertEqual(
            report.validate_measurements(
                complete_timing_summary(),
                complete_memory_summary(),
                TestConfig(),
                [],
            ),
            [],
        )

    def test_timing_oom_allows_partial_rows_and_drops_the_case(self):
        timing = complete_timing_summary()
        timing.get_case_summary("encrypt", report.CPABE_ATTRIBUTES, 1).samples[
            NS_PER_OP
        ].pop()
        oom_cases = [OutOfMemoryCase("Encrypt", report.CPABE_ATTRIBUTES, 1)]

        self.assertEqual(
            report.validate_measurements(
                timing, complete_memory_summary(), TestConfig(), oom_cases
            ),
            [],
        )

        rows = report.apply_out_of_memory_cases(timing, oom_cases)

        self.assertFalse(timing.has_case("encrypt", report.CPABE_ATTRIBUTES, 1))
        self.assertEqual(
            rows,
            [["Encrypt", "CPABEAttributes/1", "Out of memory"]],
        )

    def test_unexplained_timing_count_is_invalid(self):
        timing = complete_timing_summary()
        timing.get_case_summary("encrypt", report.CPABE_ATTRIBUTES, 1).samples[
            NS_PER_OP
        ].pop()

        errors = report.validate_measurements(
            timing, complete_memory_summary(), TestConfig(), []
        )

        self.assertTrue(any("Encrypt CPABEAttributes/1" in error for error in errors))

    def test_any_memory_count_mismatch_is_invalid(self):
        for count in (1, 3):
            with self.subTest(count=count):
                memory = complete_memory_summary()
                case = memory.get_case_summary("encrypt", report.CPABE_ATTRIBUTES, 1)
                case.samples[PEAK_RSS_BYTES] = [1.0] * count

                errors = report.validate_measurements(
                    complete_timing_summary(), memory, TestConfig(), []
                )

                self.assertTrue(
                    any("MemoryEncrypt CPABEAttributes/1" in error for error in errors)
                )

    def test_invalid_measurements_stop_before_report_generation(self):
        timing = complete_timing_summary()
        timing.get_case_summary("encrypt", report.CPABE_ATTRIBUTES, 1).samples[
            NS_PER_OP
        ].pop()

        with io.StringIO() as stderr:
            with (
                patch.object(report, "Config", return_value=TestConfig()),
                patch.object(
                    report,
                    "load_results",
                    side_effect=[timing, complete_memory_summary()],
                ),
                patch.object(report, "load_out_of_memory_cases", return_value=[]),
                patch.object(report, "plot_sweep") as plot_sweep,
                patch.object(report, "write_html_report") as write_html_report,
                redirect_stderr(stderr),
                self.assertRaises(SystemExit),
            ):
                report.main()

            self.assertIn("Invalid benchmark result", stderr.getvalue())

        plot_sweep.assert_not_called()
        write_html_report.assert_not_called()

    def test_oom_notice_has_no_sample_or_exit_code(self):
        html = build_html_out_of_memory_notice(
            [["Encrypt", "CPABEAttributes/32", "Out of memory"]]
        )

        self.assertIn("Out of memory", html)
        self.assertNotIn("SAMPLE", html)
        self.assertNotIn("EXIT CODE", html)


if __name__ == "__main__":
    unittest.main()
