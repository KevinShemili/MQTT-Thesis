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

	payloadSizes := []int{16, 32}

	expected := []string{
		cache.AESKeyFileName,
		cache.ASCONKeyFileName,
		cache.AESNonceFileName,
		cache.ASCONNonceFileName,
		fmt.Sprintf(cache.PlaintextFileWSizeName, 16),
		fmt.Sprintf(cache.AESCiphertextWSizeFileName, 16),
		fmt.Sprintf(cache.ASCONCiphertextWSizeFileName, 16),
		fmt.Sprintf(cache.PlaintextFileWSizeName, 32),
		fmt.Sprintf(cache.AESCiphertextWSizeFileName, 32),
		fmt.Sprintf(cache.ASCONCiphertextWSizeFileName, 32),
	}

	// Act
	runProvision(payloadSizes, 16, 16, dependencies)

	// Assert
	for _, fileName := range expected {
		if !stored[fileName] {
			t.Fatalf("expected %s to be stored", fileName)
		}
	}
}
