# Ciphersuite naming

How to name concrete cryptographic primitives so reviewers can map every symbol in the construction to a standardised, deployable instantiation. The IACR PC expects every hash, signature, KEM, KDF, VRF, MAC, and AEAD used in a construction to carry either an RFC ciphersuite label or a precise reference to a standardised parameter set.

This reference fixes the naming for each primitive class.

## General pattern

```
<PRIMITIVE>-<CURVE/MODULUS>-<HASH>-<MODE>-<ADDITIONAL>
```

For RFC-defined ciphersuites, use the RFC label verbatim. For primitives without an RFC, use the convention of the closest analogous RFC.

## Hash functions

Bare hash functions: name by the FIPS or RFC the digest is defined in.

- `SHA-256`, `SHA-384`, `SHA-512` — FIPS 180-4.
- `SHA3-256`, `SHA3-512`, `SHAKE128`, `SHAKE256` — FIPS 202.
- `BLAKE2b-256`, `BLAKE2s-256` — RFC 7693.
- `BLAKE3` — no RFC; cite Aumasson et al. "BLAKE3: one function, fast everywhere" (2020).

When the hash is modelled as a random oracle in the proof but instantiated from a concrete hash, state this at first use:

> The random oracle `H_chal` is instantiated from SHA-256 with DST `"EPC-v1-chal"` using the `expand_message_xmd` construction of RFC 9380, §5.3.

## Hash to elliptic-curve points (RFC 9380)

RFC 9380 ("Hashing to Elliptic Curves", IRTF CFRG, 2023) defines the canonical hash-to-curve ciphersuite labels. Use them verbatim.

- `BLS12381G1_XMD:SHA-256_SSWU_RO_` — BLS12-381 G1, SHA-256 expand_message_xmd, simplified SWU, random-oracle variant.
- `BLS12381G2_XMD:SHA-256_SSWU_RO_` — same for G2.
- `P256_XMD:SHA-256_SSWU_RO_` — NIST P-256.
- `P384_XMD:SHA-384_SSWU_RO_` — NIST P-384.
- `edwards25519_XMD:SHA-512_ELL2_RO_` — Curve25519/Edwards form.
- `edwards448_XMD:SHAKE256_ELL2_RO_` — Curve448.

The trailing underscore is part of the label. Do not strip it.

When citing, write:

> `H_curve: {0,1}^* → G_1` is the BLS12-381 G1 hash-to-curve function with ciphersuite label `BLS12381G1_XMD:SHA-256_SSWU_RO_`, as defined in RFC 9380 §8.8.1.

## Verifiable Random Functions (RFC 9381)

RFC 9381 ("Verifiable Random Functions (VRFs)", IRTF CFRG, 2023) defines the ECVRF ciphersuites. Use the suite-string label.

- `ECVRF-EDWARDS25519-SHA512-ELL2` — Edwards25519, SHA-512, Elligator2 encoding.
- `ECVRF-EDWARDS25519-SHA512-TAI` — same curve, try-and-increment encoding (slower, simpler).
- `ECVRF-P256-SHA256-TAI` — NIST P-256, SHA-256, try-and-increment.
- `ECVRF-P256-SHA256-SSWU` — same, with SSWU encoding.

Cardano's Ouroboros Praos VRF uses `ECVRF-EDWARDS25519-SHA512-ELL2`. When deviating from a registered RFC 9381 suite, document the suite_string byte and cite the deviation.

> The VRF is instantiated as `ECVRF-EDWARDS25519-SHA512-ELL2` (RFC 9381 §5.5), with `suite_string = 0x04`.

## Key Encapsulation Mechanisms (NIST PQC)

Post-quantum KEMs use the NIST-standardised names.

- `ML-KEM-512`, `ML-KEM-768`, `ML-KEM-1024` — FIPS 203 (formerly Kyber). NIST levels I, III, V.
- `HQC-128`, `HQC-192`, `HQC-256` — NIST round-4 candidate; cite the NIST submission package.

For classical KEMs: cite RFC 9180 (HPKE) for hybrid public-key encryption, which composes a KEM + KDF + AEAD ciphersuite.

## Hybrid Public-Key Encryption (RFC 9180)

RFC 9180 defines HPKE ciphersuites by triple `(KEM, KDF, AEAD)`.

- `(DHKEM(X25519, HKDF-SHA256), HKDF-SHA256, AES-128-GCM)` — KEM ID `0x0020`, KDF ID `0x0001`, AEAD ID `0x0001`.
- `(DHKEM(P-256, HKDF-SHA256), HKDF-SHA256, AES-128-GCM)` — KEM ID `0x0010`.
- `(DHKEM(X448, HKDF-SHA512), HKDF-SHA512, AES-256-GCM)` — KEM ID `0x0021`, KDF ID `0x0003`, AEAD ID `0x0002`.

Cite RFC 9180 §7 for the IANA-registered ciphersuite IDs.

## Signatures

Classical signatures: by FIPS or RFC.

- `Ed25519` — RFC 8032 §5.1. Use `Ed25519ctx` (with context byte) or `Ed25519ph` (pre-hashed) where applicable.
- `Ed448` — RFC 8032 §5.2.
- `ECDSA-P256-SHA256` — FIPS 186-5 (and SEC 1 v2.0).
- `RSA-PSS-SHA256` with explicit mask generation `MGF1-SHA256` and salt length — RFC 8017.

Post-quantum signatures: NIST FIPS 204 and 205.

