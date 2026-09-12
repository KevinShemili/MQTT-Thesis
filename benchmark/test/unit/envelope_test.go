package unit

import (
	"benchmark/envelope"
	"bytes"
	"testing"
)

func TestJSONEnvelopeRoundTrip(t *testing.T) {

	// Arrange
	message := envelope.Envelope{
		AsymmetricCiphertext: []byte("asymmetric ciphertext"),
		Nonce:                []byte("nonce"),
		SymmetricCiphertext:  []byte("symmetric ciphertext"),
	}

	// Act
	serialized := envelope.SerializeJSON(message)
	deserialized := envelope.DeserializeJSON(serialized)

	// Assert
	if !bytes.Equal(deserialized.AsymmetricCiphertext, message.AsymmetricCiphertext) {
		t.Fatalf(
			"asymmetric ciphertext produced %q, want %q",
			deserialized.AsymmetricCiphertext,
			message.AsymmetricCiphertext,
		)
	}

	if !bytes.Equal(deserialized.Nonce, message.Nonce) {
		t.Fatalf(
			"nonce produced %q, want %q",
			deserialized.Nonce,
			message.Nonce,
		)
	}

	if !bytes.Equal(deserialized.SymmetricCiphertext, message.SymmetricCiphertext) {
		t.Fatalf(
			"symmetric ciphertext produced %q, want %q",
			deserialized.SymmetricCiphertext,
			message.SymmetricCiphertext,
		)
	}
}

func TestCBOREnvelopeRoundTrip(t *testing.T) {

	// Arrange
	message := envelope.Envelope{
		AsymmetricCiphertext: []byte("asymmetric ciphertext"),
		Nonce:                []byte("nonce"),
		SymmetricCiphertext:  []byte("symmetric ciphertext"),
	}

	// Act
	serialized := envelope.SerializeCBOR(message)
	deserialized := envelope.DeserializeCBOR(serialized)

	// Assert
	if !bytes.Equal(deserialized.AsymmetricCiphertext, message.AsymmetricCiphertext) {
		t.Fatalf(
			"asymmetric ciphertext produced %q, want %q",
			deserialized.AsymmetricCiphertext,
			message.AsymmetricCiphertext,
		)
	}

	if !bytes.Equal(deserialized.Nonce, message.Nonce) {
		t.Fatalf(
			"nonce produced %q, want %q",
			deserialized.Nonce,
			message.Nonce,
		)
	}

	if !bytes.Equal(deserialized.SymmetricCiphertext, message.SymmetricCiphertext) {
		t.Fatalf(
			"symmetric ciphertext produced %q, want %q",
			deserialized.SymmetricCiphertext,
			message.SymmetricCiphertext,
		)
	}
}

func TestCBORIntegerKeyEnvelopeRoundTrip(t *testing.T) {

	// Arrange
	message := envelope.EnvelopeIntKeys{
		AsymmetricCiphertext: []byte("asymmetric ciphertext"),
		Nonce:                []byte("nonce"),
		SymmetricCiphertext:  []byte("symmetric ciphertext"),
	}

	// Act
	serialized := envelope.SerializeCBORKeyAsInt(message)
	deserialized := envelope.DeserializeCBORKeyAsInt(serialized)

	// Assert
	if !bytes.Equal(deserialized.AsymmetricCiphertext, message.AsymmetricCiphertext) {
		t.Fatalf(
			"asymmetric ciphertext produced %q, want %q",
			deserialized.AsymmetricCiphertext,
			message.AsymmetricCiphertext,
		)
	}

	if !bytes.Equal(deserialized.Nonce, message.Nonce) {
		t.Fatalf(
			"nonce produced %q, want %q",
			deserialized.Nonce,
			message.Nonce,
		)
	}

	if !bytes.Equal(deserialized.SymmetricCiphertext, message.SymmetricCiphertext) {
		t.Fatalf(
			"symmetric ciphertext produced %q, want %q",
			deserialized.SymmetricCiphertext,
			message.SymmetricCiphertext,
		)
	}
}
