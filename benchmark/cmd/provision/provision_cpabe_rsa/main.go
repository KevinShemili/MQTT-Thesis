package main

import (
	"fmt"
	"thesis/benchmark/cmd/provision"
	"thesis/benchmark/micro/cpabe_rsa"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
	"thesis/utility/golang/cache"
	"thesis/utility/golang/generator"
)

// The point of this program is to provide the fixture data for the CP-ABE/RSA
// memory benchmarks by populating the cache in an earlier process.
func main() {

	config := cpabe_rsa.NewCPABERSAConfig()

	dependencies := provision.Dependency{
		GenerateRandomBytes: generator.GenerateRandomBytes,
		Store:               cache.Store,
	}

	runProvision(config.AttributeCounts, config.SubscriberCounts, config.AESKeySize, config.FixedRSAKeyBits, dependencies)
}

func runProvision(attributeCounts []int, subscriberCounts []int, aesKeySize int,
	fixedRSAKeyBits int, dependencies provision.Dependency) {

	symmetricKey := dependencies.GenerateRandomBytes(aesKeySize)
	dependencies.Store(cache.AESKeyFileName, symmetricKey)

	authority := cpabe.NewAuthority()

	dependencies.Store(
		cache.CPABEPublicKeyFileName,
		authority.PublicKeyBytes(),
	)

	for _, attributeCount := range attributeCounts {

		policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

		dependencies.Store(fmt.Sprintf(cache.CPABEPolicyWCountFileName, attributeCount), []byte(policy.String()))
		dependencies.Store(fmt.Sprintf(cache.CPABEPrivateKeyWCountFileName, attributeCount), authority.IssuePrivateKey(attributes).Bytes())
		dependencies.Store(fmt.Sprintf(cache.CPABECiphertextWCountFileName, attributeCount), authority.Encrypt(policy, symmetricKey))
	}

	maximumSubscriberCount := subscriberCounts[len(subscriberCounts)-1]

	for index := range maximumSubscriberCount {

		subscriber := rsa.NewRSA(fixedRSAKeyBits)

		dependencies.Store(fmt.Sprintf(cache.RSAPublicKeyWIndexFileName, index), subscriber.PublicKeyBytes())

		if index == 0 {

			dependencies.Store(cache.RSAPrivateKeyFileName, subscriber.PrivateKeyBytes())

			dependencies.Store(cache.RSACiphertextFileName, subscriber.Encrypt(symmetricKey))
		}
	}
}
