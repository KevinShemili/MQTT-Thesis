#!/bin/sh

mkdir -p /results/payload-scaling

echo 'Running Payload Size Scaling benchmark...'

PayloadSizeCount=$(echo "${PAYLOAD_SCALING_PAYLOAD_SIZES}" | tr ',' '\n' | wc -l)
TotalLines=$((2 * 3 * PayloadSizeCount * PAYLOAD_SCALING_RUNS))

./benchmark-binary \
  -test.run=^$ \
  -test.bench=^BenchmarkPayloadScaling \
  -test.benchtime=5s \
  -test.count=${PAYLOAD_SCALING_RUNS} \
  -test.cpu=1 \
  | pv \
      --force \
      --wait \
      --line-mode \
      --size "${TotalLines}" \
      --interval 5 \
      --format "Payload Scaling: %p %e" \
      > /results/payload-scaling/bench_output.txt

echo 'Generating Payload Size Scaling HTML report...'

python3 src/payload_scaling_report.py