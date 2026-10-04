package shared

import (
	"testing"

	"thesis/benchmark/macro"
)

func TestPreparePublisherResults(t *testing.T) {

	// Arrange
	config := macro.BenchmarkConfig{
		PayloadSizes: []int{16, 32},
		Runs:         2,
		MessageCount: 3,
	}

	// Act
	results := PreparePublisherResults(config)

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
	results := PrepareSubscriberResults(config)

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
