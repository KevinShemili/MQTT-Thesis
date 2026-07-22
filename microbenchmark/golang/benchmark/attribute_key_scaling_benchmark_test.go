package benchmark

import (
	"fmt"
	"project/cryptography"
	"project/utils"
	"testing"
)

type AttributeKeyScalingConfig struct {
	AttributeCountList  []int
	SubscriberCountList []int
	RSAKeySizeList      []int
	FixedRSAKeyBits     int
	AESKeySize          int
}

func BenchmarkAttributeKeyScalingEncrypt(benchmark *testing.B) {

	config := loadAttributeKeyScalingConfig()

	// Scheme Setup
	// 1. CP-ABE authority
	// 2. RSA recipient pool at fixed key size
	cpAbe := cryptography.NewCPABEAuthority()

	// Get highest subscriber count to provision the recipient pool once
	maxSubscriberCount := config.SubscriberCountList[len(config.SubscriberCountList)-1]
	rsaSubscribers := make([]cryptography.RSA, maxSubscriberCount)
	for index := range maxSubscriberCount {
		rsaSubscribers[index] = cryptography.NewRSA(config.FixedRSAKeyBits)
	}

	// True cryptographic realism is not necessary here either,
	// rather isolation of asymmetric cost is the goal
	aesKey := utils.GenerateRandomBytes(config.AESKeySize)

	// Scenario 1: CP-ABE scaling attribute count
	for _, attributeCount := range config.AttributeCountList {

		// Build policy for given attribute number
		abePolicy, _ := cryptography.BuildSyntheticPolicyAndAttributes(attributeCount)

		// Ciphertext size is fixed, so measured once outside timed loop
		abeCiphertextSize := len(cpAbe.Encrypt(abePolicy, aesKey))

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {
			for b.Loop() {
				cpAbe.Encrypt(abePolicy, aesKey)
			}

			b.ReportMetric(float64(abeCiphertextSize), "ciphertext_bytes")
		})
	}

	// Scenario 2: RSA scaling subscriber count
	for _, subscriberCount := range config.SubscriberCountList {

		// Size of a single wrapped key, directly comparable to CP-ABE's single ciphertext
		singleCiphertextSize := len(rsaSubscribers[0].Encrypt(aesKey))

		// However, in RSA each one gets its own key
		totalCiphertextSize := subscriberCount * singleCiphertextSize

		benchmark.Run(fmt.Sprintf("RSASubscribers/%d", subscriberCount), func(b *testing.B) {
			for b.Loop() {
				for index := range subscriberCount {
					rsaSubscribers[index].Encrypt(aesKey)
				}
			}

			b.ReportMetric(float64(singleCiphertextSize), "ciphertext_bytes")
			b.ReportMetric(float64(totalCiphertextSize), "total_ciphertext_bytes")
		})
	}

	// Scenario 3: RSA scaling key size
	for _, rsaKeyBits := range config.RSAKeySizeList {

		rsaScheme := cryptography.NewRSA(rsaKeyBits)

		rsaCiphertextSize := len(rsaScheme.Encrypt(aesKey))

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

			for b.Loop() {
				rsaScheme.Encrypt(aesKey)
			}

			b.ReportMetric(float64(rsaCiphertextSize), "ciphertext_bytes")
		})
	}
}

func BenchmarkAttributeKeyScalingDecrypt(benchmark *testing.B) {

	config := loadAttributeKeyScalingConfig()
	aesKey := utils.GenerateRandomBytes(config.AESKeySize)

	// Scenario 1: CP-ABE scaling attribute count
	cpAbe := cryptography.NewCPABEAuthority()
	for _, attributeCount := range config.AttributeCountList {

		abePolicy, abeAttributes := cryptography.BuildSyntheticPolicyAndAttributes(attributeCount)

		subscriberKey := cpAbe.IssueSubscriberKey(abeAttributes)
		abeCiphertext := cpAbe.Encrypt(abePolicy, aesKey)

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {
			for b.Loop() {
				subscriberKey.Decrypt(abeCiphertext)
			}
		})
	}

	// Scenario 2: RSA scaling subscriber count
	// A subscriber only ever decrypts own session key, so cost is expected to stay flat
	rsa := cryptography.NewRSA(config.FixedRSAKeyBits)
	rsaCiphertext := rsa.Encrypt(aesKey)
	for _, subscriberCount := range config.SubscriberCountList {

		benchmark.Run(fmt.Sprintf("RSASubscribers/%d", subscriberCount), func(b *testing.B) {

			for b.Loop() {
				rsa.Decrypt(rsaCiphertext)
			}
		})
	}

	// Scenario 3: RSA scaling key size
	for _, rsaKeyBits := range config.RSAKeySizeList {

		rsa := cryptography.NewRSA(rsaKeyBits)
		rsaCiphertext := rsa.Encrypt(aesKey)

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

			for b.Loop() {
				rsa.Decrypt(rsaCiphertext)
			}
		})
	}
}

func BenchmarkAttributeKeyScalingKeyGen(benchmark *testing.B) {

	config := loadAttributeKeyScalingConfig()

	// Scenario 1: CP-ABE's
	// 1. Subscriber key issuance cost
	// 2. Stored key size vs attribute count
	cpAbe := cryptography.NewCPABEAuthority()
	for _, attributeCount := range config.AttributeCountList {

		_, abeAttributes := cryptography.BuildSyntheticPolicyAndAttributes(attributeCount)

		abeStoredKeySize := cpAbe.IssueSubscriberKey(abeAttributes).StoredKeySize()

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {
			for b.Loop() {
				cpAbe.IssueSubscriberKey(abeAttributes)
			}

			b.ReportMetric(float64(abeStoredKeySize), "stored_key_bytes")
		})
	}

	// Scenario 2: RSA's
	// 1. Key generation cost
	// 2. Stored key size vs modulus size
	for _, rsaKeyBits := range config.RSAKeySizeList {

		rsaStoredKeySize := cryptography.NewRSA(rsaKeyBits).StoredKeySize()

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

			for b.Loop() {
				cryptography.NewRSA(rsaKeyBits)
			}

			b.ReportMetric(float64(rsaStoredKeySize), "stored_key_bytes")
		})
	}
}

func loadAttributeKeyScalingConfig() AttributeKeyScalingConfig {

	return AttributeKeyScalingConfig{
		AttributeCountList: utils.ParseIntListFromEnv(
			"ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT",
		),
		SubscriberCountList: utils.ParseIntListFromEnv(
			"ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT",
		),
		RSAKeySizeList: utils.ParseIntListFromEnv(
			"ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES",
		),
		FixedRSAKeyBits: utils.ParseIntFromEnv(
			"ATTRIBUTE_KEY_SCALING_FIXED_RSA_KEY_BITS",
		),
		AESKeySize: utils.ParseIntFromEnv(
			"ATTRIBUTE_KEY_SCALING_AES_KEY_SIZE",
		),
	}
}
