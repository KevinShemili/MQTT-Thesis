package main

import (
	"fmt"
	"slices"
	"testing"

	"thesis/benchmark/cmd/provision"
	"thesis/utility/golang/cache"
)

func TestRunProvisionStoresBaseAndRSAFixturesWhenAttributeCountsEmpty(t *testing.T) {

	// Arrange
	var stored []string

	dependencies := provision.Dependency{
		Store: func(fileName string, _ []byte) {
			stored = append(stored, fileName)
		},
	}

	// Act
	runProvision(nil, []int{2}, 16, 1024, dependencies)

	// Assert
	expected := []string{
		cache.AESKeyFileName,
		cache.CPABEPublicKeyFileName,
		fmt.Sprintf(cache.RSAPublicKeyWIndexFileName, 0),
		fmt.Sprintf(cache.RSAPublicKeyWIndexFileName, 1),
		cache.RSAPrivateKeyFileName,
		cache.RSACiphertextFileName,
	}

	slices.Sort(stored)
	slices.Sort(expected)

	if !slices.Equal(stored, expected) {
		t.Fatalf("stored %v, want %v", stored, expected)
	}
}

func TestRunProvisionStoresAllFixtures(t *testing.T) {

	// Arrange
	var stored []string

	dependencies := provision.Dependency{
		Store: func(fileName string, _ []byte) {
			stored = append(stored, fileName)
		},
	}

	attributeCounts := []int{1}
	subscriberCounts := []int{2}

	// Act
	runProvision(attributeCounts, subscriberCounts, 16, 1024, dependencies)

	// Assert
	expected := []string{
		cache.AESKeyFileName,
		cache.CPABEPublicKeyFileName,

		fmt.Sprintf(cache.CPABEPolicyWCountFileName, 1),
		fmt.Sprintf(cache.CPABEPrivateKeyWCountFileName, 1),
		fmt.Sprintf(cache.CPABECiphertextWCountFileName, 1),

		fmt.Sprintf(cache.RSAPublicKeyWIndexFileName, 0),
		fmt.Sprintf(cache.RSAPublicKeyWIndexFileName, 1),
		cache.RSAPrivateKeyFileName,
		cache.RSACiphertextFileName,
	}

	slices.Sort(stored)
	slices.Sort(expected)

	if !slices.Equal(stored, expected) {
		t.Fatalf("stored %v, want %v", stored, expected)
	}
}
