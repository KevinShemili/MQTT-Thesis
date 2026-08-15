package benchmark

import (
	"fmt"
	"project/cryptography/aes"
	"project/cryptography/ascon"
	"project/utils"
	"testing"
)

type AESASCONConfig struct {
	PayloadSizes []int
	AESKeySize   int
	ASCONKeySize int
}

func BenchmarkAESASCONEncrypt(benchmark *testing.B) {

	config := loadAESASCONConfig()

	// Construct ciphers outside timed benchmarks
	aesGcm := aes.NewAES(utils.GenerateRandomBytes(config.AESKeySize))
	ascon := ascon.NewASCON(utils.GenerateRandomBytes(config.ASCONKeySize))

	// Construct nonces outside timed benchmarks
	// Normally reusing nonce is insecure, but acceptable here because ciphertexts are discarded benchmark artifacts
	aesGcmNonce := utils.GenerateRandomBytes(aesGcm.NonceSize())
	asconNonce := utils.GenerateRandomBytes(ascon.NonceSize())

	for _, payloadSize := range config.PayloadSizes {

		// Construct plaintext outside timed benchmarks
		plaintext := utils.GenerateRandomBytes(payloadSize)

		// Pre-allocate output destination buffers, to avoid allocation inside loop
		aesGcmCiphertext := make([]byte, 0, payloadSize+aesGcm.Overhead())
		asconCiphertext := make([]byte, 0, payloadSize+ascon.Overhead())

		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {
			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			throttle := utils.WatchThrottling()

			for b.Loop() {
				aesGcm.Seal(aesGcmCiphertext[:0], aesGcmNonce, plaintext, nil)
			}

			// Wire overhead = authentication tag size + nonce size
			b.ReportMetric(float64(aesGcm.Overhead()+aesGcm.NonceSize()), "wire_overhead_bytes/op")
			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {
			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			throttle := utils.WatchThrottling()

			for b.Loop() {
				ascon.Seal(asconCiphertext[:0], asconNonce, plaintext, nil)
			}

			// Wire overhead = authentication tag size + nonce size
			b.ReportMetric(float64(ascon.Overhead()+ascon.NonceSize()), "wire_overhead_bytes/op")
			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}
}

func BenchmarkAESASCONDecrypt(benchmark *testing.B) {

	config := loadAESASCONConfig()

	// Construct ciphers outside timed benchmarks
	aesGcm := aes.NewAES(utils.GenerateRandomBytes(config.AESKeySize))
	ascon := ascon.NewASCON(utils.GenerateRandomBytes(config.ASCONKeySize))

	// Construct nonces outside timed benchmarks
	aesGcmNonce := utils.GenerateRandomBytes(aesGcm.NonceSize())
	asconNonce := utils.GenerateRandomBytes(ascon.NonceSize())

	for _, payloadSize := range config.PayloadSizes {

		plaintext := utils.GenerateRandomBytes(payloadSize)

		// Calculate ciphertext
		aesGcmCiphertext := aesGcm.Seal(nil, aesGcmNonce, plaintext, nil)
		asconCiphertext := ascon.Seal(nil, asconNonce, plaintext, nil)

		// Pre-allocate output decryption buffers, to avoid allocation inside loop
		aesGcmPlaintext := make([]byte, 0, payloadSize)
		asconPlaintext := make([]byte, 0, payloadSize)

		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {
			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			throttle := utils.WatchThrottling()

			for b.Loop() {
				aesGcm.Open(aesGcmPlaintext[:0], aesGcmNonce, aesGcmCiphertext, nil)
			}

			// Wire overhead = authentication tag size + nonce size
			b.ReportMetric(float64(aesGcm.Overhead()+aesGcm.NonceSize()), "wire_overhead_bytes/op")
			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {
			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			throttle := utils.WatchThrottling()

			for b.Loop() {
				ascon.Open(asconPlaintext[:0], asconNonce, asconCiphertext, nil)
			}

			// Wire overhead = authentication tag size + nonce size
			b.ReportMetric(float64(ascon.Overhead()+ascon.NonceSize()), "wire_overhead_bytes/op")
			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}
}

func loadAESASCONConfig() AESASCONConfig {

	return AESASCONConfig{
		PayloadSizes: utils.ParseIntListFromEnv("AES_ASCON_PAYLOAD_SIZES"),
		AESKeySize:   utils.ParseIntFromEnv("AES_ASCON_KEY_SIZE"),
		ASCONKeySize: utils.ParseIntFromEnv("AES_ASCON_KEY_SIZE"),
	}
}
