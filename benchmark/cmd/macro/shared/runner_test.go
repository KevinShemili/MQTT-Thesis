package shared

import (
	"errors"
	"slices"
	"testing"

	"thesis/benchmark/macro"
)

func TestRunPublisherCallsOperationsInExpectedOrder(t *testing.T) {

	// Arrange
	calls := []string{}

	dependencies := buildPublisherTestDependencies(&calls, nil)

	config := macro.MacroConfig{
		Benchmark: macro.BenchmarkConfig{
			PayloadSizes: []int{256},
			Runs:         1,
			WarmupRuns:   0,
		},
	}

	expected := []string{
		"Connect",
		"read GO",
		"benchmark",
		"write DONE",
		"read FINISH",
		"Disconnect",
		"write results",
	}

	// Act
	err := runPublisher(config, dependencies)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func TestRunPublisherExecutesWarmup(t *testing.T) {

	// Arrange
	calls := []string{}

	dependencies := buildPublisherTestDependencies(&calls, nil)

	config := macro.MacroConfig{
		Benchmark: macro.BenchmarkConfig{
			PayloadSizes: []int{256},
			Runs:         0,
			WarmupRuns:   1,
		},
	}

	expected := []string{
		"Connect",
		"read GO",
		"warmup",
		"write DONE",
		"read FINISH",
		"Disconnect",
		"write results",
	}

	// Act
	err := runPublisher(config, dependencies)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func TestRunPublisherStopsImmediatelyWhenBenchmarkFails(t *testing.T) {

	// Arrange
	calls := []string{}
	benchmarkError := errors.New("benchmark failed")

	dependencies := buildPublisherTestDependencies(
		&calls,
		benchmarkError,
	)

	config := macro.MacroConfig{
		Benchmark: macro.BenchmarkConfig{
			PayloadSizes: []int{256},
			Runs:         1,
			WarmupRuns:   0,
		},
	}

	expected := []string{
		"Connect",
		"read GO",
		"benchmark",
	}

	// Act
	err := runPublisher(config, dependencies)

	// Assert
	if !errors.Is(err, benchmarkError) {
		t.Fatalf("expected %v, got %v", benchmarkError, err)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func TestRunSubscriberCallsOperationsInExpectedOrder(t *testing.T) {

	// Arrange
	calls := []string{}

	dependencies := buildSubscriberTestDependencies(&calls, nil)

	config := macro.MacroConfig{
		Benchmark: macro.BenchmarkConfig{
			PayloadSizes: []int{256},
			Runs:         1,
			WarmupRuns:   0,
		},
	}

	expected := []string{
		"Connect",
		"read GO",
		"benchmark",
		"write DONE",
		"read FINISH",
		"Disconnect",
		"write results",
	}

	// Act
	err := runSubscriber(config, dependencies)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func TestRunSubscriberExecutesWarmup(t *testing.T) {

	// Arrange
	calls := []string{}

	dependencies := buildSubscriberTestDependencies(&calls, nil)

	config := macro.MacroConfig{
		Benchmark: macro.BenchmarkConfig{
			PayloadSizes: []int{256},
			Runs:         0,
			WarmupRuns:   1,
		},
	}

	expected := []string{
		"Connect",
		"read GO",
		"warmup",
		"write DONE",
		"read FINISH",
		"Disconnect",
		"write results",
	}

	// Act
	err := runSubscriber(config, dependencies)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func TestRunSubscriberStopsImmediatelyWhenBenchmarkFails(t *testing.T) {

	// Arrange
	calls := []string{}
	benchmarkError := errors.New("benchmark failed")

	dependencies := buildSubscriberTestDependencies(
		&calls,
		benchmarkError,
	)

	config := macro.MacroConfig{
		Benchmark: macro.BenchmarkConfig{
			PayloadSizes: []int{256},
			Runs:         1,
			WarmupRuns:   0,
		},
	}

	expected := []string{
		"Connect",
		"read GO",
		"benchmark",
	}

	// Act
	err := runSubscriber(config, dependencies)

	// Assert
	if !errors.Is(err, benchmarkError) {
		t.Fatalf("expected %v, got %v", benchmarkError, err)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func TestPreparePublisherResults(t *testing.T) {

	// Arrange
	config := macro.BenchmarkConfig{
		PayloadSizes: []int{16, 32},
		Runs:         2,
		MessageCount: 3,
	}

	// Act
	results := preparePublisherResults(config)

	// Assert
	// 2 payload sizes × 2 runs = 4 results
	if len(results) != 4 {
		t.Fatalf("got %d results, want 4", len(results))
	}

	for _, result := range results {

		// Each result must contain 3 pre-allocated measurements
		if len(result.Measurements) != 3 {
			t.Fatalf("got %d measurements, want 3", len(result.Measurements))
		}

		// Verify touchMemory set StartTime to -1 for each measurement
		for _, measurement := range result.Measurements {
			if measurement.StartTime != -1 {
				t.Fatalf("StartTime = %d, want -1", measurement.StartTime)
			}
		}
	}
}

func TestPrepareSubscriberResults(t *testing.T) {

	// Arrange
	config := macro.BenchmarkConfig{
		PayloadSizes: []int{16, 32},
		Runs:         2,
		MessageCount: 3,
	}

	// Act
	results := prepareSubscriberResults(config)

	// Assert
	// 2 payload sizes × 2 runs = 4 results
	if len(results) != 4 {
		t.Fatalf("got %d results, want 4", len(results))
	}

	for _, result := range results {

		// Each result must contain 3 pre-allocated measurements
		if len(result.Measurements) != 3 {
			t.Fatalf("got %d measurements, want 3", len(result.Measurements))
		}

		// Verify touchMemory set EndTime to -1 for each measurement
		for _, measurement := range result.Measurements {
			if measurement.EndTime != -1 {
				t.Fatalf("EndTime = %d, want -1", measurement.EndTime)
			}
		}
	}
}

func buildPublisherTestDependencies(calls *[]string, benchmarkError error) publisherDependency {

	return publisherDependency{
		Connect: func() error {
			*calls = append(*calls, "Connect")
			return nil
		},

		Disconnect: func() {
			*calls = append(*calls, "Disconnect")
		},

		ReadSignal: func(signal string) error {
			*calls = append(*calls, "read "+signal)
			return nil
		},

		WriteSignal: func(signal string) error {
			*calls = append(*calls, "write "+signal)
			return nil
		},

		RunBenchmark: func(
			_ int,
			_ []macro.PublisherSample,
			isWarmup bool,
		) (macro.PublisherSamples, error) {

			if isWarmup {
				*calls = append(*calls, "warmup")
			} else {
				*calls = append(*calls, "benchmark")
			}

			return macro.PublisherSamples{}, benchmarkError
		},

		WriteResults: func(_ []macro.PublisherSamples) error {
			*calls = append(*calls, "write results")
			return nil
		},
	}
}

func buildSubscriberTestDependencies(calls *[]string, benchmarkError error) subscriberDependency {

	return subscriberDependency{
		Connect: func() error {
			*calls = append(*calls, "Connect")
			return nil
		},

		Disconnect: func() {
			*calls = append(*calls, "Disconnect")
		},

		ReadSignal: func(signal string) error {
			*calls = append(*calls, "read "+signal)
			return nil
		},

		WriteSignal: func(signal string) error {
			*calls = append(*calls, "write "+signal)
			return nil
		},

		RunBenchmark: func(
			_ []macro.SubscriberSample,
			isWarmup bool,
		) (macro.SubscriberSamples, error) {

			if isWarmup {
				*calls = append(*calls, "warmup")
			} else {
				*calls = append(*calls, "benchmark")
			}

			return macro.SubscriberSamples{}, benchmarkError
		},

		WriteResults: func(_ []macro.SubscriberSamples) error {
			*calls = append(*calls, "write results")
			return nil
		},
	}
}
