package shared

import "thesis/benchmark/utility"

type FullSchemaConfig struct {
	PayloadSizes     []int
	SymmetricKeySize int
	AttributeCount   int
	RSAKeyBits       int
}

func LoadFullSchemaConfig() FullSchemaConfig {

	return FullSchemaConfig{
		PayloadSizes: utility.ParseIntListFromEnv(
			"FULL_SCHEMA_PAYLOAD_SIZES",
		),
		SymmetricKeySize: utility.ParseIntFromEnv(
			"SYMMETRIC_KEY_SIZE",
		),
		AttributeCount: utility.ParseIntFromEnv(
			"FULL_SCHEMA_ATTRIBUTE_COUNT",
		),
		RSAKeyBits: utility.ParseIntFromEnv(
			"FULL_SCHEMA_RSA_KEY_BITS",
		),
	}
}
