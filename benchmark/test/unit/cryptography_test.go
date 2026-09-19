package unit

import (
	"bytes"
	"testing"
	"thesis/benchmark/utility"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
)

var AES_KEY_SIZE = 16
var ASCON_KEY_SIZE = 16
var RSA_KEY_SIZE = 2048

func TestAESRoundTrip(t *testing.T) {

	// Arrange
	key := utility.GenerateRandomBytes(AES_KEY_SIZE)
	plaintext := []byte("test")
	aes := aes.NewAES(key)
	nonce := utility.GenerateRandomBytes(aes.NonceSize())

	// Act
	ciphertext := aes.Encrypt(nil, nonce, plaintext)
	decrypted := aes.Decrypt(nil, nonce, ciphertext)

	// Assert
	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("AES: Round trip produced %q, want %q", decrypted, plaintext)
	}
}

func TestASCONRoundTrip(t *testing.T) {

	// Arrange
	key := utility.GenerateRandomBytes(ASCON_KEY_SIZE)
	plaintext := []byte("test")
	ascon := ascon.NewASCON(key)
	nonce := utility.GenerateRandomBytes(ascon.NonceSize())

	// Act
	ciphertext := ascon.Encrypt(nil, nonce, plaintext)
	decrypted := ascon.Decrypt(nil, nonce, ciphertext)

	// Assert
	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("ASCON: Round trip produced %q, want %q", decrypted, plaintext)
	}
}

func TestRSARoundTrip(t *testing.T) {

	// Arrange
	plaintext := []byte("test")
	rsaScheme := rsa.NewRSA(RSA_KEY_SIZE)
	publicKey := rsa.RSAFromPublicKeyBytes(rsaScheme.PublicKeyBytes())
	privateKey := rsa.RSAFromPrivateKeyBytes(rsaScheme.PrivateKeyBytes())

	// Act
	ciphertext := publicKey.Encrypt(plaintext)
	decrypted := privateKey.Decrypt(ciphertext)

	// Assert
	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("RSA: Round trip produced %q, want %q", decrypted, plaintext)
	}
}

func TestCPABERoundTrip(t *testing.T) {

	// Arrange
	plaintext := []byte("test")
	policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(1)
	authority := cpabe.NewAuthority()
	publicAuthority := cpabe.AuthorityFromPublicKeyBytes(authority.PublicKeyBytes())
	privateKey := cpabe.PrivateKeyFromBytes(authority.IssuePrivateKey(attributes).Bytes())

	// Act
	ciphertext := publicAuthority.Encrypt(policy, plaintext)
	decrypted := privateKey.Decrypt(ciphertext)

	// Assert
	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("CP-ABE: Round trip produced %q, want %q", decrypted, plaintext)
	}
}
