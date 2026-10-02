package main

import (
	"testing"

	cmdshared "thesis/benchmark/cmd/provision/shared"
	macroshared "thesis/benchmark/macro/shared"
)

func TestRunProvisionStoresAllKeys(t *testing.T) {

	// Arrange
	stored := map[string]bool{}

	config := macroshared.CryptographyConfig{
		SymmetricKeySize: 32,
		RSAKeyBits:       2048,
		AttributeCount:   1,
	}

	dependencies := cmdshared.ProvisionDependencies{
		GenerateRandomBytes: func(size int) []byte {
			return make([]byte, size)
		},
		Store: func(name string, data []byte) {
			stored[name] = true
		},
	}

	expected := []string{
		macroshared.AESKeyFileName,
		macroshared.ASCONKeyFileName,
		macroshared.RSAPublicKeyFileName,
		macroshared.RSAPrivateKeyFileName,
		macroshared.CPABEPublicKeyFileName,
		macroshared.CPABEPrivateKeyFileName,
	}

	// Act
	runProvision(config, dependencies)

	// Assert
	for _, name := range expected {
		if !stored[name] {
			t.Fatalf("expected %s to be stored", name)
		}
	}
}
