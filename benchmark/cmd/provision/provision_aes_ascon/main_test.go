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
	runProvision(nil, 16, 16, dependencies)

	// Assert
	expected := []string{
		cache.AESKeyFileName,
		cache.ASCONKeyFileName,
		cache.AESNonceFileName,
		cache.ASCONNonceFileName,
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
	runProvision(payloadSizes, 16, 16, dependencies)

	// Assert
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

	slices.Sort(stored)
	slices.Sort(expected)

	if !slices.Equal(stored, expected) {
		t.Fatalf("stored %v, want %v", stored, expected)
	}
}
