package tls_cbor

import (
	"fmt"
	"time"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro/shared"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
)

type TLSCBORSubscriberInput struct {
	Client       mqtt.Client
	Config       shared.MacroConfig
	Measurements []shared.SubscriberMeasurement
	IsWarmup     bool
}

func RunSubscribeBenchmark(input TLSCBORSubscriberInput, notifyReady func() error) (shared.SubscriberResult, error) {

	return runSubscribeBenchmark(input, notifyReady, cpu.NewCPUPerf)
}

func runSubscribeBenchmark(input TLSCBORSubscriberInput, notifyReady func() error,
	newCPU func() (cpu.CPU, error)) (shared.SubscriberResult, error) {

	if input.IsWarmup {

		err := consumeMessages(input, notifyReady)
		if err != nil {
			return shared.SubscriberResult{}, err
		}

		return shared.SubscriberResult{}, nil
	}

	measurement, err := newCPU()
	if err != nil {
		return shared.SubscriberResult{}, err
	}

	workloadErr := consumeMessages(input, func() error {
		if err := measurement.Enable(); err != nil {
			return err
		}
		return notifyReady()
	})
	if workloadErr != nil {
		measurement.Abort()
		return shared.SubscriberResult{}, workloadErr
	}

	cycles, err := measurement.Stop()
	if err != nil {
		return shared.SubscriberResult{}, err
	}

	return shared.SubscriberResult{
		Measurements: input.Measurements,
		Cycles:       cycles,
	}, nil
}

func consumeMessages(input TLSCBORSubscriberInput, notifyReady func() error) error {

	serializer := serialization.CBORSerializer{}

	messageIndex := 0
	benchmarkResult := make(chan error, 1)

	err := input.Client.Subscribe(input.Config.Benchmark.Topic, func(delivery mqtt.MQTTDelivery) {

		if input.IsWarmup {

			_, err := consumeMessage(input, serializer, delivery)
			if err != nil {
				benchmarkResult <- err
				return
			}

			messageIndex++
			if messageIndex == input.Config.Benchmark.MessageCount {
				benchmarkResult <- nil
			}
			return
		}

		msg, err := consumeMessage(input, serializer, delivery)
		if err != nil {
			benchmarkResult <- err
			return
		}

		endTime := time.Now().UnixNano()

		input.Measurements[messageIndex] = shared.SubscriberMeasurement{
			MessageID: msg.ID,
			EndTime:   endTime,
		}

		messageIndex++
		if messageIndex == input.Config.Benchmark.MessageCount {
			benchmarkResult <- nil
		}
	})
	if err != nil {
		return err
	}

	if err := notifyReady(); err != nil {
		return fmt.Errorf("notify subscriber ready: %w", err)
	}

	if err := <-benchmarkResult; err != nil {
		return err
	}

	return nil
}

func consumeMessage(input TLSCBORSubscriberInput, serializer serialization.CBORSerializer, delivery mqtt.MQTTDelivery) (message.Message, error) {

	var msg message.Message

	if err := serializer.Deserialize(delivery.Payload, &msg); err != nil {
		return message.Message{}, fmt.Errorf("deserialize received message: %w", err)
	}

	return msg, nil
}
