package aes_ascon

import (
	"fmt"
	"testing"
	"thesis/benchmark/thermal"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
	"thesis/utility/golang/generator"
)

func BenchmarkAESASCONEncrypt(benchmark *testing.B) {

	config := NewAESASCONConfig()

	for _, payloadSize := range config.PayloadSizes {

		// Scenario 1: AES Scaling Payload Size
		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {

			// Instantiate AES cipher
			aes := aes.NewAES(generator.GenerateRandomBytes(config.AESKeySize))

			// Construct plaintexts
			plaintext := generator.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := generator.GenerateRandomBytes(aes.NonceSize())

			// Pre-allocate output destination buffers, to avoid allocation inside loop
			ciphertext := make([]byte, 0, payloadSize+aes.Overhead())

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				aes.Encrypt(ciphertext[:0], nonce, plaintext)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 2: ASCON Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {

			// Instantiate cipher
			ascon := ascon.NewASCON(
				generator.GenerateRandomBytes(config.ASCONKeySize),
			)

			// Construct plaintext for given payload size
			plaintext := generator.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := generator.GenerateRandomBytes(ascon.NonceSize())

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			ciphertext := make([]byte, 0, payloadSize+ascon.Overhead())

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				ascon.Encrypt(ciphertext[:0], nonce, plaintext)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}

func BenchmarkAESASCONDecrypt(benchmark *testing.B) {

	config := NewAESASCONConfig()

	// Scenario 1: AES-GCM Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {

			// Instantiate cipher
			aes := aes.NewAES(
				generator.GenerateRandomBytes(config.AESKeySize),
			)

			// Construct plaintext for given payload size
			plaintext := generator.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := generator.GenerateRandomBytes(aes.NonceSize())

			// Create ciphertext to measure decryption cost
			ciphertext := aes.Encrypt(nil, nonce, plaintext)

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			decryptedPlaintext := make([]byte, 0, payloadSize)

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				aes.Decrypt(decryptedPlaintext[:0], nonce, ciphertext)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 2: ASCON Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {

			// Instantiate cipher
			ascon := ascon.NewASCON(
				generator.GenerateRandomBytes(config.ASCONKeySize),
			)

			// Construct plaintext for given payload size
			plaintext := generator.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := generator.GenerateRandomBytes(ascon.NonceSize())

			// Create ciphertext to measure decryption cost
			ciphertext := ascon.Encrypt(nil, nonce, plaintext)

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			decryptedPlaintext := make([]byte, 0, payloadSize)

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				ascon.Decrypt(decryptedPlaintext[:0], nonce, ciphertext)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}
