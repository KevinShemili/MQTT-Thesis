package main

import (
	"slices"
	"testing"

	"thesis/benchmark/cmd/provision"
	"thesis/benchmark/macro"
	"thesis/utility/golang/cache"
)

func TestRunProvisionStoresAllKeys(t *testing.T) {

	// Arrange
	var stored []string

	config := macro.CryptographyConfig{
		SymmetricKeySize: 32,
		RSAKeyBits:       2048,
		AttributeCount:   1,
	}

	dependencies := provision.Dependency{
		Store: func(name string, _ []byte) {
			stored = append(stored, name)
		},
	}

	// Act
	runProvision(config, dependencies)

	// Assert
	expected := []string{
		cache.AESKeyFileName,
		cache.ASCONKeyFileName,
		cache.RSAPublicKeyFileName,
		cache.RSAPrivateKeyFileName,
		cache.CPABEPublicKeyFileName,
		cache.CPABEPrivateKeyFileName,
	}

	slices.Sort(stored)
	slices.Sort(expected)

	if !slices.Equal(stored, expected) {
		t.Fatalf("stored %v, want %v", stored, expected)
	}
}
