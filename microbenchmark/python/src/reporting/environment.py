import os
from dataclasses import dataclass

DEFAULT_RESULT_ROOT = "/results"
DEFAULT_TEMPLATE_DIR = "/app/template"
TEMPLATE_DIR_VAR = "TEMPLATE_DIR"
BENCH_OUTPUT_NAME = "bench_output.txt"
REPORT_NAME = "report.html"


# Reads environment variables, single values
def parse_int_env(name: str) -> int:
    return int(os.environ[name].strip())


# Reads environment variables, list values
def parse_int_list_env(name: str) -> list[int]:
    return [int(part.strip()) for part in os.environ[name].split(",")]


# Groups all file paths used by one benchmark scenario
@dataclass(frozen=True)
class FilePaths:
    result_dir: str
    bench_output: str
    report: str
    template: str

    def figure(self, filename: str) -> str:
        return os.path.join(self.result_dir, filename)


# Resolves all standard file paths required by one benchmark scenario
def resolve_paths(scenario: str, result_dir_var: str, template_name: str) -> FilePaths:
    result_dir = os.environ.get(result_dir_var, f"{DEFAULT_RESULT_ROOT}/{scenario}")
    template_dir = os.environ.get(TEMPLATE_DIR_VAR, DEFAULT_TEMPLATE_DIR)

    return FilePaths(
        result_dir=result_dir,
        bench_output=os.path.join(result_dir, BENCH_OUTPUT_NAME),
        report=os.path.join(result_dir, REPORT_NAME),
        template=os.path.join(template_dir, template_name),
    )
