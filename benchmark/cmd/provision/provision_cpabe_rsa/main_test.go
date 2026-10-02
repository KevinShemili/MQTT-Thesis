package main

import (
	"fmt"
	"testing"

	cmdshared "thesis/benchmark/cmd/provision/shared"
	"thesis/benchmark/micro/cpabe_rsa/shared"
)

func TestRunProvisionStoresAllFixtures(t *testing.T) {

	// Arrange
	stored := map[string]bool{}

	dependencies := cmdshared.ProvisionDependencies{
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
		shared.AESKeyFileName,
		shared.CPABEPublicKeyFileName,
		fmt.Sprintf(shared.CPABEPolicyFileNameFormat, 1),
		fmt.Sprintf(shared.CPABEPrivateKeyFileNameFormat, 1),
		fmt.Sprintf(shared.CPABECiphertextFileNameFormat, 1),
		fmt.Sprintf(shared.RSAPublicKeyFileNameFormat, 0),
		fmt.Sprintf(shared.RSAPublicKeyFileNameFormat, 1),
		shared.RSAPrivateKeyFileName,
		shared.RSACiphertextFileName,
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
