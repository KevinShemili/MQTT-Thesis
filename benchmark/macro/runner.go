package macro

import (
	"fmt"
	"thesis/benchmark/cpu"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/utility/golang/communication"
	"time"

	"github.com/google/uuid"
)

type PublisherSample struct {
	MessageID uuid.UUID
	StartTime int64
}

type PublisherSamples struct {
	Measurements []PublisherSample
	Cycles       uint64
}

type SubscriberSample struct {
	MessageID uuid.UUID
	EndTime   int64
}

type SubscriberSamples struct {
	Measurements []SubscriberSample
	Cycles       uint64
}

type publisherDependency struct {
	NewCPU          func() (cpu.CPU, error)
	PublishMessages func() error
}

type subscriberDependency struct {
	NewCPU       func() (cpu.CPU, error)
	Subscribe    func() error
	WriteReady   func() error
	WaitMessages func() error
}

func BenchmarkSubscriber(input SubscriberInput, scenario SubscriberScenario, newCPU func() (cpu.CPU, error)) (SubscriberSamples, error) {

	messageIndex := 0
	benchmarkResult := make(chan error, 1)

	dependencies := subscriberDependency{
		NewCPU: newCPU,

		Subscribe: func() error {

			return input.Client.Subscribe(input.Config.Benchmark.Topic, func(delivery mqtt.MQTTDelivery) {

				msg, err := scenario.ConsumeMessage(delivery)
				if err != nil {
					benchmarkResult <- err
					return
				}

				if !input.IsWarmup {
					input.Measurements[messageIndex] = SubscriberSample{
						MessageID: msg.ID,
						EndTime:   time.Now().UnixNano(),
					}
				}

				messageIndex++

				if messageIndex == input.Config.Benchmark.MessageCount {
					benchmarkResult <- nil
				}
			},
			)
		},

		WriteReady: func() error {
			return communication.WriteSignal(input.IOWriter, "READY")
		},

		WaitMessages: func() error {
			return <-benchmarkResult
		},
	}

	return benchmarkSubscriber(input, dependencies)
}

func BenchmarkPublisher(input PublisherInput, scenario PublisherScenario, newCPU func() (cpu.CPU, error)) (PublisherSamples, error) {

	messages := message.BuildMessages(input.Config.Benchmark.MessageCount, input.PayloadSize)
	publishTokens := make([]mqtt.PublishToken, input.Config.Benchmark.MessageCount)

	dependencies := publisherDependency{
		NewCPU: newCPU,

		PublishMessages: func() error {

			for messageIndex := range input.Config.Benchmark.MessageCount {

				time.Sleep(input.Config.Benchmark.PublishInterval)

				msg := messages[messageIndex]

				if input.IsWarmup {

					publishToken, err := scenario.PublishMessage(input, msg)
					if err != nil {
						return err
					}

					publishTokens[messageIndex] = publishToken
					continue
				}

				startTime := time.Now().UnixNano()

				publishToken, err := scenario.PublishMessage(input, msg)
				if err != nil {
					return err
				}

				publishTokens[messageIndex] = publishToken

				input.Measurements[messageIndex] = PublisherSample{
					MessageID: msg.ID,
					StartTime: startTime,
				}
			}

			for messageIndex, publishToken := range publishTokens {

				publishToken.Wait()

				if err := publishToken.Error(); err != nil {
					return fmt.Errorf("publish message %s: %w", messages[messageIndex].ID, err)
				}
			}

			return nil
		},
	}

	return benchmarkPublisher(input, dependencies)
}

func benchmarkPublisher(input PublisherInput, dependencies publisherDependency) (PublisherSamples, error) {

	if input.IsWarmup {

		if err := dependencies.PublishMessages(); err != nil {
			return PublisherSamples{}, err
		}

		return PublisherSamples{}, nil
	}

	measurement, err := dependencies.NewCPU()
	if err != nil {
		return PublisherSamples{}, err
	}

	if err := measurement.Enable(); err != nil {
		measurement.Abort()
		return PublisherSamples{}, err
	}

	if err := dependencies.PublishMessages(); err != nil {
		measurement.Abort()
		return PublisherSamples{}, err
	}

	cycles, err := measurement.Stop()
	if err != nil {
		return PublisherSamples{}, err
	}

	return PublisherSamples{
		Measurements: input.Measurements,
		Cycles:       cycles,
	}, nil
}

func benchmarkSubscriber(input SubscriberInput, dependencies subscriberDependency) (SubscriberSamples, error) {

	if input.IsWarmup {

		if err := dependencies.Subscribe(); err != nil {
			return SubscriberSamples{}, err
		}

		if err := dependencies.WriteReady(); err != nil {
			return SubscriberSamples{}, err
		}

		if err := dependencies.WaitMessages(); err != nil {
			return SubscriberSamples{}, err
		}

		return SubscriberSamples{}, nil
	}

	measurement, err := dependencies.NewCPU()
	if err != nil {
		return SubscriberSamples{}, err
	}

	if err := dependencies.Subscribe(); err != nil {
		measurement.Abort()
		return SubscriberSamples{}, err
	}

	if err := measurement.Enable(); err != nil {
		measurement.Abort()
		return SubscriberSamples{}, err
	}

	if err := dependencies.WriteReady(); err != nil {
		measurement.Abort()
		return SubscriberSamples{}, err
	}

	if err := dependencies.WaitMessages(); err != nil {
		measurement.Abort()
		return SubscriberSamples{}, err
	}

	cycles, err := measurement.Stop()
	if err != nil {
		return SubscriberSamples{}, err
	}

	return SubscriberSamples{
		Measurements: input.Measurements,
		Cycles:       cycles,
	}, nil
}
