package tls_light

import (
	"fmt"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
)

type TLSLightPublisherScenario struct{}

var _ macro.PublisherScenario = TLSLightPublisherScenario{}

func (scenario TLSLightPublisherScenario) Run(input macro.PublisherInput) (macro.PublisherSamples, error) {

	return macro.BenchmarkPublisher(input, scenario, cpu.NewCPUPerf)
}

func (TLSLightPublisherScenario) PublishMessage(input macro.PublisherInput, msg message.Message) (mqtt.PublishToken, error) {

	serializer := serialization.CBORSerializer{}

	payload, err := serializer.Serialize(msg)
	if err != nil {
		return nil, fmt.Errorf("serialize message %s: %w", msg.ID, err)
	}

	return input.Client.Publish(input.Config.Benchmark.Topic, payload), nil
}
