package macro

import (
	"slices"
	"testing"

	"thesis/benchmark/cpu"
)

func TestRunSubscriberBenchmarkMeasuredCallOrder(t *testing.T) {

	// Arrange
	calls := []string{}

	dependencies := subscriberDependency{
		NewCPU: func() (cpu.CPU, error) {
			calls = append(calls, "new cpu")
			return &fakeCPU{calls: &calls}, nil
		},
		Subscribe: func() error {
			calls = append(calls, "subscribe")
			return nil
		},
		WriteReady: func() error {
			calls = append(calls, "ready")
			return nil
		},
		WaitMessages: func() error {
			calls = append(calls, "wait messages")
			return nil
		},
	}

	expected := []string{
		"new cpu",
		"subscribe",
		"enable",
		"ready",
		"wait messages",
		"stop",
	}

	// Act
	_, err := benchmarkSubscriber(SubscriberInput{IsWarmup: false}, dependencies)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func TestRunSubscriberBenchmarkWarmupDoesNotMeasure(t *testing.T) {

	// Arrange
	calls := []string{}

	input := SubscriberInput{
		IsWarmup:     true,
		Measurements: make([]SubscriberSample, 1),
	}

	dependencies := subscriberDependency{
		NewCPU: func() (cpu.CPU, error) {
			calls = append(calls, "new cpu")
			return &fakeCPU{calls: &calls}, nil
		},
		Subscribe: func() error {
			calls = append(calls, "subscribe")
			return nil
		},
		WriteReady: func() error {
			calls = append(calls, "ready")
			return nil
		},
		WaitMessages: func() error {
			calls = append(calls, "wait messages")
			return nil
		},
	}

	expected := []string{
		"subscribe",
		"ready",
		"wait messages",
	}

	// Act
	result, err := benchmarkSubscriber(input, dependencies)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}

	if len(result.Measurements) != 0 {
		t.Fatal("warmup must not return measurements")
	}

	if result.Cycles != 0 {
		t.Fatal("warmup must not return CPU cycles")
	}
}

func TestRunPublisherBenchmarkMeasuredCallOrder(t *testing.T) {

	// Arrange
	calls := []string{}

	dependencies := publisherDependency{
		NewCPU: func() (cpu.CPU, error) {
			calls = append(calls, "new cpu")
			return &fakeCPU{calls: &calls}, nil
		},
		PublishMessages: func() error {
			calls = append(calls, "publish messages")
			return nil
		},
	}

	expected := []string{
		"new cpu",
		"enable",
		"publish messages",
		"stop",
	}

	// Act
	_, err := benchmarkPublisher(PublisherInput{IsWarmup: false}, dependencies)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func TestRunPublisherBenchmarkWarmupDoesNotMeasure(t *testing.T) {

	// Arrange
	calls := []string{}

	input := PublisherInput{
		IsWarmup:     true,
		Measurements: make([]PublisherSample, 1),
	}

	dependencies := publisherDependency{
		NewCPU: func() (cpu.CPU, error) {
			calls = append(calls, "new cpu")
			return &fakeCPU{calls: &calls}, nil
		},
		PublishMessages: func() error {
			calls = append(calls, "publish messages")
			return nil
		},
	}

	expected := []string{
		"publish messages",
	}

	// Act
	result, err := benchmarkPublisher(input, dependencies)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}

	if len(result.Measurements) != 0 {
		t.Fatal("warmup must not return measurements")
	}

	if result.Cycles != 0 {
		t.Fatal("warmup must not return CPU cycles")
	}
}

type fakeCPU struct {
	calls *[]string
}

func (measurement *fakeCPU) Enable() error {
	*measurement.calls = append(*measurement.calls, "enable")
	return nil
}

func (measurement *fakeCPU) Stop() (uint64, error) {
	*measurement.calls = append(*measurement.calls, "stop")
	return 123, nil
}

func (measurement *fakeCPU) Abort() {
	*measurement.calls = append(*measurement.calls, "abort")
}
