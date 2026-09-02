package json_cbor

import (
	"benchmark/cryptography/aes"
	"benchmark/cryptography/cpabe"
	"benchmark/envelope"
	"benchmark/micro/json_cbor/shared"
	"benchmark/thermal"
	"benchmark/utility"
	"fmt"
	"testing"
	"time"
)

var (
	warmupDuration = time.Duration(utility.ParseIntFromEnv("WARMUP_DURATION")) * time.Second
	tailDuration   = time.Duration(utility.ParseIntFromEnv("TAIL_DURATION")) * time.Second
)

func BenchmarkEnvelopeEnergySerialize(benchmark *testing.B) {

	config := shared.NewJSONCBORConfig()

	// Scenario 1: JSON Scaling Attribute Count
	for _, attributeCount := range config.AttributeCounts {

		benchmark.Run(fmt.Sprintf("JSON/%dAttrs", attributeCount), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aes := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(config.PayloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Encrypt payload
			aesCiphertext := aes.Seal(nil, nonce, plaintext, nil)

			// Build policy for given attribute count
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				ABECiphertext: abeCiphertext,
				Nonce:         nonce,
				AESCiphertext: aesCiphertext,
			}

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				envelope.SerializeJSON(env)
			}

			// Actually measure this region
			for b.Loop() {
				envelope.SerializeJSON(env)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				envelope.SerializeJSON(env)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 2: CBOR Scaling Attribute Count
	for _, attributeCount := range config.AttributeCounts {

		benchmark.Run(fmt.Sprintf("CBOR/%dAttrs", attributeCount), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aes := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(config.PayloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Encrypt payload
			aesCiphertext := aes.Seal(nil, nonce, plaintext, nil)

			// Build policy for given attribute count
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				ABECiphertext: abeCiphertext,
				Nonce:         nonce,
				AESCiphertext: aesCiphertext,
			}

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				envelope.SerializeCBOR(env)
			}

			// Actually measure this region
			for b.Loop() {
				envelope.SerializeCBOR(env)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				envelope.SerializeCBOR(env)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 3: CBOR With Integer Keys Scaling Attribute Count
	for _, attributeCount := range config.AttributeCounts {

		benchmark.Run(fmt.Sprintf("CBORKeyAsInt/%dAttrs", attributeCount), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aes := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(config.PayloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Encrypt payload
			aesCiphertext := aes.Seal(nil, nonce, plaintext, nil)

			// Build policy for given attribute count
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope using integer keys
			env := envelope.EnvelopeIntKeys{
				ABECiphertext: abeCiphertext,
				Nonce:         nonce,
				AESCiphertext: aesCiphertext,
			}

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				envelope.SerializeCBORKeyAsInt(env)
			}

			// Actually measure this region
			for b.Loop() {
				envelope.SerializeCBORKeyAsInt(env)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				envelope.SerializeCBORKeyAsInt(env)
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

	// Scenario 1: JSON Scaling Attribute Count
	for _, attributeCount := range config.AttributeCounts {

		benchmark.Run(fmt.Sprintf("JSON/%dAttrs", attributeCount), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aes := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(config.PayloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Encrypt payload
			aesCiphertext := aes.Seal(nil, nonce, plaintext, nil)

			// Build policy for given attribute count
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				ABECiphertext: abeCiphertext,
				Nonce:         nonce,
				AESCiphertext: aesCiphertext,
			}

			// Serialize outside measured workload so only deserialization is measured
			serializedEnvelope := envelope.SerializeJSON(env)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				envelope.DeserializeJSON(serializedEnvelope)
			}

			// Actually measure this region
			for b.Loop() {
				envelope.DeserializeJSON(serializedEnvelope)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				envelope.DeserializeJSON(serializedEnvelope)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 2: CBOR Scaling Attribute Count
	for _, attributeCount := range config.AttributeCounts {

		benchmark.Run(fmt.Sprintf("CBOR/%dAttrs", attributeCount), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aes := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(config.PayloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Encrypt payload
			aesCiphertext := aes.Seal(nil, nonce, plaintext, nil)

			// Build policy for given attribute count
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				ABECiphertext: abeCiphertext,
				Nonce:         nonce,
				AESCiphertext: aesCiphertext,
			}

			// Serialize outside measured workload so only deserialization is measured
			serializedEnvelope := envelope.SerializeCBOR(env)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				envelope.DeserializeCBOR(serializedEnvelope)
			}

			// Actually measure this region
			for b.Loop() {
				envelope.DeserializeCBOR(serializedEnvelope)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				envelope.DeserializeCBOR(serializedEnvelope)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 3: CBOR With Integer Keys Scaling Attribute Count
	for _, attributeCount := range config.AttributeCounts {

		benchmark.Run(fmt.Sprintf("CBORKeyAsInt/%dAttrs", attributeCount), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aes := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(config.PayloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Encrypt payload
			aesCiphertext := aes.Seal(nil, nonce, plaintext, nil)

			// Build policy for given attribute count
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope using integer keys
			env := envelope.EnvelopeIntKeys{
				ABECiphertext: abeCiphertext,
				Nonce:         nonce,
				AESCiphertext: aesCiphertext,
			}

			// Serialize outside measured workload so only deserialization is measured
			serializedEnvelope := envelope.SerializeCBORKeyAsInt(env)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				envelope.DeserializeCBORKeyAsInt(serializedEnvelope)
			}

			// Actually measure this region
			for b.Loop() {
				envelope.DeserializeCBORKeyAsInt(serializedEnvelope)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				envelope.DeserializeCBORKeyAsInt(serializedEnvelope)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}
