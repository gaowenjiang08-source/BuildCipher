"""
Interactive Tutorial System
交互式密码学教程系统
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Tutorial:
    """Tutorial structure"""
    id: str
    title: str
    description: str
    difficulty: str  # beginner, intermediate, advanced
    duration_minutes: int
    steps: List[Dict[str, Any]]
    example_requirements: str
    expected_output: Dict[str, Any]


class TutorialManager:
    """Manage interactive tutorials"""

    def __init__(self):
        self.tutorials = self._create_tutorials()

    def get_all_tutorials(self) -> List[Tutorial]:
        """Get all available tutorials"""
        return list(self.tutorials.values())

    def get_tutorial(self, tutorial_id: str) -> Optional[Tutorial]:
        """Get specific tutorial by ID"""
        return self.tutorials.get(tutorial_id)

    def get_tutorials_by_difficulty(self, difficulty: str) -> List[Tutorial]:
        """Filter tutorials by difficulty"""
        return [
            tutorial for tutorial in self.tutorials.values()
            if tutorial.difficulty.lower() == difficulty.lower()
        ]

    def _create_tutorials(self) -> Dict[str, Tutorial]:
        """Create tutorial content"""
        tutorials = {}

        # Tutorial 1: Getting Started - Basic Encryption Scheme
        tutorials["getting_started"] = Tutorial(
            id="getting_started",
            title="Getting Started with BuildTrust",
            description="Learn the basics of encryption using AES-GCM. This tutorial covers symmetric encryption, key generation, and secure message exchange.",
            difficulty="beginner",
            duration_minutes=15,
            steps=[
                {
                    "step": 1,
                    "title": "Import Required Modules",
                    "description": "Import the necessary cryptographic modules used by BuildTrust",
                    "code_example": """
from cipher_genius.core.encryption import SymmetricEncryption
from cipher_genius.utils.key_management import KeyGenerator
""",
                    "explanation": "These modules provide symmetric encryption capabilities and key generation utilities."
                },
                {
                    "step": 2,
                    "title": "Generate Encryption Key",
                    "description": "Create a secure 256-bit encryption key",
                    "code_example": """
key_gen = KeyGenerator()
encryption_key = key_gen.generate_symmetric_key(algorithm='AES', key_size=256)
print(f"Generated key: {encryption_key.hex()[:32]}...")
""",
                    "explanation": "AES-256 provides strong security for most applications. The key is randomly generated using a cryptographically secure random number generator."
                },
                {
                    "step": 3,
                    "title": "Encrypt a Message",
                    "description": "Encrypt your first message using AES-GCM",
                    "code_example": """
encryptor = SymmetricEncryption(algorithm='AES-GCM')
message = b"Hello, BuildTrust!"
ciphertext, tag, nonce = encryptor.encrypt(encryption_key, message)
print(f"Ciphertext: {ciphertext.hex()}")
print(f"Auth tag: {tag.hex()}")
""",
                    "explanation": "AES-GCM provides both confidentiality and authenticity. The authentication tag ensures the message hasn't been tampered with."
                },
                {
                    "step": 4,
                    "title": "Decrypt the Message",
                    "description": "Recover the original message",
                    "code_example": """
plaintext = encryptor.decrypt(encryption_key, ciphertext, tag, nonce)
print(f"Decrypted: {plaintext.decode()}")
assert plaintext == message, "Decryption failed!"
""",
                    "explanation": "Decryption verifies the authentication tag before returning the plaintext, protecting against forgery."
                },
                {
                    "step": 5,
                    "title": "Practice Exercise",
                    "description": "Encrypt and decrypt your own message",
                    "task": "Create a function that encrypts a user-provided message and returns the ciphertext and authentication components.",
                    "validation": "Function should successfully encrypt and decrypt any message"
                }
            ],
            example_requirements="Python 3.8+, cryptography library",
            expected_output={
                "encrypted": True,
                "decrypted": True,
                "authentication_verified": True,
                "components": ["ciphertext", "tag", "nonce"]
            }
        )

        # Tutorial 2: Post-Quantum Cryptography
        tutorials["post_quantum"] = Tutorial(
            id="post_quantum",
            title="Post-Quantum Cryptography with Kyber and Dilithium",
            description="Explore quantum-resistant cryptographic algorithms. Learn how to use CRYSTALS-Kyber for key encapsulation and CRYSTALS-Dilithium for digital signatures.",
            difficulty="intermediate",
            duration_minutes=30,
            steps=[
                {
                    "step": 1,
                    "title": "Understanding Post-Quantum Threats",
                    "description": "Learn why post-quantum cryptography is necessary",
                    "explanation": """
