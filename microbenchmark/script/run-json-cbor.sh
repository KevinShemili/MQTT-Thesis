#!/bin/sh

mkdir -p /results/json-cbor

echo 'Running JSON/CBOR Serialization benchmark...'

AttributeCountCount=$(echo "${JSON_CBOR_ATTRIBUTE_COUNTS}" | tr ',' '\n' | wc -l)
TotalLines=$((2 * 2 * AttributeCountCount * JSON_CBOR_RUNS))

./benchmark-binary \
  -test.run=^$ \
  -test.bench=^BenchmarkEnvelope \
  -test.benchtime=5s \
  -test.benchmem \
  -test.count=${JSON_CBOR_RUNS} \
  -test.cpu=1 \
  | pv \
      --force \
      --wait \
      --line-mode \
      --size "${TotalLines}" \
      --interval 5 \
      --format "JSON vs CBOR: %p %e" \
      > /results/json-cbor/bench_output.txt

echo 'Generating JSON/CBOR Serialization HTML report...'

python3 src/json_cbor_report.py