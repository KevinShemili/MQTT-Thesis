package shared

import "benchmark/utility"

type AESASCONConfig struct {
	PayloadSizes []int
	AESKeySize   int
	ASCONKeySize int
}

func NewAESASCONConfig() AESASCONConfig {

	return AESASCONConfig{
		PayloadSizes: utility.ParseIntListFromEnv("AES_ASCON_PAYLOAD_SIZES"),
		AESKeySize:   utility.ParseIntFromEnv("AES_ASCON_KEY_SIZE"),
		ASCONKeySize: utility.ParseIntFromEnv("AES_ASCON_KEY_SIZE"),
	}
}