Quantum computers threaten current public-key cryptography:
- Shor's algorithm breaks RSA and ECC
- Grover's algorithm weakens symmetric crypto
- NIST selected Kyber (KEM) and Dilithium (signatures) as standards
- Migration to PQC is critical for long-term security
""",
                    "reading": "NIST Post-Quantum Cryptography Standardization"
                },
                {
                    "step": 2,
                    "title": "Key Encapsulation with Kyber",
                    "description": "Generate Kyber keypair and encapsulate a shared secret",
                    "code_example": """
from cipher_genius.pqc.kyber import KyberKEM

# Initialize Kyber-768 (NIST security level 3)
kyber = KyberKEM(security_level=768)

# Generate keypair
public_key, secret_key = kyber.keygen()
print(f"Public key size: {len(public_key)} bytes")

# Encapsulation (sender side)
ciphertext, shared_secret = kyber.encapsulate(public_key)
print(f"Shared secret: {shared_secret.hex()[:32]}...")
""",
                    "explanation": "Kyber uses lattice-based cryptography (Module-LWE). The shared secret can be used for symmetric encryption."
                },
                {
                    "step": 3,
                    "title": "Decapsulation Process",
                    "description": "Recover the shared secret using the private key",
                    "code_example": """
# Decapsulation (receiver side)
recovered_secret = kyber.decapsulate(secret_key, ciphertext)

# Verify secrets match
assert recovered_secret == shared_secret, "Decapsulation failed!"
print("✓ Shared secret successfully established")
""",
                    "explanation": "Only the holder of the secret key can recover the shared secret from the ciphertext."
                },
                {
                    "step": 4,
                    "title": "Digital Signatures with Dilithium",
                    "description": "Sign and verify messages using Dilithium",
                    "code_example": """
from cipher_genius.pqc.dilithium import DilithiumSignature

# Initialize Dilithium-3 (NIST security level 3)
dilithium = DilithiumSignature(security_level=3)

# Generate signing keypair
sign_public_key, sign_secret_key = dilithium.keygen()

# Sign a message
message = b"This is a quantum-safe signature"
signature = dilithium.sign(sign_secret_key, message)
print(f"Signature size: {len(signature)} bytes")

# Verify signature
is_valid = dilithium.verify(sign_public_key, message, signature)
print(f"Signature valid: {is_valid}")
""",
                    "explanation": "Dilithium is based on lattice problems (Module-LWE/SIS). Signatures are larger than ECDSA but quantum-resistant."
                },
                {
                    "step": 5,
                    "title": "Hybrid Approach",
                    "description": "Combine classical and post-quantum cryptography",
                    "code_example": """
from cipher_genius.hybrid.pqc_hybrid import HybridKEM

# Use both ECDH and Kyber
hybrid = HybridKEM(classical='X25519', pqc='Kyber768')

# Generate hybrid keypair
pub_key, sec_key = hybrid.keygen()

# Hybrid key exchange
ct, shared = hybrid.encapsulate(pub_key)

# Result combines security of both algorithms
print(f"Hybrid shared secret: {shared.hex()[:32]}...")
""",
                    "explanation": "Hybrid schemes provide defense-in-depth: secure if either algorithm remains unbroken."
                },
                {
                    "step": 6,
                    "title": "Practice Exercise",
                    "description": "Implement a secure message exchange using Kyber + AES-GCM",
                    "task": "Create a system that uses Kyber for key establishment and AES-GCM for message encryption",
                    "validation": "Successfully exchange encrypted messages between two parties"
                }
            ],
            example_requirements="Python 3.8+, pqcrypto library or liboqs",
            expected_output={
                "kyber_encapsulation": True,
                "dilithium_signature": True,
                "hybrid_mode": True,
                "key_sizes": {
                    "kyber768_public": 1184,
                    "kyber768_ciphertext": 1088,
                    "dilithium3_signature": 3293
                }
            }
        )

        # Tutorial 3: AEAD Modes - Authenticated Encryption
        tutorials["aead_modes"] = Tutorial(
            id="aead_modes",
            title="Authenticated Encryption with Associated Data (AEAD)",
            description="Master AEAD modes like AES-GCM, ChaCha20-Poly1305, and AES-GCM-SIV. Learn when and how to use each mode for maximum security.",
            difficulty="intermediate",
            duration_minutes=25,
            steps=[
                {
                    "step": 1,
                    "title": "Why AEAD Matters",
                    "description": "Understanding the importance of authenticated encryption",
                    "explanation": """
