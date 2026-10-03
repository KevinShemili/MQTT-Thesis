package main

import (
	"thesis/benchmark/cmd/provision"
	"thesis/benchmark/macro"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
	"thesis/utility/golang/cache"
	"thesis/utility/golang/generator"
)

func main() {
	config := macro.NewCryptographyConfig()

	dependencies := provision.Dependency{
		GenerateRandomBytes: generator.GenerateRandomBytes,
		Store:               cache.Store,
	}

	runProvision(config, dependencies)
}

func runProvision(config macro.CryptographyConfig, dependencies provision.Dependency) {
	dependencies.Store(cache.AESKeyFileName, dependencies.GenerateRandomBytes(config.SymmetricKeySize))
	dependencies.Store(cache.ASCONKeyFileName, dependencies.GenerateRandomBytes(config.SymmetricKeySize))

	rsaScheme := rsa.NewRSA(config.RSAKeyBits)
	dependencies.Store(cache.RSAPublicKeyFileName, rsaScheme.PublicKeyBytes())
	dependencies.Store(cache.RSAPrivateKeyFileName, rsaScheme.PrivateKeyBytes())

	authority := cpabe.NewAuthority()
	dependencies.Store(cache.CPABEPublicKeyFileName, authority.PublicKeyBytes())

	_, attributes := cpabe.BuildSyntheticPolicyAndAttributes(config.AttributeCount)
	dependencies.Store(cache.CPABEPrivateKeyFileName, authority.IssuePrivateKey(attributes).Bytes())
}
