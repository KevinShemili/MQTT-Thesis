from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENVIRONMENT_FILE = PROJECT_ROOT / "environment" / "benchmark.env"

SSH_TARGET = "pi"

REMOTE_PROJECT_DIRECTORY = "/home/thesis/MQTT-Thesis"
REMOTE_BENCHMARK_DIRECTORY = f"{REMOTE_PROJECT_DIRECTORY}/benchmark"
REMOTE_ENVIRONMENT_FILE = f"{REMOTE_PROJECT_DIRECTORY}/environment/benchmark.env"
REMOTE_CACHE_DIRECTORY = f"{REMOTE_PROJECT_DIRECTORY}/disk-cache"
