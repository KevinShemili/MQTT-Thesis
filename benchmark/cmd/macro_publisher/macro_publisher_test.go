package main

import (
	"errors"
	"slices"
	"testing"
)

func TestRunPublisherCallsOperationsInExpectedOrder(t *testing.T) {

	// Arrange
	calls := []string{}

	dependencies := buildTestDependencies(&calls, nil)

	payloadSizes := []int{256}
	runs := 1
	warmupRuns := 1

	expectedFlow := []string{
		"connect",
		"read GO",
		"benchmark",
		"write DONE",
		"read GO",
		"benchmark",
		"write DONE",
		"read FINISH",
		"disconnect",
		"write results",
	}

	// Act
	err := runPublisher(payloadSizes, runs, warmupRuns, dependencies)

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

	dependencies := buildTestDependencies(&calls, benchmarkError)

	expected := []string{
		"connect",
		"read GO",
		"benchmark",
	}

	// Act
	err := runPublisher([]int{256}, 1, 0, dependencies)

	// Assert
	if !errors.Is(err, benchmarkError) {
		t.Fatalf("expected %v, got %v", benchmarkError, err)
	}
	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func buildTestDependencies(calls *[]string, benchmarkError error) publisherDependencies {

	return publisherDependencies{
		connect: func() error {
			*calls = append(*calls, "connect")
			return nil
		},
		disconnect: func() {
			*calls = append(*calls, "disconnect")
		},
		readSignal: func(signal string) error {
			*calls = append(*calls, "read "+signal)
			return nil
		},
		writeSignal: func(signal string) error {
			*calls = append(*calls, "write "+signal)
			return nil
		},
		runBenchmark: func(_ int, _ int, _ int, _ bool) error {
			*calls = append(*calls, "benchmark")
			return benchmarkError
		},
		writeResults: func() error {
			*calls = append(*calls, "write results")
			return nil
		},
	}
}
