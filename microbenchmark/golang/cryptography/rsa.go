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

// Reads every stored key in the given directory
func LoadRSAKeys(directory string) []RSA {

	entries, err := os.ReadDir(directory)
	if err != nil {
		return nil
	}

	keys := []RSA{}

	for _, entry := range entries {

		keyBytes, err := os.ReadFile(filepath.Join(directory, entry.Name()))
		if err != nil {
			panic(err)
		}

		privateKey, err := x509.ParsePKCS1PrivateKey(keyBytes)
		if err != nil {
			panic(err)
		}

		keys = append(keys, RSA{PrivateKey: privateKey, PublicKey: &privateKey.PublicKey})
	}

	return keys
}

// Appends one key to the directory, named by its position
func StoreRSAKey(key RSA, directory string, index int) {

	if err := os.MkdirAll(directory, 0o755); err != nil {
		panic(err)
	}

	keyPath := filepath.Join(directory, fmt.Sprintf("%d.der", index))

	if err := os.WriteFile(keyPath, x509.MarshalPKCS1PrivateKey(key.PrivateKey), 0o644); err != nil {
		panic(err)
	}
}
