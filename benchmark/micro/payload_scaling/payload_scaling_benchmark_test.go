package benchmark

import (
	"benchmark/cryptography/aes"
	"benchmark/cryptography/cpabe"
	"benchmark/cryptography/rsa"
	"benchmark/support"
	"fmt"
	"testing"
)

type PayloadScalingConfig struct {
	PayloadSizes   []int
	AESKeySize     int
	AttributeCount int
	RSAKeyBits     int
}

func BenchmarkPayloadScalingEncrypt(benchmark *testing.B) {

	config := loadPayloadScalingConfig()

	// Scenario 1: PSK Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSK/%dB", payloadSize), func(b *testing.B) {

			// Instantiate AES-GCM cipher
			aesGcm := aes.NewAES(
				support.GenerateRandomBytes(config.AESKeySize),
			)

			// Construct plaintext for given payload size
			plaintext := support.GenerateRandomBytes(payloadSize)

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			ciphertext := make([]byte, 0, payloadSize+aesGcm.Overhead())

			// Calculate fixed wire overhead
			wireOverhead := aesGcm.NonceSize() + aesGcm.Overhead()

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			waitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := support.WatchThrottling()

			// A realistic implementation of PSK necessitates a fresh nonce per message
			for b.Loop() {
				nonce := support.GenerateRandomBytes(aesGcm.NonceSize())

				aesGcm.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			b.ReportMetric(
				float64(wireOverhead),
				"wire_overhead_bytes/op",
			)

			if throttled, isAvailable := throttle.Throttled(); isAvailable {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}

	// Scenario 2: RSA + AES Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSA/%dB", payloadSize), func(b *testing.B) {

			// Instantiate RSA cipher
			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			// Construct plaintext for given payload size
			plaintext := support.GenerateRandomBytes(payloadSize)

			// Instantiate AES-GCM once outside timed loop to obtain its fixed sizes
			aesGcm := aes.NewAES(
				support.GenerateRandomBytes(config.AESKeySize),
			)

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			ciphertext := make([]byte, 0, payloadSize+aesGcm.Overhead())

			// Calculate fixed RSA wrapped-key size
			asymmetricCiphertextSize := len(
				rsaScheme.Encrypt(
					support.GenerateRandomBytes(config.AESKeySize),
				),
			)

			// Calculate fixed wire overhead
			wireOverhead := aesGcm.NonceSize() +
				aesGcm.Overhead() +
				asymmetricCiphertextSize

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			waitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := support.WatchThrottling()

			// A realistic implementation of RSA + AES necessitates a fresh session key & nonce per message
			for b.Loop() {
				nonce := support.GenerateRandomBytes(aesGcm.NonceSize())
				symmetricKey := support.GenerateRandomBytes(config.AESKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				rsaScheme.Encrypt(symmetricKey)
				messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			b.ReportMetric(
				float64(wireOverhead),
				"wire_overhead_bytes/op",
			)

			if throttled, isAvailable := throttle.Throttled(); isAvailable {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}

	// Scenario 3: CP-ABE + AES Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABE/%dB", payloadSize), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Build policy for configured attribute count
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(
				config.AttributeCount,
			)

			// Construct plaintext for given payload size
			plaintext := support.GenerateRandomBytes(payloadSize)

			// Instantiate AES-GCM once outside timed loop to obtain its fixed sizes
			aesGcm := aes.NewAES(
				support.GenerateRandomBytes(config.AESKeySize),
			)

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			ciphertext := make([]byte, 0, payloadSize+aesGcm.Overhead())

			// Calculate fixed CP-ABE encrypted-key size
			asymmetricCiphertextSize := len(
				authority.Encrypt(
					abePolicy,
					support.GenerateRandomBytes(config.AESKeySize),
				),
			)

			// Calculate fixed wire overhead
			wireOverhead := aesGcm.NonceSize() +
				aesGcm.Overhead() +
				asymmetricCiphertextSize

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			waitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := support.WatchThrottling()

			// A realistic implementation of CP-ABE + AES necessitates a fresh session key & nonce per message
			for b.Loop() {
				nonce := support.GenerateRandomBytes(aesGcm.NonceSize())
				symmetricKey := support.GenerateRandomBytes(config.AESKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				authority.Encrypt(abePolicy, symmetricKey)
				messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			b.ReportMetric(
				float64(wireOverhead),
				"wire_overhead_bytes/op",
			)

			if throttled, isAvailable := throttle.Throttled(); isAvailable {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}
}

func BenchmarkPayloadScalingDecrypt(benchmark *testing.B) {

	config := loadPayloadScalingConfig()

	// Scenario 1: PSK Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSK/%dB", payloadSize), func(b *testing.B) {

			// Generate symmetric key
			symmetricKey := support.GenerateRandomBytes(config.AESKeySize)

			// Instantiate AES-GCM cipher
			aesGcm := aes.NewAES(symmetricKey)

			// Construct plaintext for given payload size
			plaintext := support.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := support.GenerateRandomBytes(aesGcm.NonceSize())

			// Create ciphertext to measure decryption cost
			ciphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			decryptedPlaintext := make([]byte, 0, payloadSize)

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			waitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := support.WatchThrottling()

			for b.Loop() {
				aesGcm.Open(
					decryptedPlaintext[:0],
					nonce,
					ciphertext,
					nil,
				)
			}

			if throttled, isAvailable := throttle.Throttled(); isAvailable {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}

	// Scenario 2: RSA + AES Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSA/%dB", payloadSize), func(b *testing.B) {

			// Instantiate RSA cipher
			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			// Generate symmetric key
			symmetricKey := support.GenerateRandomBytes(config.AESKeySize)

			// Instantiate AES-GCM cipher
			aesGcm := aes.NewAES(symmetricKey)

			// Construct plaintext for given payload size
			plaintext := support.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := support.GenerateRandomBytes(aesGcm.NonceSize())

			// Encrypt symmetric key under RSA
			asymmetricCiphertext := rsaScheme.Encrypt(symmetricKey)

			// Encrypt payload under symmetric key
			ciphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			decryptedPlaintext := make([]byte, 0, payloadSize)

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			waitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := support.WatchThrottling()

			for b.Loop() {
				recoveredSymmetricKey := rsaScheme.Decrypt(asymmetricCiphertext)

				aes.NewAES(recoveredSymmetricKey).Open(
					decryptedPlaintext[:0],
					nonce,
					ciphertext,
					nil,
				)
			}

			if throttled, isAvailable := throttle.Throttled(); isAvailable {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}

	// Scenario 3: CP-ABE + AES Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABE/%dB", payloadSize), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Build policy and attributes
			abePolicy, abeAttributes := cpabe.BuildSyntheticPolicyAndAttributes(
				config.AttributeCount,
			)

			// Issue subscriber private key
			subscriberKey := authority.IssuePrivateKey(abeAttributes)

			// Generate symmetric key
			symmetricKey := support.GenerateRandomBytes(config.AESKeySize)

			// Instantiate AES-GCM cipher
			aesGcm := aes.NewAES(symmetricKey)

			// Construct plaintext for given payload size
			plaintext := support.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := support.GenerateRandomBytes(aesGcm.NonceSize())

			// Encrypt symmetric key under CP-ABE policy
			asymmetricCiphertext := authority.Encrypt(
				abePolicy,
				symmetricKey,
			)

			// Encrypt payload under symmetric key
			ciphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			decryptedPlaintext := make([]byte, 0, payloadSize)

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			waitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := support.WatchThrottling()

			for b.Loop() {
				recoveredSymmetricKey := subscriberKey.Decrypt(
					asymmetricCiphertext,
				)

				aes.NewAES(recoveredSymmetricKey).Open(
					decryptedPlaintext[:0],
					nonce,
					ciphertext,
					nil,
				)
			}

			if throttled, isAvailable := throttle.Throttled(); isAvailable {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}
}

func loadPayloadScalingConfig() PayloadScalingConfig {

	return PayloadScalingConfig{
		PayloadSizes: support.ParseIntListFromEnv(
			"PAYLOAD_SCALING_PAYLOAD_SIZES",
		),
		AESKeySize: support.ParseIntFromEnv(
			"PAYLOAD_SCALING_AES_KEY_SIZE",
		),
		AttributeCount: support.ParseIntFromEnv(
			"PAYLOAD_SCALING_ATTRIBUTE_COUNT",
		),
		RSAKeyBits: support.ParseIntFromEnv(
			"PAYLOAD_SCALING_RSA_KEY_BITS",
		),
	}
}

func waitForCooldown() {
	support.WaitForCooldown(
		support.ParseIntFromEnv("THERMAL_COOLDOWN_CELSIUS"),
		support.CooldownTimeout,
	)
}
