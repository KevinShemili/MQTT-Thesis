package cpabe

import "github.com/cloudflare/circl/abe/cpabe/tkn20"

type Subscriber struct {
	key tkn20.AttributeKey
}

// Decrypts using subscriber's private key
func (privateKey Subscriber) Decrypt(ciphertext []byte) []byte {

	plaintext, err := privateKey.key.Decrypt(ciphertext)
	if err != nil {
		panic(err)
	}

	return plaintext
}

func (privateKey Subscriber) Bytes() []byte {

	keyBytes, err := privateKey.key.MarshalBinary()
	if err != nil {
		panic(err)
	}

	return keyBytes
}

func PrivateKeyFromBytes(keyBytes []byte) Subscriber {

	var key tkn20.AttributeKey

	if err := key.UnmarshalBinary(keyBytes); err != nil {
		panic(err)
	}

	return Subscriber{key: key}
}
