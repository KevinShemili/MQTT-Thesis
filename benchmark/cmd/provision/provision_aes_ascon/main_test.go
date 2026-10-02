package main

import (
	"fmt"
	"testing"

	cmdshared "thesis/benchmark/cmd/provision/shared"
	"thesis/benchmark/micro/aes_ascon/shared"
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

	payloadSizes := []int{16, 32}

	expected := []string{
		shared.AESKeyFileName,
		shared.ASCONKeyFileName,
		shared.AESNonceFileName,
		shared.ASCONNonceFileName,
		fmt.Sprintf(shared.PlaintextFileNameFormat, 16),
		fmt.Sprintf(shared.AESCiphertextFileNameFormat, 16),
		fmt.Sprintf(shared.ASCONCiphertextFileNameFormat, 16),
		fmt.Sprintf(shared.PlaintextFileNameFormat, 32),
		fmt.Sprintf(shared.AESCiphertextFileNameFormat, 32),
		fmt.Sprintf(shared.ASCONCiphertextFileNameFormat, 32),
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
