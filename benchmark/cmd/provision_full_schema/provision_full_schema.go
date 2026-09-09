package main

import (
	"benchmark/cache"
	"benchmark/cryptography/ascon"
	"benchmark/cryptography/cpabe"
	"benchmark/cryptography/rsa"
	"benchmark/envelope"
	"benchmark/micro/full_schema/shared"
	"benchmark/utility"
)

// The point of this program is to provide the fixture data for the Full Schema
// memory benchmarks by populating the cache in an earlier process.
func main() {

	config := shared.LoadFullSchemaConfig()

	symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
	cache.StoreFile(
		cache.CreateASCONKeyFileName(config.SymmetricKeySize),
		symmetricKey,
	)
	symmetricCipher := ascon.NewASCON(symmetricKey)
	nonce := utility.GenerateRandomBytes(symmetricCipher.NonceSize())

	rsaScheme := rsa.NewRSA(config.RSAKeyBits)
	cache.StoreFile(
		cache.CreateRSAPrivateKeyFileName(config.RSAKeyBits, 0),
		rsa.MarshalPrivateKey(rsaScheme.PrivateKey),
	)
	cache.StoreFile(
		cache.CreateRSAPublicKeyFileName(config.RSAKeyBits, 0),
		rsa.MarshalPublicKey(rsaScheme.PublicKey),
	)
	rsaCiphertext := rsaScheme.Encrypt(symmetricKey)

	authority := cpabe.NewCPABEAuthority()
	cache.StoreFile(
		cache.CPABEPublicKeyFileName,
		cpabe.MarshalCPABEPublicKey(authority.PublicKey),
	)

	policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(config.AttributeCount)
	cache.StoreFile(
		cache.CreateCPABEPolicyFileName(config.AttributeCount),
		[]byte(policy.String()),
	)
	cache.StoreFile(
		cache.CreateCPABEPrivateKeyFileName(config.AttributeCount),
		cpabe.MarshalCPABEPrivateKey(authority.IssuePrivateKey(attributes).PrivateKey),
	)
	cpabeCiphertext := authority.Encrypt(policy, symmetricKey)

	for _, payloadSize := range config.PayloadSizes {

		plaintext := utility.GenerateRandomBytes(payloadSize)
		cache.StoreFile(
			cache.CreateFullSchemaPlaintextFileName(payloadSize),
			plaintext,
		)

		symmetricCiphertext := symmetricCipher.Seal(nil, nonce, plaintext, nil)

		cache.StoreFile(
			cache.CreateFullSchemaEnvelopeFileName("psk", payloadSize),
			envelope.SerializeCBOR(envelope.Envelope{
				Nonce:               nonce,
				SymmetricCiphertext: symmetricCiphertext,
			}),
		)
		cache.StoreFile(
			cache.CreateFullSchemaEnvelopeFileName("rsa", payloadSize),
			envelope.SerializeCBOR(envelope.Envelope{
				AsymmetricCiphertext: rsaCiphertext,
				Nonce:                nonce,
				SymmetricCiphertext:  symmetricCiphertext,
			}),
		)
		cache.StoreFile(
			cache.CreateFullSchemaEnvelopeFileName("cpabe", payloadSize),
			envelope.SerializeCBOR(envelope.Envelope{
				AsymmetricCiphertext: cpabeCiphertext,
				Nonce:                nonce,
				SymmetricCiphertext:  symmetricCiphertext,
			}),
		)
	}
}
