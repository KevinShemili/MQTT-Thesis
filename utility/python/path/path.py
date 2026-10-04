from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ENVIRONMENT_FILE = PROJECT_ROOT / "environment" / "benchmark.env"

TEMPLATE_DIR = PROJECT_ROOT / "report" / "template"
REPORT_NAME = "report.html"

TIMING_TEXT_NAME = "timing.txt"
MEMORY_TEXT_NAME = "memory.txt"

TIMING_RESULT_NAME = "timing.csv"
MEMORY_RESULT_NAME = "memory.csv"
ENERGY_RESULT_NAME = "energy.csv"

PUBLISHER_RESULT_NAME = "publisher.csv"
SUBSCRIBER_RESULT_NAME = "subscriber.csv"

SSH_TARGET = "pi"

REMOTE_GO_EXECUTABLE = "/usr/local/go/bin/go"
REMOTE_COOLDOWN_BINARY = "/tmp/benchmark-cooldown"
REMOTE_PROJECT_DIRECTORY = "/home/thesis/MQTT-Thesis"
REMOTE_BENCHMARK_DIRECTORY = f"{REMOTE_PROJECT_DIRECTORY}/benchmark"
REMOTE_ENVIRONMENT_FILE = f"{REMOTE_PROJECT_DIRECTORY}/environment/benchmark.env"
