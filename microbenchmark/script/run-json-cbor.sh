#!/bin/sh

mkdir -p /results/json-cbor

echo 'Running JSON/CBOR Serialization benchmark...'

AttributeCountCount=$(echo "${JSON_CBOR_ATTRIBUTE_COUNTS}" | tr ',' '\n' | wc -l)
SerializeCases=$((3 * AttributeCountCount))
DeserializeCases=$((3 * AttributeCountCount))
SerializeDeserializeCases=$((SerializeCases + DeserializeCases))
BenchmarkLines=$((SerializeDeserializeCases * JSON_CBOR_RUNS))
FixedOverheadLines=6
TotalLines=$((BenchmarkLines + FixedOverheadLines))

./benchmark-binary \
  -test.run=^$ \
  -test.bench='^BenchmarkEnvelope(Serialize|Deserialize)$' \
  -test.benchtime=5s \
  -test.count=${JSON_CBOR_RUNS} \
  | pv \
      --force \
      --wait \
      --line-mode \
      --size "${TotalLines}" \
      --interval 5 \
      --format "JSON vs CBOR: %p %t" \
      > /results/json-cbor/bench_output.txt

echo 'Generating JSON/CBOR Serialization HTML report...'

python3 src/json_cbor_report.py