- `ML-DSA-44`, `ML-DSA-65`, `ML-DSA-87` — FIPS 204 (formerly Dilithium).
- `SLH-DSA-SHA2-128s`, `SLH-DSA-SHA2-128f`, `SLH-DSA-SHAKE-256s`, … — FIPS 205 (formerly SPHINCS+).
- `Falcon-512`, `Falcon-1024` — pending FIPS 206 (`FN-DSA`); cite NIST submission until standardised.

## Key Evolving Signatures (KES)

KES schemes have no RFC. The de facto reference is the Bellare–Miner sum-composition construction.

- `Sum-KES-d` for tree depth `d` over a base scheme (commonly Ed25519 or Schnorr).
- Cite Bellare–Miner "A forward-secure digital signature scheme" (Crypto 1999) and the Praos KES construction (David–Gaži–Kiayias–Russell, "Ouroboros Praos", Eurocrypt 2018).
- NIST 800-208 ("Stateful Hash-Based Signature Schemes") covers `LMS` and `XMSS` (RFC 8554 and RFC 8391), which are related but distinct from generic KES.

When using KES in a construction:

> The KES scheme `KES = Sum-KES-7(Ed25519)` is the Bellare–Miner sum-composition of depth 7 over Ed25519, giving `2^7 = 128` evolving periods. Period evolution follows the algorithm of Praos §5 (David et al., Eurocrypt 2018).

## Hash-based stateful signatures

- `LMS` and `LM-OTS` — RFC 8554, NIST SP 800-208.
- `XMSS`, `XMSS^MT` — RFC 8391, NIST SP 800-208.

State the parameter set verbatim: `XMSS-SHA2_10_256`, `LMS_SHA256_M32_H10`, etc.

## Key Derivation Functions

- `HKDF-SHA256`, `HKDF-SHA512` — RFC 5869.
- `Argon2id` (parameters `(t, m, p)`) — RFC 9106.
- `PBKDF2-HMAC-SHA256` — RFC 8018.
- `Scrypt(N, r, p)` — RFC 7914.

Always state the parameters. `Argon2id(t=3, m=64MB, p=4)` is acceptable; `Argon2id` alone is not.

## MACs

- `HMAC-SHA256`, `HMAC-SHA512` — RFC 2104, FIPS 198-1.
- `KMAC128`, `KMAC256` — NIST SP 800-185.
- `Poly1305` — RFC 8439 (only secure as part of ChaCha20-Poly1305).

## Authenticated Encryption with Associated Data (AEAD)

- `AES-128-GCM`, `AES-256-GCM` — NIST SP 800-38D.
- `ChaCha20-Poly1305` — RFC 8439.
- `AES-128-GCM-SIV`, `AES-256-GCM-SIV` — RFC 8452.
- `Ascon-128`, `Ascon-128a`, `Ascon-80pq` — NIST SP 800-232 (lightweight cryptography winner).

## Verifiable Delay Functions (VDF)

VDFs have no RFC. Use the canonical construction name and cite.

- `Wesolowski-VDF` — Wesolowski "Efficient Verifiable Delay Functions" (Eurocrypt 2019).
- `Pietrzak-VDF` — Pietrzak "Simple Verifiable Delay Functions" (ITCS 2019).
- State the underlying group: `Wesolowski-VDF` over RSA-2048, `Wesolowski-VDF` over a class group of discriminant `-d`.

## Threshold signatures

- `FROST` — RFC 9591 (Two-Round Threshold Schnorr Signatures with FROST).
- `BLS-threshold` — Boldyreva "Threshold Signatures, Multisignatures and Blind Signatures Based on the Gap-Diffie-Hellman-Group Signature Scheme" (PKC 2003).
- State the threshold parameters: `FROST(t, n)` with `t = ceil(2n/3) + 1` for Byzantine resilience.

## Commitments

- `Pedersen` over `G`: state `G` and the two independent generators `g, h ∈ G`.
- `Halo2-IPA` — cite the Halo paper (Bowe–Grigg–Hopwood, 2019) and the ZCash Halo2 specification.
- `KZG` (Kate–Zaverucha–Goldberg) — cite Kate et al. "Constant-Size Commitments to Polynomials and Their Applications" (Asiacrypt 2010).

## Random oracle instantiation

State, at first use of the random oracle, exactly how it is instantiated:

> `H: {0,1}^* → ℤ_p` is modelled as a random oracle in the proof and instantiated from SHA-256 via `expand_message_xmd` (RFC 9380 §5.3) with DST `"EPC-v1-prf"`.

Without the instantiation, reviewers ask: "what does the implementation actually use?"

## DST naming convention (project-local)

For project-internal hashes (not RFC-bound), use the pattern:

```
"<PROJECT>-v<VERSION>-<ROLE>[-<SUBROLE>]"
```

Examples (EpochPoET):

- `"EPC-v1-commit"` — commit-phase hash.
- `"EPC-v1-chal"` — Fiat-Shamir challenge.
- `"EPC-v1-vrf-suite-04"` — VRF suite-string discriminator.
- `"EPC-v1-kes-evolve"` — KES period evolution.

State the DST byte length and encoding rule (RFC 9380 mandates DST length `≤ 255` bytes; longer DSTs are H-prefixed).

## Cross-skill notes

- For inserting DSTs into hash calls in protocol pseudocode, see `protocol-pseudocode.md`.
- For declaring the hash in the theorem statement, see `theorem-statement-style.md`.
- For the proof's use of random-oracle programming, see `proof-style-uc.md` (for UC) or `proof-style-game-based.md` (for game-based).

## What this reference does not cover

- Implementation-level details (constant-time, masking, side-channel resistance) — out of scope for prose-level naming. Cite a CHES paper for those.
- Library-specific bindings (libsodium, OpenSSL, BoringSSL) — out of scope; the paper specifies the primitive, not the library.
