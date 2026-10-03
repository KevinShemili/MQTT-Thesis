package full_schema

import (
	"thesis/utility/golang/parser"
)

type FullSchemaConfig struct {
	PayloadSizes     []int
	SymmetricKeySize int
	AttributeCount   int
	RSAKeyBits       int
}

func NewFullSchemaConfig() FullSchemaConfig {

	return FullSchemaConfig{
		PayloadSizes: parser.ParseIntListFromEnv(
			"FULL_SCHEMA_PAYLOAD_SIZES",
		),
		SymmetricKeySize: parser.ParseIntFromEnv(
			"SYMMETRIC_KEY_SIZE",
		),
		AttributeCount: parser.ParseIntFromEnv(
			"FULL_SCHEMA_ATTRIBUTE_COUNT",
		),
		RSAKeyBits: parser.ParseIntFromEnv(
			"FULL_SCHEMA_RSA_KEY_BITS",
		),
	}
}
