package attribute_key_scaling

import (
	"benchmark/cryptography/cpabe"
	"benchmark/cryptography/rsa"
	"benchmark/micro/attribute_key_scaling/shared"
	"benchmark/thermal"
	"benchmark/utility"
	"fmt"
	"testing"
)

func BenchmarkAttributeKeyScalingEncrypt(benchmark *testing.B) {

	config := shared.NewAttributeKeyScalingConfig()

	// Scenario 1: Scaling attribute count in CP-ABE
	for _, attributeCount := range config.AttributeCounts {

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {

			// Instantiate authority
			authority := cpabe.NewCPABEAuthority()

			// Build policy for given attribute number
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

			// True cryptographic realism is not necessary here,
			// hence no need to regenerate a symmetric key for each new encryption
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)

			// Ciphertext size is fixed, so measured once outside timed loop
			asymmetricCiphertextSize := len(authority.Encrypt(abePolicy, symmetricKey))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				authority.Encrypt(abePolicy, symmetricKey)
			}

			b.ReportMetric(float64(asymmetricCiphertextSize), "ciphertext_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 2: Scaling subscriber count in RSA
	for _, subscriberCount := range config.SubscriberCounts {

		benchmark.Run(fmt.Sprintf("RSASubscribers/%d", subscriberCount), func(b *testing.B) {

			publicKeySlice := shared.LoadRSAKeysFromInMemoryCache(config.FixedRSAKeyBits, subscriberCount)
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)

			// Size of a single wrapped key
			// - Directly comparable with CP-ABE's single ciphertext
			asymmetricCiphertextSize := len(publicKeySlice[0].Encrypt(symmetricKey))

			// However, in RSA each sub gets own key
			totalAsymmetricCiphertextSize := subscriberCount * asymmetricCiphertextSize

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				for index := range subscriberCount {
					publicKeySlice[index].Encrypt(symmetricKey)
				}
			}

			b.ReportMetric(float64(asymmetricCiphertextSize), "ciphertext_bytes")

			b.ReportMetric(float64(totalAsymmetricCiphertextSize), "total_ciphertext_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 3: Scaling key size in RSA
	for _, rsaKeyBits := range config.RSAKeyBits {

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

			// Get just 1 RSA key of the specified size
			publicKey := shared.LoadRSAKeysFromInMemoryCache(rsaKeyBits, 1)[0]
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)

			// Ciphertext size is fixed, so measured once outside timed loop
			asymmetricCiphertextSize := len(publicKey.Encrypt(symmetricKey))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				publicKey.Encrypt(symmetricKey)
			}

			b.ReportMetric(float64(asymmetricCiphertextSize), "ciphertext_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}

func BenchmarkAttributeKeyScalingDecrypt(benchmark *testing.B) {

	config := shared.NewAttributeKeyScalingConfig()

	// Scenario 1: CP-ABE scaling attribute count
	for _, attributeCount := range config.AttributeCounts {

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {

			// Instantiate authority
			authority := cpabe.NewCPABEAuthority()

			// Create synthetic policy and attributes for given attribute count
			abePolicy, abeAttributes := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)

			// Create private key based on attributes
			privateKey := authority.IssuePrivateKey(abeAttributes)

			// Create ciphertext based on policy to measure decryption cost
			asymmetricCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Measure size of created private key, relevant as it is attribute count dependent
			privateKeySize := privateKey.StoredPrivateKeySize()

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				privateKey.Decrypt(asymmetricCiphertext)
			}

			b.ReportMetric(float64(privateKeySize), "stored_key_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 2: RSA scaling key size
	for _, rsaKeyBits := range config.RSAKeyBits {

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

			// Get just 1 RSA key of the specified size
			privateKey := shared.LoadRSAKeysFromInMemoryCache(rsaKeyBits, 1)[0]
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)

			// Create ciphertext based on policy to measure decryption cost
			asymmetricCiphertext := privateKey.Encrypt(symmetricKey)

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				privateKey.Decrypt(asymmetricCiphertext)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}

func BenchmarkAttributeKeyScalingKeyGen(benchmark *testing.B) {

	config := shared.NewAttributeKeyScalingConfig()

	// CP-ABE key issuance is deliberately not measured. It is executed by the attribute
	// authority, which holds the master secret and is by definition a trusted,
	// unconstrained entity, so it is never a cost the constrained device pays...

	// However it is reported for RSA
	// In RSA, key generation is a probabilistic prime search, so its cost is a random variable
	// with a long right tail... hence an averaged figure is not representative

	// Instead this case is run with an explicit -benchtime=1x, ensuring b.loop is executed exactly once,
	// making ns/op a single sample...
	// We use then -test.count = x to collect x samples, enabling reporting of:
	// - Median
	// - IQR
	// - Min & Max
	for _, rsaKeyBits := range config.RSAKeyBits {

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			var schema rsa.RSA

			for b.Loop() {
				schema = rsa.NewRSA(rsaKeyBits)
			}

			b.ReportMetric(float64(schema.StoredKeySize()), "stored_key_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}
