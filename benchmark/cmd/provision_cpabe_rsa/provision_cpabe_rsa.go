package main

import (
	"thesis/benchmark/cache"
	"thesis/benchmark/micro/cpabe_rsa/shared"
	"thesis/benchmark/utility"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
)

// The point of this program is to provide the fixture data for the CP-ABE/RSA
// memory benchmarks by populating the cache in an earlier process.
func main() {

	config := shared.NewCPABERSAConfig()

	symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
	cache.Store(cache.AESKeyFileName, symmetricKey)

	authority := cpabe.NewAuthority()
	cache.Store(
		cache.CPABEPublicKeyFileName,
		authority.PublicKeyBytes(),
	)

	for _, attributeCount := range config.AttributeCounts {

		policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

		cache.Store(
			cache.CreateCPABEPolicyFileName(attributeCount),
			[]byte(policy.String()),
		)
		cache.Store(
			cache.CreateCPABEPrivateKeyFileName(attributeCount),
			authority.IssuePrivateKey(attributes).Bytes(),
		)
		cache.Store(
			cache.CreateCPABECiphertextFileName(attributeCount),
			authority.Encrypt(policy, symmetricKey),
		)
	}

	maximumSubscriberCount := 0
	for _, subscriberCount := range config.SubscriberCounts {
		if subscriberCount > maximumSubscriberCount {
			maximumSubscriberCount = subscriberCount
		}
	}

	for index := range maximumSubscriberCount {

		subscriber := rsa.NewRSA(config.FixedRSAKeyBits)
		cache.Store(
			cache.CreateRSAPublicKeyFileName(index),
			subscriber.PublicKeyBytes(),
		)

		if index == 0 {
			cache.Store(cache.RSAPrivateKeyFileName, subscriber.PrivateKeyBytes())
			cache.Store(cache.RSACiphertextFileName, subscriber.Encrypt(symmetricKey))
		}
	}
}
