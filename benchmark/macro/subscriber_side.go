package macro

import (
	"fmt"
	"io"
	"time"

	"thesis/benchmark/macro/shared"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"

	"github.com/google/uuid"
)

func ExecuteSubscribeBenchmark(
	client mqtt.IClient,
	serializer serialization.ISerializer,
	config shared.ExperimentConfig,
	output io.Writer,
) error {
	if err := client.Connect(); err != nil {
		return err
	}
	defer client.Disconnect()

	completedMessageIDs := make(map[uuid.UUID]struct{}, config.MessageCount)

	duplicates := 0
	benchmarkResult := make(chan error, 1)

	err := client.Subscribe(config.Topic, func(delivery mqtt.MQTTDelivery) {

		var msg message.Message

		if err := serializer.Deserialize(delivery.Payload, &msg); err != nil {
			benchmarkResult <- fmt.Errorf(
				"deserialize received message: %w",
				err,
			)
			return
		}

		if err := message.ValidateMessage(msg, config.PayloadSize); err != nil {
			benchmarkResult <- fmt.Errorf(
				"validate message %s: %w",
				msg.ID,
				err,
			)
			return
		}

		if _, exists := completedMessageIDs[msg.ID]; exists {
			duplicates++

			fmt.Fprintf(
				output,
				"DUPLICATE message_id=%s mqtt_duplicate=%t\n",
				msg.ID,
				delivery.Duplicate,
			)

			return
		}

		completedAt := time.Now()

		completedMessageIDs[msg.ID] = struct{}{}

		fmt.Fprintf(
			output,
			"DELIVERED message_id=%s subscriber_completed_unix_ns=%d\n",
			msg.ID,
			completedAt.UnixNano(),
		)

		if len(completedMessageIDs) == config.MessageCount {
			benchmarkResult <- nil
		}
	},
	)
	if err != nil {
		return err
	}

	fmt.Fprintln(output, "READY role=subscriber")

	if err := <-benchmarkResult; err != nil {
		return err
	}

	fmt.Fprintf(
		output,
		"SUMMARY role=subscriber completed=%d duplicates=%d\n",
		len(completedMessageIDs),
		duplicates,
	)

	return nil
}
