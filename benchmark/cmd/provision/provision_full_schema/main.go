package main

import (
	"fmt"
	"thesis/benchmark/cache"
	"thesis/benchmark/cmd/provision/shared"
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

	dependencies := cmdshared.ProvisionDependencies{
		GenerateRandomBytes: utility.GenerateRandomBytes,
		Store:               cache.Store,
	}

	runProvision(config.PayloadSizes, config.SymmetricKeySize, config.RSAKeyBits, config.AttributeCount, dependencies)
}

func runProvision(payloadSizes []int, symmetricKeySize int, rsaKeyBits int,
	attributeCount int, dependencies cmdshared.ProvisionDependencies) {

	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	standardSymmetricKey := dependencies.GenerateRandomBytes(symmetricKeySize)
	dependencies.Store(shared.AESKeyFileName, standardSymmetricKey)
	standardCipher := aes.NewAES(standardSymmetricKey)
	standardNonce := dependencies.GenerateRandomBytes(standardCipher.NonceSize())

	lightweightSymmetricKey := dependencies.GenerateRandomBytes(symmetricKeySize)
	dependencies.Store(shared.ASCONKeyFileName, lightweightSymmetricKey)
	lightweightCipher := ascon.NewASCON(lightweightSymmetricKey)
	lightweightNonce := dependencies.GenerateRandomBytes(lightweightCipher.NonceSize())

	rsaScheme := rsa.NewRSA(rsaKeyBits)
	dependencies.Store(shared.RSAPrivateKeyFileName, rsaScheme.PrivateKeyBytes())
	dependencies.Store(shared.RSAPublicKeyFileName, rsaScheme.PublicKeyBytes())
	standardRSACiphertext := rsaScheme.Encrypt(standardSymmetricKey)
	lightweightRSACiphertext := rsaScheme.Encrypt(lightweightSymmetricKey)

	authority := cpabe.NewAuthority()

	dependencies.Store(shared.CPABEPublicKeyFileName, authority.PublicKeyBytes())

	policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

	dependencies.Store(shared.CPABEPolicyFileName, []byte(policy.String()))

	dependencies.Store(shared.CPABEPrivateKeyFileName, authority.IssuePrivateKey(attributes).Bytes())

	standardCPABECiphertext := authority.Encrypt(policy, standardSymmetricKey)

	lightweightCPABECiphertext := authority.Encrypt(policy, lightweightSymmetricKey)

	for _, payloadSize := range payloadSizes {

		plaintext := dependencies.GenerateRandomBytes(payloadSize)

		dependencies.Store(fmt.Sprintf(shared.PlaintextFileNameFormat, payloadSize), plaintext)

		standardSymmetricCiphertext := standardCipher.Encrypt(nil, standardNonce, plaintext)

		lightweightSymmetricCiphertext := lightweightCipher.Encrypt(nil, lightweightNonce, plaintext)

		pskStandardEnvelope, err := jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
			Nonce:               standardNonce,
			SymmetricCiphertext: standardSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.Store(fmt.Sprintf(shared.PSKStandardEnvelopeFileNameFormat, payloadSize), pskStandardEnvelope)

		pskLightweightEnvelope, err := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
			Nonce:               lightweightNonce,
			SymmetricCiphertext: lightweightSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.Store(fmt.Sprintf(shared.PSKLightweightEnvelopeFileNameFormat, payloadSize), pskLightweightEnvelope)

		rsaStandardEnvelope, err := jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
			AsymmetricCiphertext: standardRSACiphertext,
			Nonce:                standardNonce,
			SymmetricCiphertext:  standardSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.Store(fmt.Sprintf(shared.RSAStandardEnvelopeFileNameFormat, payloadSize), rsaStandardEnvelope)

		rsaLightweightEnvelope, err := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
			AsymmetricCiphertext: lightweightRSACiphertext,
			Nonce:                lightweightNonce,
			SymmetricCiphertext:  lightweightSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.Store(fmt.Sprintf(shared.RSALightweightEnvelopeFileNameFormat, payloadSize), rsaLightweightEnvelope)

		cpabeStandardEnvelope, err := jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
			AsymmetricCiphertext: standardCPABECiphertext,
			Nonce:                standardNonce,
			SymmetricCiphertext:  standardSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.Store(fmt.Sprintf(shared.CPABEStandardEnvelopeFileNameFormat, payloadSize), cpabeStandardEnvelope)

		cpabeLightweightEnvelope, err := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
			AsymmetricCiphertext: lightweightCPABECiphertext,
			Nonce:                lightweightNonce,
			SymmetricCiphertext:  lightweightSymmetricCiphertext,
		})
		if err != nil {
			panic(err)
		}

		dependencies.Store(fmt.Sprintf(shared.CPABELightweightEnvelopeFileNameFormat, payloadSize), cpabeLightweightEnvelope)
	}
}
