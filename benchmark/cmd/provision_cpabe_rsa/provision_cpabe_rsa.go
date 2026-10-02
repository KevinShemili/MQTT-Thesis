package main

import (
	"fmt"
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
	dependencies.store(shared.AESKeyFileName, symmetricKey)

	authority := cpabe.NewAuthority()

	dependencies.store(
		shared.CPABEPublicKeyFileName,
		authority.PublicKeyBytes(),
	)

	for _, attributeCount := range attributeCounts {

		policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

		dependencies.store(fmt.Sprintf(shared.CPABEPolicyFileNameFormat, attributeCount), []byte(policy.String()))
		dependencies.store(fmt.Sprintf(shared.CPABEPrivateKeyFileNameFormat, attributeCount), authority.IssuePrivateKey(attributes).Bytes())
		dependencies.store(fmt.Sprintf(shared.CPABECiphertextFileNameFormat, attributeCount), authority.Encrypt(policy, symmetricKey))
	}

	maximumSubscriberCount := subscriberCounts[len(subscriberCounts)-1]

	for index := range maximumSubscriberCount {

		subscriber := rsa.NewRSA(fixedRSAKeyBits)

		dependencies.store(fmt.Sprintf(shared.RSAPublicKeyFileNameFormat, index), subscriber.PublicKeyBytes())

		if index == 0 {

			dependencies.store(shared.RSAPrivateKeyFileName, subscriber.PrivateKeyBytes())

			dependencies.store(shared.RSACiphertextFileName, subscriber.Encrypt(symmetricKey))
		}
	}
}
