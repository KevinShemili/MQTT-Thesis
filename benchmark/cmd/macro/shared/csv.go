package shared

import (
	"encoding/csv"
	"os"
	"strconv"
	"thesis/benchmark/macro"
)

func WritePublisherResults(results []macro.PublisherResult, config macro.BenchmarkConfig) error {

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

func WriteSubscriberResults(results []macro.SubscriberResult, config macro.BenchmarkConfig) error {

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