AEAD provides:
- Confidentiality: Encrypted data is unreadable
- Integrity: Detect any modifications
- Authenticity: Verify sender identity
- Associated Data: Authenticate metadata without encrypting it

Common mistakes with non-AEAD:
- Using CBC without HMAC (padding oracle attacks)
- Incorrect MAC-then-encrypt or encrypt-then-MAC
- Timing attacks on MAC verification
""",
                    "reading": "AEAD is the modern standard for symmetric encryption"
                },
                {
                    "step": 2,
                    "title": "AES-GCM Implementation",
                    "description": "Use AES-GCM for high-performance AEAD",
                    "code_example": """
from cipher_genius.aead.aes_gcm import AESGCM

# Initialize AES-GCM
aead = AESGCM(key_size=256)
key = aead.generate_key()

# Encrypt with associated data
plaintext = b"Approved IFC delivery package"
associated_data = b"project_id=buildtrust-demo,version=v3"

ciphertext, tag = aead.encrypt(
    key=key,
    plaintext=plaintext,
    associated_data=associated_data
)

print(f"Ciphertext: {ciphertext.hex()}")
print(f"Auth tag: {tag.hex()}")
""",
                    "explanation": "Associated data is authenticated but not encrypted. Perfect for headers, metadata, or protocol fields."
                },
                {
                    "step": 3,
                    "title": "ChaCha20-Poly1305 for Constant-Time Security",
                    "description": "Use ChaCha20-Poly1305 when AES hardware acceleration is unavailable",
                    "code_example": """
from cipher_genius.aead.chacha20_poly1305 import ChaCha20Poly1305

# Initialize ChaCha20-Poly1305
chacha = ChaCha20Poly1305()
key = chacha.generate_key()

# Encrypt message
message = b"Mobile device communication"
nonce = chacha.generate_nonce()

ciphertext = chacha.encrypt(
    key=key,
    nonce=nonce,
    plaintext=message,
    associated_data=b"device_id=mobile_001"
)

# Decrypt and verify
plaintext = chacha.decrypt(
    key=key,
    nonce=nonce,
    ciphertext=ciphertext,
    associated_data=b"device_id=mobile_001"
)

print(f"Decrypted: {plaintext.decode()}")
""",
                    "explanation": "ChaCha20-Poly1305 is constant-time, resistant to cache-timing attacks, and faster on devices without AES-NI."
                },
                {
                    "step": 4,
                    "title": "AES-GCM-SIV for Nonce Misuse Resistance",
                    "description": "Use AES-GCM-SIV when nonce uniqueness is difficult to guarantee",
                    "code_example": """
from cipher_genius.aead.aes_gcm_siv import AESGCMSIV

# Initialize AES-GCM-SIV
gcm_siv = AESGCMSIV(key_size=256)
key = gcm_siv.generate_key()

# Even with repeated nonces, still secure (but not recommended)
nonce = b"\\x00" * 12  # Same nonce (for demonstration only)

ct1 = gcm_siv.encrypt(key, nonce, b"Message 1")
ct2 = gcm_siv.encrypt(key, nonce, b"Message 2")

# Different ciphertexts despite same nonce
assert ct1 != ct2
print("✓ Nonce misuse resistance demonstrated")
""",
                    "explanation": "AES-GCM-SIV is 'nonce-misuse resistant' - it degrades gracefully if nonces are repeated, unlike standard GCM."
                },
                {
                    "step": 5,
                    "title": "Choosing the Right AEAD Mode",
                    "description": "Decision guide for AEAD selection",
                    "explanation": """
AES-GCM:
✓ Hardware acceleration available (AES-NI)
✓ Maximum performance needed
✗ Nonce management is critical
✗ No misuse resistance

ChaCha20-Poly1305:
✓ Software-only implementation
✓ Mobile/embedded devices
✓ Constant-time security
✗ Slightly larger ciphertexts

AES-GCM-SIV:
✓ Nonce uniqueness hard to guarantee
✓ Need misuse resistance
✗ Slower than AES-GCM
✗ Less widely supported
""",
                    "code_example": """
from cipher_genius.aead.selector import AEADSelector

