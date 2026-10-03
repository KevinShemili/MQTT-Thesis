package aes_ascon

import (
	"thesis/utility/golang/parser"
)

type AESASCONConfig struct {
	PayloadSizes []int
	AESKeySize   int
	ASCONKeySize int
}

func NewAESASCONConfig() AESASCONConfig {

	return AESASCONConfig{
		PayloadSizes: parser.ParseIntListFromEnv("PAYLOAD_SIZES"),
		AESKeySize:   parser.ParseIntFromEnv("SYMMETRIC_KEY_SIZE"),
		ASCONKeySize: parser.ParseIntFromEnv("SYMMETRIC_KEY_SIZE"),
	}
}
