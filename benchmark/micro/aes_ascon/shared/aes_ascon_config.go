package shared

import "thesis/benchmark/utility"

type AESASCONConfig struct {
	PayloadSizes []int
	AESKeySize   int
	ASCONKeySize int
}

func NewAESASCONConfig() AESASCONConfig {

	return AESASCONConfig{
		PayloadSizes: utility.ParseIntListFromEnv("PAYLOAD_SIZES"),
		AESKeySize:   utility.ParseIntFromEnv("SYMMETRIC_KEY_SIZE"),
		ASCONKeySize: utility.ParseIntFromEnv("SYMMETRIC_KEY_SIZE"),
	}
}
