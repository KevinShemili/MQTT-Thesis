package shared

import (
	"thesis/benchmark/utility"
	"time"
)

type ExperimentConfig struct {
	PayloadSizes    []int
	MessageCount    int
	PublishInterval time.Duration
	Topic           string
}

func NewExperimentConfig() ExperimentConfig {

	return ExperimentConfig{
		PayloadSizes: utility.ParseIntListFromEnv("MACRO_PAYLOAD_SIZES"),
		MessageCount: utility.ParseIntFromEnv("MACRO_MESSAGE_COUNT"),
		PublishInterval: time.Duration(
			utility.ParseIntFromEnv("MACRO_PUBLISH_INTERVAL_MILLISECONDS"),
		) * time.Millisecond,
		Topic: utility.ParseStringFromEnv("MACRO_BENCHMARK_TOPIC"),
	}
}
