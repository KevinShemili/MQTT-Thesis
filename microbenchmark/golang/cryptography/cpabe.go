package cryptography

import (
	"crypto/rand"
	"fmt"

	"github.com/cloudflare/circl/abe/cpabe/tkn20"
)

type CPABE struct {
	PublicKey  tkn20.PublicKey
	PrivateKey tkn20.SystemSecretKey
}

// Mimics authority setup phase
func NewCPABE() CPABE {

	publicKey, privateKey, err := tkn20.Setup(rand.Reader)
	if err != nil {
		panic(err)
	}

	return CPABE{PublicKey: publicKey, PrivateKey: privateKey}
}

// Encrypt a key under a given policy
func (cpAbe CPABE) Encrypt(policy tkn20.Policy, msg []byte) []byte {

	abeCiphertext, err := cpAbe.PublicKey.Encrypt(rand.Reader, policy, msg)
	if err != nil {
		panic(err)
	}

	return abeCiphertext
}

// Creates AND only policy
func BuildSyntheticConjunctivePolicy(attributeCount int) tkn20.Policy {

	policyString := ""

	for index := range attributeCount {

		// Create a synthetic policy like (attr0: val0) and (attr1: val1) and ...
		var clause string = fmt.Sprintf("(attr%d: val%d)", index, index)

		if index == 0 {
			policyString = clause
		} else {
			policyString += " and " + clause
		}
	}

	var policy tkn20.Policy
	err := policy.FromString(policyString)
	if err != nil {
		panic(err)
	}

	return policy
}
