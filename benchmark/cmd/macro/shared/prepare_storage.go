package shared

import (
	"thesis/benchmark/macro"
)

func PreparePublisherResults(config macro.BenchmarkConfig) []macro.PublisherResult {

	results := make([]macro.PublisherResult, len(config.PayloadSizes)*config.Runs)
	measurements := make([]macro.PublisherMeasurement, len(config.PayloadSizes)*config.Runs*config.MessageCount)

	// Touch memory once
	touchMemory(measurements)

	// Assign the pre-allocated memory to results
	for run := range results {
		start := run * config.MessageCount
		end := start + config.MessageCount
		results[run].Measurements = measurements[start:end]
	}

	return results
}

func PrepareSubscriberResults(config macro.BenchmarkConfig) []macro.SubscriberResult {

	results := make([]macro.SubscriberResult, len(config.PayloadSizes)*config.Runs)
	measurements := make([]macro.SubscriberMeasurement, len(config.PayloadSizes)*config.Runs*config.MessageCount)

	// Touch memory once
	touchMemory(measurements)

	// Assign the pre-allocated memory to results
	for run := range results {

		start := run * config.MessageCount
		end := start + config.MessageCount

		results[run].Measurements = measurements[start:end]
	}

	return results
}

func touchMemory[T macro.PublisherMeasurement | macro.SubscriberMeasurement](measurements []T) {

	for index := range measurements {

		switch measurement := any(&measurements[index]).(type) {

		case *macro.PublisherMeasurement:
			measurement.StartTime = -1

		case *macro.SubscriberMeasurement:
			measurement.EndTime = -1
		}
	}
}
