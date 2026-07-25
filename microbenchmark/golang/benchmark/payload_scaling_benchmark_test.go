package benchmark

import (
	"fmt"
	"project/cryptography"
	"project/utils"
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

	// Scheme Setup
	// 1. PSK
	// 2. RSA
	// 3. CP-ABE
	aesGcm := cryptography.NewAESGCM(utils.GenerateRandomBytes(config.AESKeySize))
	rsaScheme := cryptography.NewRSA(config.RSAKeyBits)
	cpAbe := cryptography.NewCPABEAuthority()

	abePolicy, _ := cryptography.BuildSyntheticPolicyAndAttributes(config.AttributeCount)

	for _, payloadSize := range config.PayloadSizes {

		// Construct arbitrary plaintext
		plaintext := utils.GenerateRandomBytes(payloadSize)

		// Pre-allocate buffer to avoid allocation noise
		aesCiphertextBuffer := make([]byte, 0, payloadSize+aesGcm.Overhead())

		pskWireOverhead := aesGcm.NonceSize() + aesGcm.Overhead()
		rsaWireOverhead := aesGcm.NonceSize() + aesGcm.Overhead() + len(rsaScheme.Encrypt(utils.GenerateRandomBytes(config.AESKeySize)))
		abeWireOverhead := aesGcm.NonceSize() + aesGcm.Overhead() + len(cpAbe.Encrypt(abePolicy, utils.GenerateRandomBytes(config.AESKeySize)))

		benchmark.Run(fmt.Sprintf("PSK/%dB", payloadSize), func(b *testing.B) {

			b.SetBytes(int64(payloadSize))
			// A realistic implementation of PSK would necessitate a fresh nonce per message
			for b.Loop() {
				nonce := utils.GenerateRandomBytes(aesGcm.NonceSize())

				aesGcm.Seal(aesCiphertextBuffer[:0], nonce, plaintext, nil)
			}

			b.ReportMetric(float64(pskWireOverhead), "wire_overhead_bytes/op")
		})

		benchmark.Run(fmt.Sprintf("RSA/%dB", payloadSize), func(b *testing.B) {

			b.SetBytes(int64(payloadSize))

			// A realistic implementation of RSA + AES would necessitate a fresh session key & nonce per message
			for b.Loop() {
				nonce := utils.GenerateRandomBytes(aesGcm.NonceSize())
				symmetricKey := utils.GenerateRandomBytes(config.AESKeySize)
				aesGcm := cryptography.NewAESGCM(symmetricKey)

				rsaScheme.Encrypt(symmetricKey)
				aesGcm.Seal(aesCiphertextBuffer[:0], nonce, plaintext, nil)
			}

			b.ReportMetric(float64(rsaWireOverhead), "wire_overhead_bytes/op")
		})

		benchmark.Run(fmt.Sprintf("CPABE/%dB", payloadSize), func(b *testing.B) {

			b.SetBytes(int64(payloadSize))

			// A realistic implementation of CP-ABE + AES would necessitate a fresh session key & nonce per message
			for b.Loop() {
				nonce := utils.GenerateRandomBytes(aesGcm.NonceSize())
				symmetricKey := utils.GenerateRandomBytes(config.AESKeySize)
				aesGcm := cryptography.NewAESGCM(symmetricKey)

				cpAbe.Encrypt(abePolicy, symmetricKey)
				aesGcm.Seal(aesCiphertextBuffer[:0], nonce, plaintext, nil)
			}

			b.ReportMetric(float64(abeWireOverhead), "wire_overhead_bytes/op")
		})
	}
}

func BenchmarkPayloadScalingDecrypt(benchmark *testing.B) {

	config := loadPayloadScalingConfig()

	// Scheme Setup
	// 1. PSK
	// 2. RSA
	// 3. CP-ABE
	// One-time scheme setup, mirroring the encrypt benchmark
	symmetricKey := utils.GenerateRandomBytes(config.AESKeySize)
	aesGcm := cryptography.NewAESGCM(symmetricKey)
	rsaScheme := cryptography.NewRSA(config.RSAKeyBits)
	cpAbe := cryptography.NewCPABEAuthority()

	// Obtain a policy & attributes forming that policy
	abePolicy, abeAttributes := cryptography.BuildSyntheticPolicyAndAttributes(config.AttributeCount)

	// Issue the subscriber's key since it is not per-message work
	subscriberKey := cpAbe.IssueSubscriberKey(abeAttributes)

	nonce := utils.GenerateRandomBytes(aesGcm.NonceSize())

	for _, payloadSize := range config.PayloadSizes {

		plaintext := utils.GenerateRandomBytes(payloadSize)

		// Fixture needs the symmetric key to be encrypted under each scheme
		asymmetricRSAKey := rsaScheme.Encrypt(symmetricKey)
		asymmetricABEKey := cpAbe.Encrypt(abePolicy, symmetricKey)

		aesCiphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

		// Pre-allocate output decryption buffer, to avoid allocation inside loop
		plaintextBuffer := make([]byte, 0, payloadSize)

		benchmark.Run(fmt.Sprintf("PSK/%dB", payloadSize), func(b *testing.B) {

			b.SetBytes(int64(payloadSize))

			// Simple symmetric decryption
			for b.Loop() {
				aesGcm.Open(plaintextBuffer[:0], nonce, aesCiphertext, nil)
			}
		})

		benchmark.Run(fmt.Sprintf("RSA/%dB", payloadSize), func(b *testing.B) {

			b.SetBytes(int64(payloadSize))

			for b.Loop() {
				recoveredSymmetricAESKey := rsaScheme.Decrypt(asymmetricRSAKey)
				cryptography.NewAESGCM(recoveredSymmetricAESKey).Open(plaintextBuffer[:0], nonce, aesCiphertext, nil)
			}
		})

		benchmark.Run(fmt.Sprintf("CPABE/%dB", payloadSize), func(b *testing.B) {

			b.SetBytes(int64(payloadSize))

			for b.Loop() {
				recoveredSymmetricAESKey := subscriberKey.Decrypt(asymmetricABEKey)
				cryptography.NewAESGCM(recoveredSymmetricAESKey).Open(plaintextBuffer[:0], nonce, aesCiphertext, nil)
			}
		})
	}
}

func loadPayloadScalingConfig() PayloadScalingConfig {

	return PayloadScalingConfig{
		PayloadSizes: utils.ParseIntListFromEnv(
			"PAYLOAD_SCALING_PAYLOAD_SIZES",
		),
		AESKeySize: utils.ParseIntFromEnv(
			"PAYLOAD_SCALING_AES_KEY_SIZE",
		),
		AttributeCount: utils.ParseIntFromEnv(
			"PAYLOAD_SCALING_ATTRIBUTE_COUNT",
		),
		RSAKeyBits: utils.ParseIntFromEnv(
			"PAYLOAD_SCALING_RSA_KEY_BITS",
		),
	}
}
