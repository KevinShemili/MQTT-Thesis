package benchmark

import (
	"fmt"
	"path/filepath"
	"project/cryptography"
	"project/utils"
	"slices"
	"testing"
	"time"
)

const cooldownTimeout = 5 * time.Minute
const keyCacheDirectory = "key-cache"

var rsaKeyCache = map[int][]cryptography.RSA{}

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
	maxSubscriberCount := slices.Max(config.SubscriberCountList)
	rsaSubscribers := rsaKeyPool(config.FixedRSAKeyBits, maxSubscriberCount)

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
			waitForCooldown()
			b.ResetTimer()

			throttle := utils.WatchThrottling()

			for b.Loop() {
				cpAbe.Encrypt(abePolicy, aesKey)
			}

			b.ReportMetric(float64(abeCiphertextSize), "ciphertext_bytes")
			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}

	// Scenario 2: RSA scaling subscriber count
	// Size of a single wrapped key, directly comparable to CP-ABE's single ciphertext.
	// Fixed by the key size, so measured once outside the sweep
	singleCiphertextSize := len(rsaSubscribers[0].Encrypt(aesKey))

	for _, subscriberCount := range config.SubscriberCountList {

		// However, in RSA each one gets its own key
		totalCiphertextSize := subscriberCount * singleCiphertextSize

		benchmark.Run(fmt.Sprintf("RSASubscribers/%d", subscriberCount), func(b *testing.B) {
			waitForCooldown()
			b.ResetTimer()

			throttle := utils.WatchThrottling()

			for b.Loop() {
				for index := range subscriberCount {
					rsaSubscribers[index].Encrypt(aesKey)
				}
			}

			b.ReportMetric(float64(singleCiphertextSize), "ciphertext_bytes")
			b.ReportMetric(float64(totalCiphertextSize), "total_ciphertext_bytes")
			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}

	// Scenario 3: RSA scaling key size
	for _, rsaKeyBits := range config.RSAKeySizeList {

		rsaScheme := rsaKeyPool(rsaKeyBits, 1)[0]

		rsaCiphertextSize := len(rsaScheme.Encrypt(aesKey))

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {
			waitForCooldown()
			b.ResetTimer()

			throttle := utils.WatchThrottling()

			for b.Loop() {
				rsaScheme.Encrypt(aesKey)
			}

			b.ReportMetric(float64(rsaCiphertextSize), "ciphertext_bytes")
			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}
}

func BenchmarkAttributeKeyScalingDecrypt(benchmark *testing.B) {

	config := loadAttributeKeyScalingConfig()
	aesKey := utils.GenerateRandomBytes(config.AESKeySize)
	subscriberKeys := rsaKeyPool(config.FixedRSAKeyBits, len(config.SubscriberCountList))

	// Scenario 1: CP-ABE scaling attribute count
	cpAbe := cryptography.NewCPABEAuthority()
	for _, attributeCount := range config.AttributeCountList {

		abePolicy, abeAttributes := cryptography.BuildSyntheticPolicyAndAttributes(attributeCount)

		subscriberKey := cpAbe.IssueSubscriberKey(abeAttributes)
		abeCiphertext := cpAbe.Encrypt(abePolicy, aesKey)
		abeStoredKeySize := subscriberKey.StoredKeySize()

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {
			waitForCooldown()
			b.ResetTimer()

			throttle := utils.WatchThrottling()

			for b.Loop() {
				subscriberKey.Decrypt(abeCiphertext)
			}

			b.ReportMetric(float64(abeStoredKeySize), "stored_key_bytes")
			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}

	// Scenario 2: RSA scaling subscriber count
	// A subscriber only ever decrypts own session key, so cost is expected to stay flat.
	// Each sweep point provisions its own subscriber and decrypts its own wrapped key, so a flat
	// result reflects measured behaviour rather than a repetition of byte-identical work
	for index, subscriberCount := range config.SubscriberCountList {

		subscriber := subscriberKeys[index]
		subscriberCiphertext := subscriber.Encrypt(aesKey)

		benchmark.Run(fmt.Sprintf("RSASubscribers/%d", subscriberCount), func(b *testing.B) {
			waitForCooldown()
			b.ResetTimer()

			throttle := utils.WatchThrottling()

			for b.Loop() {
				subscriber.Decrypt(subscriberCiphertext)
			}

			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}

	// Scenario 3: RSA scaling key size
	for _, rsaKeyBits := range config.RSAKeySizeList {

		rsa := rsaKeyPool(rsaKeyBits, 1)[0]
		rsaCiphertext := rsa.Encrypt(aesKey)

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {
			waitForCooldown()
			b.ResetTimer()

			throttle := utils.WatchThrottling()

			for b.Loop() {
				rsa.Decrypt(rsaCiphertext)
			}

			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}
}

func BenchmarkAttributeKeyScalingKeyGen(benchmark *testing.B) {

	config := loadAttributeKeyScalingConfig()

	// CP-ABE key issuance is deliberately not measured. It is executed by the attribute
	// authority, which holds the master secret and is by definition a trusted,
	// unconstrained entity, so it is never a cost the constrained device pays.
	// CP-ABE's stored key size is reported by the decrypt benchmark instead

	// Key generation is a probabilistic prime search, so its cost is a random variable
	// with a long right tail and a single averaged figure is not representative.
	// Run with -benchtime=1x so each run performs exactly one generation and its ns/op
	// is one sample, and -count=N to collect N of them. The distribution is reduced to
	// median, IQR, min and max at reporting time
	for _, rsaKeyBits := range config.RSAKeySizeList {

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {
			waitForCooldown()
			b.ResetTimer()

			throttle := utils.WatchThrottling()

			var scheme cryptography.RSA

			for b.Loop() {
				scheme = cryptography.NewRSA(rsaKeyBits)
			}

			b.ReportMetric(float64(scheme.StoredKeySize()), "stored_key_bytes")
			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
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

func rsaKeyPool(rsaKeyBits int, requiredCount int) []cryptography.RSA {

	directory := filepath.Join(keyCacheDirectory, fmt.Sprintf("rsa-%d", rsaKeyBits))

	pool, loaded := rsaKeyCache[rsaKeyBits]
	if !loaded {
		pool = cryptography.LoadRSAKeys(directory)
	}

	// Only generation extends the pool, so the same key can never be added twice
	for len(pool) < requiredCount {
		key := cryptography.NewRSA(rsaKeyBits)
		cryptography.StoreRSAKey(key, directory, len(pool))
		pool = append(pool, key)
	}

	rsaKeyCache[rsaKeyBits] = pool

	return pool[:requiredCount]
}

func waitForCooldown() {
	utils.WaitForCooldown(
		utils.ParseIntFromEnv("THERMAL_COOLDOWN_CELSIUS"),
		cooldownTimeout,
	)
}
