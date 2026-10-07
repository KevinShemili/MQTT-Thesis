package main

import (
	"errors"
	"path/filepath"
	"slices"
	"testing"
)

func TestRunCoordinatorCallsStagesInExpectedOrder(t *testing.T) {

	// Arrange
	calls := []string{}

	originalScenarios := scenarios
	scenarios = []scenario{
		{
			name:       "scenario_one",
			publisher:  "publisher_one",
			subscriber: "subscriber_one",
		},
		{
			name:       "scenario_two",
			publisher:  "publisher_two",
			subscriber: "subscriber_two",
		},
	}
	t.Cleanup(func() {
		scenarios = originalScenarios
	})

	payloadSizes = []int{256}
	runs = 1
	warmupRuns = 1
	resultDirectory = t.TempDir()

	dependencies := coordinatorDependency{
		LoadEnvironment: func() {
			calls = append(calls, "load environment")
		},
		ProvisionFixtures: func() error {
			calls = append(calls, "provision fixtures")
			return nil
		},
		DistributeFixtures: func() error {
			calls = append(calls, "distribute fixtures")
			return nil
		},
		DistributeBrokerCA: func() error {
			calls = append(calls, "distribute broker CA")
			return nil
		},
		BuildBinary: func(_, _, executable string) error {
			calls = append(calls, "build "+executable)
			return nil
		},
		OrchestrateMacro: func(_, _, _, _, publisherExecutable, subscriberExecutable string, _ int) error {
			calls = append(calls, "run "+publisherExecutable+" "+subscriberExecutable)
			return nil
		},
		TransferResult: func(_, _, scenarioDirectory, filename string) error {
			calls = append(calls, "transfer "+filepath.Base(scenarioDirectory)+" "+filename)
			return nil
		},
		GenerateReport: func() error {
			calls = append(calls, "generate report")
			return nil
		},
	}

	expected := []string{
		"load environment",
		"provision fixtures",
		"distribute fixtures",
		"distribute broker CA",

		"build publisher_one",
		"build subscriber_one",
		"run publisher_one subscriber_one",
		"transfer scenario_one publisher.csv",
		"transfer scenario_one subscriber.csv",

		"build publisher_two",
		"build subscriber_two",
		"run publisher_two subscriber_two",
		"transfer scenario_two publisher.csv",
		"transfer scenario_two subscriber.csv",

		"generate report",
	}

	// Act
	err := runCoordinator(dependencies)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func TestRunCoordinatorStopsImmediatelyWhenBuildFails(t *testing.T) {

	// Arrange
	calls := []string{}
	buildError := errors.New("build failed")

	originalScenarios := scenarios
	scenarios = []scenario{
		{
			name:       "scenario_one",
			publisher:  "publisher_one",
			subscriber: "subscriber_one",
		},
	}
	t.Cleanup(func() {
		scenarios = originalScenarios
	})

	payloadSizes = []int{256}
	runs = 1
	warmupRuns = 0
	resultDirectory = t.TempDir()

	dependencies := coordinatorDependency{
		LoadEnvironment: func() {
			calls = append(calls, "load environment")
		},
		ProvisionFixtures: func() error {
			calls = append(calls, "provision fixtures")
			return nil
		},
		DistributeFixtures: func() error {
			calls = append(calls, "distribute fixtures")
			return nil
		},
		DistributeBrokerCA: func() error {
			calls = append(calls, "distribute broker CA")
			return nil
		},
		BuildBinary: func(_, _, _ string) error {
			calls = append(calls, "build")
			return buildError
		},
		OrchestrateMacro: func(_, _, _, _, _, _ string, _ int) error {
			calls = append(calls, "run")
			return nil
		},
		TransferResult: func(_, _, _, _ string) error {
			calls = append(calls, "transfer")
			return nil
		},
		GenerateReport: func() error {
			calls = append(calls, "generate report")
			return nil
		},
	}

	expected := []string{
		"load environment",
		"provision fixtures",
		"distribute fixtures",
		"distribute broker CA",
		"build",
	}

	// Act
	err := runCoordinator(dependencies)

	// Assert
	if !errors.Is(err, buildError) {
		t.Fatalf("expected %v, got %v", buildError, err)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func TestRunCommunicationSignalsCallsSignalsInExpectedOrder(t *testing.T) {

	// Arrange
	calls := []string{}

	dependencies := communicationDependency{
		WritePublisher: func(signal string) error {
			calls = append(calls, "write publisher "+signal)
			return nil
		},
		ReadPublisher: func(signal string) error {
			calls = append(calls, "read publisher "+signal)
			return nil
		},
		WriteSubscriber: func(signal string) error {
			calls = append(calls, "write subscriber "+signal)
			return nil
		},
		ReadSubscriber: func(signal string) error {
			calls = append(calls, "read subscriber "+signal)
			return nil
		},
	}

	expected := []string{
		"write subscriber GO",
		"read subscriber READY",
		"write publisher GO",
		"read publisher DONE",
		"read subscriber DONE",
	}

	// Act
	err := runCommunicationSignals(dependencies)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected protocol order:\nexpected: %v\ngot: %v", expected, calls)
	}
}
