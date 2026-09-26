package aes

import (
	"crypto/aes"
	"crypto/cipher"
)

type AES struct {
	aead cipher.AEAD
}

func NewAES(key []byte) AES {

	block, err := aes.NewCipher(key)
	if err != nil {
		panic(err)
	}

	aeadCipher, err := cipher.NewGCM(block)
	if err != nil {
		panic(err)
	}

	return AES{aead: aeadCipher}
}

func (aes AES) Encrypt(destination, nonce, plaintext []byte) []byte {
	return aes.aead.Seal(destination, nonce, plaintext, nil)
}

func (aes AES) Decrypt(destination, nonce, ciphertext []byte) []byte {

	plaintext, err := aes.aead.Open(destination, nonce, ciphertext, nil)
	if err != nil {
		panic(err)
	}

	return plaintext
}

func (aesCipher AES) NonceSize() int {
	return aesCipher.aead.NonceSize()
}

func (aesCipher AES) Overhead() int {
	return aesCipher.aead.Overhead()
}
