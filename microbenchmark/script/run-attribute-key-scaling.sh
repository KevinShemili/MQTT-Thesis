#!/bin/sh
set -eu

mkdir -p /results/attribute-key-scaling

echo 'Running Attribute & Key Scaling benchmark...'

AttributeCountCount=$(echo "${ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT}" | tr ',' '\n' | wc -l)
RecipientCountCount=$(echo "${ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT}" | tr ',' '\n' | wc -l)
RSAKeyBitsCount=$(echo "${ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES}" | tr ',' '\n' | wc -l)
EncryptCases=$((AttributeCountCount + RecipientCountCount + RSAKeyBitsCount))
DecryptCases=$((AttributeCountCount + RecipientCountCount + RSAKeyBitsCount))
EncryptDecryptCases=$((EncryptCases + DecryptCases))
KeyGenCases=$((AttributeCountCount + RSAKeyBitsCount))
EncryptDecryptLines=$((EncryptDecryptCases * ATTRIBUTE_KEY_SCALING_RUNS))
KeyGenLines=$((KeyGenCases * ATTRIBUTE_KEY_SCALING_RUNS))
# 4 header lines (goos/goarch/pkg/cpu) + 1 PASS, per binary invocation
FixedOverheadLines=10
TotalLines=$((EncryptDecryptLines + KeyGenLines + FixedOverheadLines))

{
  ./benchmark-binary \
    -test.run=^$ \
    -test.bench='^BenchmarkAttributeKeyScaling(Encrypt|Decrypt)$' \
    -test.benchtime=5s \
    -test.count=${ATTRIBUTE_KEY_SCALING_RUNS}

  ./benchmark-binary \
    -test.run=^$ \
    -test.bench=^BenchmarkAttributeKeyScalingKeyGen$ \
    -test.benchtime=20x \
    -test.count=${ATTRIBUTE_KEY_SCALING_RUNS}
} | pv \
    --force \
    --wait \
    --line-mode \
    --size "${TotalLines}" \
    --interval 5 \
    --format "Attribute & Key Scaling: %p %t" \
    > /results/attribute-key-scaling/bench_output.txt

echo 'Generating Attribute & Key Scaling HTML report...'

python3 src/attribute_key_scaling_report.py