selector = AEADSelector()
mode = selector.recommend(
    hardware_aes=True,
    nonce_management="strict",
    platform="server"
)
print(f"Recommended: {mode}")  # AES-GCM
""",
                },
                {
                    "step": 6,
                    "title": "Practice Exercise",
                    "description": "Implement a secure API request/response system",
                    "task": """
Create a system that:
1. Encrypts API payloads with AEAD
2. Authenticates request headers as associated data
3. Handles nonce generation and management
4. Implements proper error handling
""",
                    "validation": "API requests are encrypted, headers authenticated, and tampering detected"
                }
            ],
            example_requirements="Python 3.8+, cryptography library",
            expected_output={
                "aes_gcm_working": True,
                "chacha20_working": True,
                "gcm_siv_working": True,
                "associated_data_authenticated": True,
                "tampering_detected": True
            }
        )

        # Tutorial 4: Zero-Knowledge Proofs
        tutorials["zero_knowledge"] = Tutorial(
            id="zero_knowledge",
            title="Zero-Knowledge Proofs for Privacy-Preserving Authentication",
            description="Learn how to implement zero-knowledge proofs for password verification, age verification, and range proofs without revealing sensitive information.",
            difficulty="advanced",
            duration_minutes=40,
            steps=[
                {
                    "step": 1,
                    "title": "Zero-Knowledge Fundamentals",
                    "description": "Understanding the core principles of ZK proofs",
                    "explanation": """
Zero-Knowledge Proof Properties:
1. Completeness: If statement is true, honest verifier will be convinced
2. Soundness: If statement is false, cheating prover cannot convince verifier
3. Zero-Knowledge: Verifier learns nothing except truth of statement

Applications:
- Password authentication without sending password
- Age verification without revealing birthdate
- Proving solvency without revealing balance
- Anonymous credentials and voting
""",
                    "reading": "ZK-SNARKs, ZK-STARKs, and Sigma protocols"
                },
                {
                    "step": 2,
                    "title": "Schnorr Protocol for Password Proof",
                    "description": "Implement a ZK proof that you know a password",
                    "code_example": """
from cipher_genius.zkp.schnorr import SchnorrProtocol

# Setup
zkp = SchnorrProtocol()
password = b"my_secret_password"

# Prover: Generate commitment
secret_key = zkp.hash_to_scalar(password)
public_key = zkp.generate_public_key(secret_key)

# Store only public key on server
print(f"Public key: {public_key.hex()[:32]}...")

# Authentication: Prove knowledge without revealing password
commitment = zkp.commit(secret_key)
challenge = zkp.generate_challenge()
response = zkp.respond(secret_key, commitment, challenge)

# Verify proof
is_valid = zkp.verify(public_key, commitment, challenge, response)
print(f"Proof valid: {is_valid}")
print("✓ Password verified without transmission!")
""",
                    "explanation": "The server never sees the password, only the proof of knowledge. Resistant to replay attacks with fresh challenges."
                },
                {
                    "step": 3,
                    "title": "Range Proofs for Age Verification",
                    "description": "Prove age > 18 without revealing exact age",
                    "code_example": """
from cipher_genius.zkp.range_proof import RangeProof

# Setup range proof system
range_prover = RangeProof(bit_length=8)  # Ages 0-255

# User's actual age (kept secret)
actual_age = 25

# Generate proof: age >= 18
proof = range_prover.prove_greater_than(
    secret_value=actual_age,
    threshold=18
)

# Verifier checks proof without learning exact age
is_adult = range_prover.verify_greater_than(
    proof=proof,
    threshold=18
)

print(f"Is adult: {is_adult}")
print(f"Exact age revealed: NO")
print("✓ Privacy-preserving age verification")
""",
                    "explanation": "Range proofs use Pedersen commitments and binary decomposition. Common in cryptocurrencies (Monero) and privacy tech."
                },
                {
                    "step": 4,
                    "title": "Set Membership Proofs",
                    "description": "Prove you're in a group without revealing which member",
                    "code_example": """
from cipher_genius.zkp.set_membership import SetMembershipProof

# Setup: whitelist of authorized users
authorized_ids = [
    b"alice@example.com",
    b"bob@example.com",
    b"charlie@example.com"
]

smp = SetMembershipProof()
merkle_root = smp.build_membership_tree(authorized_ids)

