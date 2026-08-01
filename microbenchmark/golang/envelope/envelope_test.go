package envelope

import (
	"bytes"
	"testing"
)

func TestJSONEnvelopeRoundTrip(t *testing.T) {

	// Arrange
	message := Envelope{
		ABECiphertext: []byte("abe ciphertext"),
		Nonce:         []byte("nonce"),
		AESCiphertext: []byte("aes ciphertext"),
	}

	// Act
	serialized := SerializeJSON(message)
	deserialized := DeserializeJSON(serialized)

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
	message := Envelope{
		ABECiphertext: []byte("abe ciphertext"),
		Nonce:         []byte("nonce"),
		AESCiphertext: []byte("aes ciphertext"),
	}

	// Act
	serialized := SerializeCBOR(message)
	deserialized := DeserializeCBOR(serialized)

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
	message := EnvelopeIntKeys{
		ABECiphertext: []byte("abe ciphertext"),
		Nonce:         []byte("nonce"),
		AESCiphertext: []byte("aes ciphertext"),
	}

	// Act
	serialized := SerializeCBORKeyAsInt(message)
	deserialized := DeserializeCBORKeyAsInt(serialized)

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
