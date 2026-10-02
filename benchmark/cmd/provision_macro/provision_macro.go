package main

import (
	"thesis/benchmark/cache"
	"thesis/benchmark/macro/shared"
	"thesis/benchmark/utility"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
)

type provisionDependencies struct {
	generateRandomBytes func(int) []byte
	store               func(string, []byte)
}

func main() {
	config := shared.NewCryptographyConfig()

	dependencies := provisionDependencies{
		generateRandomBytes: utility.GenerateRandomBytes,
		store:               cache.Store,
	}

	runProvision(config, dependencies)
}

func runProvision(config shared.CryptographyConfig, dependencies provisionDependencies) {
	dependencies.store(shared.AESKeyFileName, dependencies.generateRandomBytes(config.SymmetricKeySize))
	dependencies.store(shared.ASCONKeyFileName, dependencies.generateRandomBytes(config.SymmetricKeySize))

	rsaScheme := rsa.NewRSA(config.RSAKeyBits)
	dependencies.store(shared.RSAPublicKeyFileName, rsaScheme.PublicKeyBytes())
	dependencies.store(shared.RSAPrivateKeyFileName, rsaScheme.PrivateKeyBytes())

	authority := cpabe.NewAuthority()
	dependencies.store(shared.CPABEPublicKeyFileName, authority.PublicKeyBytes())

	_, attributes := cpabe.BuildSyntheticPolicyAndAttributes(config.AttributeCount)
	dependencies.store(shared.CPABEPrivateKeyFileName, authority.IssuePrivateKey(attributes).Bytes())
}
