package benchmark

import (
	"fmt"
	"project/cryptography"
	"project/fixture"
	"project/utils"
	"testing"
	"time"
)

const cooldownTimeout = 5 * time.Minute

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

	// Scenario 1: Scaling attribute count in CP-ABE
	for _, attributeCount := range config.AttributeCountList {

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {

			cpAbe := cryptography.NewCPABEAuthority()

			// Build policy for given attribute number
			abePolicy, _ := cryptography.BuildSyntheticPolicyAndAttributes(attributeCount)

			// True cryptographic realism is not necessary here,
			// hence no need to regenerate a symmetric key for each new encryption
			aesKey := utils.GenerateRandomBytes(config.AESKeySize)

			// Ciphertext size is fixed, so measured once outside timed loop
			abeCiphertextSize := len(cpAbe.Encrypt(abePolicy, aesKey))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			waitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
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

	// Scenario 2: Scaling subscriber count in RSA
	for _, subscriberCount := range config.SubscriberCountList {

		benchmark.Run(fmt.Sprintf("RSASubscribers/%d", subscriberCount), func(b *testing.B) {

			rsaSubscribers := rsaKeyPool(config.FixedRSAKeyBits, subscriberCount)
			aesKey := utils.GenerateRandomBytes(config.AESKeySize)

			// Size of a single wrapped key, directly comparable to CP-ABE's single
			// ciphertext. Fixed by the key size, so measured once outside timed loop
			singleCiphertextSize := len(rsaSubscribers[0].Encrypt(aesKey))

			// However, in RSA each one gets its own key
			totalCiphertextSize := subscriberCount * singleCiphertextSize

			waitForCooldown()

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

	// Scenario 3: Scaling key size in RSA
	for _, rsaKeyBits := range config.RSAKeySizeList {

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

			rsaScheme := rsaKeyPool(rsaKeyBits, 1)[0]
			aesKey := utils.GenerateRandomBytes(config.AESKeySize)

			rsaCiphertextSize := len(rsaScheme.Encrypt(aesKey))

			waitForCooldown()

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

	// Scenario 1: CP-ABE scaling attribute count
	for _, attributeCount := range config.AttributeCountList {

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {

			cpAbe := cryptography.NewCPABEAuthority()
			abePolicy, abeAttributes := cryptography.BuildSyntheticPolicyAndAttributes(attributeCount)
			aesKey := utils.GenerateRandomBytes(config.AESKeySize)

			subscriberKey := cpAbe.IssueSubscriberKey(abeAttributes)
			abeCiphertext := cpAbe.Encrypt(abePolicy, aesKey)
			abeStoredKeySize := subscriberKey.StoredKeySize()

			waitForCooldown()

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

		benchmark.Run(fmt.Sprintf("RSASubscribers/%d", subscriberCount), func(b *testing.B) {

			subscriber := rsaKeyPool(config.FixedRSAKeyBits, index+1)[index]
			aesKey := utils.GenerateRandomBytes(config.AESKeySize)

			subscriberCiphertext := subscriber.Encrypt(aesKey)

			waitForCooldown()

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

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

			rsa := rsaKeyPool(rsaKeyBits, 1)[0]
			aesKey := utils.GenerateRandomBytes(config.AESKeySize)

			rsaCiphertext := rsa.Encrypt(aesKey)

			waitForCooldown()

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

	directory := fixture.RSAKeyDirectory(rsaKeyBits)

	pool := rsaKeyCache[rsaKeyBits]

	// Keys are reached by position rather than by listing the directory, so the pool
	// only ever grows and the same key can never be added twice
	for len(pool) < requiredCount {

		key, stored := cryptography.LoadRSAKey(directory, len(pool))
		if !stored {
			key = cryptography.NewRSA(rsaKeyBits)
			cryptography.StoreRSAKey(key, directory, len(pool))
		}

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
