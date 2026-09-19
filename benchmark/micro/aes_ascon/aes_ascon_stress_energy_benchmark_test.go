package aes_ascon

import (
	"fmt"
	"testing"
	"thesis/benchmark/micro/aes_ascon/shared"
	"thesis/benchmark/thermal"
	"thesis/benchmark/utility"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
	"time"
)

var (
	warmupDuration = time.Duration(utility.ParseIntFromEnv("WARMUP_DURATION")) * time.Second
	tailDuration   = time.Duration(utility.ParseIntFromEnv("TAIL_DURATION")) * time.Second
)

func BenchmarkAESASCONEnergyEncrypt(benchmark *testing.B) {

	config := shared.NewAESASCONConfig()

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {

			aes := aes.NewAES(utility.GenerateRandomBytes(config.AESKeySize))
			plaintext := utility.GenerateRandomBytes(payloadSize)
			nonce := utility.GenerateRandomBytes(aes.NonceSize())
			ciphertext := make([]byte, 0, payloadSize+aes.Overhead())

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				aes.Encrypt(ciphertext[:0], nonce, plaintext)
			}

			// Actually measure this region
			for b.Loop() {
				aes.Encrypt(ciphertext[:0], nonce, plaintext)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				aes.Encrypt(ciphertext[:0], nonce, plaintext)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {

			ascon := ascon.NewASCON(utility.GenerateRandomBytes(config.ASCONKeySize))
			plaintext := utility.GenerateRandomBytes(payloadSize)
			nonce := utility.GenerateRandomBytes(ascon.NonceSize())
			ciphertext := make([]byte, 0, payloadSize+ascon.Overhead())

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				ascon.Encrypt(ciphertext[:0], nonce, plaintext)
			}

			// Actually measure this region
			for b.Loop() {
				ascon.Encrypt(ciphertext[:0], nonce, plaintext)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
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

func BenchmarkAESASCONEnergyDecrypt(benchmark *testing.B) {

	config := shared.NewAESASCONConfig()

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {

			aes := aes.NewAES(utility.GenerateRandomBytes(config.AESKeySize))
			plaintext := utility.GenerateRandomBytes(payloadSize)
			nonce := utility.GenerateRandomBytes(aes.NonceSize())
			ciphertext := aes.Encrypt(nil, nonce, plaintext)
			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				aes.Decrypt(decryptedPlaintext[:0], nonce, ciphertext)
			}

			// Actually measure this region
			for b.Loop() {
				aes.Decrypt(decryptedPlaintext[:0], nonce, ciphertext)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				aes.Decrypt(decryptedPlaintext[:0], nonce, ciphertext)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {

			ascon := ascon.NewASCON(utility.GenerateRandomBytes(config.ASCONKeySize))
			plaintext := utility.GenerateRandomBytes(payloadSize)
			nonce := utility.GenerateRandomBytes(ascon.NonceSize())
			ciphertext := ascon.Encrypt(nil, nonce, plaintext)
			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				ascon.Decrypt(decryptedPlaintext[:0], nonce, ciphertext)
			}

			// Actually measure this region
			for b.Loop() {
				ascon.Decrypt(decryptedPlaintext[:0], nonce, ciphertext)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
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
