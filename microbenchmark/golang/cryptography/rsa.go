package cryptography

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"fmt"
	"os"
	"path/filepath"
)

type RSA struct {
	PrivateKey *rsa.PrivateKey
	PublicKey  *rsa.PublicKey
}

func NewRSA(keyBits int) RSA {

	privateKey, err := rsa.GenerateKey(rand.Reader, keyBits)
	if err != nil {
		panic(err)
	}

	return RSA{PrivateKey: privateKey, PublicKey: &privateKey.PublicKey}
}

func (r RSA) Encrypt(plaintext []byte) []byte {

	ciphertext, err := rsa.EncryptOAEP(sha256.New(), rand.Reader, r.PublicKey, plaintext, nil)
	if err != nil {
		panic(err)
	}

	return ciphertext
}

func (r RSA) Decrypt(ciphertext []byte) []byte {

	plaintext, err := rsa.DecryptOAEP(sha256.New(), rand.Reader, r.PrivateKey, ciphertext, nil)
	if err != nil {
		panic(err)
	}

	return plaintext
}

func (r RSA) StoredKeySize() int {

	return len(x509.MarshalPKCS1PrivateKey(r.PrivateKey))
}

// Reads the key stored at one position, and reports whether it was ever stored.
// Keys are reached by position rather than by listing the directory so that a caller
// restores exactly the ones it asked for
func LoadRSAKey(directory string, index int) (RSA, bool) {

	keyBytes, found := readKeyFile(privateKeyPath(directory, index))
	if !found {
		return RSA{}, false
	}

	privateKey, err := x509.ParsePKCS1PrivateKey(keyBytes)
	if err != nil {
		panic(err)
	}

	return RSA{PrivateKey: privateKey, PublicKey: &privateKey.PublicKey}, true
}

// A publisher holds public keys and never private ones, so the two halves are stored
// apart and this restores one without the private material entering the process at all
func LoadRSAPublicKey(directory string, index int) (RSA, bool) {

	keyBytes, found := readKeyFile(publicKeyPath(directory, index))
	if !found {
		return RSA{}, false
	}

	publicKey, err := x509.ParsePKCS1PublicKey(keyBytes)
	if err != nil {
		panic(err)
	}

	return RSA{PublicKey: publicKey}, true
}

// Appends one key to the directory, named by its position
func StoreRSAKey(key RSA, directory string, index int) {

	writeKeyFile(
		privateKeyPath(directory, index),
		x509.MarshalPKCS1PrivateKey(key.PrivateKey),
	)
}

// The public half of the same position, so that a publisher-side fixture can be
// restored on its own
func StoreRSAPublicKey(key RSA, directory string, index int) {

	writeKeyFile(
		publicKeyPath(directory, index),
		x509.MarshalPKCS1PublicKey(key.PublicKey),
	)
}

func privateKeyPath(directory string, index int) string {

	return filepath.Join(directory, fmt.Sprintf("%d.der", index))
}

func publicKeyPath(directory string, index int) string {

	return filepath.Join(directory, fmt.Sprintf("%d.pub.der", index))
}

// A key that was never stored is a fact about the filesystem the caller decides on,
// whereas a key that is there but unreadable is a broken experiment
func readKeyFile(keyPath string) ([]byte, bool) {

	keyBytes, err := os.ReadFile(keyPath)
	if err != nil {
		return nil, false
	}

	return keyBytes, true
}

func writeKeyFile(keyPath string, keyBytes []byte) {

	if err := os.MkdirAll(filepath.Dir(keyPath), 0o755); err != nil {
		panic(err)
	}

	if err := os.WriteFile(keyPath, keyBytes, 0o644); err != nil {
		panic(err)
	}
}
