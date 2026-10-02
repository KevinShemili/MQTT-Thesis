package main

import (
	"flag"
	"os"
	"thesis/benchmark/thermal"
	"thesis/internal/message"
	"thesis/internal/serialization"
	"time"
)

func main() {

	algorithm := flag.String("algorithm", "", "")
	operation := flag.String("operation", "", "")
	duration := flag.Duration("duration", 0, "")
	payloadSize := flag.Int("payload-size", 0, "")

	flag.Parse()

	var throttled bool

	switch {
	case *algorithm == "JSON" && *operation == "Serialize":
		throttled = serializeJSON(*payloadSize, *duration)
	case *algorithm == "CBOR" && *operation == "Serialize":
		throttled = serializeCBOR(*payloadSize, *duration)
	case *algorithm == "CBORKeyAsInt" && *operation == "Serialize":
		throttled = serializeCBORKeyAsInt(*payloadSize, *duration)
	case *algorithm == "JSON" && *operation == "Deserialize":
		throttled = deserializeJSON(*payloadSize, *duration)
	case *algorithm == "CBOR" && *operation == "Deserialize":
		throttled = deserializeCBOR(*payloadSize, *duration)
	case *algorithm == "CBORKeyAsInt" && *operation == "Deserialize":
		throttled = deserializeCBORKeyAsInt(*payloadSize, *duration)
	default:
		panic("Unknown energy case")
	}

	if throttled {
		os.Exit(3)
	}
}

func serializeJSON(payloadSize int, duration time.Duration) bool {

	jsonSerializer := serialization.JSONSerializer{}

	msg := message.NewMessage(payloadSize)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		jsonSerializer.Serialize(msg)
	}

	return throttle.IsThrottled()
}

func serializeCBOR(payloadSize int, duration time.Duration) bool {

	cborSerializer := serialization.CBORSerializer{}

	msg := message.NewMessage(payloadSize)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		cborSerializer.Serialize(msg)
	}

	return throttle.IsThrottled()
}

func serializeCBORKeyAsInt(payloadSize int, duration time.Duration) bool {

	cborSerializer := serialization.CBORSerializer{}

	msg := message.NewMessageIntKeys(payloadSize)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		cborSerializer.Serialize(msg)
	}

	return throttle.IsThrottled()
}

func deserializeJSON(payloadSize int, duration time.Duration) bool {

	jsonSerializer := serialization.JSONSerializer{}

	msg := message.NewMessage(payloadSize)

	serializedMessage, _ := jsonSerializer.Serialize(msg)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		var decoded message.Message
		jsonSerializer.Deserialize(serializedMessage, &decoded)
	}

	return throttle.IsThrottled()
}

func deserializeCBOR(payloadSize int, duration time.Duration) bool {

	cborSerializer := serialization.CBORSerializer{}

	msg := message.NewMessage(payloadSize)
	serializedMessage, _ := cborSerializer.Serialize(msg)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		var decoded message.Message
		cborSerializer.Deserialize(serializedMessage, &decoded)
	}

	return throttle.IsThrottled()
}

func deserializeCBORKeyAsInt(payloadSize int, duration time.Duration) bool {

	cborSerializer := serialization.CBORSerializer{}

	msg := message.NewMessageIntKeys(payloadSize)

	serializedMessage, _ := cborSerializer.Serialize(msg)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		var decoded message.MessageIntKeys
		cborSerializer.Deserialize(serializedMessage, &decoded)
	}

	return throttle.IsThrottled()
}
