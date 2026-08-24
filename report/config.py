import os
from pathlib import Path

DEFAULT_RESULT_ROOT = "/results"

TEMPLATE_DIR = str(Path(__file__).resolve().parent / "template")

BENCH_OUTPUT_NAME = "bench_output.txt"
MEMORY_OUTPUT_NAME = "memory_output.txt"
CASE_STATUS_NAME = "case_status.txt"
REPORT_NAME = "report.html"


def parse_int_env(name: str) -> int:
    return int(os.environ[name].strip())


def parse_int_list_env(name: str) -> list[int]:
    return [int(part.strip()) for part in os.environ[name].split(",")]
