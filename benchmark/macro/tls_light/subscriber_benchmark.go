package tls_light

import (
	"fmt"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
)

type TLSLightSubscriberScenario struct{}

var _ macro.SubscriberScenario = TLSLightSubscriberScenario{}

func (scenario TLSLightSubscriberScenario) Run(input macro.SubscriberInput) (macro.SubscriberSamples, error) {

	return macro.BenchmarkSubscriber(input, scenario, cpu.NewCPUPerf)
}

func (TLSLightSubscriberScenario) ConsumeMessage(delivery mqtt.MQTTDelivery) (message.Message, error) {

	serializer := serialization.CBORSerializer{}

	var msg message.Message

	if err := serializer.Deserialize(delivery.Payload, &msg); err != nil {
		return message.Message{}, fmt.Errorf("deserialize received message: %w", err)
	}

	return msg, nil
}
