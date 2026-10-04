package main

import (
	"fmt"
	"slices"
	"testing"

	"thesis/benchmark/cmd/provision"
	"thesis/utility/golang/cache"
)

func TestRunProvisionStoresBaseFixturesWhenPayloadSizesEmpty(t *testing.T) {

	// Arrange
	var stored []string

	dependencies := provision.Dependency{
		Store: func(fileName string, _ []byte) {
			stored = append(stored, fileName)
		},
	}

	// Act
	runProvision(nil, 16, 2048, 1, dependencies)

	// Assert
	expected := []string{
		cache.AESKeyFileName,
		cache.ASCONKeyFileName,
		cache.RSAPrivateKeyFileName,
		cache.RSAPublicKeyFileName,
		cache.CPABEPublicKeyFileName,
		cache.CPABEPolicyFileName,
		cache.CPABEPrivateKeyFileName,
	}

	slices.Sort(stored)
	slices.Sort(expected)

	if !slices.Equal(stored, expected) {
		t.Fatalf("stored %v, want %v", stored, expected)
	}
}

func TestRunProvisionStoresPayloadFixtures(t *testing.T) {

	// Arrange
	var stored []string

	dependencies := provision.Dependency{
		Store: func(fileName string, _ []byte) {
			stored = append(stored, fileName)
		},
	}

	payloadSizes := []int{16, 32}

	// Act
	runProvision(payloadSizes, 16, 2048, 1, dependencies)

	// Assert
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

		fmt.Sprintf(cache.PlaintextFileWSizeName, 32),
		fmt.Sprintf(cache.PSKStandardEnvelopeWSizeFileName, 32),
		fmt.Sprintf(cache.PSKLightEnvelopeWSizeFileName, 32),
		fmt.Sprintf(cache.RSAStandardEnvelopeWSizeFileName, 32),
		fmt.Sprintf(cache.RSALightEnvelopeWSizeFileName, 32),
		fmt.Sprintf(cache.CPABEStandardEnvelopeWSizeFileName, 32),
		fmt.Sprintf(cache.CPABELightEnvelopeWSizeFileName, 32),
	}

	slices.Sort(stored)
	slices.Sort(expected)

	if !slices.Equal(stored, expected) {
		t.Fatalf("stored %v, want %v", stored, expected)
	}
}
