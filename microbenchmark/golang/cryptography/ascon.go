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
	// 128 bits
	key := utils.GenerateRandomBytes(16)

	aeadCipher, err := ascon.New(key, ascon.Ascon128)
	if err != nil {
		panic(err)
	}

	return ASCON{AEAD: aeadCipher}
}
