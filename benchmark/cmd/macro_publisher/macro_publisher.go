package main

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"os"
	"strconv"

	"thesis/benchmark/macro/baseline"
	"thesis/benchmark/macro/shared"
	"thesis/benchmark/utility"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
)

type publisherDependencies struct {
	connect      func() error
	disconnect   func()
	readSignal   func(string) error
	writeSignal  func(string) error
	runBenchmark func(payloadIndex int, payloadSize int, run int, isCPUMeasured bool) error
	writeResults func() error
}

func main() {

	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}
}

func run() error {

	config := shared.NewExperimentConfig()
	mqttConfig := shared.NewMQTTConfig()
	runs := utility.ParseIntFromEnv("MACRO_RUNS")
	warmupRuns := utility.ParseIntFromEnv("MACRO_WARMUP_RUNS")

	tlsConfig, err := mqtt.NewTLSConfig(mqttConfig.CACertificate, mqttConfig.BrokerURL)
	if err != nil {
		return err
	}

	client := mqtt.NewClient(mqtt.ClientConfig{
		BrokerURL: mqttConfig.BrokerURL,
		ClientID:  mqttConfig.PublisherClientID,
		Username:  mqttConfig.PublisherUsername,
		Password:  mqttConfig.PublisherPassword,
		TLSConfig: tlsConfig,
	})

	results := make([]baseline.PublisherResult, len(config.PayloadSizes)*runs)
	measurements := make([]baseline.PublisherMeasurement, len(config.PayloadSizes)*runs*config.MessageCount)
	warmupMeasurements := make([]baseline.PublisherMeasurement, config.MessageCount)

	// Touch memory once
	touchMemory(measurements)

	// Assign the pre-allocated memory to results
	for run := range results {
		start := run * config.MessageCount
		end := start + config.MessageCount
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
		runBenchmark: func(payloadIndex int, payloadSize int, run int, isCPUMeasured bool) error {

			if isCPUMeasured {

				resultIndex := payloadIndex*runs + run - warmupRuns

				result, err := baseline.RunPublishBenchmark(client, serialization.JSONSerializer{}, config,
					payloadSize, results[resultIndex].Measurements, true)
				if err != nil {
					return err
				}

				results[resultIndex] = result

				return nil
			}

			_, err := baseline.RunPublishBenchmark(client, serialization.JSONSerializer{}, config,
				payloadSize, warmupMeasurements, false)
			return err
		},

		writeResults: func() error {
			return writeResults(results, config.PayloadSizes, runs)
		},
	}

	return runPublisher(config.PayloadSizes, runs, warmupRuns, dependencies)
}

func runPublisher(payloadSizes []int, runs int, warmupRuns int, dependencies publisherDependencies) error {

	if err := dependencies.connect(); err != nil {
		return err
	}

	for payloadIndex, payloadSize := range payloadSizes {

		for run := 0; run < warmupRuns+runs; run++ {

			if err := dependencies.readSignal("GO"); err != nil {
				return err
			}

			isCPUMeasured := run >= warmupRuns

			if err := dependencies.runBenchmark(payloadIndex, payloadSize, run, isCPUMeasured); err != nil {
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

func writeResults(results []baseline.PublisherResult, payloadSizes []int, runs int) error {

	output, err := os.Create("publisher.csv")
	if err != nil {
		return err
	}
	defer output.Close()

	writer := csv.NewWriter(output)

	writer.Write([]string{
		"payload_size",
		"repetition",
		"message_id",
		"publisher_started_unix_ns",
		"publisher_cycles",
	})

	for resultIndex, result := range results {

		for _, measurement := range result.Measurements {

			writer.Write([]string{
				strconv.Itoa(payloadSizes[resultIndex/runs]),
				strconv.Itoa(resultIndex%runs + 1),
				measurement.MessageID.String(),
				strconv.FormatInt(measurement.StartTime, 10),
				strconv.FormatUint(result.Cycles, 10),
			})
		}
	}

	writer.Flush()

	return writer.Error()
}

func touchMemory(measurements []baseline.PublisherMeasurement) {

	for index := range measurements {
		measurements[index].StartTime = -1
	}
}
