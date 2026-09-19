package ascon

import (
	"crypto/cipher"

	"repani.com/ascon"
)

type ASCON struct {
	aead cipher.AEAD
}

func NewASCON(key []byte) ASCON {

	aeadCipher, err := ascon.NewAEAD(key)
	if err != nil {
		panic(err)
	}

	return ASCON{aead: aeadCipher}
}

func (ascon ASCON) Encrypt(destination []byte, nonce []byte, plaintext []byte) []byte {
	return ascon.aead.Seal(destination, nonce, plaintext, nil)
}

func (ascon ASCON) Decrypt(destination []byte, nonce []byte, ciphertext []byte) []byte {

	plaintext, err := ascon.aead.Open(destination, nonce, ciphertext, nil)
	if err != nil {
		panic(err)
	}

	return plaintext
}

func (ascon ASCON) NonceSize() int {
	return ascon.aead.NonceSize()
}

func (ascon ASCON) Overhead() int {
	return ascon.aead.Overhead()
}
