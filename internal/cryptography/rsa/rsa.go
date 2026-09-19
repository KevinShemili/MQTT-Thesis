package rsa

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
)

type RSA struct {
	privateKey *rsa.PrivateKey
	publicKey  *rsa.PublicKey
}

// ctor
func NewRSA(keyBits int) RSA {

	privateKey, err := rsa.GenerateKey(rand.Reader, keyBits)
	if err != nil {
		panic(err)
	}

	return RSA{privateKey: privateKey, publicKey: &privateKey.PublicKey}
}

func (r RSA) Encrypt(plaintext []byte) []byte {

	ciphertext, err := rsa.EncryptOAEP(sha256.New(), rand.Reader, r.publicKey, plaintext, nil)
	if err != nil {
		panic(err)
	}

	return ciphertext
}

func (r RSA) Decrypt(ciphertext []byte) []byte {

	plaintext, err := rsa.DecryptOAEP(sha256.New(), rand.Reader, r.privateKey, ciphertext, nil)
	if err != nil {
		panic(err)
	}

	return plaintext
}

func (r RSA) PrivateKeyBytes() []byte {

	return x509.MarshalPKCS1PrivateKey(r.privateKey)
}

func RSAFromPrivateKeyBytes(keyBytes []byte) RSA {

	privateKey, err := x509.ParsePKCS1PrivateKey(keyBytes)
	if err != nil {
		panic(err)
	}

	return RSA{privateKey: privateKey, publicKey: &privateKey.PublicKey}
}

func (r RSA) PublicKeyBytes() []byte {

	return x509.MarshalPKCS1PublicKey(r.publicKey)
}

func RSAFromPublicKeyBytes(keyBytes []byte) RSA {

	publicKey, err := x509.ParsePKCS1PublicKey(keyBytes)
	if err != nil {
		panic(err)
	}

	return RSA{publicKey: publicKey}
}
