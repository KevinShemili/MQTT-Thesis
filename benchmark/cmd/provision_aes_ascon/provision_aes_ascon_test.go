package main

import (
	"slices"
	"testing"
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
		"store aes.key",
		"generate",
		"store ascon.key",
		"generate",
		"store aes.nonce",
		"generate",
		"store ascon.nonce",
		"generate",
		"store plaintext-16.bin",
		"store aes-ciphertext-16.bin",
		"store ascon-ciphertext-16.bin",
		"generate",
		"store plaintext-32.bin",
		"store aes-ciphertext-32.bin",
		"store ascon-ciphertext-32.bin",
	}

	// Act
	runProvision(payloadSizes, 16, 16, dependencies)

	// Assert
	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}
