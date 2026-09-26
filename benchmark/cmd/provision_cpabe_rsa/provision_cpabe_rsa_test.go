package main

import (
	"slices"
	"testing"

	"thesis/benchmark/cache"
)

func TestRunProvisionCallsOperationsInExpectedOrder(t *testing.T) {

	// Arrange
	calls := []string{}

	dependencies := provisionDependencies{
		generateRandomBytes: func(count int) []byte {
			calls = append(calls, "generate")
			return make([]byte, count)
		},
		store: func(fileName string, _ []byte) {
			calls = append(calls, "store "+fileName)
		},
	}

	attributeCounts := []int{1}
	subscriberCounts := []int{2}

	expected := []string{
		"generate",
		"store " + cache.AESKeyFileName,
		"store " + cache.CPABEPublicKeyFileName,
		"store " + cache.CreateCPABEPolicyFileName(1),
		"store " + cache.CreateCPABEPrivateKeyFileName(1),
		"store " + cache.CreateCPABECiphertextFileName(1),
		"store " + cache.CreateRSAPublicKeyFileName(0),
		"store " + cache.RSAPrivateKeyFileName,
		"store " + cache.RSACiphertextFileName,
		"store " + cache.CreateRSAPublicKeyFileName(1),
	}

	// Act
	runProvision(attributeCounts, subscriberCounts, 16, 1024, dependencies)

	// Assert
	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}
