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

	payloadSizes := []int{16}

	expected := []string{
		cache.AESKeyFileName,
		cache.ASCONKeyFileName,
		cache.RSAPrivateKeyFileName,
		cache.RSAPublicKeyFileName,
		cache.CPABEPublicKeyFileName,
		cache.CPABEPolicyFileName,
		cache.CPABEPrivateKeyFileName,
		fmt.Sprintf(cache.PlaintextFileWSizeName, 16),
		fmt.Sprintf(cache.PSKStandardEnvelopeWSizeFileName, 16),
		fmt.Sprintf(cache.PSKLightEnvelopeWSizeFileName, 16),
		fmt.Sprintf(cache.RSAStandardEnvelopeWSizeFileName, 16),
		fmt.Sprintf(cache.RSALightEnvelopeWSizeFileName, 16),
		fmt.Sprintf(cache.CPABEStandardEnvelopeWSizeFileName, 16),
		fmt.Sprintf(cache.CPABELightEnvelopeWSizeFileName, 16),
	}

	// Act
	runProvision(
		payloadSizes,
		16,
		2048,
		1,
		dependencies,
	)

	// Assert
	for _, fileName := range expected {
		if !stored[fileName] {
			t.Fatalf("expected %s to be stored", fileName)
		}
	}
}