# Alice proves membership without revealing identity
alice_proof = smp.prove_membership(
    element=b"alice@example.com",
    authorized_set=authorized_ids
)

# Verifier confirms Alice is authorized
is_member = smp.verify_membership(
    proof=alice_proof,
    merkle_root=merkle_root
)

print(f"Is authorized: {is_member}")
print(f"Identity revealed: NO")
print("✓ Anonymous authentication")
""",
                    "explanation": "Uses Merkle trees for efficient set membership. Scales logarithmically with set size."
                },
                {
                    "step": 5,
                    "title": "zk-SNARKs for Complex Statements",
                    "description": "Prove complex computations with succinct proofs",
                    "code_example": """
from cipher_genius.zkp.snark import ZKSnark

# Setup: Prove you know x such that SHA256(x) = known_hash
# without revealing x
snark = ZKSnark()

# Trusted setup (one-time)
proving_key, verification_key = snark.setup(
    circuit="sha256_preimage"
)

# Prover: I know the preimage
secret_input = b"correct_password"
known_hash = snark.sha256(secret_input)

proof = snark.prove(
    proving_key=proving_key,
    public_input=known_hash,
    secret_witness=secret_input
)

# Verifier: Proof is tiny (~200 bytes) and fast to verify
is_valid = snark.verify(
    verification_key=verification_key,
    public_input=known_hash,
    proof=proof
)

print(f"Proof size: {len(proof)} bytes")
print(f"Proof valid: {is_valid}")
print("✓ Succinct proof of complex computation")
""",
                    "explanation": "zk-SNARKs enable arbitrary computation proofs. Used in Zcash, zkSync, and blockchain privacy."
                },
                {
                    "step": 6,
                    "title": "Practical ZKP System Design",
                    "description": "Best practices for production ZKP systems",
                    "explanation": """
Design Considerations:
1. Trusted Setup: zk-SNARKs need trusted setup (MPC ceremonies)
2. Performance: zk-STARKs are slower but transparent (no trusted setup)
3. Proof Size: SNARKs small, STARKs large
4. Quantum Resistance: STARKs are quantum-resistant

Security:
- Use battle-tested libraries (libsnark, circom, bellman)
- Careful circuit design (no side channels)
- Challenge randomness must be unpredictable
- Protect against malleability attacks
""",
                    "code_example": """
from cipher_genius.zkp.system import ZKPSystem

# Production-ready ZKP system
system = ZKPSystem(
    protocol='groth16',  # or 'plonk', 'stark'
    security_level=128,
    curve='bn254'
)

# Generate system parameters
params = system.generate_parameters()

# Use in application
proof = system.create_proof(
    statement="age >= 18",
    witness={"age": 25}
)

verified = system.verify_proof(proof, "age >= 18")
print(f"System verified: {verified}")
""",
                },
                {
                    "step": 7,
                    "title": "Practice Exercise",
                    "description": "Build a private credential system",
                    "task": """
Implement a system where:
1. Users prove they have valid credentials without revealing them
2. Support multiple attributes (age, country, membership level)
3. Selective disclosure (prove age without revealing other attributes)
4. Revocation mechanism without identifying users
""",
                    "validation": "Successfully prove credentials while maintaining zero-knowledge property"
                }
            ],
            example_requirements="Python 3.8+, cryptography, zkp library (libsnark or similar)",
            expected_output={
                "schnorr_protocol": True,
                "range_proof": True,
                "set_membership": True,
                "snark_proof": True,
                "zero_knowledge_maintained": True,
                "completeness": True,
                "soundness": True
            }
        )

        # Tutorial 5: IoT Security
        tutorials["iot_security"] = Tutorial(
            id="iot_security",
            title="Cryptography for IoT and Resource-Constrained Devices",
            description="Learn to implement efficient cryptography for embedded systems, including lightweight ciphers, constrained key exchange, and secure firmware updates.",
            difficulty="advanced",
            duration_minutes=35,
            steps=[
                {
                    "step": 1,
                    "title": "IoT Security Challenges",
                    "description": "Understanding constraints of embedded devices",
                    "explanation": """
Resource Constraints:
- Limited RAM (2-64 KB typical)
- Low CPU power (8-32 bit microcontrollers)
- Battery-powered (energy efficiency critical)
- Small code size (32-256 KB flash)

Security Requirements:
- Device authentication
- Secure communication
- Firmware integrity
- Key management
- Resistance to physical attacks

