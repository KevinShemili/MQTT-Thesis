package baseline

import (
	"fmt"
	"time"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro/shared"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"

	"github.com/google/uuid"
)

type SubscriberMeasurement struct {
	MessageID uuid.UUID
	EndTime   int64
}

type SubscriberResult struct {
	Measurements []SubscriberMeasurement
	Cycles       uint64
}

func RunSubscribeBenchmark(client mqtt.Client, serializer serialization.Serializer, config shared.ExperimentConfig,
	measurements []SubscriberMeasurement, isCPUMeasured bool, notifyReady func() error) (SubscriberResult, error) {

	if isCPUMeasured == false {

		measurements, err := consumeMessages(client, serializer, config, measurements, notifyReady)
		if err != nil {
			return SubscriberResult{}, err
		}

		return SubscriberResult{Measurements: measurements}, nil
	}

	measurement, err := cpu.StartMeasurement()
	if err != nil {
		return SubscriberResult{}, err
	}

	measurements, workloadErr := consumeMessages(client, serializer, config, measurements, func() error {
		if err := measurement.Enable(); err != nil {
			return err
		}
		return notifyReady()
	})
	if workloadErr != nil {
		measurement.Abort()
		return SubscriberResult{}, workloadErr
	}

	cycles, err := measurement.Stop()
	if err != nil {
		return SubscriberResult{}, err
	}

	return SubscriberResult{
		Measurements: measurements,
		Cycles:       cycles,
	}, nil
}

func consumeMessages(client mqtt.Client, serializer serialization.Serializer, config shared.ExperimentConfig,
	measurements []SubscriberMeasurement, notifyReady func() error) ([]SubscriberMeasurement, error) {

	messageIndex := 0
	benchmarkResult := make(chan error, 1)

	err := client.Subscribe(config.Topic, func(delivery mqtt.MQTTDelivery) {

		var msg message.Message

		if err := serializer.Deserialize(delivery.Payload, &msg); err != nil {
			benchmarkResult <- fmt.Errorf("deserialize received message: %w", err)
			return
		}

		endTime := time.Now().UnixNano()

		if err := message.ValidateMessage(msg, config.PayloadSize); err != nil {
			benchmarkResult <- fmt.Errorf("validate message %s: %w", msg.ID, err)
			return
		}

		measurements[messageIndex] = SubscriberMeasurement{
			MessageID: msg.ID,
			EndTime:   endTime,
		}
		messageIndex++

		if messageIndex == config.MessageCount {
			benchmarkResult <- nil
		}
	})
	if err != nil {
		return nil, err
	}

	if err := notifyReady(); err != nil {
		return nil, fmt.Errorf("notify subscriber ready: %w", err)
	}

	if err := <-benchmarkResult; err != nil {
		return nil, err
	}

	return measurements, nil
}
