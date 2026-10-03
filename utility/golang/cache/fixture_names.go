package cache

// Plaintext
const PlaintextFileWSizeName = "plaintext-%d.bin"

// AES Key, Nonce & Ciphertext
const AESKeyFileName = "aes.key"
const AESNonceFileName = "aes.nonce"
const AESCiphertextWSizeFileName = "aes-ciphertext-%d.bin"

// ASCON Key, Nonce & Ciphertext
const ASCONKeyFileName = "ascon.key"
const ASCONNonceFileName = "ascon.nonce"
const ASCONCiphertextWSizeFileName = "ascon-ciphertext-%d.bin"

// PSK Envelope
const PSKStandardEnvelopeWSizeFileName = "psk-standard-%d.bin"
const PSKLightEnvelopeWSizeFileName = "psk-lightweight-%d.bin"

// RSA Public, Private Key, Ciphertext & Envelope
const RSAPublicKeyFileName = "rsa-public.key"
const RSAPublicKeyWIndexFileName = "rsa-public-%d.key"
const RSAPrivateKeyFileName = "rsa-private.key"
const RSACiphertextFileName = "rsa-ciphertext.bin"
const RSAStandardEnvelopeWSizeFileName = "rsa-standard-%d.bin"
const RSALightEnvelopeWSizeFileName = "rsa-lightweight-%d.bin"

// CP-ABE Public, Private Key, Policy, Ciphertext & Envelope
const CPABEPublicKeyFileName = "cpabe-public.key"
const CPABEPrivateKeyFileName = "cpabe-private.key"
const CPABEPrivateKeyWCountFileName = "cpabe-private-%d.key"
const CPABEPolicyFileName = "cpabe-policy.txt"
const CPABEPolicyWCountFileName = "cpabe-policy-%d.txt"
const CPABECiphertextWCountFileName = "cpabe-ciphertext-%d.bin"
const CPABEStandardEnvelopeWSizeFileName = "cpabe-standard-%d.bin"
const CPABELightEnvelopeWSizeFileName = "cpabe-lightweight-%d.bin"
