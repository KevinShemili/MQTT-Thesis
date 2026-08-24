package cpabe

import (
	"crypto/rand"
	"fmt"

	"github.com/cloudflare/circl/abe/cpabe/tkn20"
)

type CPABEAuthority struct {
	PublicKey       tkn20.PublicKey
	SystemSecretKey tkn20.SystemSecretKey
}

// Ctor Authority
func NewCPABEAuthority() CPABEAuthority {

	publicKey, systemSecretKey, err := tkn20.Setup(rand.Reader)
	if err != nil {
		panic(err)
	}

	return CPABEAuthority{PublicKey: publicKey, SystemSecretKey: systemSecretKey}
}

// Encrypt a key under a given policy
func (authority CPABEAuthority) Encrypt(policy tkn20.Policy, plaintext []byte) []byte {

	ciphertext, err := authority.PublicKey.Encrypt(rand.Reader, policy, plaintext)
	if err != nil {
		panic(err)
	}

	return ciphertext
}

// Issues a private key to a subscriber for given an attribute set
func (authority CPABEAuthority) IssuePrivateKey(attributes tkn20.Attributes) CPABESubscriber {

	privateKey, err := authority.SystemSecretKey.KeyGen(rand.Reader, attributes)
	if err != nil {
		panic(err)
	}

	return CPABESubscriber{PrivateKey: privateKey}
}

func MarshalCPABEPublicKey(publicKey tkn20.PublicKey) []byte {

	keyBytes, err := publicKey.MarshalBinary()
	if err != nil {
		panic(err)
	}

	return keyBytes
}

func UnmarshalCPABEPublicKey(keyBytes []byte) CPABEAuthority {

	var publicKey tkn20.PublicKey

	if err := publicKey.UnmarshalBinary(keyBytes); err != nil {
		panic(err)
	}

	return CPABEAuthority{PublicKey: publicKey}
}

func MarshalCPABEMasterSecret(systemSecretKey tkn20.SystemSecretKey) []byte {

	secretBytes, err := systemSecretKey.MarshalBinary()
	if err != nil {
		panic(err)
	}

	return secretBytes
}

func UnmarshalCPABEAuthority(publicKeyBytes []byte, masterSecretBytes []byte) CPABEAuthority {

	var systemSecretKey tkn20.SystemSecretKey

	if err := systemSecretKey.UnmarshalBinary(masterSecretBytes); err != nil {
		panic(err)
	}

	return CPABEAuthority{
		PublicKey:       UnmarshalCPABEPublicKey(publicKeyBytes).PublicKey,
		SystemSecretKey: systemSecretKey,
	}
}

func BuildSyntheticPolicyAndAttributes(attributeCount int) (tkn20.Policy, tkn20.Attributes) {

	attributeList := make(map[string]string, attributeCount)

	for index := range attributeCount {

		// Attribute side: the same synthetic pair the policy states as a clause
		attributeList[syntheticAttributeName(index)] = syntheticAttributeValue(index)
	}

	var attributes tkn20.Attributes
	attributes.FromMap(attributeList)

	return ParseCPABEPolicy(BuildSyntheticPolicyString(attributeCount)), attributes
}

func BuildSyntheticPolicyString(attributeCount int) string {

	policyString := ""

	for index := range attributeCount {

		clause := fmt.Sprintf(
			"(%s: %s)",
			syntheticAttributeName(index),
			syntheticAttributeValue(index),
		)

		if index == 0 {
			policyString = clause
		} else {
			policyString += " and " + clause
		}
	}

	return policyString
}

func ParseCPABEPolicy(policyText string) tkn20.Policy {

	var policy tkn20.Policy

	if err := policy.FromString(policyText); err != nil {
		panic(err)
	}

	return policy
}

// Synthetic attribute name: attr0, attr1, ...
func syntheticAttributeName(index int) string {

	return fmt.Sprintf("attr%d", index)
}

// Synthetic attribute value: val0, val1, ...
func syntheticAttributeValue(index int) string {

	return fmt.Sprintf("val%d", index)
}
