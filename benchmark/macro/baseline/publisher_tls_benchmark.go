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

type PublisherMeasurement struct {
	MessageID uuid.UUID
	StartTime int64
}

type PublisherResult struct {
	Measurements []PublisherMeasurement
	Cycles       uint64
}

func RunPublishBenchmark(client mqtt.Client, serializer serialization.Serializer,
	config shared.ExperimentConfig, measurements []PublisherMeasurement, isCPUMeasured bool) (PublisherResult, error) {

	messages := shared.BuildMessages(config.MessageCount, config.PayloadSize)

	if isCPUMeasured == false {

		measurements, err := publishMessages(client, serializer, config, messages, measurements)
		if err != nil {
			return PublisherResult{}, err
		}

		return PublisherResult{Measurements: measurements}, nil
	}

	measurement, err := cpu.StartMeasurement()
	if err != nil {
		return PublisherResult{}, err
	}
	if err := measurement.Enable(); err != nil {
		measurement.Abort()
		return PublisherResult{}, err
	}

	measurements, workloadErr := publishMessages(client, serializer, config, messages, measurements)
	if workloadErr != nil {
		measurement.Abort()
		return PublisherResult{}, workloadErr
	}

	cycles, err := measurement.Stop()
	if err != nil {
		return PublisherResult{}, err
	}

	return PublisherResult{
		Measurements: measurements,
		Cycles:       cycles,
	}, nil
}

func publishMessages(client mqtt.Client, serializer serialization.Serializer,
	config shared.ExperimentConfig, messages []message.Message,
	measurements []PublisherMeasurement) ([]PublisherMeasurement, error) {

	publishTokens := make([]mqtt.PublishToken, 0, config.MessageCount)

	for messageIndex := range config.MessageCount {

		time.Sleep(config.PublishInterval)

		msg := messages[messageIndex]

		startTime := time.Now().UnixNano()

		serializedMessage, err := serializer.Serialize(msg)
		if err != nil {
			return nil, fmt.Errorf("serialize message %s: %w", msg.ID, err)
		}

		publishTokens = append(publishTokens, client.Publish(config.Topic, serializedMessage))

		measurements[messageIndex] = PublisherMeasurement{
			MessageID: msg.ID,
			StartTime: startTime,
		}
	}

	for messageIndex, publishToken := range publishTokens {

		publishToken.Wait()

		if err := publishToken.Error(); err != nil {
			return nil, fmt.Errorf("publish message %s: %w", measurements[messageIndex].MessageID, err)
		}
	}

	return measurements, nil
}
