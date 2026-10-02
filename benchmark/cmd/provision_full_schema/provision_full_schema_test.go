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

	payloadSizes := []int{16}

	expected := []string{
		"generate",
		"store aes.key",
		"generate",

		"generate",
		"store ascon.key",
		"generate",

		"store rsa-private.key",
		"store rsa-public.key",

		"store cpabe-public.key",
		"store cpabe-policy.txt",
		"store cpabe-private.key",

		"generate",
		"store plaintext-16.bin",

		"store psk-standard-16.bin",
		"store psk-lightweight-16.bin",
		"store rsa-standard-16.bin",
		"store rsa-lightweight-16.bin",
		"store cpabe-standard-16.bin",
		"store cpabe-lightweight-16.bin",
	}

	// Act
	runProvision(
		payloadSizes,
		16,
		2048,
		1,
		dependencies,
	)

	// Assert
	if !slices.Equal(calls, expected) {
		t.Fatalf(
			"unexpected call order:\nexpected: %v\ngot:      %v",
			expected,
			calls,
		)
	}
}
