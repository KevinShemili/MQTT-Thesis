package main

import (
	"fmt"
	"testing"

	"thesis/benchmark/cmd/provision"
	"thesis/utility/golang/cache"
)

func TestRunProvisionStoresAllFixtures(t *testing.T) {

	// Arrange
	stored := map[string]bool{}

	dependencies := provision.Dependency{
		GenerateRandomBytes: func(count int) []byte {
			return make([]byte, count)
		},
		Store: func(fileName string, _ []byte) {
			stored[fileName] = true
		},
	}

	attributeCounts := []int{1}
	subscriberCounts := []int{2}

	expected := []string{
		cache.AESKeyFileName,
		cache.CPABEPublicKeyFileName,
		fmt.Sprintf(cache.CPABEPolicyWCountFileName, 1),
		fmt.Sprintf(cache.CPABEPrivateKeyWCountFileName, 1),
		fmt.Sprintf(cache.CPABECiphertextWCountFileName, 1),
		fmt.Sprintf(cache.RSAPublicKeyWIndexFileName, 0),
		fmt.Sprintf(cache.RSAPublicKeyWIndexFileName, 1),
		cache.RSAPrivateKeyFileName,
		cache.RSACiphertextFileName,
	}

	// Act
	runProvision(attributeCounts, subscriberCounts, 16, 1024, dependencies)

	// Assert
	for _, fileName := range expected {
		if !stored[fileName] {
			t.Fatalf("expected %s to be stored", fileName)
		}
	}
}
