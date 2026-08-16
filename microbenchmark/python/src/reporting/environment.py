import os
from pathlib import Path
from .statistics import get_student_t_critical_95

DEFAULT_RESULT_ROOT = "/results"

# The templates ship beside the reporting code, two directories above this one, so a
# report renders the same whether it is run from the image or from a clone on a host
TEMPLATE_DIR = str(Path(__file__).resolve().parents[2] / "template")
BENCH_OUTPUT_NAME = "bench_output.txt"
MEMORY_OUTPUT_NAME = "memory_output.txt"
CASE_STATUS_NAME = "case_status.txt"
CASE_LOG_DIR_NAME = "case_logs"
REPORT_NAME = "report.html"


# Reads environment variables, single values
def parse_int_env(name: str) -> int:
    return int(os.environ[name].strip())


# Reads environment variables, list values
def parse_int_list_env(name: str) -> list[int]:
    return [int(part.strip()) for part in os.environ[name].split(",")]


# Everything one benchmark scenario is configured with: how many times it was run, the
# t multiplier that follows from that, the files it reads and writes, and the sweep
# values it was given. All of it comes from the environment variables the scenario
# shares with the Go benchmark, which are prefixed by scenario, ex.
# "ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT" is reached as integers("SUBSCRIBER_COUNT")
class Config:
    def __init__(self, scenario: str, template_name: str, prefix: str) -> None:

        self.scenario = scenario
        self.prefix = prefix

        # Parsed environment values are kept so that repeatedly asking for the
        # same sweep does not re-read and re-split the variable every time
        self._values: dict[str, int | list[int]] = {}

        self.runs = self.integer("RUNS")
        self.t_critical = get_student_t_critical_95(self.runs - 1)

        # A scenario that is measured more than once, ex. AES with and without
        # hardware acceleration, redirects its results with <PREFIX>_RESULT_DIR
        self.result_dir = os.environ.get(
            f"{prefix}_RESULT_DIR",
            f"{DEFAULT_RESULT_ROOT}/{scenario}",
        )

        self.bench_output = os.path.join(self.result_dir, BENCH_OUTPUT_NAME)

        # Peak memory is a separate experiment from timing and keeps its own raw file,
        # so neither parser has to defend itself against the other's rows. The status
        # file and the logs beside it are what the orchestrator recorded per process
        self.memory_output = os.path.join(self.result_dir, MEMORY_OUTPUT_NAME)
        self.case_status = os.path.join(self.result_dir, CASE_STATUS_NAME)
        self.case_logs = os.path.join(self.result_dir, CASE_LOG_DIR_NAME)

        self.report = os.path.join(self.result_dir, REPORT_NAME)
        self.template = os.path.join(TEMPLATE_DIR, template_name)

    def integer(self, name: str) -> int:
        if name not in self._values:
            self._values[name] = parse_int_env(f"{self.prefix}_{name}")

        return self._values[name]  # type: ignore

    def integers(self, name: str) -> list[int]:
        if name not in self._values:
            self._values[name] = parse_int_list_env(f"{self.prefix}_{name}")

        return self._values[name]  # type: ignore

    def figure(self, filename: str) -> str:
        return os.path.join(self.result_dir, filename)
