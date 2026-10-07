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
)

type CPABESubscriberScenario struct {
	PrivateKey cpabe.Subscriber
}

var _ macro.SubscriberScenario = CPABESubscriberScenario{}

func (subscriber CPABESubscriberScenario) Run(input macro.SubscriberInput) (macro.SubscriberSamples, error) {

	return macro.BenchmarkSubscriber(input, subscriber, cpu.NewCPUPerf)
}

func (subscriber CPABESubscriberScenario) ConsumeMessage(delivery mqtt.MQTTDelivery) (message.Message, error) {

	serializer := serialization.JSONSerializer{}

	var env envelope.AsymmetricEnvelope

	if err := serializer.Deserialize(delivery.Payload, &env); err != nil {
		return message.Message{}, fmt.Errorf("deserialize received envelope: %w", err)
	}

	symmetricKey := subscriber.PrivateKey.Decrypt(env.AsymmetricCiphertext)
	cipher := aes.NewAES(symmetricKey)

	plaintext := cipher.Decrypt(nil, env.Nonce, env.SymmetricCiphertext)

	var msg message.Message

	if err := serializer.Deserialize(plaintext, &msg); err != nil {
		return message.Message{}, fmt.Errorf("deserialize received message: %w", err)
	}

	return msg, nil
}
