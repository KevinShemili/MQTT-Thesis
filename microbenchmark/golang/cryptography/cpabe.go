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

// What a publisher holds and all it needs to encrypt: the authority's public key,
// without the master secret that issues keys
type CPABEPublicKey struct {
	PublicKey tkn20.PublicKey
}

type CPABESubscriberKey struct {
	PrivateKey tkn20.AttributeKey
}

// Ctor Authority
func NewCPABEAuthority() CPABEAuthority {

	publicKey, systemSecretKey, err := tkn20.Setup(rand.Reader)
	if err != nil {
		panic(err)
	}

	return CPABEAuthority{PublicKey: publicKey, systemSecretKey: systemSecretKey}
}

// The half of itself the authority hands to publishers
func (authority CPABEAuthority) PublisherKey() CPABEPublicKey {

	return CPABEPublicKey{PublicKey: authority.PublicKey}
}

// Encrypt a key under a given policy
func (authority CPABEAuthority) Encrypt(policy tkn20.Policy, plaintext []byte) []byte {

	return authority.PublisherKey().Encrypt(policy, plaintext)
}

// The same encryption, performed from what a publisher actually holds
func (publicKey CPABEPublicKey) Encrypt(policy tkn20.Policy, plaintext []byte) []byte {

	ciphertext, err := publicKey.PublicKey.Encrypt(rand.Reader, policy, plaintext)
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

func (subscriberKey CPABESubscriberKey) StoredKeySize() int {

	return len(MarshalCPABESubscriberKey(subscriberKey))
}

// The authority's two halves marshal apart, so a publisher can be restored from the
// public one alone and the master secret never enters a process that only encrypts
func MarshalCPABEPublicKey(publicKey CPABEPublicKey) []byte {

	keyBytes, err := publicKey.PublicKey.MarshalBinary()
	if err != nil {
		panic(err)
	}

	return keyBytes
}

func UnmarshalCPABEPublicKey(keyBytes []byte) CPABEPublicKey {

	var publicKey tkn20.PublicKey

	if err := publicKey.UnmarshalBinary(keyBytes); err != nil {
		panic(err)
	}

	return CPABEPublicKey{PublicKey: publicKey}
}

func MarshalCPABEMasterSecret(authority CPABEAuthority) []byte {

	secretBytes, err := authority.systemSecretKey.MarshalBinary()
	if err != nil {
		panic(err)
	}

	return secretBytes
}

// Only key issuance needs the authority whole, so only a provisioning side restores it
func UnmarshalCPABEAuthority(publicKeyBytes []byte, masterSecretBytes []byte) CPABEAuthority {

	var systemSecretKey tkn20.SystemSecretKey

	if err := systemSecretKey.UnmarshalBinary(masterSecretBytes); err != nil {
		panic(err)
	}

	return CPABEAuthority{
		PublicKey:       UnmarshalCPABEPublicKey(publicKeyBytes).PublicKey,
		systemSecretKey: systemSecretKey,
	}
}

func MarshalCPABESubscriberKey(subscriberKey CPABESubscriberKey) []byte {

	keyBytes, err := subscriberKey.PrivateKey.MarshalBinary()
	if err != nil {
		panic(err)
	}

	return keyBytes
}

func UnmarshalCPABESubscriberKey(keyBytes []byte) CPABESubscriberKey {

	var privateKey tkn20.AttributeKey

	if err := privateKey.UnmarshalBinary(keyBytes); err != nil {
		panic(err)
	}

	return CPABESubscriberKey{PrivateKey: privateKey}
}

// Returns synthetic policy & attribute set
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

// The policy on its own, as the text it is parsed from. It is fully determined by the
// attribute count, so it can be stored and read back instead of being built by a
// process whose allocations are being measured
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
