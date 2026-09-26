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

	payloadSizes := []int{16, 32}

	expected := []string{
		"generate",
		"store " + cache.AESKeyFileName,
		"generate",
		"store " + cache.ASCONKeyFileName,
		"generate",
		"store " + cache.AESGCMNonceFileName,
		"generate",
		"store " + cache.ASCONNonceFileName,
		"generate",
		"store " + cache.CreateAESASCONPlaintextFileName(16),
		"store " + cache.CreateAESGCMCiphertextFileName(16),
		"store " + cache.CreateASCONCiphertextFileName(16),
		"generate",
		"store " + cache.CreateAESASCONPlaintextFileName(32),
		"store " + cache.CreateAESGCMCiphertextFileName(32),
		"store " + cache.CreateASCONCiphertextFileName(32),
	}

	// Act
	runProvision(payloadSizes, 16, 16, dependencies)

	// Assert
	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}