Standards:
- NIST Lightweight Cryptography
- RFC 7748 (X25519)
- COSE (RFC 8152)
- DTLS 1.3 for UDP
""",
                    "reading": "NIST Lightweight Cryptography project"
                },
                {
                    "step": 2,
                    "title": "Lightweight Block Ciphers",
                    "description": "Using ASCON and other lightweight AEAD ciphers",
                    "code_example": """
from cipher_genius.lightweight.ascon import Ascon128

# ASCON - NIST Lightweight Crypto winner
ascon = Ascon128()

# Generate key (128 bits)
key = ascon.generate_key()
nonce = ascon.generate_nonce()

# Encrypt sensor data
sensor_data = b"temp=23.5,humidity=65"
associated_data = b"device_id=sensor_01,timestamp=1698765432"

ciphertext = ascon.encrypt(
    key=key,
    nonce=nonce,
    plaintext=sensor_data,
    associated_data=associated_data
)

# Memory efficient: minimal RAM usage
print(f"Ciphertext: {ciphertext.hex()}")
print(f"RAM usage: ~200 bytes")
print(f"Code size: ~2 KB")
""",
                    "explanation": "ASCON is optimized for hardware and constrained devices. Faster and smaller than AES-GCM on low-end devices."
                },
                {
                    "step": 3,
                    "title": "Efficient Key Exchange with X25519",
                    "description": "Implement elliptic curve Diffie-Hellman for IoT",
                    "code_example": """
from cipher_genius.lightweight.x25519 import X25519

# Device A (IoT sensor)
device_a = X25519()
device_a_private = device_a.generate_private_key()
device_a_public = device_a.generate_public_key(device_a_private)

# Device B (gateway)
device_b = X25519()
device_b_private = device_b.generate_private_key()
device_b_public = device_b.generate_public_key(device_b_private)

# Both devices compute same shared secret
shared_a = device_a.compute_shared_secret(device_a_private, device_b_public)
shared_b = device_b.compute_shared_secret(device_b_private, device_a_public)

assert shared_a == shared_b
print(f"Shared secret: {shared_a.hex()[:32]}...")
print(f"Computation time: <10ms on ARM Cortex-M4")
""",
                    "explanation": "X25519 is fast, constant-time, and requires only 32-byte keys. Ideal for constrained devices."
                },
                {
                    "step": 4,
                    "title": "Ed25519 Signatures for Firmware Verification",
                    "description": "Verify firmware authenticity using compact signatures",
                    "code_example": """
from cipher_genius.lightweight.ed25519 import Ed25519

# Manufacturer signing key
ed = Ed25519()
signing_key = ed.generate_signing_key()
verify_key = ed.get_verify_key(signing_key)

# Sign firmware update
firmware = b"\\x00" * 10240  # 10 KB firmware binary
signature = ed.sign(signing_key, firmware)

print(f"Signature size: {len(signature)} bytes")  # Only 64 bytes!

# Device verifies firmware before flashing
is_authentic = ed.verify(verify_key, firmware, signature)

if is_authentic:
    print("✓ Firmware authentic - safe to flash")
else:
    print("✗ Firmware verification failed - rejected")
""",
                    "explanation": "Ed25519 signatures are tiny (64 bytes), fast to verify, and deterministic. Perfect for OTA updates."
                },
                {
                    "step": 5,
                    "title": "DTLS for Secure IoT Communication",
                    "description": "Implement DTLS 1.3 for UDP-based IoT protocols",
                    "code_example": """
from cipher_genius.lightweight.dtls import DTLSv13

# Setup DTLS connection
dtls = DTLSv13(
    cipher_suite='TLS_CHACHA20_POLY1305_SHA256',
    psk_mode=True  # Pre-shared keys for IoT
)

# Pre-provisioned symmetric key
psk = bytes.fromhex('0123456789abcdef' * 8)
psk_identity = b'sensor_device_001'

# Client (IoT device) initiates connection
client_hello = dtls.client_hello(psk_identity)

# Server response
server_hello = dtls.server_hello()

# Establish encrypted channel
dtls.establish_session(psk)

# Send encrypted data over UDP
encrypted_packet = dtls.encrypt_packet(
    b"sensor reading: temperature=22.5C"
)

print(f"Encrypted packet: {encrypted_packet.hex()[:64]}...")
print("✓ UDP packets encrypted with DTLS 1.3")
""",
                    "explanation": "DTLS provides TLS security for UDP. 1.3 version reduces handshake overhead - critical for battery life."
                },
                {
                    "step": 6,
                    "title": "Hardware Security Modules (HSM) Integration",
                    "description": "Using secure elements and TPMs for key storage",
                    "code_example": """
