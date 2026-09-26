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

	payloadSizes := []int{16}

	expected := []string{
		"generate",
		"store " + cache.AESKeyFileName,
		"generate",

		"generate",
		"store " + cache.ASCONKeyFileName,
		"generate",

		"store " + cache.RSAPrivateKeyFileName,
		"store " + cache.RSAPublicKeyFileName,

		"store " + cache.CPABEPublicKeyFileName,
		"store " + cache.CPABEPolicyFileName,
		"store " + cache.CPABEPrivateKeyFileName,

		"generate",
		"store " + cache.CreateFullSchemaPlaintextFileName(16),

		"store " + cache.CreateFullSchemaEnvelopeFileName(
			"psk",
			"standard",
			16,
		),

		"store " + cache.CreateFullSchemaEnvelopeFileName(
			"psk",
			"lightweight",
			16,
		),

		"store " + cache.CreateFullSchemaEnvelopeFileName(
			"rsa",
			"standard",
			16,
		),

		"store " + cache.CreateFullSchemaEnvelopeFileName(
			"rsa",
			"lightweight",
			16,
		),

		"store " + cache.CreateFullSchemaEnvelopeFileName(
			"cpabe",
			"standard",
			16,
		),

		"store " + cache.CreateFullSchemaEnvelopeFileName(
			"cpabe",
			"lightweight",
			16,
		),
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
