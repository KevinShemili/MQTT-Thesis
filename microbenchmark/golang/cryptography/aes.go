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

	// 128 bit key
	key := utils.GenerateRandomBytes(16)

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
