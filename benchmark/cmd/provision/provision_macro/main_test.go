package main

import (
	"testing"

	"thesis/benchmark/cmd/provision"
	"thesis/benchmark/macro"
	"thesis/utility/golang/cache"
)

func TestRunProvisionStoresAllKeys(t *testing.T) {

	// Arrange
	stored := map[string]bool{}

	config := macro.CryptographyConfig{
		SymmetricKeySize: 32,
		RSAKeyBits:       2048,
		AttributeCount:   1,
	}

	dependencies := provision.Dependency{
		GenerateRandomBytes: func(size int) []byte {
			return make([]byte, size)
		},
		Store: func(name string, data []byte) {
			stored[name] = true
		},
	}

	expected := []string{
		cache.AESKeyFileName,
		cache.ASCONKeyFileName,
		cache.RSAPublicKeyFileName,
		cache.RSAPrivateKeyFileName,
		cache.CPABEPublicKeyFileName,
		cache.CPABEPrivateKeyFileName,
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
