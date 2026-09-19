package main

import (
	"thesis/benchmark/cache"
	"thesis/benchmark/micro/full_schema/shared"
	"thesis/benchmark/utility"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
	"thesis/internal/envelope"
	"thesis/internal/serialization"
)

// The point of this program is to provide the fixture data for the Full Schema
// memory benchmarks by populating the cache in an earlier process.
func main() {

	config := shared.LoadFullSchemaConfig()
	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	standardSymmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
	cache.Store(
		cache.AESKeyFileName,
		standardSymmetricKey,
	)
	standardCipher := aes.NewAES(standardSymmetricKey)
	standardNonce := utility.GenerateRandomBytes(standardCipher.NonceSize())

	lightweightSymmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
	cache.Store(
		cache.ASCONKeyFileName,
		lightweightSymmetricKey,
	)
	lightweightCipher := ascon.NewASCON(lightweightSymmetricKey)
	lightweightNonce := utility.GenerateRandomBytes(lightweightCipher.NonceSize())

	rsaScheme := rsa.NewRSA(config.RSAKeyBits)
	cache.Store(
		cache.RSAPrivateKeyFileName,
		rsaScheme.PrivateKeyBytes(),
	)
	cache.Store(
		cache.RSAPublicKeyFileName,
		rsaScheme.PublicKeyBytes(),
	)
	standardRSACiphertext := rsaScheme.Encrypt(standardSymmetricKey)
	lightweightRSACiphertext := rsaScheme.Encrypt(lightweightSymmetricKey)

	authority := cpabe.NewAuthority()
	cache.Store(
		cache.CPABEPublicKeyFileName,
		authority.PublicKeyBytes(),
	)

	policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(config.AttributeCount)
	cache.Store(
		cache.CPABEPolicyFileName,
		[]byte(policy.String()),
	)
	cache.Store(
		cache.CPABEPrivateKeyFileName,
		authority.IssuePrivateKey(attributes).Bytes(),
	)
	standardCPABECiphertext := authority.Encrypt(policy, standardSymmetricKey)
	lightweightCPABECiphertext := authority.Encrypt(policy, lightweightSymmetricKey)

	for _, payloadSize := range config.PayloadSizes {

		plaintext := utility.GenerateRandomBytes(payloadSize)
		cache.Store(
			cache.CreateFullSchemaPlaintextFileName(payloadSize),
			plaintext,
		)

		standardSymmetricCiphertext := standardCipher.Encrypt(
			nil,
			standardNonce,
			plaintext,
		)
		lightweightSymmetricCiphertext := lightweightCipher.Encrypt(
			nil,
			lightweightNonce,
			plaintext,
		)

		pskStandardEnvelope, err := jsonSerializer.Serialize(envelope.Envelope{
			Nonce:               standardNonce,
			SymmetricCiphertext: standardSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}
		cache.Store(
			cache.CreateFullSchemaEnvelopeFileName("psk", "standard", payloadSize),
			pskStandardEnvelope,
		)

		pskLightweightEnvelope, err := cborSerializer.Serialize(envelope.Envelope{
			Nonce:               lightweightNonce,
			SymmetricCiphertext: lightweightSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}
		cache.Store(
			cache.CreateFullSchemaEnvelopeFileName("psk", "lightweight", payloadSize),
			pskLightweightEnvelope,
		)

		rsaStandardEnvelope, err := jsonSerializer.Serialize(envelope.Envelope{
			AsymmetricCiphertext: standardRSACiphertext,
			Nonce:                standardNonce,
			SymmetricCiphertext:  standardSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}
		cache.Store(
			cache.CreateFullSchemaEnvelopeFileName("rsa", "standard", payloadSize),
			rsaStandardEnvelope,
		)

		rsaLightweightEnvelope, err := cborSerializer.Serialize(envelope.Envelope{
			AsymmetricCiphertext: lightweightRSACiphertext,
			Nonce:                lightweightNonce,
			SymmetricCiphertext:  lightweightSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}
		cache.Store(
			cache.CreateFullSchemaEnvelopeFileName("rsa", "lightweight", payloadSize),
			rsaLightweightEnvelope,
		)

		cpabeStandardEnvelope, err := jsonSerializer.Serialize(envelope.Envelope{
			AsymmetricCiphertext: standardCPABECiphertext,
			Nonce:                standardNonce,
			SymmetricCiphertext:  standardSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}
		cache.Store(
			cache.CreateFullSchemaEnvelopeFileName("cpabe", "standard", payloadSize),
			cpabeStandardEnvelope,
		)

		cpabeLightweightEnvelope, err := cborSerializer.Serialize(envelope.Envelope{
			AsymmetricCiphertext: lightweightCPABECiphertext,
			Nonce:                lightweightNonce,
			SymmetricCiphertext:  lightweightSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}
		cache.Store(
			cache.CreateFullSchemaEnvelopeFileName("cpabe", "lightweight", payloadSize),
			cpabeLightweightEnvelope,
		)
	}
}
