package macro

import (
	"fmt"
	"io"
	"time"

	"thesis/benchmark/macro/shared"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
)

func ExecutePublishBenchmark(
	client mqtt.IClient,
	serializer serialization.ISerializer,
	config shared.ExperimentConfig,
	output io.Writer,
) error {
	if err := client.Connect(); err != nil {
		return err
	}
	defer client.Disconnect()

	publishedMessages := 0
	var lastReleaseTime time.Time

	for range config.MessageCount {
		msg := message.NewMessage(config.PayloadSize)

		if !lastReleaseTime.IsZero() {
			time.Sleep(
				time.Until(lastReleaseTime.Add(config.PublishInterval)),
			)
		}

		releaseTime := time.Now()

		serializedMessage, err := serializer.Serialize(msg)
		if err != nil {
			return fmt.Errorf("serialize message %s: %w", msg.ID, err)
		}

		client.Publish(config.Topic, serializedMessage)
		publishedMessages++

		lastReleaseTime = releaseTime

		fmt.Fprintf(
			output,
			"PUBLISHED message_id=%s publisher_started_unix_ns=%d\n",
			msg.ID,
			releaseTime.UnixNano(),
		)
	}

	fmt.Fprintf(
		output,
		"SUMMARY role=publisher published=%d\n",
		publishedMessages,
	)

	return nil
}
