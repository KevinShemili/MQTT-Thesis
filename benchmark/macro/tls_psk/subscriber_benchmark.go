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
)

type PSKSubscriberScenario struct {
	Cipher aes.AES
}

var _ macro.SubscriberScenario = PSKSubscriberScenario{}

func (subscriber PSKSubscriberScenario) Run(input macro.SubscriberInput) (macro.SubscriberSamples, error) {

	return macro.BenchmarkSubscriber(input, subscriber, cpu.NewCPUPerf)
}

func (subscriber PSKSubscriberScenario) ConsumeMessage(delivery mqtt.MQTTDelivery) (message.Message, error) {

	serializer := serialization.JSONSerializer{}

	var env envelope.SymmetricEnvelope

	if err := serializer.Deserialize(delivery.Payload, &env); err != nil {
		return message.Message{}, fmt.Errorf("deserialize received envelope: %w", err)
	}

	plaintext := subscriber.Cipher.Decrypt(nil, env.Nonce, env.Ciphertext)

	var msg message.Message

	if err := serializer.Deserialize(plaintext, &msg); err != nil {
		return message.Message{}, fmt.Errorf("deserialize received message: %w", err)
	}

	return msg, nil
}
