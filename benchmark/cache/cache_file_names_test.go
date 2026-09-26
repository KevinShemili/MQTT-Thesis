package cache

import "testing"

func TestCreateCPABEPolicyFileName(t *testing.T) {

	// Arrange
	attributeCount := 5
	expected := "cpabe-policy-a5"

	// Act
	actual := CreateCPABEPolicyFileName(attributeCount)

	// Assert
	if actual != expected {
		t.Fatalf("expected %q, got %q", expected, actual)
	}
}

func TestCreateCPABEPrivateKeyFileName(t *testing.T) {

	// Arrange
	attributeCount := 5
	expected := "cpabe-private-key-a5"

	// Act
	actual := CreateCPABEPrivateKeyFileName(attributeCount)

	// Assert
	if actual != expected {
		t.Fatalf("expected %q, got %q", expected, actual)
	}
}

func TestCreateCPABECiphertextFileName(t *testing.T) {

	// Arrange
	attributeCount := 5
	expected := "cpabe-ciphertext-a5"

	// Act
	actual := CreateCPABECiphertextFileName(attributeCount)

	// Assert
	if actual != expected {
		t.Fatalf("expected %q, got %q", expected, actual)
	}
}

func TestCreateAESASCONPlaintextFileName(t *testing.T) {

	// Arrange
	payloadSize := 256
	expected := "aes-ascon-plaintext-256"

	// Act
	actual := CreateAESASCONPlaintextFileName(payloadSize)

	// Assert
	if actual != expected {
		t.Fatalf("expected %q, got %q", expected, actual)
	}
}

func TestCreateAESGCMCiphertextFileName(t *testing.T) {

	// Arrange
	payloadSize := 256
	expected := "aes-gcm-ciphertext-256"

	// Act
	actual := CreateAESGCMCiphertextFileName(payloadSize)

	// Assert
	if actual != expected {
		t.Fatalf("expected %q, got %q", expected, actual)
	}
}

func TestCreateFullSchemaPlaintextFileName(t *testing.T) {

	// Arrange
	payloadSize := 256
	expected := "full-schema-plaintext-256"

	// Act
	actual := CreateFullSchemaPlaintextFileName(payloadSize)

	// Assert
	if actual != expected {
		t.Fatalf("expected %q, got %q", expected, actual)
	}
}

func TestCreateFullSchemaEnvelopeFileName(t *testing.T) {

	// Arrange
	keyManagement := "cpabe"
	profile := "lightweight"
	payloadSize := 256
	expected := "full-schema-cpabe-lightweight-envelope-256"

	// Act
	actual := CreateFullSchemaEnvelopeFileName(
		keyManagement,
		profile,
		payloadSize,
	)

	// Assert
	if actual != expected {
		t.Fatalf("expected %q, got %q", expected, actual)
	}
}

func TestCreateASCONCiphertextFileName(t *testing.T) {

	// Arrange
	payloadSize := 256
	expected := "ascon-ciphertext-256"

	// Act
	actual := CreateASCONCiphertextFileName(payloadSize)

	// Assert
	if actual != expected {
		t.Fatalf("expected %q, got %q", expected, actual)
	}
}

func TestCreateRSAPublicKeyFileName(t *testing.T) {

	// Arrange
	subscriberIndex := 3
	expected := "rsa-public-key-i3"

	// Act
	actual := CreateRSAPublicKeyFileName(subscriberIndex)

	// Assert
	if actual != expected {
		t.Fatalf("expected %q, got %q", expected, actual)
	}
}
