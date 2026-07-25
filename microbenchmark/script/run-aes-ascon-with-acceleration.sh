#!/bin/sh

set -eu

ResultDirectory="/results/aes-ascon/with-acceleration"

mkdir -p "${ResultDirectory}"

echo 'Running AES vs ASCON benchmark with hardware acceleration...'

PayloadSizeCount=$(echo "${AES_ASCON_PAYLOAD_SIZES}" | tr ',' '\n' | wc -l)
BenchmarkLines=$((2 * 2 * PayloadSizeCount * AES_ASCON_RUNS))
FixedOverheadLines=6
TotalLines=$((BenchmarkLines + FixedOverheadLines))

GODEBUG="" ./benchmark-binary \
  -test.run=^$ \
  -test.bench=^BenchmarkAESASCON \
  -test.benchtime=5s \
  -test.benchmem \
  -test.count="${AES_ASCON_RUNS}" \
  | pv \
      --force \
      --wait \
      --line-mode \
      --size "${TotalLines}" \
      --interval 5 \
      --format "AES vs ASCON with acceleration: %p %e" \
      > "${ResultDirectory}/bench_output.txt"

echo 'Generating AES vs ASCON HTML report with hardware acceleration...'

AES_ASCON_RESULT_DIR="${ResultDirectory}" python3 src/aes_ascon_report.py
