package tls_json

import (
	"slices"
	"strconv"
	"testing"
	"time"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro/shared"
	"thesis/internal/mqtt"
)

func TestRunPublishBenchmarkMeasuredCallOrder(t *testing.T) {

	// Arrange
	calls := []string{}

	tokens := []*fakePublishToken{
		{
			calls: &calls,
			index: 1,
		},
		{
			calls: &calls,
			index: 2,
		},
	}

	client := &fakeMQTTClient{
		calls:  &calls,
		tokens: tokens,
	}

	cpuMeasurement := &fakeCPU{
		calls: &calls,
	}

	config := shared.BenchmarkConfig{
		MessageCount:    2,
		PublishInterval: 0,
		Topic:           "test/topic",
	}

	measurements := make([]shared.PublisherMeasurement, config.MessageCount)

	newCPU := func() (cpu.CPU, error) {
		calls = append(calls, "new cpu")
		return cpuMeasurement, nil
	}

	expected := []string{
		"new cpu",
		"enable",
		"publish 1",
		"publish 2",
		"wait 1",
		"error 1",
		"wait 2",
		"error 2",
		"stop",
	}

	// Act
	result, err := runPublishBenchmark(TLSJSONPublisherInput{
		Client:       client,
		Config:       shared.MacroConfig{Benchmark: config},
		PayloadSize:  16,
		Measurements: measurements,
		IsWarmup:     false,
	}, newCPU)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if result.Measurements[0].StartTime == 0 {
		t.Fatal("expected publisher timestamp to be recorded")
	}

	if result.Measurements[0].StartTime > client.firstPublishTime {
		t.Fatal("publisher timestamp must precede publishing")
	}

	if result.Cycles != 123 {
		t.Fatalf("expected 123 cycles, got %d", result.Cycles)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func TestRunPublishBenchmarkWarmupDoesNotMeasure(t *testing.T) {

	// Arrange
	calls := []string{}

	tokens := []*fakePublishToken{
		{
			calls: &calls,
			index: 1,
		},
	}

	client := &fakeMQTTClient{
		calls:  &calls,
		tokens: tokens,
	}

	config := shared.BenchmarkConfig{
		MessageCount:    1,
		PublishInterval: 0,
		Topic:           "test/topic",
	}

	newCPU := func() (cpu.CPU, error) {
		calls = append(calls, "new cpu")
		return &fakeCPU{calls: &calls}, nil
	}

	expected := []string{
		"publish 1",
		"wait 1",
		"error 1",
	}

	// Act
	result, err := runPublishBenchmark(TLSJSONPublisherInput{
		Client:      client,
		Config:      shared.MacroConfig{Benchmark: config},
		PayloadSize: 16,
		IsWarmup:    true,
	}, newCPU)

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

type fakeCPU struct {
	calls *[]string
}

func (measurement *fakeCPU) Enable() error {

	*measurement.calls = append(
		*measurement.calls,
		"enable",
	)

	return nil
}

func (measurement *fakeCPU) Stop() (uint64, error) {

	*measurement.calls = append(
		*measurement.calls,
		"stop",
	)

	return 123, nil
}

func (measurement *fakeCPU) Abort() {

	*measurement.calls = append(
		*measurement.calls,
		"abort",
	)
}

type fakeMQTTClient struct {
	calls            *[]string
	tokens           []*fakePublishToken
	publishIndex     int
	firstPublishTime int64
}

func (client *fakeMQTTClient) Connect() error {
	return nil
}

func (client *fakeMQTTClient) Subscribe(
	_ string,
	_ func(mqtt.MQTTDelivery),
) error {
	return nil
}

func (client *fakeMQTTClient) Publish(
	_ string,
	_ []byte,
) mqtt.PublishToken {

	if client.publishIndex == 0 {
		client.firstPublishTime = time.Now().UnixNano()
	}

	index := client.publishIndex
	client.publishIndex++

	*client.calls = append(
		*client.calls,
		"publish "+strconv.Itoa(index+1),
	)

	return client.tokens[index]
}

func (client *fakeMQTTClient) Disconnect() {
}

type fakePublishToken struct {
	calls *[]string
	index int
}

func (token *fakePublishToken) Wait() bool {

	*token.calls = append(
		*token.calls,
		"wait "+strconv.Itoa(token.index),
	)

	return true
}

func (token *fakePublishToken) Error() error {

	*token.calls = append(
		*token.calls,
		"error "+strconv.Itoa(token.index),
	)

	return nil
}
