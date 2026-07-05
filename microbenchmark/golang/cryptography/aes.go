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

	keySize := utils.ParseIntFromEnv("AES_ASCON_KEY_SIZE")

	key := utils.GenerateRandomBytes(keySize)

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
