package json_cbor

import (
	"fmt"
	"testing"
	"thesis/benchmark/micro/json_cbor/shared"
	"thesis/benchmark/thermal"
	"thesis/benchmark/utility"
	"thesis/internal/message"
	"thesis/internal/serialization"
	"time"
)

var (
	warmupDuration = time.Duration(utility.ParseIntFromEnv("WARMUP_DURATION")) * time.Second
	tailDuration   = time.Duration(utility.ParseIntFromEnv("TAIL_DURATION")) * time.Second
)

func BenchmarkMessageEnergySerialize(benchmark *testing.B) {
	config := shared.NewJSONCBORConfig()

	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	for _, payloadSize := range config.PayloadSizes {

		// JSON Serialization
		benchmark.Run(fmt.Sprintf("JSON/%dB", payloadSize), func(b *testing.B) {

			msg := message.NewMessage(payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()
			fmt.Println("ENRG-START")

			warmupDeadline := time.Now().Add(warmupDuration)

			for time.Now().Before(warmupDeadline) {
				jsonSerializer.Serialize(msg)
			}
			for b.Loop() {
				jsonSerializer.Serialize(msg)
			}
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				jsonSerializer.Serialize(msg)
			}

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

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()
			fmt.Println("ENRG-START")

			warmupDeadline := time.Now().Add(warmupDuration)

			for time.Now().Before(warmupDeadline) {
				cborSerializer.Serialize(msg)
			}
			for b.Loop() {
				cborSerializer.Serialize(msg)
			}
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				cborSerializer.Serialize(msg)
			}

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

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()
			fmt.Println("ENRG-START")

			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				cborSerializer.Serialize(msg)
			}
			for b.Loop() {
				cborSerializer.Serialize(msg)
			}
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				cborSerializer.Serialize(msg)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}

func BenchmarkMessageEnergyDeserialize(benchmark *testing.B) {
	config := shared.NewJSONCBORConfig()

	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	for _, payloadSize := range config.PayloadSizes {

		// JSON Deserialization
		benchmark.Run(fmt.Sprintf("JSON/%dB", payloadSize), func(b *testing.B) {

			msg := message.NewMessage(payloadSize)

			serializedMessage, _ := jsonSerializer.Serialize(msg)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()
			fmt.Println("ENRG-START")

			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				var decoded message.Message
				jsonSerializer.Deserialize(serializedMessage, &decoded)
			}
			for b.Loop() {
				var decoded message.Message
				jsonSerializer.Deserialize(serializedMessage, &decoded)
			}
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
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
			fmt.Println("ENRG-START")

			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				var decoded message.Message
				cborSerializer.Deserialize(serializedMessage, &decoded)
			}
			for b.Loop() {
				var decoded message.Message
				cborSerializer.Deserialize(serializedMessage, &decoded)
			}
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
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
		benchmark.Run(fmt.Sprintf("CBORKeyAsInt/%dB", payloadSize), func(b *testing.B) {
			msg := message.NewMessageIntKeys(payloadSize)

			serializedMessage, _ := cborSerializer.Serialize(msg)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()
			fmt.Println("ENRG-START")

			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				var decoded message.MessageIntKeys
				cborSerializer.Deserialize(serializedMessage, &decoded)
			}
			for b.Loop() {
				var decoded message.MessageIntKeys
				cborSerializer.Deserialize(serializedMessage, &decoded)
			}
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
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
