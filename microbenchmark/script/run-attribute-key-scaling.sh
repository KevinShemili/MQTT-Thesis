#!/bin/sh
set -eu

ResultDirectory=/results/attribute-key-scaling
OutputFile="${ResultDirectory}/bench_output.txt"
MemoryOutputFile="${ResultDirectory}/memory_output.txt"
StatusFile="${ResultDirectory}/case_status.txt"
LogDirectory="${ResultDirectory}/case_logs"

rm -rf key-cache "${LogDirectory}" # ensure old keys and old logs are not used in PI

mkdir -p "${ResultDirectory}" "${LogDirectory}"
: > "${OutputFile}"
: > "${MemoryOutputFile}"
printf '# operation group sweep_value sample exit_code log_file\n' > "${StatusFile}"

# One exact case in its own process. Its stdout joins the raw output of the experiment it
# belongs to, its stderr is kept whole in a file of its own, and the code it exited with
# is recorded beside the name of that file. What the pair means is the report's to decide
RunBenchmark() {
  Operation=$1
  Group=$2
  SweepValue=$3
  Sample=$4
  OutputTarget=$5
  BenchTime=$6
  Count=$7

  LogFile="${Operation}-${Group}-${SweepValue}-${Sample}.log"

  echo "  ${Operation} ${Group}/${SweepValue} #${Sample}"

  set +e
  ./benchmark-binary \
    -test.run='^$' \
    -test.bench="^BenchmarkAttributeKeyScaling${Operation}\$/^${Group}\$/^${SweepValue}\$" \
    -test.benchtime="${BenchTime}" \
    -test.count="${Count}" \
    -test.timeout=0 \
    >> "${OutputTarget}" 2> "${LogDirectory}/${LogFile}"
  ExitCode=$?
  set -e

  printf '%s %s %s %d %d %s\n' \
    "${Operation}" "${Group}" "${SweepValue}" "${Sample}" "${ExitCode}" "${LogFile}" \
    >> "${StatusFile}"
}

# The program that builds one case's prerequisites, recorded the same way so that a
# failure to provision is attributable to the case it would have served
RunProvision() {
  Group=$1
  SweepValue=$2

  LogFile="Provision-${Group}-${SweepValue}-1.log"

  echo "  Provision ${Group}/${SweepValue}"

  set +e
  ./provision-binary "${Group}" "${SweepValue}" > "${LogDirectory}/${LogFile}" 2>&1
  ExitCode=$?
  set -e

  printf '%s %s %s %d %d %s\n' \
    'Provision' "${Group}" "${SweepValue}" 1 "${ExitCode}" "${LogFile}" \
    >> "${StatusFile}"
}

# Peak resident memory belongs to a process, so a second sample has to come from a second
# process that has never allocated before. Prerequisites are built once, ahead of them all
RunMemoryCase() {
  Group=$1
  SweepValue=$2

  RunProvision "${Group}" "${SweepValue}"

  Sample=1
  while [ "${Sample}" -le "${ATTRIBUTE_KEY_SCALING_RUNS}" ]; do
    RunBenchmark MemoryEncrypt "${Group}" "${SweepValue}" "${Sample}" "${MemoryOutputFile}" 1x 1
    RunBenchmark MemoryDecrypt "${Group}" "${SweepValue}" "${Sample}" "${MemoryOutputFile}" 1x 1
    Sample=$((Sample + 1))
  done
}

echo 'Phase 1 of 4 - CP-ABE attribute scaling'

for AttributeCount in $(echo "${ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT}" | tr ',' ' '); do
  RunBenchmark Encrypt CPABEAttributes "${AttributeCount}" 1 "${OutputFile}" 5s "${ATTRIBUTE_KEY_SCALING_RUNS}"
  RunBenchmark Decrypt CPABEAttributes "${AttributeCount}" 1 "${OutputFile}" 5s "${ATTRIBUTE_KEY_SCALING_RUNS}"
done

echo 'Phase 2 of 4 - RSA subscriber and key-size scaling'

for SubscriberCount in $(echo "${ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT}" | tr ',' ' '); do
  RunBenchmark Encrypt RSASubscribers "${SubscriberCount}" 1 "${OutputFile}" 5s "${ATTRIBUTE_KEY_SCALING_RUNS}"
  RunBenchmark Decrypt RSASubscribers "${SubscriberCount}" 1 "${OutputFile}" 5s "${ATTRIBUTE_KEY_SCALING_RUNS}"
done

for RSAKeyBits in $(echo "${ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES}" | tr ',' ' '); do
  RunBenchmark Encrypt RSAKeyBits "${RSAKeyBits}" 1 "${OutputFile}" 5s "${ATTRIBUTE_KEY_SCALING_RUNS}"
  RunBenchmark Decrypt RSAKeyBits "${RSAKeyBits}" 1 "${OutputFile}" 5s "${ATTRIBUTE_KEY_SCALING_RUNS}"
done

echo 'Phase 3 of 4 - RSA key generation'

for RSAKeyBits in $(echo "${ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES}" | tr ',' ' '); do
  RunBenchmark KeyGen RSAKeyBits "${RSAKeyBits}" 1 "${OutputFile}" 1x "${ATTRIBUTE_KEY_SCALING_KEYGEN_RUNS}"
done

echo 'Phase 4 of 4 - Peak process memory'

for AttributeCount in $(echo "${ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT}" | tr ',' ' '); do
  RunMemoryCase CPABEAttributes "${AttributeCount}"
done

for SubscriberCount in $(echo "${ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT}" | tr ',' ' '); do
  RunMemoryCase RSASubscribers "${SubscriberCount}"
done

for RSAKeyBits in $(echo "${ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES}" | tr ',' ' '); do
  RunMemoryCase RSAKeyBits "${RSAKeyBits}"
done

echo 'Generating Attribute & Key Scaling HTML report...'

python3 src/attribute_key_scaling_report.py
