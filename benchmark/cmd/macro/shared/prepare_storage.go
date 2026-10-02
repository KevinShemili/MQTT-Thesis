package cmdshared

import (
	"thesis/benchmark/macro/shared"
	"thesis/benchmark/memory"
)

func PreparePublisherResults(config shared.BenchmarkConfig) []shared.PublisherResult {

	results := make([]shared.PublisherResult, len(config.PayloadSizes)*config.Runs)
	measurements := make([]shared.PublisherMeasurement, len(config.PayloadSizes)*config.Runs*config.MessageCount)

	// Touch memory once
	memory.TouchMemory(measurements)

	// Assign the pre-allocated memory to results
	for run := range results {
		start := run * config.MessageCount
		end := start + config.MessageCount
		results[run].Measurements = measurements[start:end]
	}

	return results
}

func PrepareSubscriberResults(config shared.BenchmarkConfig) []shared.SubscriberResult {

	results := make([]shared.SubscriberResult, len(config.PayloadSizes)*config.Runs)
	measurements := make([]shared.SubscriberMeasurement, len(config.PayloadSizes)*config.Runs*config.MessageCount)

	// Touch memory once
	memory.TouchMemory(measurements)

	// Assign the pre-allocated memory to results
	for run := range results {

		start := run * config.MessageCount
		end := start + config.MessageCount

		results[run].Measurements = measurements[start:end]
	}

	return results
}
