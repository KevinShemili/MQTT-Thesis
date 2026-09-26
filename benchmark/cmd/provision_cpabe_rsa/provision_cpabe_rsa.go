package main

import (
	"thesis/benchmark/cache"
	"thesis/benchmark/micro/cpabe_rsa/shared"
	"thesis/benchmark/utility"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
)

type provisionDependencies struct {
	generateRandomBytes func(int) []byte
	store               func(string, []byte)
}

// The point of this program is to provide the fixture data for the CP-ABE/RSA
// memory benchmarks by populating the cache in an earlier process.
func main() {

	config := shared.NewCPABERSAConfig()

	dependencies := provisionDependencies{
		generateRandomBytes: utility.GenerateRandomBytes,
		store:               cache.Store,
	}

	runProvision(config.AttributeCounts, config.SubscriberCounts, config.AESKeySize, config.FixedRSAKeyBits, dependencies)
}

func runProvision(attributeCounts []int, subscriberCounts []int, aesKeySize int,
	fixedRSAKeyBits int, dependencies provisionDependencies) {

	symmetricKey := dependencies.generateRandomBytes(aesKeySize)
	dependencies.store(cache.AESKeyFileName, symmetricKey)

	authority := cpabe.NewAuthority()

	dependencies.store(
		cache.CPABEPublicKeyFileName,
		authority.PublicKeyBytes(),
	)

	for _, attributeCount := range attributeCounts {

		policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

		dependencies.store(cache.CreateCPABEPolicyFileName(attributeCount), []byte(policy.String()))
		dependencies.store(cache.CreateCPABEPrivateKeyFileName(attributeCount), authority.IssuePrivateKey(attributes).Bytes())
		dependencies.store(cache.CreateCPABECiphertextFileName(attributeCount), authority.Encrypt(policy, symmetricKey))
	}

	maximumSubscriberCount := 0

	for _, subscriberCount := range subscriberCounts {
		if subscriberCount > maximumSubscriberCount {
			maximumSubscriberCount = subscriberCount
		}
	}

	for index := range maximumSubscriberCount {

		subscriber := rsa.NewRSA(fixedRSAKeyBits)

		dependencies.store(cache.CreateRSAPublicKeyFileName(index), subscriber.PublicKeyBytes())

		if index == 0 {

			dependencies.store(cache.RSAPrivateKeyFileName, subscriber.PrivateKeyBytes())

			dependencies.store(cache.RSACiphertextFileName, subscriber.Encrypt(symmetricKey))
		}
	}
}
