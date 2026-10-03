package json_cbor

import (
	"fmt"
	"testing"
	"thesis/benchmark/thermal"
	"thesis/internal/message"
	"thesis/internal/serialization"
)

func BenchmarkMessageSerialize(benchmark *testing.B) {

	config := NewJSONCBORConfig()

	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	for _, payloadSize := range config.PayloadSizes {

		// JSON Serialization
		benchmark.Run(fmt.Sprintf("JSON/%dB", payloadSize), func(b *testing.B) {

			msg := message.NewMessage(payloadSize)

			serializedMessage, _ := jsonSerializer.Serialize(msg)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				jsonSerializer.Serialize(msg)
			}

			b.ReportMetric(float64(len(serializedMessage)), "serialized_bytes")
			b.ReportMetric(float64(len(msg.ID)+len(msg.Payload)), "raw_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		// CBOR Serialization
		benchmark.Run(fmt.Sprintf("CBOR/%dB", payloadSize), func(b *testing.B) {

			msg := message.NewMessage(payloadSize)

			serializedMessage, _ := cborSerializer.Serialize(msg)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				cborSerializer.Serialize(msg)
			}

			b.ReportMetric(float64(len(serializedMessage)), "serialized_bytes")
			b.ReportMetric(float64(len(msg.ID)+len(msg.Payload)), "raw_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		// CBOR Serialization with Integer Keys
		benchmark.Run(fmt.Sprintf("CBORKeyAsInt/%dB", payloadSize), func(b *testing.B) {

			msg := message.NewMessageIntKeys(payloadSize)

			serializedMessage, _ := cborSerializer.Serialize(msg)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				cborSerializer.Serialize(msg)
			}

			b.ReportMetric(float64(len(serializedMessage)), "serialized_bytes")
			b.ReportMetric(float64(len(msg.ID)+len(msg.Payload)), "raw_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}

func BenchmarkMessageDeserialize(benchmark *testing.B) {

	config := NewJSONCBORConfig()

	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	for _, payloadSize := range config.PayloadSizes {

		// JSON Deserialization
		benchmark.Run(fmt.Sprintf("JSON/%dB", payloadSize), func(b *testing.B) {

			msg := message.NewMessage(payloadSize)
			serializedMessage, _ := jsonSerializer.Serialize(msg)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var decoded message.Message
				jsonSerializer.Deserialize(serializedMessage, &decoded)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		// CBOR Deserialization
		benchmark.Run(fmt.Sprintf("CBOR/%dB", payloadSize), func(b *testing.B) {

			msg := message.NewMessage(payloadSize)
			serializedMessage, _ := cborSerializer.Serialize(msg)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var decoded message.Message
				cborSerializer.Deserialize(serializedMessage, &decoded)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		// CBOR Deserialization with Integer Keys
		benchmark.Run(fmt.Sprintf("CBORKeyAsInt/%dB", payloadSize), func(b *testing.B) {
			msg := message.NewMessageIntKeys(payloadSize)

			serializedMessage, _ := cborSerializer.Serialize(msg)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var decoded message.MessageIntKeys
				cborSerializer.Deserialize(serializedMessage, &decoded)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}
