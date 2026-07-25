#!/bin/sh

mkdir -p /results/payload-scaling

echo 'Running Payload Size Scaling benchmark...'

PayloadSizeCount=$(echo "${PAYLOAD_SCALING_PAYLOAD_SIZES}" | tr ',' '\n' | wc -l)
EncryptCases=$((3 * PayloadSizeCount))
DecryptCases=$((3 * PayloadSizeCount))
EncryptDecryptCases=$((EncryptCases + DecryptCases))
EncryptDecryptLines=$((EncryptDecryptCases * PAYLOAD_SCALING_RUNS))
FixedOverheadLines=6
TotalLines=$((EncryptDecryptLines + FixedOverheadLines))

./benchmark-binary \
  -test.run=^$ \
  -test.bench='^BenchmarkPayloadScaling(Encrypt|Decrypt)$' \
  -test.benchtime=5s \
  -test.count=${PAYLOAD_SCALING_RUNS} \
  | pv \
      --force \
      --wait \
      --line-mode \
      --size "${TotalLines}" \
      --interval 5 \
      --format "Payload Scaling: %p %t" \
      > /results/payload-scaling/bench_output.txt

echo 'Generating Payload Size Scaling HTML report...'

python3 src/payload_scaling_report.py