package tls_psk

import (
	"fmt"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro"
	"thesis/internal/cryptography/aes"
	"thesis/internal/envelope"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
	"thesis/utility/golang/generator"
)

type PSKPublisherScenario struct {
	Cipher aes.AES
}

var _ macro.PublisherScenario = PSKPublisherScenario{}

func (publisher PSKPublisherScenario) Run(input macro.PublisherInput) (macro.PublisherSamples, error) {

	return macro.BenchmarkPublisher(input, publisher, cpu.NewCPUPerf)
}

func (publisher PSKPublisherScenario) PublishMessage(input macro.PublisherInput, msg message.Message) (mqtt.PublishToken, error) {

	serializer := serialization.JSONSerializer{}

	plaintext, err := serializer.Serialize(msg)
	if err != nil {
		return nil, fmt.Errorf("serialize message %s: %w", msg.ID, err)
	}

	nonce := generator.GenerateRandomBytes(publisher.Cipher.NonceSize())
	ciphertext := publisher.Cipher.Encrypt(nil, nonce, plaintext)

	payload, err := serializer.Serialize(envelope.SymmetricEnvelope{
		Nonce:      nonce,
		Ciphertext: ciphertext,
	})
	if err != nil {
		return nil, fmt.Errorf("serialize envelope for message %s: %w", msg.ID, err)
	}

	return input.Client.Publish(input.Config.Benchmark.Topic, payload), nil
}