from cipher_genius.lightweight.secure_element import SecureElement

# Interface with hardware security module
se = SecureElement(interface='I2C', device='ATECC608')

# Generate key in secure element (never leaves chip)
key_slot = 0
se.generate_key(slot=key_slot, key_type='ECC-P256')

# Sign data using hardware key
data = b"authenticate this message"
signature = se.sign(slot=key_slot, data=data)

# Public key can be exported, private key cannot
public_key = se.get_public_key(slot=key_slot)

print(f"Public key: {public_key.hex()[:32]}...")
print("✓ Private key protected by hardware")
print("✓ Resistant to physical attacks")
""",
                    "explanation": "Secure elements provide tamper resistance, key storage, and crypto acceleration. Essential for high-security IoT."
                },
                {
                    "step": 7,
                    "title": "Power Analysis Attack Mitigation",
                    "description": "Implementing side-channel resistant code",
                    "explanation": """
Side-Channel Attacks on IoT:
- Power analysis (SPA/DPA)
- Timing attacks
- EM radiation
- Fault injection

Countermeasures:
1. Constant-time algorithms (X25519, ChaCha20)
2. Blinding/masking of secret operations
3. Random delays (with caution)
4. Hardware countermeasures (secure elements)

Code Practices:
- No secret-dependent branches
- No secret-dependent memory access patterns
- Use constant-time comparisons
- Avoid cache-timing vulnerabilities
""",
                    "code_example": """
from cipher_genius.lightweight.constant_time import ct_compare

# Wrong: timing leak
def insecure_compare(a, b):
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x != y:  # Exits early! Timing leak
            return False
    return True

# Right: constant time
def secure_compare(a, b):
    return ct_compare(a, b)  # Always same time

# Test
key1 = b"secret_key_1234567890"
key2 = b"secret_key_1234567899"

# Secure comparison takes same time regardless of where difference is
result = secure_compare(key1, key2)
print(f"Match: {result}")
print("✓ No timing leaks")
""",
                },
                {
                    "step": 8,
                    "title": "Practice Exercise",
                    "description": "Build a complete IoT security system",
                    "task": """
Implement an end-to-end IoT security solution:
1. Device provisioning with unique keys
2. Mutual authentication (device ↔ gateway)
3. Encrypted sensor data transmission
4. Secure firmware update mechanism
5. Key rotation protocol
6. Power consumption analysis

Constraints:
- Target: ARM Cortex-M4 @ 48 MHz
- RAM: 64 KB
- Flash: 256 KB
- Battery life: >1 year
""",
                    "validation": """
