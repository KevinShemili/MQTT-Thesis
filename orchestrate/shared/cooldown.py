import subprocess

from utility.python.path.path import (
    REMOTE_COOLDOWN_BINARY,
    REMOTE_ENVIRONMENT_FILE,
    REMOTE_PROJECT_DIRECTORY,
    SSH_TARGET,
)


def wait_for_cooldown():
    command = (
        f"cd {REMOTE_PROJECT_DIRECTORY} && "
        f"set -a && "
        f". {REMOTE_ENVIRONMENT_FILE} && "
        f"set +a && "
        f"{REMOTE_COOLDOWN_BINARY}"
    )

    subprocess.run(
        ["ssh", SSH_TARGET, command],
        check=True,
    )
