package unit

import (
	"benchmark/envelope"
	"bytes"
	"testing"
)

func TestJSONEnvelopeRoundTrip(t *testing.T) {

	// Arrange
	message := envelope.Envelope{
		ABECiphertext: []byte("abe ciphertext"),
		Nonce:         []byte("nonce"),
		AESCiphertext: []byte("aes ciphertext"),
	}

	// Act
	serialized := envelope.SerializeJSON(message)
	deserialized := envelope.DeserializeJSON(serialized)

	// Assert
	if !bytes.Equal(deserialized.ABECiphertext, message.ABECiphertext) {
		t.Fatalf(
			"ABE ciphertext produced %q, want %q",
			deserialized.ABECiphertext,
			message.ABECiphertext,
		)
	}

	if !bytes.Equal(deserialized.Nonce, message.Nonce) {
		t.Fatalf(
			"nonce produced %q, want %q",
			deserialized.Nonce,
			message.Nonce,
		)
	}

	if !bytes.Equal(deserialized.AESCiphertext, message.AESCiphertext) {
		t.Fatalf(
			"AES ciphertext produced %q, want %q",
			deserialized.AESCiphertext,
			message.AESCiphertext,
		)
	}
}

func TestCBOREnvelopeRoundTrip(t *testing.T) {

	// Arrange
	message := envelope.Envelope{
		ABECiphertext: []byte("abe ciphertext"),
		Nonce:         []byte("nonce"),
		AESCiphertext: []byte("aes ciphertext"),
	}

	// Act
	serialized := envelope.SerializeCBOR(message)
	deserialized := envelope.DeserializeCBOR(serialized)

	// Assert
	if !bytes.Equal(deserialized.ABECiphertext, message.ABECiphertext) {
		t.Fatalf(
			"ABE ciphertext produced %q, want %q",
			deserialized.ABECiphertext,
			message.ABECiphertext,
		)
	}

	if !bytes.Equal(deserialized.Nonce, message.Nonce) {
		t.Fatalf(
			"nonce produced %q, want %q",
			deserialized.Nonce,
			message.Nonce,
		)
	}

	if !bytes.Equal(deserialized.AESCiphertext, message.AESCiphertext) {
		t.Fatalf(
			"AES ciphertext produced %q, want %q",
			deserialized.AESCiphertext,
			message.AESCiphertext,
		)
	}
}

func TestCBORIntegerKeyEnvelopeRoundTrip(t *testing.T) {

	// Arrange
	message := envelope.EnvelopeIntKeys{
		ABECiphertext: []byte("abe ciphertext"),
		Nonce:         []byte("nonce"),
		AESCiphertext: []byte("aes ciphertext"),
	}

	// Act
	serialized := envelope.SerializeCBORKeyAsInt(message)
	deserialized := envelope.DeserializeCBORKeyAsInt(serialized)

	// Assert
	if !bytes.Equal(deserialized.ABECiphertext, message.ABECiphertext) {
		t.Fatalf(
			"ABE ciphertext produced %q, want %q",
			deserialized.ABECiphertext,
			message.ABECiphertext,
		)
	}

	if !bytes.Equal(deserialized.Nonce, message.Nonce) {
		t.Fatalf(
			"nonce produced %q, want %q",
			deserialized.Nonce,
			message.Nonce,
		)
	}

	if !bytes.Equal(deserialized.AESCiphertext, message.AESCiphertext) {
		t.Fatalf(
			"AES ciphertext produced %q, want %q",
			deserialized.AESCiphertext,
			message.AESCiphertext,
		)
	}
}