Verify:
- All communications encrypted
- Perfect forward secrecy
- Firmware updates authenticated
- Power consumption <100 µA average
- No timing side channels
- Secure against replay attacks
"""
                }
            ],
            example_requirements="Python 3.8+, cryptography, embedded testing framework",
            expected_output={
                "ascon_encryption": True,
                "x25519_key_exchange": True,
                "ed25519_signatures": True,
                "dtls_session": True,
                "secure_element_integration": True,
                "constant_time_operations": True,
                "power_efficient": True,
                "firmware_verified": True
            }
        )

        return tutorials

    def validate_tutorial_completion(self,
                                    tutorial_id: str,
                                    user_output: Dict) -> Dict[str, Any]:
        """Check if user completed tutorial correctly"""
        tutorial = self.get_tutorial(tutorial_id)

        if not tutorial:
            return {
                "valid": False,
                "error": f"Tutorial '{tutorial_id}' not found"
            }

        expected = tutorial.expected_output
        validation_results = {
            "tutorial_id": tutorial_id,
            "tutorial_title": tutorial.title,
            "passed": True,
            "checks": [],
            "score": 0,
            "total_checks": 0,
            "feedback": []
        }

        # Validate each expected output
        for key, expected_value in expected.items():
            validation_results["total_checks"] += 1
            user_value = user_output.get(key)

            check_result = {
                "check": key,
                "expected": expected_value,
                "actual": user_value,
                "passed": False
            }

            # Type-specific validation
            if isinstance(expected_value, bool):
                check_result["passed"] = user_value is True
            elif isinstance(expected_value, dict):
                # For nested dictionaries, check all keys present
                check_result["passed"] = all(
                    k in user_value and user_value[k] == v
                    for k, v in expected_value.items()
                ) if isinstance(user_value, dict) else False
            elif isinstance(expected_value, list):
                check_result["passed"] = set(expected_value) == set(user_value or [])
            else:
                check_result["passed"] = user_value == expected_value

            validation_results["checks"].append(check_result)

            if check_result["passed"]:
                validation_results["score"] += 1
            else:
                validation_results["passed"] = False
                validation_results["feedback"].append(
                    f"Check '{key}' failed: expected {expected_value}, got {user_value}"
                )

        # Calculate percentage score
        if validation_results["total_checks"] > 0:
            validation_results["score_percentage"] = (
                validation_results["score"] / validation_results["total_checks"]
            ) * 100
        else:
            validation_results["score_percentage"] = 0

        # Add feedback based on score
        if validation_results["passed"]:
            validation_results["feedback"].append(
                f"Excellent! You've successfully completed the '{tutorial.title}' tutorial."
            )
            validation_results["next_steps"] = self._suggest_next_tutorial(tutorial)
        elif validation_results["score_percentage"] >= 70:
            validation_results["feedback"].append(
                "Good progress! Review the failed checks and try again."
            )
        else:
            validation_results["feedback"].append(
                "Keep practicing! Review the tutorial steps carefully."
            )

        return validation_results

    def _suggest_next_tutorial(self, completed_tutorial: Tutorial) -> List[str]:
        """Suggest next tutorials based on completed one"""
        difficulty_progression = {
            "beginner": "intermediate",
            "intermediate": "advanced",
            "advanced": "advanced"
        }

        next_difficulty = difficulty_progression.get(completed_tutorial.difficulty)
        suggestions = []

        # Suggest tutorials of next difficulty level
        for tutorial in self.get_tutorials_by_difficulty(next_difficulty):
            if tutorial.id != completed_tutorial.id:
                suggestions.append(tutorial.id)

        # If no higher difficulty, suggest other tutorials at same level
        if not suggestions:
            for tutorial in self.get_tutorials_by_difficulty(completed_tutorial.difficulty):
                if tutorial.id != completed_tutorial.id:
                    suggestions.append(tutorial.id)

        return suggestions[:3]  # Return up to 3 suggestions

    def get_tutorial_summary(self) -> Dict[str, Any]:
        """Get summary of all tutorials"""
        summary = {
            "total_tutorials": len(self.tutorials),
            "by_difficulty": {
                "beginner": len(self.get_tutorials_by_difficulty("beginner")),
                "intermediate": len(self.get_tutorials_by_difficulty("intermediate")),
                "advanced": len(self.get_tutorials_by_difficulty("advanced"))
            },
            "total_duration_minutes": sum(
                t.duration_minutes for t in self.tutorials.values()
            ),
            "tutorials": [
                {
                    "id": t.id,
                    "title": t.title,
                    "difficulty": t.difficulty,
                    "duration_minutes": t.duration_minutes,
                    "steps_count": len(t.steps)
                }
                for t in self.tutorials.values()
            ]
        }
        return summary


# Example usage
if __name__ == "__main__":
    manager = TutorialManager()

    # Display tutorial summary
    summary = manager.get_tutorial_summary()
    print("=== BuildTrust Tutorial System ===")
    print(f"Total Tutorials: {summary['total_tutorials']}")
    print(f"Total Duration: {summary['total_duration_minutes']} minutes")
    print(f"\nBy Difficulty:")
    for difficulty, count in summary['by_difficulty'].items():
        print(f"  {difficulty.capitalize()}: {count}")

    print("\n=== Available Tutorials ===")
    for tutorial_info in summary['tutorials']:
        print(f"\n[{tutorial_info['id']}]")
        print(f"  Title: {tutorial_info['title']}")
        print(f"  Difficulty: {tutorial_info['difficulty']}")
        print(f"  Duration: {tutorial_info['duration_minutes']} minutes")
        print(f"  Steps: {tutorial_info['steps_count']}")

    # Example: Get a specific tutorial
    print("\n=== Tutorial Details: Getting Started ===")
    tutorial = manager.get_tutorial("getting_started")
    if tutorial:
        print(f"Title: {tutorial.title}")
        print(f"Description: {tutorial.description}")
        print(f"\nSteps:")
        for step in tutorial.steps:
            print(f"  Step {step['step']}: {step['title']}")
