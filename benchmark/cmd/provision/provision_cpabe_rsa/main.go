package main

import (
	"fmt"
	"thesis/benchmark/cache"
	"thesis/benchmark/cmd/provision/shared"
	"thesis/benchmark/micro/cpabe_rsa/shared"
	"thesis/benchmark/utility"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
)

// The point of this program is to provide the fixture data for the CP-ABE/RSA
// memory benchmarks by populating the cache in an earlier process.
func main() {

	config := shared.NewCPABERSAConfig()

	dependencies := cmdshared.ProvisionDependencies{
		GenerateRandomBytes: utility.GenerateRandomBytes,
		Store:               cache.Store,
	}

	runProvision(config.AttributeCounts, config.SubscriberCounts, config.AESKeySize, config.FixedRSAKeyBits, dependencies)
}

func runProvision(attributeCounts []int, subscriberCounts []int, aesKeySize int,
	fixedRSAKeyBits int, dependencies cmdshared.ProvisionDependencies) {

	symmetricKey := dependencies.GenerateRandomBytes(aesKeySize)
	dependencies.Store(shared.AESKeyFileName, symmetricKey)

	authority := cpabe.NewAuthority()

	dependencies.Store(
		shared.CPABEPublicKeyFileName,
		authority.PublicKeyBytes(),
	)

	for _, attributeCount := range attributeCounts {

		policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

		dependencies.Store(fmt.Sprintf(shared.CPABEPolicyFileNameFormat, attributeCount), []byte(policy.String()))
		dependencies.Store(fmt.Sprintf(shared.CPABEPrivateKeyFileNameFormat, attributeCount), authority.IssuePrivateKey(attributes).Bytes())
		dependencies.Store(fmt.Sprintf(shared.CPABECiphertextFileNameFormat, attributeCount), authority.Encrypt(policy, symmetricKey))
	}

	maximumSubscriberCount := subscriberCounts[len(subscriberCounts)-1]

	for index := range maximumSubscriberCount {

		subscriber := rsa.NewRSA(fixedRSAKeyBits)

		dependencies.Store(fmt.Sprintf(shared.RSAPublicKeyFileNameFormat, index), subscriber.PublicKeyBytes())

		if index == 0 {

			dependencies.Store(shared.RSAPrivateKeyFileName, subscriber.PrivateKeyBytes())

			dependencies.Store(shared.RSACiphertextFileName, subscriber.Encrypt(symmetricKey))
		}
	}
}
