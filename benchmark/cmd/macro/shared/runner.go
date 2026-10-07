package shared

import (
	"bufio"
	"encoding/csv"
	"io"
	"os"
	"strconv"
	"thesis/benchmark/macro"
	"thesis/internal/mqtt"
	"thesis/utility/golang/communication"
)

type publisherDependency struct {
	Connect      func() error
	Disconnect   func()
	ReadSignal   func(string) error
	WriteSignal  func(string) error
	RunBenchmark func(payloadSize int, measurements []macro.PublisherSample, isWarmup bool) (macro.PublisherSamples, error)
	WriteResults func([]macro.PublisherSamples) error
}

type subscriberDependency struct {
	Connect      func() error
	Disconnect   func()
	ReadSignal   func(string) error
	WriteSignal  func(string) error
	RunBenchmark func(measurements []macro.SubscriberSample, isWarmup bool) (macro.SubscriberSamples, error)
	WriteResults func([]macro.SubscriberSamples) error
}

func RunPublisher(config macro.MacroConfig, client mqtt.Client, scenario macro.PublisherScenario, input io.Reader, output io.Writer) error {

	signals := bufio.NewReader(input)

	dependencies := publisherDependency{
		Connect:    client.Connect,
		Disconnect: client.Disconnect,

		ReadSignal: func(signal string) error {
			return communication.ReadSignal(signals, signal)
		},

		WriteSignal: func(signal string) error {
			return communication.WriteSignal(output, signal)
		},

		RunBenchmark: func(payloadSize int, measurements []macro.PublisherSample, isWarmup bool) (macro.PublisherSamples, error) {

			return scenario.Run(macro.PublisherInput{
				Client:       client,
				Config:       config,
				PayloadSize:  payloadSize,
				Measurements: measurements,
				IsWarmup:     isWarmup,
			})
		},

		WriteResults: func(results []macro.PublisherSamples) error {
			return writePublisherResults(results, config.Benchmark)
		},
	}

	return runPublisher(config, dependencies)
}

func runPublisher(config macro.MacroConfig, dependencies publisherDependency) error {

	results := preparePublisherResults(config.Benchmark)

	if err := dependencies.Connect(); err != nil {
		return err
	}

	for payloadIndex, payloadSize := range config.Benchmark.PayloadSizes {

		for run := 0; run < config.Benchmark.WarmupRuns+config.Benchmark.Runs; run++ {

			if err := dependencies.ReadSignal("GO"); err != nil {
				return err
			}

			isWarmup := run < config.Benchmark.WarmupRuns

			if isWarmup {

				_, err := dependencies.RunBenchmark(payloadSize, nil, true)
				if err != nil {
					return err
				}

			} else {

				resultIndex := payloadIndex*config.Benchmark.Runs + run - config.Benchmark.WarmupRuns

				result, err := dependencies.RunBenchmark(payloadSize, results[resultIndex].Measurements, false)
				if err != nil {
					return err
				}

				results[resultIndex] = result
			}

			if err := dependencies.WriteSignal("DONE"); err != nil {
				return err
			}
		}
	}

	if err := dependencies.ReadSignal("FINISH"); err != nil {
		return err
	}

	dependencies.Disconnect()

	return dependencies.WriteResults(results)
}

func RunSubscriber(config macro.MacroConfig, client mqtt.Client, scenario macro.SubscriberScenario, input io.Reader, output io.Writer) error {

	signals := bufio.NewReader(input)

	dependencies := subscriberDependency{
		Connect:    client.Connect,
		Disconnect: client.Disconnect,

		ReadSignal: func(signal string) error {
			return communication.ReadSignal(signals, signal)
		},

		WriteSignal: func(signal string) error {
			return communication.WriteSignal(output, signal)
		},

		RunBenchmark: func(measurements []macro.SubscriberSample, isWarmup bool) (macro.SubscriberSamples, error) {

			return scenario.Run(macro.SubscriberInput{
				Client:       client,
				Config:       config,
				Measurements: measurements,
				IsWarmup:     isWarmup,
				IOWriter:     output,
			})
		},

		WriteResults: func(results []macro.SubscriberSamples) error {
			return writeSubscriberResults(results, config.Benchmark)
		},
	}

	return runSubscriber(config, dependencies)
}

