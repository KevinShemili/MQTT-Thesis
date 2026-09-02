package payload_scaling

import (
	"benchmark/cryptography/aes"
	"benchmark/cryptography/cpabe"
	"benchmark/cryptography/rsa"
	"benchmark/micro/payload_scaling/shared"
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

func BenchmarkPayloadScalingEnergyEncrypt(benchmark *testing.B) {

	config := shared.LoadPayloadScalingConfig()

	// Scenario 1: PSK Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSK/%dB", payloadSize), func(b *testing.B) {

			aesGcm := aes.NewAES(
				utility.GenerateRandomBytes(config.AESKeySize),
			)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			ciphertext := make([]byte, 0, payloadSize+aesGcm.Overhead())

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

				aesGcm.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			// Actually measure this region
			for b.Loop() {
				nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

				aesGcm.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

				aesGcm.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 2: RSA + AES Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSA/%dB", payloadSize), func(b *testing.B) {

			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			aesGcm := aes.NewAES(
				utility.GenerateRandomBytes(config.AESKeySize),
			)

			ciphertext := make([]byte, 0, payloadSize+aesGcm.Overhead())

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				rsaScheme.Encrypt(symmetricKey)
				messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			// Actually measure this region
			for b.Loop() {
				nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				rsaScheme.Encrypt(symmetricKey)
				messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				rsaScheme.Encrypt(symmetricKey)
				messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 3: CP-ABE + AES Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABE/%dB", payloadSize), func(b *testing.B) {

			authority := cpabe.NewCPABEAuthority()

			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(
				config.AttributeCount,
			)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			aesGcm := aes.NewAES(
				utility.GenerateRandomBytes(config.AESKeySize),
			)

			ciphertext := make([]byte, 0, payloadSize+aesGcm.Overhead())

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				authority.Encrypt(abePolicy, symmetricKey)
				messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			// Actually measure this region
			for b.Loop() {
				nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				authority.Encrypt(abePolicy, symmetricKey)
				messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				authority.Encrypt(abePolicy, symmetricKey)
				messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}

func BenchmarkPayloadScalingEnergyDecrypt(benchmark *testing.B) {

	config := shared.LoadPayloadScalingConfig()

	// Scenario 1: PSK Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSK/%dB", payloadSize), func(b *testing.B) {

			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)

			aesGcm := aes.NewAES(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

			ciphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				aesGcm.Open(
					decryptedPlaintext[:0],
					nonce,
					ciphertext,
					nil,
				)
			}

			// Actually measure this region
			for b.Loop() {
				aesGcm.Open(
					decryptedPlaintext[:0],
					nonce,
					ciphertext,
					nil,
				)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				aesGcm.Open(
					decryptedPlaintext[:0],
					nonce,
					ciphertext,
					nil,
				)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 2: RSA + AES Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSA/%dB", payloadSize), func(b *testing.B) {

			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)

			aesGcm := aes.NewAES(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

			asymmetricCiphertext := rsaScheme.Encrypt(symmetricKey)

			ciphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				recoveredSymmetricKey := rsaScheme.Decrypt(asymmetricCiphertext)

				aes.NewAES(recoveredSymmetricKey).Open(
					decryptedPlaintext[:0],
					nonce,
					ciphertext,
					nil,
				)
			}

			// Actually measure this region
			for b.Loop() {
				recoveredSymmetricKey := rsaScheme.Decrypt(asymmetricCiphertext)

				aes.NewAES(recoveredSymmetricKey).Open(
					decryptedPlaintext[:0],
					nonce,
					ciphertext,
					nil,
				)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				recoveredSymmetricKey := rsaScheme.Decrypt(asymmetricCiphertext)

				aes.NewAES(recoveredSymmetricKey).Open(
					decryptedPlaintext[:0],
					nonce,
					ciphertext,
					nil,
				)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 3: CP-ABE + AES Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABE/%dB", payloadSize), func(b *testing.B) {

			authority := cpabe.NewCPABEAuthority()

			abePolicy, abeAttributes := cpabe.BuildSyntheticPolicyAndAttributes(
				config.AttributeCount,
			)

			subscriberKey := authority.IssuePrivateKey(abeAttributes)

			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)

			aesGcm := aes.NewAES(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

			asymmetricCiphertext := authority.Encrypt(
				abePolicy,
				symmetricKey,
			)

			ciphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
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

			// Actually measure this region
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

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
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

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}
