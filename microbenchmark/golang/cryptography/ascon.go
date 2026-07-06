package cryptography

import (
	"crypto/cipher"

	"github.com/cloudflare/circl/cipher/ascon"
)

type ASCON struct {
	cipher.AEAD
}

func NewASCON(key []byte) ASCON {

	// ASCON exposes itself directly as AEAD
	aeadCipher, err := ascon.New(key, ascon.Ascon128)
	if err != nil {
		panic(err)
	}

	return ASCON{AEAD: aeadCipher}
}
