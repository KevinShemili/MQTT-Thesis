package aes

import (
	"crypto/aes"
	"crypto/cipher"
)

type AES struct {
	cipher.AEAD
}

// ctor
func NewAES(key []byte) AES {

	// AES provides the block cipher
	block, err := aes.NewCipher(key)
	if err != nil {
		panic(err)
	}

	// GCM adds confidentiality & integrity
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		panic(err)
	}

	return AES{AEAD: gcm}
}
