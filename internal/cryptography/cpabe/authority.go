package cpabe

import (
	"crypto/rand"
	"fmt"

	"github.com/cloudflare/circl/abe/cpabe/tkn20"
)

type Authority struct {
	publicKey       tkn20.PublicKey
	masterSecretKey tkn20.SystemSecretKey
}

// Ctor Authority
func NewAuthority() Authority {

	publicKey, systemSecretKey, err := tkn20.Setup(rand.Reader)
	if err != nil {
		panic(err)
	}

	return Authority{
		publicKey:       publicKey,
		masterSecretKey: systemSecretKey,
	}
}

// Encrypt a key under a given policy
func (authority Authority) Encrypt(policy tkn20.Policy, plaintext []byte) []byte {

	ciphertext, err := authority.publicKey.Encrypt(rand.Reader, policy, plaintext)
	if err != nil {
		panic(err)
	}

	return ciphertext
}

// Issues a private key to a subscriber for given an attribute set
func (authority Authority) IssuePrivateKey(attributes tkn20.Attributes) Subscriber {

	key, err := authority.masterSecretKey.KeyGen(rand.Reader, attributes)
	if err != nil {
		panic(err)
	}

	return Subscriber{key: key}
}

func (authority Authority) PublicKeyBytes() []byte {

	keyBytes, err := authority.publicKey.MarshalBinary()
	if err != nil {
		panic(err)
	}

	return keyBytes
}

func AuthorityFromPublicKeyBytes(keyBytes []byte) Authority {

	var publicKey tkn20.PublicKey

	if err := publicKey.UnmarshalBinary(keyBytes); err != nil {
		panic(err)
	}

	return Authority{publicKey: publicKey}
}

func BuildSyntheticPolicyAndAttributes(attributeCount int) (tkn20.Policy, tkn20.Attributes) {

	attributeList := make(map[string]string, attributeCount)
	policyString := ""

	for index := range attributeCount {

		attributeName := fmt.Sprintf("attr%d", index)
		attributeValue := fmt.Sprintf("val%d", index)

		attributeList[attributeName] = attributeValue

		clause := fmt.Sprintf(
			"(%s: %s)",
			attributeName,
			attributeValue,
		)

		if index == 0 {
			policyString = clause
		} else {
			policyString += " and " + clause
		}
	}

	var attributes tkn20.Attributes
	attributes.FromMap(attributeList)

	return ParseCPABEPolicy(policyString), attributes
}

func ParseCPABEPolicy(policyText string) tkn20.Policy {

	var policy tkn20.Policy

	if err := policy.FromString(policyText); err != nil {
		panic(err)
	}

	return policy
}
