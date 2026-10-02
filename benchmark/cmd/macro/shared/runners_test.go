package cmdshared

import (
	"errors"
	"slices"
	"testing"

	"thesis/benchmark/macro/shared"
)

func TestRunPublisherCallsOperationsInExpectedOrder(t *testing.T) {

	// Arrange
	calls := []string{}

	dependencies := buildPublisherTestDependencies(&calls, nil)

	payloadSizes := []int{256}
	runs := 1
	warmupRuns := 1

	expectedFlow := []string{
		"Connect",
		"read GO",
		"benchmark",
		"write DONE",
		"read GO",
		"benchmark",
		"write DONE",
		"read FINISH",
		"Disconnect",
		"write results",
	}

	// Act
	err := RunPublisher(shared.BenchmarkConfig{
		PayloadSizes: payloadSizes,
		Runs:         runs,
		WarmupRuns:   warmupRuns,
	}, dependencies)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if !slices.Equal(calls, expectedFlow) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expectedFlow, calls)
	}
}

func TestRunPublisherStopsImmediatelyWhenBenchmarkFails(t *testing.T) {

	// Arrange
	calls := []string{}
	benchmarkError := errors.New("benchmark failed")

	dependencies := buildPublisherTestDependencies(&calls, benchmarkError)

	expected := []string{
		"Connect",
		"read GO",
		"benchmark",
	}

	// Act
	err := RunPublisher(shared.BenchmarkConfig{
		PayloadSizes: []int{256},
		Runs:         1,
		WarmupRuns:   0,
	}, dependencies)

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

	payloadSizes := []int{256}
	runs := 1
	warmupRuns := 1

	expected := []string{
		"Connect",
		"read GO",
		"benchmark start",
		"write READY",
		"benchmark end",
		"write DONE",
		"read GO",
		"benchmark start",
		"write READY",
		"benchmark end",
		"write DONE",
		"read FINISH",
		"Disconnect",
		"write results",
	}

	// Act
	err := RunSubscriber(shared.BenchmarkConfig{
		PayloadSizes: payloadSizes,
		Runs:         runs,
		WarmupRuns:   warmupRuns,
	}, dependencies)

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

	dependencies := buildSubscriberTestDependencies(&calls, benchmarkError)

	expected := []string{
		"Connect",
		"read GO",
		"benchmark",
	}

	// Act
	err := RunSubscriber(shared.BenchmarkConfig{
		PayloadSizes: []int{256},
		Runs:         1,
		WarmupRuns:   0,
	}, dependencies)

	// Assert
	if !errors.Is(err, benchmarkError) {
		t.Fatalf("expected %v, got %v", benchmarkError, err)
	}
	if !slices.Equal(calls, expected) {
		t.Fatalf(
			"unexpected call order:\nexpected: %v\ngot: %v", expected, calls,
		)
	}
}

func buildPublisherTestDependencies(calls *[]string, benchmarkError error) PublisherDependencies {

	return PublisherDependencies{
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
		RunBenchmark: func(_ int, _ int, _ int, _ bool) error {
			*calls = append(*calls, "benchmark")
			return benchmarkError
		},
		WriteResults: func() error {
			*calls = append(*calls, "write results")
			return nil
		},
	}
}

func buildSubscriberTestDependencies(calls *[]string, benchmarkError error) SubscriberDependencies {

	return SubscriberDependencies{
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
			_ int,
			_ bool,
			onReady func() error,
		) error {

			if benchmarkError != nil {
				*calls = append(*calls, "benchmark")
				return benchmarkError
			}

			*calls = append(*calls, "benchmark start")

			if err := onReady(); err != nil {
				return err
			}

			*calls = append(*calls, "benchmark end")

			return nil
		},
		WriteResults: func() error {
			*calls = append(*calls, "write results")
			return nil
		},
	}
}
