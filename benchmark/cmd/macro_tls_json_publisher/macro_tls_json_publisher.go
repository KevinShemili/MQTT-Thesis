package main

import (
	"bufio"
	"fmt"
	"os"

	"thesis/benchmark/macro/shared"
	"thesis/benchmark/macro/tls_json"
	"thesis/benchmark/memory"
	"thesis/benchmark/utility"
	"thesis/benchmark/utility/csv"
	"thesis/internal/mqtt"
)

type publisherDependencies struct {
	connect      func() error
	disconnect   func()
	readSignal   func(string) error
	writeSignal  func(string) error
	runBenchmark func(payloadIndex int, payloadSize int, run int, isWarmup bool) error
	writeResults func() error
}

func main() {

	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}
}

func run() error {

	config := shared.NewMacroConfig()

	tlsConfig, err := mqtt.NewTLSConfig(config.MQTT.CACertificate, config.MQTT.BrokerURL)
	if err != nil {
		return err
	}

	client := mqtt.NewClient(mqtt.ClientConfig{
		BrokerURL: config.MQTT.BrokerURL,
		ClientID:  config.MQTT.PublisherClientID,
		Username:  config.MQTT.PublisherUsername,
		Password:  config.MQTT.PublisherPassword,
		TLSConfig: tlsConfig,
	})

	results := make([]shared.PublisherResult, len(config.Benchmark.PayloadSizes)*config.Benchmark.Runs)
	measurements := make([]shared.PublisherMeasurement, len(config.Benchmark.PayloadSizes)*config.Benchmark.Runs*config.Benchmark.MessageCount)

	// Touch memory once
	memory.TouchMemory(measurements)

	// Assign the pre-allocated memory to results
	for run := range results {
		start := run * config.Benchmark.MessageCount
		end := start + config.Benchmark.MessageCount
		results[run].Measurements = measurements[start:end]
	}

	startSignal := bufio.NewReader(os.Stdin)

	dependencies := publisherDependencies{
		connect:    client.Connect,
		disconnect: client.Disconnect,
		readSignal: func(expected string) error {
			return utility.ReadSignal(startSignal, expected)
		},
		writeSignal: func(signal string) error {
			return utility.WriteSignal(os.Stdout, signal)
		},
		runBenchmark: func(payloadIndex int, payloadSize int, run int, isWarmup bool) error {

			if !isWarmup {

				resultIndex := payloadIndex*config.Benchmark.Runs + run - config.Benchmark.WarmupRuns

				result, err := tls_json.RunPublishBenchmark(tls_json.TLSJSONPublisherInput{
					Client:       client,
					Config:       config,
					PayloadSize:  payloadSize,
					Measurements: results[resultIndex].Measurements,
					IsWarmup:     false,
				})
				if err != nil {
					return err
				}

				results[resultIndex] = result

				return nil
			}

			_, err := tls_json.RunPublishBenchmark(tls_json.TLSJSONPublisherInput{
				Client:      client,
				Config:      config,
				PayloadSize: payloadSize,
				IsWarmup:    true,
			})
			return err
		},

		writeResults: func() error {
			return csv.WritePublisherResults(results, config.Benchmark)
		},
	}

	return runPublisher(config.Benchmark, dependencies)
}

func runPublisher(config shared.BenchmarkConfig, dependencies publisherDependencies) error {

	if err := dependencies.connect(); err != nil {
		return err
	}

	for payloadIndex, payloadSize := range config.PayloadSizes {

		for run := 0; run < config.WarmupRuns+config.Runs; run++ {

			if err := dependencies.readSignal("GO"); err != nil {
				return err
			}

			isWarmup := run < config.WarmupRuns

			if err := dependencies.runBenchmark(payloadIndex, payloadSize, run, isWarmup); err != nil {
				return err
			}

			if err := dependencies.writeSignal("DONE"); err != nil {
				return err
			}
		}
	}

	if err := dependencies.readSignal("FINISH"); err != nil {
		return err
	}

	dependencies.disconnect()
	return dependencies.writeResults()
}
