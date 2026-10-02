package main

import (
	"fmt"
	"testing"

	cmdshared "thesis/benchmark/cmd/provision/shared"
	"thesis/benchmark/micro/full_schema/shared"
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

	payloadSizes := []int{16}

	expected := []string{
		shared.AESKeyFileName,
		shared.ASCONKeyFileName,
		shared.RSAPrivateKeyFileName,
		shared.RSAPublicKeyFileName,
		shared.CPABEPublicKeyFileName,
		shared.CPABEPolicyFileName,
		shared.CPABEPrivateKeyFileName,
		fmt.Sprintf(shared.PlaintextFileNameFormat, 16),
		fmt.Sprintf(shared.PSKStandardEnvelopeFileNameFormat, 16),
		fmt.Sprintf(shared.PSKLightweightEnvelopeFileNameFormat, 16),
		fmt.Sprintf(shared.RSAStandardEnvelopeFileNameFormat, 16),
		fmt.Sprintf(shared.RSALightweightEnvelopeFileNameFormat, 16),
		fmt.Sprintf(shared.CPABEStandardEnvelopeFileNameFormat, 16),
		fmt.Sprintf(shared.CPABELightweightEnvelopeFileNameFormat, 16),
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
