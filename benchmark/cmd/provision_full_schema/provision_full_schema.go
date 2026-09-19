package main

import (
	"thesis/benchmark/cache"
	"thesis/benchmark/cryptography/aes"
	"thesis/benchmark/cryptography/ascon"
	"thesis/benchmark/cryptography/cpabe"
	"thesis/benchmark/cryptography/rsa"
	"thesis/benchmark/micro/full_schema/shared"
	"thesis/benchmark/utility"
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
	cache.StoreFile(
		cache.CreateAESKeyFileName(config.SymmetricKeySize),
		standardSymmetricKey,
	)
	standardCipher := aes.NewAES(standardSymmetricKey)
	standardNonce := utility.GenerateRandomBytes(standardCipher.NonceSize())

	lightweightSymmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
	cache.StoreFile(
		cache.CreateASCONKeyFileName(config.SymmetricKeySize),
		lightweightSymmetricKey,
	)
	lightweightCipher := ascon.NewASCON(lightweightSymmetricKey)
	lightweightNonce := utility.GenerateRandomBytes(lightweightCipher.NonceSize())

	rsaScheme := rsa.NewRSA(config.RSAKeyBits)
	cache.StoreFile(
		cache.CreateRSAPrivateKeyFileName(config.RSAKeyBits, 0),
		rsa.MarshalPrivateKey(rsaScheme.PrivateKey),
	)
	cache.StoreFile(
		cache.CreateRSAPublicKeyFileName(config.RSAKeyBits, 0),
		rsa.MarshalPublicKey(rsaScheme.PublicKey),
	)
	standardRSACiphertext := rsaScheme.Encrypt(standardSymmetricKey)
	lightweightRSACiphertext := rsaScheme.Encrypt(lightweightSymmetricKey)

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
	standardCPABECiphertext := authority.Encrypt(policy, standardSymmetricKey)
	lightweightCPABECiphertext := authority.Encrypt(policy, lightweightSymmetricKey)

	for _, payloadSize := range config.PayloadSizes {

		plaintext := utility.GenerateRandomBytes(payloadSize)
		cache.StoreFile(
			cache.CreateFullSchemaPlaintextFileName(payloadSize),
			plaintext,
		)

		standardSymmetricCiphertext := standardCipher.Seal(
			nil,
			standardNonce,
			plaintext,
			nil,
		)
		lightweightSymmetricCiphertext := lightweightCipher.Seal(
			nil,
			lightweightNonce,
			plaintext,
			nil,
		)

		pskStandardEnvelope, err := jsonSerializer.Serialize(envelope.Envelope{
			Nonce:               standardNonce,
			SymmetricCiphertext: standardSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}
		cache.StoreFile(
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
		cache.StoreFile(
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
		cache.StoreFile(
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
		cache.StoreFile(
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
		cache.StoreFile(
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
		cache.StoreFile(
			cache.CreateFullSchemaEnvelopeFileName("cpabe", "lightweight", payloadSize),
			cpabeLightweightEnvelope,
		)
	}
}
