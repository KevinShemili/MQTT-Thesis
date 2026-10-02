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

	attributeCounts := []int{1}
	subscriberCounts := []int{2}

	expected := []string{
		"generate",
		"store aes.key",
		"store cpabe-public.key",
		"store cpabe-policy-1.txt",
		"store cpabe-private-1.key",
		"store cpabe-ciphertext-1.bin",
		"store rsa-public-0.key",
		"store rsa-private.key",
		"store rsa-ciphertext.bin",
		"store rsa-public-1.key",
	}

	// Act
	runProvision(attributeCounts, subscriberCounts, 16, 1024, dependencies)

	// Assert
	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}
