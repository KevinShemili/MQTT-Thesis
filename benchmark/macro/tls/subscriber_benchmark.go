package tls

import (
	"fmt"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
)

type TLSSubscriberScenario struct{}

var _ macro.SubscriberScenario = TLSSubscriberScenario{}

func (scenario TLSSubscriberScenario) Run(input macro.SubscriberInput) (macro.SubscriberSamples, error) {

	return macro.BenchmarkSubscriber(input, scenario, cpu.NewCPUPerf)
}

func (TLSSubscriberScenario) ConsumeMessage(delivery mqtt.MQTTDelivery) (message.Message, error) {

	serializer := serialization.JSONSerializer{}

	var msg message.Message

	if err := serializer.Deserialize(delivery.Payload, &msg); err != nil {
		return message.Message{}, fmt.Errorf("deserialize received message: %w", err)
	}

	return msg, nil
}
