package baseline

import (
	"slices"
	"strconv"
	"testing"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro/shared"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
)

func TestRunSubscribeBenchmarkMeasuredCallOrder(t *testing.T) {

	// Arrange
	calls := []string{}

	payloadSize := 16

	config := shared.ExperimentConfig{
		MessageCount: 2,
		Topic:        "test/topic",
	}

	messages := shared.BuildMessages(config.MessageCount, payloadSize)

	jsonSerializer := serialization.JSONSerializer{}

	firstPayload, err := jsonSerializer.Serialize(messages[0])
	if err != nil {
		t.Fatalf("failed to serialize first message: %v", err)
	}

	secondPayload, err := jsonSerializer.Serialize(messages[1])
	if err != nil {
		t.Fatalf("failed to serialize second message: %v", err)
	}

	client := &fakeSubscriberMQTTClient{calls: &calls}
	serializer := &fakeSubscriberSerializer{calls: &calls}
	cpuMeasurement := &fakeSubscriberCPU{calls: &calls}

	measurements := make([]SubscriberMeasurement, config.MessageCount)

	newCPU := func() (cpu.CPU, error) {
		calls = append(calls, "new cpu")
		return cpuMeasurement, nil
	}

	notifyReady := func() error {

		calls = append(calls, "ready")
		client.handler(mqtt.MQTTDelivery{
			Payload: firstPayload,
		})
		client.handler(mqtt.MQTTDelivery{
			Payload: secondPayload,
		})
		return nil
	}

	expected := []string{
		"new cpu",
		"subscribe",
		"enable",
		"ready",
		"deserialize 1",
		"deserialize 2",
		"stop",
	}

	// Act
	_, err = runSubscribeBenchmark(client, serializer, config, payloadSize, measurements, true, notifyReady, newCPU)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func TestRunSubscribeBenchmarkWarmupDoesNotMeasureCPU(t *testing.T) {

	// Arrange
	calls := []string{}

	payloadSize := 16

	config := shared.ExperimentConfig{
		MessageCount: 1,
		Topic:        "test/topic",
	}

	messages := shared.BuildMessages(config.MessageCount, payloadSize)

	jsonSerializer := serialization.JSONSerializer{}

	payload, err := jsonSerializer.Serialize(messages[0])
	if err != nil {
		t.Fatalf("failed to serialize message: %v", err)
	}

	client := &fakeSubscriberMQTTClient{calls: &calls}
	serializer := &fakeSubscriberSerializer{calls: &calls}
	measurements := make([]SubscriberMeasurement, config.MessageCount)

	newCPU := func() (cpu.CPU, error) {
		calls = append(calls, "new cpu")
		return &fakeSubscriberCPU{calls: &calls}, nil
	}

	notifyReady := func() error {
		calls = append(calls, "ready")
		client.handler(mqtt.MQTTDelivery{Payload: payload})

		return nil
	}

	expected := []string{
		"subscribe",
		"ready",
		"deserialize 1",
	}

	// Act
	_, err = runSubscribeBenchmark(client, serializer, config, payloadSize, measurements, false, notifyReady, newCPU)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

type fakeSubscriberCPU struct {
	calls *[]string
}

func (measurement *fakeSubscriberCPU) Enable() error {

	*measurement.calls = append(
		*measurement.calls,
		"enable",
	)

	return nil
}

func (measurement *fakeSubscriberCPU) Stop() (uint64, error) {

	*measurement.calls = append(
		*measurement.calls,
		"stop",
	)

	return 123, nil
}

func (measurement *fakeSubscriberCPU) Abort() {

	*measurement.calls = append(
		*measurement.calls,
		"abort",
	)
}

type fakeSubscriberMQTTClient struct {
	calls   *[]string
	handler func(mqtt.MQTTDelivery)
}

func (client *fakeSubscriberMQTTClient) Connect() error {
	return nil
}

func (client *fakeSubscriberMQTTClient) Subscribe(
	_ string,
	handler func(mqtt.MQTTDelivery),
) error {

	*client.calls = append(
		*client.calls,
		"subscribe",
	)

	client.handler = handler

	return nil
}

func (client *fakeSubscriberMQTTClient) Publish(
	_ string,
	_ []byte,
) mqtt.PublishToken {
	return nil
}

func (client *fakeSubscriberMQTTClient) Disconnect() {
}

type fakeSubscriberSerializer struct {
	calls            *[]string
	deserializeCount int
}

func (serializer *fakeSubscriberSerializer) Serialize(
	value any,
) ([]byte, error) {

	return serialization.JSONSerializer{}.Serialize(value)
}

func (serializer *fakeSubscriberSerializer) Deserialize(
	data []byte,
	value any,
) error {

	serializer.deserializeCount++

	*serializer.calls = append(
		*serializer.calls,
		"deserialize "+strconv.Itoa(serializer.deserializeCount),
	)

	return serialization.JSONSerializer{}.Deserialize(
		data,
		value,
	)
}
