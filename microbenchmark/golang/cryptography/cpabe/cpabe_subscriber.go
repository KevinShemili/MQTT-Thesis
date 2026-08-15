package cpabe

import "github.com/cloudflare/circl/abe/cpabe/tkn20"

type CPABESubscriber struct {
	PrivateKey tkn20.AttributeKey
}

// Decrypts using subscriber's private key
func (subscriber CPABESubscriber) Decrypt(ciphertext []byte) []byte {

	plaintext, err := subscriber.PrivateKey.Decrypt(ciphertext)
	if err != nil {
		panic(err)
	}

	return plaintext
}

func (subscriber CPABESubscriber) StoredPrivateKeySize() int {

	return len(MarshalCPABEPrivateKey(subscriber.PrivateKey))
}

func MarshalCPABEPrivateKey(subscriberKey tkn20.AttributeKey) []byte {

	keyBytes, err := subscriberKey.MarshalBinary()
	if err != nil {
		panic(err)
	}

	return keyBytes
}

func UnmarshalCPABEPrivateKey(keyBytes []byte) CPABESubscriber {

	var privateKey tkn20.AttributeKey

	if err := privateKey.UnmarshalBinary(keyBytes); err != nil {
		panic(err)
	}

	return CPABESubscriber{PrivateKey: privateKey}
}
