package rsa

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
)

type RSA struct {
	PrivateKey *rsa.PrivateKey
	PublicKey  *rsa.PublicKey
}

// ctor
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

	return len(MarshalPrivateKey(r.PrivateKey))
}

func MarshalPrivateKey(privateKey *rsa.PrivateKey) []byte {

	return x509.MarshalPKCS1PrivateKey(privateKey)
}

func UnmarshalPrivateKey(keyBytes []byte) RSA {

	privateKey, err := x509.ParsePKCS1PrivateKey(keyBytes)
	if err != nil {
		panic(err)
	}

	return RSA{PrivateKey: privateKey, PublicKey: &privateKey.PublicKey}
}

func MarshalPublicKey(publicKey *rsa.PublicKey) []byte {

	return x509.MarshalPKCS1PublicKey(publicKey)
}

func UnmarshalPublicKey(keyBytes []byte) RSA {

	publicKey, err := x509.ParsePKCS1PublicKey(keyBytes)
	if err != nil {
		panic(err)
	}

	return RSA{PublicKey: publicKey}
}
