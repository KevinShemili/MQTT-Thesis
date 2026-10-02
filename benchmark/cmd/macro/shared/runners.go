package cmdshared

import "thesis/benchmark/macro/shared"

func RunPublisher(config shared.BenchmarkConfig, dependencies PublisherDependencies) error {

	if err := dependencies.Connect(); err != nil {
		return err
	}

	for payloadIndex, payloadSize := range config.PayloadSizes {

		for run := 0; run < config.WarmupRuns+config.Runs; run++ {

			if err := dependencies.ReadSignal("GO"); err != nil {
				return err
			}

			isWarmup := run < config.WarmupRuns

			if err := dependencies.RunBenchmark(payloadIndex, payloadSize, run, isWarmup); err != nil {
				return err
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
	return dependencies.WriteResults()
}

func RunSubscriber(config shared.BenchmarkConfig, dependencies SubscriberDependencies) error {

	if err := dependencies.Connect(); err != nil {
		return err
	}

	for payloadIndex := range config.PayloadSizes {

		for run := 0; run < config.WarmupRuns+config.Runs; run++ {

			if err := dependencies.ReadSignal("GO"); err != nil {
				return err
			}

			isWarmup := run < config.WarmupRuns

			if err := dependencies.RunBenchmark(payloadIndex, run, isWarmup, func() error {
				return dependencies.WriteSignal("READY")
			},
			); err != nil {
				return err
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
	return dependencies.WriteResults()
}
