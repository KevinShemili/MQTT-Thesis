package json_cbor

import (
	"fmt"
	"testing"
	"thesis/benchmark/cryptography/aes"
	"thesis/benchmark/cryptography/cpabe"
	"thesis/benchmark/micro/json_cbor/shared"
	"thesis/benchmark/thermal"
	"thesis/benchmark/utility"
	"thesis/internal/envelope"
	"thesis/internal/serialization"
	"time"
)

var (
	warmupDuration = time.Duration(utility.ParseIntFromEnv("WARMUP_DURATION")) * time.Second
	tailDuration   = time.Duration(utility.ParseIntFromEnv("TAIL_DURATION")) * time.Second
)

func BenchmarkEnvelopeEnergySerialize(benchmark *testing.B) {

	config := shared.NewJSONCBORConfig()

	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	// Scenario 1: JSON Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("JSON/%dB", payloadSize), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aes := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Encrypt payload
			aesCiphertext := aes.Seal(nil, nonce, plaintext, nil)

			// Build the fixed CP-ABE policy used by every payload-size case
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.CPABEAttributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				AsymmetricCiphertext: abeCiphertext,
				Nonce:                nonce,
				SymmetricCiphertext:  aesCiphertext,
			}

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				jsonSerializer.Serialize(env)
			}
			// Actually measure this region
			for b.Loop() {
				jsonSerializer.Serialize(env)
			}
			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				jsonSerializer.Serialize(env)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 2: CBOR Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CBOR/%dB", payloadSize), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aes := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Encrypt payload
			aesCiphertext := aes.Seal(nil, nonce, plaintext, nil)

			// Build the fixed CP-ABE policy used by every payload-size case
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.CPABEAttributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				AsymmetricCiphertext: abeCiphertext,
				Nonce:                nonce,
				SymmetricCiphertext:  aesCiphertext,
			}

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				cborSerializer.Serialize(env)
			}
			// Actually measure this region
			for b.Loop() {
				cborSerializer.Serialize(env)
			}
			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				cborSerializer.Serialize(env)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 3: CBOR With Integer Keys Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CBORKeyAsInt/%dB", payloadSize), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aes := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Encrypt payload
			aesCiphertext := aes.Seal(nil, nonce, plaintext, nil)

			// Build the fixed CP-ABE policy used by every payload-size case
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.CPABEAttributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope using integer keys
			env := envelope.EnvelopeIntKeys{
				AsymmetricCiphertext: abeCiphertext,
				Nonce:                nonce,
				SymmetricCiphertext:  aesCiphertext,
			}

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				cborSerializer.Serialize(env)

			}
			// Actually measure this region
			for b.Loop() {
				cborSerializer.Serialize(env)

			}
			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				cborSerializer.Serialize(env)

			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}

func BenchmarkEnvelopeEnergyDeserialize(benchmark *testing.B) {

	config := shared.NewJSONCBORConfig()

	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	// Scenario 1: JSON Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("JSON/%dB", payloadSize), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aes := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Encrypt payload
			aesCiphertext := aes.Seal(nil, nonce, plaintext, nil)

			// Build the fixed CP-ABE policy used by every payload-size case
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.CPABEAttributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				AsymmetricCiphertext: abeCiphertext,
				Nonce:                nonce,
				SymmetricCiphertext:  aesCiphertext,
			}

			// Serialize outside measured workload so only deserialization is measured
			serializedEnvelope, _ := jsonSerializer.Serialize(env)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				var decoded envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &decoded)
			}

			// Actually measure this region
			for b.Loop() {
				var decoded envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &decoded)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				var decoded envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &decoded)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 2: CBOR Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CBOR/%dB", payloadSize), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aes := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Encrypt payload
			aesCiphertext := aes.Seal(nil, nonce, plaintext, nil)

			// Build the fixed CP-ABE policy used by every payload-size case
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.CPABEAttributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				AsymmetricCiphertext: abeCiphertext,
				Nonce:                nonce,
				SymmetricCiphertext:  aesCiphertext,
			}

			// Serialize outside measured workload so only deserialization is measured
			serializedEnvelope, _ := cborSerializer.Serialize(env)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				var decoded envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &decoded)
			}

			// Actually measure this region
			for b.Loop() {
				var decoded envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &decoded)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				var decoded envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &decoded)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 3: CBOR With Integer Keys Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CBORKeyAsInt/%dB", payloadSize), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aes := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Encrypt payload
			aesCiphertext := aes.Seal(nil, nonce, plaintext, nil)

			// Build the fixed CP-ABE policy used by every payload-size case
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.CPABEAttributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope using integer keys
			env := envelope.EnvelopeIntKeys{
				AsymmetricCiphertext: abeCiphertext,
				Nonce:                nonce,
				SymmetricCiphertext:  aesCiphertext,
			}

			// Serialize outside measured workload so only deserialization is measured
			serializedEnvelope, _ := cborSerializer.Serialize(env)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				var decoded envelope.EnvelopeIntKeys
				cborSerializer.Deserialize(serializedEnvelope, &decoded)
			}

			// Actually measure this region
			for b.Loop() {
				var decoded envelope.EnvelopeIntKeys
				cborSerializer.Deserialize(serializedEnvelope, &decoded)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				var decoded envelope.EnvelopeIntKeys
				cborSerializer.Deserialize(serializedEnvelope, &decoded)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}
