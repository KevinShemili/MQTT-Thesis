package cryptography

import (
	"crypto/rand"
	"fmt"

	"github.com/cloudflare/circl/abe/cpabe/tkn20"
)

// CPABE holds the public key needed to encrypt under a policy.
type CPABE struct {
	PublicKey tkn20.PublicKey
}

// NewCPABE runs the CP-ABE Setup algorithm once and keeps only the public key; this benchmark never decrypts.
func NewCPABE() CPABE {
	var publicKey tkn20.PublicKey
	var err error

	// Setup also returns a SystemSecretKey; discard it via _ since only encryption is exercised here.
	publicKey, _, err = tkn20.Setup(rand.Reader)
	if err != nil {
		panic(err)
	}

	return CPABE{PublicKey: publicKey}
}

// BuildConjunctivePolicy builds a policy string with attributeCount distinct "and" clauses, e.g. "(attr0: val0) and (attr1: val1)".
func BuildConjunctivePolicy(attributeCount int) tkn20.Policy {
	var policyString string = ""

	var index int
	for index = 0; index < attributeCount; index++ {

		// Each clause uses a distinct attribute name and value so the policy does not collapse to fewer clauses.
		var clause string = fmt.Sprintf("(attr%d: val%d)", index, index)

		if index == 0 {
			policyString = clause
		} else {
			// Chain clauses with "and" so ciphertext size grows with every added attribute.
			policyString = policyString + " and " + clause
		}
	}

	var policy tkn20.Policy
	var err error = policy.FromString(policyString)
	if err != nil {
		panic(err)
	}

	return policy
}

// Encrypt runs CP-ABE encryption of msg under policy and returns the ciphertext bytes.
func (cpAbe CPABE) Encrypt(policy tkn20.Policy, msg []byte) []byte {
	var ciphertext []byte
	var err error

	ciphertext, err = cpAbe.PublicKey.Encrypt(rand.Reader, policy, msg)
	if err != nil {
		panic(err)
	}

	return ciphertext
}
