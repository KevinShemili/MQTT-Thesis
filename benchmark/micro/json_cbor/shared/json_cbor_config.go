package shared

import "thesis/benchmark/utility"

type JSONCBORConfig struct {
	PayloadSizes []int
}

func NewJSONCBORConfig() JSONCBORConfig {

	return JSONCBORConfig{
		PayloadSizes: utility.ParseIntListFromEnv("PAYLOAD_SIZES"),
	}
}
