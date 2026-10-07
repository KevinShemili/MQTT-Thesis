package macro

import (
	"io"
	"thesis/internal/message"
	"thesis/internal/mqtt"
)

type PublisherInput struct {
	Client       mqtt.Client
	Config       MacroConfig
	PayloadSize  int
	Measurements []PublisherSample
	IsWarmup     bool
}

type SubscriberInput struct {
	Client       mqtt.Client
	Config       MacroConfig
	Measurements []SubscriberSample
	IsWarmup     bool
	IOWriter     io.Writer
}

type SubscriberScenario interface {
	Run(input SubscriberInput) (SubscriberSamples, error)
	ConsumeMessage(delivery mqtt.MQTTDelivery) (message.Message, error)
}

type PublisherScenario interface {
	Run(input PublisherInput) (PublisherSamples, error)
	PublishMessage(input PublisherInput, msg message.Message) (mqtt.PublishToken, error)
}
