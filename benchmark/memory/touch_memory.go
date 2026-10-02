package memory

import "thesis/benchmark/macro/shared"

func TouchMemory[T shared.PublisherMeasurement | shared.SubscriberMeasurement](measurements []T) {

	for index := range measurements {

		switch measurement := any(&measurements[index]).(type) {

		case *shared.PublisherMeasurement:
			measurement.StartTime = -1

		case *shared.SubscriberMeasurement:
			measurement.EndTime = -1
		}
	}
}
