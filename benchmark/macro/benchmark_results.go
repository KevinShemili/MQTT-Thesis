package macro

import "github.com/google/uuid"

type PublisherMeasurement struct {
	MessageID uuid.UUID
	StartTime int64
}

type PublisherResult struct {
	Measurements []PublisherMeasurement
	Cycles       uint64
}

type SubscriberMeasurement struct {
	MessageID uuid.UUID
	EndTime   int64
}

type SubscriberResult struct {
	Measurements []SubscriberMeasurement
	Cycles       uint64
}
