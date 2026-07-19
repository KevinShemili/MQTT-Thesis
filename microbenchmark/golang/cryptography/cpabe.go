package cryptography

import (
	"crypto/rand"
	"fmt"

	"github.com/cloudflare/circl/abe/cpabe/tkn20"
)

type CPABEAuthority struct {
	PublicKey       tkn20.PublicKey
	systemSecretKey tkn20.SystemSecretKey // package private
}

type CPABESubscriberKey struct {
	PrivateKey tkn20.AttributeKey
}

// Authority setup phase
func NewCPABEAuthority() CPABEAuthority {

	publicKey, systemSecretKey, err := tkn20.Setup(rand.Reader)
	if err != nil {
		panic(err)
	}

	return CPABEAuthority{PublicKey: publicKey, systemSecretKey: systemSecretKey}
}

// Encrypt a key under a given policy
func (authority CPABEAuthority) Encrypt(policy tkn20.Policy, plaintext []byte) []byte {

	ciphertext, err := authority.PublicKey.Encrypt(rand.Reader, policy, plaintext)
	if err != nil {
		panic(err)
	}

	return ciphertext
}

// Issues a subscriber key for given an attribute set
func (authority CPABEAuthority) IssueSubscriberKey(attributes tkn20.Attributes) CPABESubscriberKey {

	privateKey, err := authority.systemSecretKey.KeyGen(rand.Reader, attributes)
	if err != nil {
		panic(err)
	}

	return CPABESubscriberKey{PrivateKey: privateKey}
}

// Decrypts using subscriber's private key
func (subscriberKey CPABESubscriberKey) Decrypt(ciphertext []byte) []byte {

	plaintext, err := subscriberKey.PrivateKey.Decrypt(ciphertext)
	if err != nil {
		panic(err)
	}

	return plaintext
}

// Returns synthetic policy & attribute set
func BuildSyntheticPolicyAndAttributes(attributeCount int) (tkn20.Policy, tkn20.Attributes) {

	policyString := ""
	attributeList := make(map[string]string, attributeCount)

	for index := range attributeCount {

		attributeName := fmt.Sprintf("attr%d", index) // Synthetic attribute name: attr0, attr1, ...
		attributeValue := fmt.Sprintf("val%d", index) // Synthetic attribute value: val0, val1, ...

		// Attribute side: the pair as a map entry
		attributeList[attributeName] = attributeValue

		// Policy side: the same pair as a clause
		clause := fmt.Sprintf("(%s: %s)", attributeName, attributeValue)
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

	var attributes tkn20.Attributes
	attributes.FromMap(attributeList)

	return policy, attributes
}
