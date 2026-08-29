package aes_ascon

import (
	"benchmark/cryptography/aes"
	"benchmark/cryptography/ascon"
	"benchmark/micro/aes_ascon/shared"
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
				aes.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			// Actually measure this region
			for b.Loop() {
				aes.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				aes.Seal(ciphertext[:0], nonce, plaintext, nil)
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
				ascon.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			// Actually measure this region
			for b.Loop() {
				ascon.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				ascon.Seal(ciphertext[:0], nonce, plaintext, nil)
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
			ciphertext := aes.Seal(nil, nonce, plaintext, nil)
			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				aes.Open(decryptedPlaintext[:0], nonce, ciphertext, nil)
			}

			// Actually measure this region
			for b.Loop() {
				aes.Open(decryptedPlaintext[:0], nonce, ciphertext, nil)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				aes.Open(decryptedPlaintext[:0], nonce, ciphertext, nil)
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
			ciphertext := ascon.Seal(nil, nonce, plaintext, nil)
			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				ascon.Open(decryptedPlaintext[:0], nonce, ciphertext, nil)
			}

			// Actually measure this region
			for b.Loop() {
				ascon.Open(decryptedPlaintext[:0], nonce, ciphertext, nil)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				ascon.Open(decryptedPlaintext[:0], nonce, ciphertext, nil)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}
