import os
from dataclasses import dataclass

DEFAULT_RESULT_ROOT = "/results"
TEMPLATE_DIR = "/app/template"
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
def resolve_paths(
    scenario: str,
    template_name: str,
    result_dir_var: str | None = None,
) -> FilePaths:

    default_result_dir = f"{DEFAULT_RESULT_ROOT}/{scenario}"
    result_dir = (
        default_result_dir
        if result_dir_var is None
        else os.environ.get(result_dir_var, default_result_dir)
    )

    return FilePaths(
        result_dir=result_dir,
        bench_output=os.path.join(result_dir, BENCH_OUTPUT_NAME),
        report=os.path.join(result_dir, REPORT_NAME),
        template=os.path.join(TEMPLATE_DIR, template_name),
    )
