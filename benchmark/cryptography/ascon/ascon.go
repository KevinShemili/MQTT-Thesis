package ascon

import (
	"crypto/cipher"

	"repani.com/ascon"
)

type ASCON struct {
	cipher.AEAD
}

// ctor
func NewASCON(key []byte) ASCON {

	// ASCON exposes itself directly as AEAD

	aeadCipher, err := ascon.NewAEAD(key)
	if err != nil {
		panic(err)
	}

	return ASCON{AEAD: aeadCipher}
}
