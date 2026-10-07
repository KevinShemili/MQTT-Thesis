package tls_cpabe

import (
	"fmt"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/envelope"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
	"thesis/utility/golang/generator"

	"github.com/cloudflare/circl/abe/cpabe/tkn20"
)

type CPABEPublisherScenario struct {
	Authority cpabe.Authority
	Policy    tkn20.Policy
}

var _ macro.PublisherScenario = CPABEPublisherScenario{}

func (publisher CPABEPublisherScenario) Run(input macro.PublisherInput) (macro.PublisherSamples, error) {

	return macro.BenchmarkPublisher(input, publisher, cpu.NewCPUPerf)
}

func (publisher CPABEPublisherScenario) PublishMessage(input macro.PublisherInput, msg message.Message) (mqtt.PublishToken, error) {

	serializer := serialization.JSONSerializer{}

	plaintext, err := serializer.Serialize(msg)
	if err != nil {
		return nil, fmt.Errorf("serialize message %s: %w", msg.ID, err)
	}

	symmetricKey := generator.GenerateRandomBytes(input.Config.Cryptography.SymmetricKeySize)
	cipher := aes.NewAES(symmetricKey)
	nonce := generator.GenerateRandomBytes(cipher.NonceSize())
	asymmetricCiphertext := publisher.Authority.Encrypt(publisher.Policy, symmetricKey)
	symmetricCiphertext := cipher.Encrypt(nil, nonce, plaintext)

	payload, err := serializer.Serialize(envelope.AsymmetricEnvelope{
		AsymmetricCiphertext: asymmetricCiphertext,
		Nonce:                nonce,
		SymmetricCiphertext:  symmetricCiphertext,
	})
	if err != nil {
		return nil, fmt.Errorf("serialize envelope for message %s: %w", msg.ID, err)
	}

	return input.Client.Publish(input.Config.Benchmark.Topic, payload), nil
}
