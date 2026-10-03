package main

import (
	"fmt"
	"thesis/benchmark/cmd/provision"
	"thesis/benchmark/micro/full_schema"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
	"thesis/internal/envelope"
	"thesis/internal/serialization"
	"thesis/utility/golang/cache"
	"thesis/utility/golang/generator"
)

// The point of this program is to provide the fixture data for the Full Schema
// memory benchmarks by populating the cache in an earlier process.
func main() {

	config := full_schema.NewFullSchemaConfig()

	dependencies := provision.Dependency{
		GenerateRandomBytes: generator.GenerateRandomBytes,
		Store:               cache.Store,
	}

	runProvision(config.PayloadSizes, config.SymmetricKeySize, config.RSAKeyBits, config.AttributeCount, dependencies)
}

func runProvision(payloadSizes []int, symmetricKeySize int, rsaKeyBits int,
	attributeCount int, dependencies provision.Dependency) {

	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	standardSymmetricKey := dependencies.GenerateRandomBytes(symmetricKeySize)
	dependencies.Store(cache.AESKeyFileName, standardSymmetricKey)
	standardCipher := aes.NewAES(standardSymmetricKey)
	standardNonce := dependencies.GenerateRandomBytes(standardCipher.NonceSize())

	lightweightSymmetricKey := dependencies.GenerateRandomBytes(symmetricKeySize)
	dependencies.Store(cache.ASCONKeyFileName, lightweightSymmetricKey)
	lightweightCipher := ascon.NewASCON(lightweightSymmetricKey)
	lightweightNonce := dependencies.GenerateRandomBytes(lightweightCipher.NonceSize())

	rsaScheme := rsa.NewRSA(rsaKeyBits)
	dependencies.Store(cache.RSAPrivateKeyFileName, rsaScheme.PrivateKeyBytes())
	dependencies.Store(cache.RSAPublicKeyFileName, rsaScheme.PublicKeyBytes())
	standardRSACiphertext := rsaScheme.Encrypt(standardSymmetricKey)
	lightweightRSACiphertext := rsaScheme.Encrypt(lightweightSymmetricKey)

	authority := cpabe.NewAuthority()

	dependencies.Store(cache.CPABEPublicKeyFileName, authority.PublicKeyBytes())

	policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

	dependencies.Store(cache.CPABEPolicyFileName, []byte(policy.String()))

	dependencies.Store(cache.CPABEPrivateKeyFileName, authority.IssuePrivateKey(attributes).Bytes())

	standardCPABECiphertext := authority.Encrypt(policy, standardSymmetricKey)

	lightweightCPABECiphertext := authority.Encrypt(policy, lightweightSymmetricKey)

	for _, payloadSize := range payloadSizes {

		plaintext := dependencies.GenerateRandomBytes(payloadSize)

		dependencies.Store(fmt.Sprintf(cache.PlaintextFileWSizeName, payloadSize), plaintext)

		standardSymmetricCiphertext := standardCipher.Encrypt(nil, standardNonce, plaintext)

		lightweightSymmetricCiphertext := lightweightCipher.Encrypt(nil, lightweightNonce, plaintext)

		pskStandardEnvelope, err := jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
			Nonce:               standardNonce,
			SymmetricCiphertext: standardSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.Store(fmt.Sprintf(cache.PSKStandardEnvelopeWSizeFileName, payloadSize), pskStandardEnvelope)

		pskLightweightEnvelope, err := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
			Nonce:               lightweightNonce,
			SymmetricCiphertext: lightweightSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.Store(fmt.Sprintf(cache.PSKLightEnvelopeWSizeFileName, payloadSize), pskLightweightEnvelope)

		rsaStandardEnvelope, err := jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
			AsymmetricCiphertext: standardRSACiphertext,
			Nonce:                standardNonce,
			SymmetricCiphertext:  standardSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.Store(fmt.Sprintf(cache.RSAStandardEnvelopeWSizeFileName, payloadSize), rsaStandardEnvelope)

		rsaLightweightEnvelope, err := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
			AsymmetricCiphertext: lightweightRSACiphertext,
			Nonce:                lightweightNonce,
			SymmetricCiphertext:  lightweightSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.Store(fmt.Sprintf(cache.RSALightEnvelopeWSizeFileName, payloadSize), rsaLightweightEnvelope)

		cpabeStandardEnvelope, err := jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
			AsymmetricCiphertext: standardCPABECiphertext,
			Nonce:                standardNonce,
			SymmetricCiphertext:  standardSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.Store(fmt.Sprintf(cache.CPABEStandardEnvelopeWSizeFileName, payloadSize), cpabeStandardEnvelope)

		cpabeLightweightEnvelope, err := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
			AsymmetricCiphertext: lightweightCPABECiphertext,
			Nonce:                lightweightNonce,
			SymmetricCiphertext:  lightweightSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.Store(fmt.Sprintf(cache.CPABELightEnvelopeWSizeFileName, payloadSize), cpabeLightweightEnvelope)
	}
}
