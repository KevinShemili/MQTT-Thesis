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

type provisionDependencies struct {
	generateRandomBytes func(int) []byte
	store               func(string, []byte)
}

// The point of this program is to provide the fixture data for the Full Schema
// memory benchmarks by populating the cache in an earlier process.
func main() {

	config := shared.LoadFullSchemaConfig()

	dependencies := provisionDependencies{
		generateRandomBytes: utility.GenerateRandomBytes,
		store:               cache.Store,
	}

	runProvision(config.PayloadSizes, config.SymmetricKeySize, config.RSAKeyBits, config.AttributeCount, dependencies)
}

func runProvision(payloadSizes []int, symmetricKeySize int, rsaKeyBits int,
	attributeCount int, dependencies provisionDependencies) {

	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	standardSymmetricKey := dependencies.generateRandomBytes(symmetricKeySize)
	dependencies.store(cache.AESKeyFileName, standardSymmetricKey)
	standardCipher := aes.NewAES(standardSymmetricKey)
	standardNonce := dependencies.generateRandomBytes(standardCipher.NonceSize())

	lightweightSymmetricKey := dependencies.generateRandomBytes(symmetricKeySize)
	dependencies.store(cache.ASCONKeyFileName, lightweightSymmetricKey)
	lightweightCipher := ascon.NewASCON(lightweightSymmetricKey)
	lightweightNonce := dependencies.generateRandomBytes(lightweightCipher.NonceSize())

	rsaScheme := rsa.NewRSA(rsaKeyBits)
	dependencies.store(cache.RSAPrivateKeyFileName, rsaScheme.PrivateKeyBytes())
	dependencies.store(cache.RSAPublicKeyFileName, rsaScheme.PublicKeyBytes())
	standardRSACiphertext := rsaScheme.Encrypt(standardSymmetricKey)
	lightweightRSACiphertext := rsaScheme.Encrypt(lightweightSymmetricKey)

	authority := cpabe.NewAuthority()

	dependencies.store(cache.CPABEPublicKeyFileName, authority.PublicKeyBytes())

	policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

	dependencies.store(cache.CPABEPolicyFileName, []byte(policy.String()))

	dependencies.store(cache.CPABEPrivateKeyFileName, authority.IssuePrivateKey(attributes).Bytes())

	standardCPABECiphertext := authority.Encrypt(policy, standardSymmetricKey)

	lightweightCPABECiphertext := authority.Encrypt(policy, lightweightSymmetricKey)

	for _, payloadSize := range payloadSizes {

		plaintext := dependencies.generateRandomBytes(payloadSize)

		dependencies.store(cache.CreateFullSchemaPlaintextFileName(payloadSize), plaintext)

		standardSymmetricCiphertext := standardCipher.Encrypt(nil, standardNonce, plaintext)

		lightweightSymmetricCiphertext := lightweightCipher.Encrypt(nil, lightweightNonce, plaintext)

		pskStandardEnvelope, err := jsonSerializer.Serialize(envelope.Envelope{
			Nonce:               standardNonce,
			SymmetricCiphertext: standardSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.store(cache.CreateFullSchemaEnvelopeFileName("psk", "standard", payloadSize), pskStandardEnvelope)

		pskLightweightEnvelope, err := cborSerializer.Serialize(envelope.Envelope{
			Nonce:               lightweightNonce,
			SymmetricCiphertext: lightweightSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.store(cache.CreateFullSchemaEnvelopeFileName("psk", "lightweight", payloadSize), pskLightweightEnvelope)

		rsaStandardEnvelope, err := jsonSerializer.Serialize(envelope.Envelope{
			AsymmetricCiphertext: standardRSACiphertext,
			Nonce:                standardNonce,
			SymmetricCiphertext:  standardSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.store(cache.CreateFullSchemaEnvelopeFileName("rsa", "standard", payloadSize), rsaStandardEnvelope)

		rsaLightweightEnvelope, err := cborSerializer.Serialize(envelope.Envelope{
			AsymmetricCiphertext: lightweightRSACiphertext,
			Nonce:                lightweightNonce,
			SymmetricCiphertext:  lightweightSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.store(cache.CreateFullSchemaEnvelopeFileName("rsa", "lightweight", payloadSize), rsaLightweightEnvelope)

		cpabeStandardEnvelope, err := jsonSerializer.Serialize(envelope.Envelope{
			AsymmetricCiphertext: standardCPABECiphertext,
			Nonce:                standardNonce,
			SymmetricCiphertext:  standardSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.store(cache.CreateFullSchemaEnvelopeFileName("cpabe", "standard", payloadSize), cpabeStandardEnvelope)

		cpabeLightweightEnvelope, err := cborSerializer.Serialize(envelope.Envelope{
			AsymmetricCiphertext: lightweightCPABECiphertext,
			Nonce:                lightweightNonce,
			SymmetricCiphertext:  lightweightSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.store(cache.CreateFullSchemaEnvelopeFileName("cpabe", "lightweight", payloadSize), cpabeLightweightEnvelope)
	}
}
