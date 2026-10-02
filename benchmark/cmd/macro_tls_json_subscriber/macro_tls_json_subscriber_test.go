package main

import (
	"errors"
	"slices"
	"testing"

	"thesis/benchmark/macro/shared"
)

func TestRunSubscriberCallsOperationsInExpectedOrder(t *testing.T) {

	// Arrange
	calls := []string{}

	dependencies := subscriberDependencies{
		connect: func() error {
			calls = append(calls, "connect")
			return nil
		},
		disconnect: func() {
			calls = append(calls, "disconnect")
		},
		readSignal: func(signal string) error {
			calls = append(calls, "read "+signal)
			return nil
		},
		writeSignal: func(signal string) error {
			calls = append(calls, "write "+signal)
			return nil
		},
		runBenchmark: func(
			_ int,
			_ int,
			_ bool,
			onReady func() error,
		) error {
			calls = append(calls, "benchmark start")

			if err := onReady(); err != nil {
				return err
			}

			calls = append(calls, "benchmark end")

			return nil
		},
		writeResults: func() error {
			calls = append(calls, "write results")
			return nil
		},
	}

	payloadSizes := []int{256}
	runs := 1
	warmupRuns := 1

	expected := []string{
		"connect",
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
		"disconnect",
		"write results",
	}

	// Act
	err := runSubscriber(shared.BenchmarkConfig{
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

	dependencies := subscriberDependencies{
		connect: func() error {
			calls = append(calls, "connect")
			return nil
		},

		disconnect: func() {
			calls = append(calls, "disconnect")
		},

		readSignal: func(signal string) error {
			calls = append(calls, "read "+signal)
			return nil
		},

		writeSignal: func(signal string) error {
			calls = append(calls, "write "+signal)
			return nil
		},

		runBenchmark: func(
			_ int,
			_ int,
			_ bool,
			_ func() error,
		) error {
			calls = append(calls, "benchmark")
			return benchmarkError
		},

		writeResults: func() error {
			calls = append(calls, "write results")
			return nil
		},
	}

	expected := []string{
		"connect",
		"read GO",
		"benchmark",
	}

	// Act
	err := runSubscriber(shared.BenchmarkConfig{
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
