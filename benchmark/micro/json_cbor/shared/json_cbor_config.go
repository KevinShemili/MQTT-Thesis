package shared

import "benchmark/utility"

const fixedCPABEAttributeCount = 1

type JSONCBORConfig struct {
	PayloadSizes        []int
	AESKeySize          int
	CPABEAttributeCount int
}

func NewJSONCBORConfig() JSONCBORConfig {

	return JSONCBORConfig{
		PayloadSizes:        utility.ParseIntListFromEnv("PAYLOAD_SIZES"),
		CPABEAttributeCount: fixedCPABEAttributeCount,
		AESKeySize:          utility.ParseIntFromEnv("AES_ASCON_KEY_SIZE"),
	}
}
