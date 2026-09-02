package shared

import "benchmark/utility"

type JSONCBORConfig struct {
	AttributeCounts []int
	PayloadSize     int
	AESKeySize      int
}

func NewJSONCBORConfig() JSONCBORConfig {

	return JSONCBORConfig{
		AttributeCounts: utility.ParseIntListFromEnv("JSON_CBOR_ATTRIBUTE_COUNTS"),
		PayloadSize:     utility.ParseIntFromEnv("JSON_CBOR_PAYLOAD_SIZE"),
		AESKeySize:      utility.ParseIntFromEnv("AES_ASCON_KEY_SIZE"),
	}
}
