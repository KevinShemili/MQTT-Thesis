package tls_cbor

import (
	"slices"
	"testing"
	"time"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro/shared"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
)

func TestRunSubscribeBenchmarkMeasuredCallOrder(t *testing.T) {

	// Arrange
	calls := []string{}

	payloadSize := 16

	config := shared.BenchmarkConfig{
		MessageCount: 2,
		Topic:        "test/topic",
	}

	messages := shared.BuildMessages(config.MessageCount, payloadSize)

	cborSerializer := serialization.CBORSerializer{}

	firstPayload, err := cborSerializer.Serialize(messages[0])
	if err != nil {
		t.Fatalf("failed to serialize first message: %v", err)
	}

	secondPayload, err := cborSerializer.Serialize(messages[1])
	if err != nil {
		t.Fatalf("failed to serialize second message: %v", err)
	}

	client := &fakeSubscriberMQTTClient{calls: &calls}
	var firstHandlerStart, firstHandlerEnd int64

	cpuMeasurement := &fakeSubscriberCPU{calls: &calls}

	measurements := make([]shared.SubscriberMeasurement, config.MessageCount)

	newCPU := func() (cpu.CPU, error) {
		calls = append(calls, "new cpu")
		return cpuMeasurement, nil
	}

	notifyReady := func() error {

		calls = append(calls, "ready")

		firstHandlerStart = time.Now().UnixNano()

		client.handler(mqtt.MQTTDelivery{
			Payload: firstPayload,
		})

		firstHandlerEnd = time.Now().UnixNano()

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
		"stop",
	}

	// Act
	result, err := runSubscribeBenchmark(TLSCBORSubscriberInput{
		Client:       client,
		Config:       shared.MacroConfig{Benchmark: config},
		Measurements: measurements,
		IsWarmup:     false,
	}, notifyReady, newCPU)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if measurements[0].EndTime == 0 {
		t.Fatal("expected subscriber timestamp to be recorded")
	}

	if measurements[0].EndTime < firstHandlerStart ||
		measurements[0].EndTime > firstHandlerEnd {
		t.Fatal("subscriber timestamp must be recorded during the MQTT handler")
	}

	if measurements[0].MessageID != messages[0].ID {
		t.Fatal("subscriber measurement must contain the decoded message ID")
	}

	if result.Cycles != 123 {
		t.Fatalf("expected 123 cycles, got %d", result.Cycles)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func TestRunSubscribeBenchmarkWarmupDoesNotMeasure(t *testing.T) {

	// Arrange
	calls := []string{}

	payloadSize := 16

	config := shared.BenchmarkConfig{
		MessageCount: 1,
		Topic:        "test/topic",
	}

	messages := shared.BuildMessages(config.MessageCount, payloadSize)

	cborSerializer := serialization.CBORSerializer{}

	payload, err := cborSerializer.Serialize(messages[0])
	if err != nil {
		t.Fatalf("failed to serialize message: %v", err)
	}

	client := &fakeSubscriberMQTTClient{calls: &calls}

	newCPU := func() (cpu.CPU, error) {
		calls = append(calls, "new cpu")
		return &fakeSubscriberCPU{calls: &calls}, nil
	}

	notifyReady := func() error {

		calls = append(calls, "ready")

		client.handler(mqtt.MQTTDelivery{
			Payload: payload,
		})

		return nil
	}

	expected := []string{
		"subscribe",
		"ready",
	}

	// Act
	result, err := runSubscribeBenchmark(TLSCBORSubscriberInput{
		Client:   client,
		Config:   shared.MacroConfig{Benchmark: config},
		IsWarmup: true,
	}, notifyReady, newCPU)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(result.Measurements) != 0 {
		t.Fatal("warmup must not return measurements")
	}

	if result.Cycles != 0 {
		t.Fatal("warmup must not return CPU cycles")
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
