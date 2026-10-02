package main

import (
	"thesis/benchmark/cache"
	"thesis/benchmark/cmd/provision/shared"
	"thesis/benchmark/macro/shared"
	"thesis/benchmark/utility"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
)

func main() {
	config := shared.NewCryptographyConfig()

	dependencies := cmdshared.ProvisionDependencies{
		GenerateRandomBytes: utility.GenerateRandomBytes,
		Store:               cache.Store,
	}

	runProvision(config, dependencies)
}

func runProvision(config shared.CryptographyConfig, dependencies cmdshared.ProvisionDependencies) {
	dependencies.Store(shared.AESKeyFileName, dependencies.GenerateRandomBytes(config.SymmetricKeySize))
	dependencies.Store(shared.ASCONKeyFileName, dependencies.GenerateRandomBytes(config.SymmetricKeySize))

	rsaScheme := rsa.NewRSA(config.RSAKeyBits)
	dependencies.Store(shared.RSAPublicKeyFileName, rsaScheme.PublicKeyBytes())
	dependencies.Store(shared.RSAPrivateKeyFileName, rsaScheme.PrivateKeyBytes())

	authority := cpabe.NewAuthority()
	dependencies.Store(shared.CPABEPublicKeyFileName, authority.PublicKeyBytes())

	_, attributes := cpabe.BuildSyntheticPolicyAndAttributes(config.AttributeCount)
	dependencies.Store(shared.CPABEPrivateKeyFileName, authority.IssuePrivateKey(attributes).Bytes())
}