func runSubscriber(config macro.MacroConfig, dependencies subscriberDependency) error {

	results := prepareSubscriberResults(config.Benchmark)

	if err := dependencies.Connect(); err != nil {
		return err
	}

	for payloadIndex := range config.Benchmark.PayloadSizes {

		for run := 0; run < config.Benchmark.WarmupRuns+config.Benchmark.Runs; run++ {

			if err := dependencies.ReadSignal("GO"); err != nil {
				return err
			}

			isWarmup := run < config.Benchmark.WarmupRuns

			if isWarmup {

				_, err := dependencies.RunBenchmark(nil, true)
				if err != nil {
					return err
				}

			} else {

				resultIndex := payloadIndex*config.Benchmark.Runs + run - config.Benchmark.WarmupRuns

				result, err := dependencies.RunBenchmark(results[resultIndex].Measurements, false)
				if err != nil {
					return err
				}

				results[resultIndex] = result
			}

			if err := dependencies.WriteSignal("DONE"); err != nil {
				return err
			}
		}
	}

	if err := dependencies.ReadSignal("FINISH"); err != nil {
		return err
	}

	dependencies.Disconnect()

	return dependencies.WriteResults(results)
}

func writePublisherResults(results []macro.PublisherSamples, config macro.BenchmarkConfig) error {

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
				strconv.Itoa(config.PayloadSizes[resultIndex/config.Runs]),
				strconv.Itoa(resultIndex%config.Runs + 1),
				measurement.MessageID.String(),
				strconv.FormatInt(measurement.StartTime, 10),
				strconv.FormatUint(result.Cycles, 10),
			})
		}
	}

	writer.Flush()

	return writer.Error()
}

func writeSubscriberResults(results []macro.SubscriberSamples, config macro.BenchmarkConfig) error {

	output, err := os.Create("subscriber.csv")
	if err != nil {
		return err
	}
	defer output.Close()

	writer := csv.NewWriter(output)

	writer.Write([]string{
		"payload_size",
		"repetition",
		"message_id",
		"subscriber_arrived_unix_ns",
		"subscriber_cycles",
	})

	for resultIndex, result := range results {

		for _, measurement := range result.Measurements {

			writer.Write([]string{
				strconv.Itoa(config.PayloadSizes[resultIndex/config.Runs]),
				strconv.Itoa(resultIndex%config.Runs + 1),
				measurement.MessageID.String(),
				strconv.FormatInt(measurement.EndTime, 10),
				strconv.FormatUint(result.Cycles, 10),
			})
		}
	}

	writer.Flush()

	return writer.Error()
}

func preparePublisherResults(config macro.BenchmarkConfig) []macro.PublisherSamples {

	results := make([]macro.PublisherSamples, len(config.PayloadSizes)*config.Runs)
	measurements := make([]macro.PublisherSample, len(config.PayloadSizes)*config.Runs*config.MessageCount)

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

func prepareSubscriberResults(config macro.BenchmarkConfig) []macro.SubscriberSamples {

	results := make([]macro.SubscriberSamples, len(config.PayloadSizes)*config.Runs)
	measurements := make([]macro.SubscriberSample, len(config.PayloadSizes)*config.Runs*config.MessageCount)

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

func touchMemory[T macro.PublisherSample | macro.SubscriberSample](measurements []T) {

	for index := range measurements {

		switch measurement := any(&measurements[index]).(type) {

		case *macro.PublisherSample:
			measurement.StartTime = -1

		case *macro.SubscriberSample:
			measurement.EndTime = -1
		}
	}
}
