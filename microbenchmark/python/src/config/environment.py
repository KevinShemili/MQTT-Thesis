import os
from pathlib import Path

DEFAULT_RESULT_ROOT = "/results"

# The templates ship beside the reporting code, two directories above this one, so a
# report renders the same whether it is run from the image or from a clone on a host
TEMPLATE_DIR = str(Path(__file__).resolve().parents[2] / "template")
BENCH_OUTPUT_NAME = "bench_output.txt"
MEMORY_OUTPUT_NAME = "memory_output.txt"
CASE_STATUS_NAME = "case_status.txt"
REPORT_NAME = "report.html"


# Reads environment variables, single values
def parse_int_env(name: str) -> int:
    return int(os.environ[name].strip())


# Reads environment variables, list values
def parse_int_list_env(name: str) -> list[int]:
    return [int(part.strip()) for part in os.environ[name].split(",")]
