package tls_cpabe_light

import (
	"fmt"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro"
	"thesis/internal/cryptography/ascon"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/envelope"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
)

type CPABELightSubscriberScenario struct {
	PrivateKey cpabe.Subscriber
}

var _ macro.SubscriberScenario = CPABELightSubscriberScenario{}

func (subscriber CPABELightSubscriberScenario) Run(input macro.SubscriberInput) (macro.SubscriberSamples, error) {

	return macro.BenchmarkSubscriber(input, subscriber, cpu.NewCPUPerf)
}

func (subscriber CPABELightSubscriberScenario) ConsumeMessage(delivery mqtt.MQTTDelivery) (message.Message, error) {

	serializer := serialization.CBORSerializer{}

	var env envelope.AsymmetricEnvelope

	if err := serializer.Deserialize(delivery.Payload, &env); err != nil {
		return message.Message{}, fmt.Errorf("deserialize received envelope: %w", err)
	}

	symmetricKey := subscriber.PrivateKey.Decrypt(env.AsymmetricCiphertext)
	cipher := ascon.NewASCON(symmetricKey)

	plaintext := cipher.Decrypt(nil, env.Nonce, env.SymmetricCiphertext)

	var msg message.Message

	if err := serializer.Deserialize(plaintext, &msg); err != nil {
		return message.Message{}, fmt.Errorf("deserialize received message: %w", err)
	}

	return msg, nil
}
