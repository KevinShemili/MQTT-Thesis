package cryptography

import (
	"crypto/aes"
	"crypto/cipher"
	"project/utils"
)

type AESGCM struct {
	cipher.AEAD
}

func NewAESGCM() AESGCM {
	// 128 bits
	key := utils.GenerateRandomBytes(16)

	block, err := aes.NewCipher(key)
	if err != nil {
		panic(err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		panic(err)
	}

	return AESGCM{AEAD: gcm}
}
