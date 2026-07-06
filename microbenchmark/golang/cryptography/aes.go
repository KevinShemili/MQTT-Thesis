package cryptography

import (
	"crypto/aes"
	"crypto/cipher"
)

type AESGCM struct {
	cipher.AEAD
}

func NewAESGCM(key []byte) AESGCM {

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

	return AESGCM{AEAD: gcm}
}
