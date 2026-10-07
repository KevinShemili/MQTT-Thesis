package tls_rsa_light

import (
	"fmt"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro"
	"thesis/internal/cryptography/ascon"
	"thesis/internal/cryptography/rsa"
	"thesis/internal/envelope"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
)

type RSALightSubscriberScenario struct {
	RSAScheme rsa.RSA
}

var _ macro.SubscriberScenario = RSALightSubscriberScenario{}

func (subscriber RSALightSubscriberScenario) Run(input macro.SubscriberInput) (macro.SubscriberSamples, error) {

	return macro.BenchmarkSubscriber(input, subscriber, cpu.NewCPUPerf)
}

func (subscriber RSALightSubscriberScenario) ConsumeMessage(delivery mqtt.MQTTDelivery) (message.Message, error) {

	serializer := serialization.CBORSerializer{}

	var env envelope.AsymmetricEnvelope

	if err := serializer.Deserialize(delivery.Payload, &env); err != nil {
		return message.Message{}, fmt.Errorf("deserialize received envelope: %w", err)
	}

	symmetricKey := subscriber.RSAScheme.Decrypt(env.AsymmetricCiphertext)
	cipher := ascon.NewASCON(symmetricKey)

	plaintext := cipher.Decrypt(nil, env.Nonce, env.SymmetricCiphertext)

	var msg message.Message

	if err := serializer.Deserialize(plaintext, &msg); err != nil {
		return message.Message{}, fmt.Errorf("deserialize received message: %w", err)
	}

	return msg, nil
}
