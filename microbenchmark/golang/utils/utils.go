package utils

import "crypto/rand"

// Produce random bytes for keys, nonces, etc.
func GenerateRandomBytes(count int) []byte {

	buffer := make([]byte, count)

	if _, err := rand.Read(buffer); err != nil {
		panic(err)
	}

	return buffer
}
