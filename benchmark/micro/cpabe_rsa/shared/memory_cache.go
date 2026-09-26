package shared

import "thesis/internal/cryptography/rsa"

// Helps if -test.count >>> 1
var rsaKeyInMemoryCache = map[int][]rsa.RSA{}

// Generate RSA keys & retain them for the lifetime of this process
func LoadRSAKeysFromInMemoryCache(rsaKeyBits, amount int) []rsa.RSA {

	keySlice := rsaKeyInMemoryCache[rsaKeyBits]

	// If not enough keys are cached, generate & store
	for len(keySlice) < amount {
		keySlice = append(keySlice, rsa.NewRSA(rsaKeyBits))
	}

	// Update in-memory cache
	rsaKeyInMemoryCache[rsaKeyBits] = keySlice

	// Return desired amount
	return keySlice[:amount]
}
