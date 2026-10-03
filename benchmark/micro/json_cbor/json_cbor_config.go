package json_cbor

import "thesis/utility/golang/parser"

type JSONCBORConfig struct {
	PayloadSizes []int
}

func NewJSONCBORConfig() JSONCBORConfig {

	return JSONCBORConfig{
		PayloadSizes: parser.ParseIntListFromEnv("PAYLOAD_SIZES"),
	}
}
