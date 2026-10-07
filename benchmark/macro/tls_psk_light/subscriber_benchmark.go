package tls_psk_light

import (
	"fmt"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro"
	"thesis/internal/cryptography/ascon"
	"thesis/internal/envelope"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
)

type PSKLightSubscriberScenario struct {
	Cipher ascon.ASCON
}

var _ macro.SubscriberScenario = PSKLightSubscriberScenario{}

func (subscriber PSKLightSubscriberScenario) Run(input macro.SubscriberInput) (macro.SubscriberSamples, error) {

	return macro.BenchmarkSubscriber(input, subscriber, cpu.NewCPUPerf)
}

func (subscriber PSKLightSubscriberScenario) ConsumeMessage(delivery mqtt.MQTTDelivery) (message.Message, error) {

	serializer := serialization.CBORSerializer{}

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
