package cryptography

import (
	"crypto/cipher"
	"project/utils"

	"github.com/cloudflare/circl/cipher/ascon"
)

type ASCON struct {
	cipher.AEAD
}

func NewASCON() ASCON {

	keySize := utils.ParseIntFromEnv("AES_ASCON_KEY_SIZE")

	// 128 bit key
	key := utils.GenerateRandomBytes(keySize)

	// ASCON exposes itself directly as AEAD
	aeadCipher, err := ascon.New(key, ascon.Ascon128)
	if err != nil {
		panic(err)
	}

	return ASCON{AEAD: aeadCipher}
}
