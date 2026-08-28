package aes_ascon

import (
	"benchmark/cryptography/aes"
	"benchmark/cryptography/ascon"
	"benchmark/thermal"
	"benchmark/utility"
	"fmt"
	"testing"
	"time"
)

const (
	warmupDuration = 2 * time.Second
	tailDuration   = 2 * time.Second
)

type AESASCONEnergyConfig struct {
	PayloadSizes []int
	AESKeySize   int
	ASCONKeySize int
}

func BenchmarkAESASCONEnergyEncrypt(benchmark *testing.B) {

	config := loadAESASCONEnergyConfig()

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {

			// Prepare everything before the workload starts.
			aes := aes.NewAES(
				utility.GenerateRandomBytes(config.AESKeySize),
			)

			plaintext := utility.GenerateRandomBytes(payloadSize)
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			ciphertext := make(
				[]byte,
				0,
				payloadSize+aes.Overhead(),
			)

			// Start every repetition from the same thermal condition.
			thermal.WaitForCooldown()

			// Tell the laptop that the complete workload is beginning.
			fmt.Println("RUN START")

			// Warm up continuously before the measured benchmark region.
			warmupDeadline := time.Now().Add(warmupDuration)

			for time.Now().Before(warmupDeadline) {
				aes.Seal(
					ciphertext[:0],
					nonce,
					plaintext,
					nil,
				)
			}

			// Go measures only this region and reports ns/op.
			for b.Loop() {
				aes.Seal(
					ciphertext[:0],
					nonce,
					plaintext,
					nil,
				)
			}

			// Keep the same workload running after the measured region.
			tailDeadline := time.Now().Add(tailDuration)

			for time.Now().Before(tailDeadline) {
				aes.Seal(
					ciphertext[:0],
					nonce,
					plaintext,
					nil,
				)
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {

			// Prepare everything before the workload starts.
			ascon := ascon.NewASCON(
				utility.GenerateRandomBytes(config.ASCONKeySize),
			)

			plaintext := utility.GenerateRandomBytes(payloadSize)
			nonce := utility.GenerateRandomBytes(ascon.NonceSize())

			ciphertext := make(
				[]byte,
				0,
				payloadSize+ascon.Overhead(),
			)

			// Start every repetition from the same thermal condition.
			thermal.WaitForCooldown()

			// Tell the laptop that the complete workload is beginning.
			fmt.Println("RUN START")

			// Warm up continuously before the measured benchmark region.
			warmupDeadline := time.Now().Add(warmupDuration)

			for time.Now().Before(warmupDeadline) {
				ascon.Seal(
					ciphertext[:0],
					nonce,
					plaintext,
					nil,
				)
			}

			// Go measures only this region and reports ns/op.
			for b.Loop() {
				ascon.Seal(
					ciphertext[:0],
					nonce,
					plaintext,
					nil,
				)
			}

			// Keep the same workload running after the measured region.
			tailDeadline := time.Now().Add(tailDuration)

			for time.Now().Before(tailDeadline) {
				ascon.Seal(
					ciphertext[:0],
					nonce,
					plaintext,
					nil,
				)
			}
		})
	}
}

func BenchmarkAESASCONEnergyDecrypt(benchmark *testing.B) {

	config := loadAESASCONEnergyConfig()

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {

			// Prepare everything before the workload starts.
			aes := aes.NewAES(
				utility.GenerateRandomBytes(config.AESKeySize),
			)

			plaintext := utility.GenerateRandomBytes(payloadSize)
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			ciphertext := aes.Seal(
				nil,
				nonce,
				plaintext,
				nil,
			)

			decryptedPlaintext := make(
				[]byte,
				0,
				payloadSize,
			)

			// Start every repetition from the same thermal condition.
			thermal.WaitForCooldown()

			// Tell the laptop that the complete workload is beginning.
			fmt.Println("RUN START")

			// Warm up continuously before the measured benchmark region.
			warmupDeadline := time.Now().Add(warmupDuration)

			for time.Now().Before(warmupDeadline) {
				aes.Open(
					decryptedPlaintext[:0],
					nonce,
					ciphertext,
					nil,
				)
			}

			// Go measures only this region and reports ns/op.
			for b.Loop() {
				aes.Open(
					decryptedPlaintext[:0],
					nonce,
					ciphertext,
					nil,
				)
			}

			// Keep the same workload running after the measured region.
			tailDeadline := time.Now().Add(tailDuration)

			for time.Now().Before(tailDeadline) {
				aes.Open(
					decryptedPlaintext[:0],
					nonce,
					ciphertext,
					nil,
				)
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {

			// Prepare everything before the workload starts.
			ascon := ascon.NewASCON(
				utility.GenerateRandomBytes(config.ASCONKeySize),
			)

			plaintext := utility.GenerateRandomBytes(payloadSize)
			nonce := utility.GenerateRandomBytes(ascon.NonceSize())

			ciphertext := ascon.Seal(
				nil,
				nonce,
				plaintext,
				nil,
			)

			decryptedPlaintext := make(
				[]byte,
				0,
				payloadSize,
			)

			// Start every repetition from the same thermal condition.
			thermal.WaitForCooldown()

			// Tell the laptop that the complete workload is beginning.
			fmt.Println("RUN START")

			// Warm up continuously before the measured benchmark region.
			warmupDeadline := time.Now().Add(warmupDuration)

			for time.Now().Before(warmupDeadline) {
				ascon.Open(
					decryptedPlaintext[:0],
					nonce,
					ciphertext,
					nil,
				)
			}

			// Go measures only this region and reports ns/op.
			for b.Loop() {
				ascon.Open(
					decryptedPlaintext[:0],
					nonce,
					ciphertext,
					nil,
				)
			}

			// Keep the same workload running after the measured region.
			tailDeadline := time.Now().Add(tailDuration)

			for time.Now().Before(tailDeadline) {
				ascon.Open(
					decryptedPlaintext[:0],
					nonce,
					ciphertext,
					nil,
				)
			}
		})
	}
}

func loadAESASCONEnergyConfig() AESASCONEnergyConfig {

	return AESASCONEnergyConfig{
		PayloadSizes: utility.ParseIntListFromEnv(
			"AES_ASCON_PAYLOAD_SIZES",
		),
		AESKeySize: utility.ParseIntFromEnv(
			"AES_ASCON_KEY_SIZE",
		),
		ASCONKeySize: utility.ParseIntFromEnv(
			"AES_ASCON_KEY_SIZE",
		),
	}
}
