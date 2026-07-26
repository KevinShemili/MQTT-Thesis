#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)

cd "${PROJECT_DIR}"

run_service() {
  service_name=$1

  echo "Building ${service_name}..."
  docker compose build "${service_name}"

  echo "Running ${service_name}..."
  docker compose run --rm "${service_name}"
}

run_service aes-ascon-with-acceleration
run_service aes-ascon-without-acceleration
run_service json-cbor
run_service payload-scaling
run_service attribute-key-scaling

echo 'All benchmark scenarios completed successfully.'