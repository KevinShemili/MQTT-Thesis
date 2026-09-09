package main

import (
	"benchmark/cache"
	"benchmark/cryptography/cpabe"
	"benchmark/cryptography/rsa"
	"benchmark/micro/cpabe_rsa/shared"
	"benchmark/utility"
)

// The point of this program is to provide the fixture data for the CP-ABE/RSA
// memory benchmarks by populating the cache in an earlier process.
func main() {

	config := shared.NewCPABERSAConfig()

	symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
	cache.StoreFile(cache.CreateAESKeyFileName(config.AESKeySize), symmetricKey)

	authority := cpabe.NewCPABEAuthority()
	cache.StoreFile(
		cache.CPABEPublicKeyFileName,
		cpabe.MarshalCPABEPublicKey(authority.PublicKey),
	)

	for _, attributeCount := range config.AttributeCounts {

		policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

		cache.StoreFile(
			cache.CreateCPABEPolicyFileName(attributeCount),
			[]byte(policy.String()),
		)
		cache.StoreFile(
			cache.CreateCPABEPrivateKeyFileName(attributeCount),
			cpabe.MarshalCPABEPrivateKey(authority.IssuePrivateKey(attributes).PrivateKey),
		)
		cache.StoreFile(
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

	var firstSubscriber rsa.RSA
	for index := range maximumSubscriberCount {

		subscriber := rsa.NewRSA(config.FixedRSAKeyBits)
		if index == 0 {
			firstSubscriber = subscriber
		}

		cache.StoreFile(
			cache.CreateRSAPrivateKeyFileName(config.FixedRSAKeyBits, index),
			rsa.MarshalPrivateKey(subscriber.PrivateKey),
		)
		cache.StoreFile(
			cache.CreateRSAPublicKeyFileName(config.FixedRSAKeyBits, index),
			rsa.MarshalPublicKey(subscriber.PublicKey),
		)
	}

	cache.StoreFile(
		cache.CreateRSACiphertextFileName(config.FixedRSAKeyBits, 0),
		firstSubscriber.Encrypt(symmetricKey),
	)
}
