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

	// 128 bit key
	key := utils.GenerateRandomBytes(16)

	// ASCON exposes itself directly as AEAD
	aeadCipher, err := ascon.New(key, ascon.Ascon128)
	if err != nil {
		panic(err)
	}

	return ASCON{AEAD: aeadCipher}
}
