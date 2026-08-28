package aes_ascon

import (
	"benchmark/cryptography/aes"
	"benchmark/cryptography/ascon"
	"benchmark/thermal"
	"benchmark/utility"
	"fmt"
	"testing"
)

type AESASCONConfig struct {
	PayloadSizes []int
	AESKeySize   int
	ASCONKeySize int
}

func BenchmarkAESASCONEncrypt(benchmark *testing.B) {

	config := loadAESASCONConfig()

	for _, payloadSize := range config.PayloadSizes {

		// Scenario 1: AES Scaling Payload Size
		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {

			// Instantiate AES cipher
			aes := aes.NewAES(utility.GenerateRandomBytes(config.AESKeySize))

			// Construct plaintexts
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Pre-allocate output destination buffers, to avoid allocation inside loop
			ciphertext := make([]byte, 0, payloadSize+aes.Overhead())

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				aes.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			// Wire overhead = authentication tag size + nonce size
			b.ReportMetric(
				float64(aes.Overhead()+aes.NonceSize()),
				"wire_overhead_bytes/op",
			)

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
				utility.GenerateRandomBytes(config.ASCONKeySize),
			)

			// Construct plaintext for given payload size
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(ascon.NonceSize())

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			ciphertext := make([]byte, 0, payloadSize+ascon.Overhead())

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				ascon.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			// Wire overhead = authentication tag size + nonce size
			b.ReportMetric(
				float64(ascon.Overhead()+ascon.NonceSize()),
				"wire_overhead_bytes/op",
			)

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}

func BenchmarkAESASCONDecrypt(benchmark *testing.B) {

	config := loadAESASCONConfig()

	// Scenario 1: AES-GCM Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {

			// Instantiate cipher
			aes := aes.NewAES(
				utility.GenerateRandomBytes(config.AESKeySize),
			)

			// Construct plaintext for given payload size
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Create ciphertext to measure decryption cost
			ciphertext := aes.Seal(nil, nonce, plaintext, nil)

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			decryptedPlaintext := make([]byte, 0, payloadSize)

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				aes.Open(decryptedPlaintext[:0], nonce, ciphertext, nil)
			}

			// Wire overhead = authentication tag size + nonce size
			b.ReportMetric(
				float64(aes.Overhead()+aes.NonceSize()),
				"wire_overhead_bytes/op",
			)

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
				utility.GenerateRandomBytes(config.ASCONKeySize),
			)

			// Construct plaintext for given payload size
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(ascon.NonceSize())

			// Create ciphertext to measure decryption cost
			ciphertext := ascon.Seal(nil, nonce, plaintext, nil)

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			decryptedPlaintext := make([]byte, 0, payloadSize)

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				ascon.Open(decryptedPlaintext[:0], nonce, ciphertext, nil)
			}

			// Wire overhead = authentication tag size + nonce size
			b.ReportMetric(
				float64(ascon.Overhead()+ascon.NonceSize()),
				"wire_overhead_bytes/op",
			)

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}

func loadAESASCONConfig() AESASCONConfig {

	return AESASCONConfig{
		PayloadSizes: utility.ParseIntListFromEnv("AES_ASCON_PAYLOAD_SIZES"),
		AESKeySize:   utility.ParseIntFromEnv("AES_ASCON_KEY_SIZE"),
		ASCONKeySize: utility.ParseIntFromEnv("AES_ASCON_KEY_SIZE"),
	}
}
