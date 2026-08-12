"""
Enhanced Interactive Tutorial System with Detailed Content
增强版交互式密码学教程系统 - 详细内容版
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class TutorialStep:
    """Enhanced tutorial step with rich content"""
    step: int
    title: str
    description: str
    learning_objectives: List[str] = field(default_factory=list)
    explanation: str = ""
    code_example: str = ""
    code_explanation: List[Dict[str, str]] = field(default_factory=list)  # Line-by-line explanations
    visual_aid: Optional[str] = None  # ASCII art, diagrams, or flowcharts
    common_mistakes: List[str] = field(default_factory=list)
    troubleshooting: List[Dict[str, str]] = field(default_factory=list)
    practice_exercise: Optional[str] = None
    validation_criteria: List[str] = field(default_factory=list)
    further_reading: List[str] = field(default_factory=list)
    quiz_questions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Tutorial:
    """Enhanced tutorial structure with comprehensive content"""
    id: str
    title: str
    description: str
    difficulty: str  # beginner, intermediate, advanced
    duration_minutes: int
    prerequisites: List[str] = field(default_factory=list)
    learning_outcomes: List[str] = field(default_factory=list)
    steps: List[TutorialStep] = field(default_factory=list)
    example_requirements: str = ""
    expected_output: Dict[str, Any] = field(default_factory=dict)
    real_world_applications: List[str] = field(default_factory=list)
    security_considerations: List[str] = field(default_factory=list)
    performance_tips: List[str] = field(default_factory=list)
    additional_resources: List[Dict[str, str]] = field(default_factory=list)


class EnhancedTutorialManager:
    """Manage enhanced interactive tutorials with detailed content"""

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
        """Create enhanced tutorial content"""
        tutorials = {}

        # Tutorial 1: Getting Started - Enhanced with detailed explanations
        tutorials["getting_started"] = Tutorial(
            id="getting_started",
            title="Getting Started with BuildTrust: Your First Trusted Asset",
            description="Master the fundamentals of symmetric encryption using AES-GCM. This comprehensive tutorial covers cryptographic key generation, authenticated encryption, secure decryption, and common pitfalls to avoid.",
            difficulty="beginner",
            duration_minutes=20,
            prerequisites=[
                "Python 3.8 or higher installed",
                "Basic understanding of binary data (bytes)",
                "Familiarity with command line",
                "Text editor or IDE"
            ],
            learning_outcomes=[
                "Understand the difference between encryption and authentication",
                "Generate cryptographically secure keys",
                "Implement AES-GCM encryption and decryption",
                "Handle nonces and authentication tags correctly",
                "Recognize and avoid common encryption mistakes",
                "Validate encrypted data integrity"
            ],
            steps=[
                TutorialStep(
                    step=1,
                    title="Understanding AES-GCM: Why Authenticated Encryption Matters",
                    description="Learn the fundamental concepts before writing code",
                    learning_objectives=[
                        "Understand what AES-GCM provides",
                        "Learn why authentication is critical",
                        "Recognize the components of AEAD"
                    ],
                    explanation="""
**What is AES-GCM?**

AES-GCM (Advanced Encryption Standard - Galois/Counter Mode) is an AEAD
(Authenticated Encryption with Associated Data) cipher that provides THREE
critical security properties:

1. **Confidentiality** - Encrypted data cannot be read without the key
2. **Integrity** - Any modifications to the ciphertext are detected
3. **Authenticity** - Proof that the message came from someone with the key

**Key Components:**
- Plaintext: Your original message
- Key: Secret 128/192/256-bit value (we'll use 256-bit)
- Nonce: Number used once - MUST be unique for each encryption
- Ciphertext: Encrypted output (same length as plaintext)
- Authentication Tag: 128-bit value proving integrity
- Associated Data (optional): Metadata that is authenticated but not encrypted

**Why Not Just Use Encryption Alone?**

Historical attacks on encryption-only systems:
- Padding oracle attacks (millions of websites vulnerable)
- Bit-flipping attacks (modify ciphertext to change plaintext)
- Replay attacks (resend old valid messages)

AES-GCM prevents ALL of these by combining encryption with authentication.
""",
                    visual_aid="""
┌─────────────────────────────────────────────────────────────┐
│                   AES-GCM Encryption Flow                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Plaintext ──┐                                             │
│              ├──→ [AES-GCM Encrypt] ──┬──→ Ciphertext       │
│  Key ────────┤                        │                     │
│  Nonce ──────┤                        └──→ Auth Tag        │
│  AAD ────────┘                                              │
│                                                             │
│  To decrypt, you need:                                      │
│  - Key (same as encryption)                                 │
│  - Nonce (from encryption)                                  │
│  - Ciphertext                                               │
│  - Auth Tag (verifies integrity)                            │
│  - AAD (must match encryption)                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
""",
                    common_mistakes=[
                        "Using the same nonce twice with the same key (CATASTROPHIC!)",
                        "Not verifying the authentication tag before using plaintext",
                        "Storing the key in plaintext alongside encrypted data",
                        "Using weak random number generators for key/nonce",
                        "Forgetting to transmit the nonce with the ciphertext"
                    ],
                    quiz_questions=[
                        {
                            "question": "What happens if you reuse a nonce with AES-GCM?",
                            "options": [
                                "Nothing, it's safe",
                                "Performance degradation",
                                "Complete loss of confidentiality and authenticity",
                                "Slower decryption"
                            ],
                            "correct": 2,
                            "explanation": "Nonce reuse with AES-GCM is catastrophic - attackers can recover the authentication key and forge messages."
                        },
                        {
                            "question": "What does the authentication tag provide?",
                            "options": [
                                "Additional encryption",
                                "Proof of integrity and authenticity",
                                "Faster decryption",
                                "Compression"
                            ],
                            "correct": 1,
                            "explanation": "The authentication tag is a cryptographic checksum that proves the ciphertext hasn't been tampered with."
                        }
                    ],
                    further_reading=[
                        "NIST SP 800-38D: Recommendation for Block Cipher Modes (GCM)",
                        "RFC 5116: An Interface and Algorithms for Authenticated Encryption",
                        "https://csrc.nist.gov/publications/detail/sp/800-38d/final"
                    ]
                ),
                TutorialStep(
                    step=2,
                    title="Setting Up Your Environment and Importing Modules",
                    description="Install dependencies and import required cryptographic libraries",
                    learning_objectives=[
                        "Install necessary Python packages",
                        "Import cryptographic modules correctly",
                        "Verify installation success"
                    ],
                    code_example="""# Step 1: Install required packages (run in terminal)
# pip install cryptography

# Step 2: Import necessary modules
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import secrets

# Step 3: Verify imports
print("✓ All modules imported successfully")
print(f"cryptography version: {cryptography.__version__}")
""",
                    code_explanation=[
                        {
                            "line": "from cryptography.hazmat.primitives.ciphers.aead import AESGCM",
                            "explanation": "Imports the AES-GCM implementation. 'hazmat' stands for 'hazardous materials' - low-level crypto primitives that require careful use."
                        },
                        {
                            "line": "import os",
                            "explanation": "Provides access to os.urandom() - the operating system's cryptographically secure random number generator."
                        },
                        {
                            "line": "import secrets",
                            "explanation": "Python's secrets module is designed for generating cryptographically strong random numbers suitable for security/cryptography."
                        }
                    ],
                    common_mistakes=[
                        "Using 'random' module instead of 'secrets' for cryptographic operations",
                        "Not checking if cryptography package is installed",
                        "Using outdated versions with known vulnerabilities"
                    ],
                    troubleshooting=[
                        {
                            "error": "ModuleNotFoundError: No module named 'cryptography'",
                            "solution": "Run: pip install cryptography --upgrade"
                        },
                        {
                            "error": "ImportError: cannot import name 'AESGCM'",
                            "solution": "Update cryptography: pip install cryptography>=3.4"
                        }
                    ]
                ),
                TutorialStep(
                    step=3,
                    title="Generating a Cryptographically Secure Key",
                    description="Create a secure 256-bit encryption key using best practices",
                    learning_objectives=[
                        "Understand key size requirements",
                        "Generate secure random keys",
                        "Store keys safely"
                    ],
                    explanation="""
**Key Generation Best Practices:**

1. **Key Size**: Use 256-bit (32 bytes) for long-term security
   - 128-bit: Sufficient for most applications
   - 192-bit: Rare, offers middle ground
   - 256-bit: Maximum security, future-proof

2. **Randomness Source**: ALWAYS use cryptographically secure RNG
   - ✓ secrets.token_bytes() - Python's secure generator
   - ✓ os.urandom() - OS-level entropy
   - ✗ random.randbytes() - NOT cryptographically secure!

3. **Key Storage**: NEVER hardcode keys in source code
   - Use environment variables
   - Use key management services (AWS KMS, Azure Key Vault)
   - Use hardware security modules (HSM) for production
""",
                    code_example="""# Method 1: Using secrets module (RECOMMENDED)
encryption_key = secrets.token_bytes(32)  # 32 bytes = 256 bits
print(f"Key length: {len(encryption_key)} bytes")
print(f"Key (hex): {encryption_key.hex()[:32]}...")  # Show first 16 bytes

# Method 2: Using os.urandom (also secure)
encryption_key_alt = os.urandom(32)

# Method 3: Derive key from password (for password-based encryption)
password = b"user_password_here"
salt = os.urandom(16)  # Random salt

kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=600000,  # OWASP recommendation (2023)
)
derived_key = kdf.derive(password)
print(f"Derived key (hex): {derived_key.hex()[:32]}...")

# IMPORTANT: Store the salt with the ciphertext!
# You'll need it to derive the same key for decryption
""",
                    code_explanation=[
                        {
                            "line": "encryption_key = secrets.token_bytes(32)",
                            "explanation": "Generates 32 random bytes (256 bits) using a cryptographically secure source. This is your encryption key - keep it secret!"
                        },
                        {
                            "line": "iterations=600000",
                            "explanation": "PBKDF2 iterations slow down brute-force attacks. 600,000 is the 2023 OWASP recommendation for PBKDF2-HMAC-SHA256."
                        },
                        {
                            "line": "salt = os.urandom(16)",
                            "explanation": "Salt ensures different keys are derived from the same password. Must be random and stored with the ciphertext."
                        }
                    ],
                    visual_aid="""
Key Generation Methods:

┌────────────────────┐
│ Random Key Gen     │  ← Best for most use cases
│ (secrets module)   │    Fast, secure, simple
└────────────────────┘

┌────────────────────┐
│ Password-Based     │  ← When users provide passwords
│ (PBKDF2)           │    Slower, resistant to brute force
└────────────────────┘

Key Security Levels:
128-bit: 2^128 possibilities (340 undecillion)
256-bit: 2^256 possibilities (10^77 - more than atoms in universe!)
""",
                    common_mistakes=[
                        "Using random.randbytes() instead of secrets.token_bytes()",
                        "Generating keys with insufficient entropy (predictable patterns)",
                        "Reusing the same key for different purposes",
                        "Not using a salt with password-based key derivation",
                        "Using too few PBKDF2 iterations (<100,000)"
                    ],
                    practice_exercise="""
**Exercise**: Create a function that generates a key and saves it securely

Requirements:
1. Generate a 256-bit AES key
2. Save it to a file with proper permissions (read-only for owner)
3. Load it back and verify it's the same
4. Handle errors gracefully

Bonus: Add key rotation functionality
""",
                    validation_criteria=[
                        "Key is exactly 32 bytes (256 bits)",
                        "Key is different each time (randomness check)",
                        "File permissions restrict access to owner only",
                        "Can successfully load and match original key"
                    ]
                ),
                TutorialStep(
                    step=4,
                    title="Encrypting Your First Message",
                    description="Implement secure encryption with AES-GCM",
                    learning_objectives=[
                        "Initialize AES-GCM cipher",
                        "Generate unique nonces",
                        "Encrypt data with authentication",
                        "Handle associated data correctly"
                    ],
                    explanation="""
**Encryption Process Step-by-Step:**

1. **Initialize cipher**: Create AESGCM instance with your key
2. **Generate nonce**: Create a unique 96-bit (12 bytes) random value
3. **Prepare data**: Convert your message to bytes
4. **Encrypt**: Call encrypt() with nonce, plaintext, and optional AAD
5. **Store all components**: You need nonce + ciphertext + tag for decryption

**Critical: Nonce Management**

The nonce (Number Used Once) MUST be unique for every encryption with the same key.

Options for nonce generation:
- Random (12 bytes): Collision risk after 2^32 encryptions
- Counter: Requires state management but guaranteed unique
- Timestamp + random: Hybrid approach

For most applications, random nonces are fine if you don't encrypt billions of messages.
""",
                    code_example="""# Initialize AES-GCM cipher with your key
aesgcm = AESGCM(encryption_key)

# Your plaintext message
plaintext = b"Hello, BuildTrust! This is my first trusted asset."
print(f"Original message: {plaintext.decode()}")
print(f"Message length: {len(plaintext)} bytes")

# Generate a unique nonce (96 bits = 12 bytes for GCM)
nonce = os.urandom(12)
print(f"Nonce (hex): {nonce.hex()}")

# Optional: Associated data (authenticated but not encrypted)
# This is perfect for headers, metadata, protocol version, etc.
associated_data = b"version=1.0,timestamp=2025-10-21,user=alice"
print(f"Associated data: {associated_data.decode()}")

# Encrypt the message
# Returns: ciphertext with authentication tag appended (last 16 bytes)
ciphertext_with_tag = aesgcm.encrypt(
    nonce=nonce,
    plaintext=plaintext,
    associated_data=associated_data  # Can be None if not needed
)

# The ciphertext includes the 16-byte authentication tag at the end
ciphertext = ciphertext_with_tag[:-16]  # Actual encrypted data
auth_tag = ciphertext_with_tag[-16:]    # Authentication tag

print(f"\\nEncryption Results:")
print(f"Ciphertext (hex): {ciphertext.hex()[:64]}...")
print(f"Ciphertext length: {len(ciphertext)} bytes (same as plaintext)")
print(f"Auth tag (hex): {auth_tag.hex()}")
print(f"Auth tag length: {len(auth_tag)} bytes (always 16 for GCM)")

# What you need to store/transmit:
# 1. Ciphertext + tag (or combined ciphertext_with_tag)
# 2. Nonce (NOT secret, but must be transmitted)
# 3. Associated data (if used)
# Note: The key stays secret and is NOT transmitted
print(f"\\nTo decrypt, you need:")
print(f"- Key (secret, {len(encryption_key)} bytes)")
print(f"- Nonce ({len(nonce)} bytes)")
print(f"- Ciphertext + Tag ({len(ciphertext_with_tag)} bytes)")
print(f"- Associated data ({len(associated_data)} bytes)")
""",
                    code_explanation=[
                        {
                            "line": "aesgcm = AESGCM(encryption_key)",
                            "explanation": "Creates an AES-GCM cipher object. The key size (16/24/32 bytes) determines whether you're using AES-128/192/256."
                        },
                        {
                            "line": "nonce = os.urandom(12)",
                            "explanation": "GCM uses 96-bit (12 byte) nonces. Larger nonces are possible but less efficient. NEVER reuse a nonce with the same key!"
                        },
                        {
                            "line": "associated_data=associated_data",
                            "explanation": "This data is authenticated (integrity-protected) but NOT encrypted. Perfect for packet headers, metadata, or protocol info."
                        },
                        {
                            "line": "ciphertext_with_tag = aesgcm.encrypt(...)",
                            "explanation": "Returns ciphertext with 16-byte authentication tag appended. Total length = plaintext_length + 16."
                        }
                    ],
                    visual_aid="""
Encryption Workflow:

Input:                          Output:
┌──────────────┐               ┌──────────────┐
│  Plaintext   │──┐            │ Ciphertext   │
└──────────────┘  │            └──────────────┘
                  │                    ▲
┌──────────────┐  │                    │
│     Key      │──┼────→ [AES-GCM] ───┤
└──────────────┘  │       Encrypt      │
                  │                    │
┌──────────────┐  │            ┌──────────────┐
│    Nonce     │──┘            │   Auth Tag   │
└──────────────┘               └──────────────┘

Storage/Transmission Format:
┌─────────┬──────────────┬──────────┐
│  Nonce  │  Ciphertext  │ Auth Tag │
│ 12 bytes│   N bytes    │ 16 bytes │
└─────────┴──────────────┴──────────┘
""",
                    common_mistakes=[
                        "Reusing the same nonce for multiple encryptions (CRITICAL ERROR!)",
                        "Not storing/transmitting the nonce with the ciphertext",
                        "Encrypting the associated data (it should remain plaintext)",
                        "Using wrong nonce size (should be 12 bytes for efficiency)",
                        "Not handling the authentication tag correctly"
                    ],
                    troubleshooting=[
                        {
                            "error": "ValueError: Nonce must be 96 bits",
                            "solution": "Use os.urandom(12) to generate a 12-byte (96-bit) nonce"
                        },
                        {
                            "error": "TypeError: plaintext must be bytes-like",
                            "solution": "Convert strings to bytes using .encode(): plaintext = 'message'.encode()"
                        }
                    ]
                ),
                TutorialStep(
                    step=5,
                    title="Decrypting and Verifying the Message",
                    description="Safely decrypt data and verify authenticity",
                    learning_objectives=[
                        "Implement secure decryption",
                        "Verify authentication tags",
                        "Handle decryption failures properly",
                        "Detect tampering attempts"
                    ],
                    explanation="""
**Decryption Process:**

1. **Gather all components**: Key, nonce, ciphertext+tag, AAD
2. **Call decrypt()**: AES-GCM verifies the tag BEFORE decrypting
3. **Handle success**: If tag is valid, plaintext is returned
4. **Handle failure**: If tag is invalid, exception is raised

**Critical Security Point:**

AES-GCM decryption FIRST verifies the authentication tag, then decrypts.
This prevents attackers from:
- Modifying ciphertext
- Replaying old messages
- Mounting chosen-ciphertext attacks

NEVER use plaintext if tag verification fails!
""",
                    code_example="""# Decryption: Recover the original message
# You need: key, nonce, ciphertext+tag, and associated_data (if used)

try:
    # Decrypt and verify authentication
    decrypted_plaintext = aesgcm.decrypt(
        nonce=nonce,                      # Same nonce used for encryption
        ciphertext=ciphertext_with_tag,   # Ciphertext + tag
        associated_data=associated_data   # Must match encryption AAD
    )

    print("✓ Authentication tag verified successfully!")
    print(f"✓ Ciphertext integrity confirmed")
    print(f"Decrypted message: {decrypted_plaintext.decode()}")

    # Verify it matches original
    assert decrypted_plaintext == plaintext
    print("✓ Decryption successful - message matches original!")

except Exception as e:
    # Tag verification failed - DO NOT use the plaintext!
    print(f"✗ Decryption failed: {e}")
    print("✗ Message may have been tampered with!")
    print("✗ NEVER use data that fails authentication!")
    # In production: log the error, alert security team, discard data

# Demonstrate tampering detection
print("\\n--- Tampering Detection Demo ---")
tampered_ciphertext = bytearray(ciphertext_with_tag)
tampered_ciphertext[0] ^= 0x01  # Flip one bit

try:
    aesgcm.decrypt(nonce, bytes(tampered_ciphertext), associated_data)
    print("ERROR: Should have detected tampering!")
except Exception as e:
    print(f"✓ Tampering detected: {type(e).__name__}")
    print("✓ System correctly rejected modified ciphertext")

# Demonstrate AAD verification
print("\\n--- Associated Data Verification Demo ---")
wrong_aad = b"version=2.0,timestamp=2025-10-22,user=eve"

try:
    aesgcm.decrypt(nonce, ciphertext_with_tag, wrong_aad)
    print("ERROR: Should have detected wrong AAD!")
except Exception as e:
    print(f"✓ Wrong AAD detected: {type(e).__name__}")
    print("✓ Associated data must match exactly")
""",
                    code_explanation=[
                        {
                            "line": "decrypted_plaintext = aesgcm.decrypt(...)",
                            "explanation": "Verifies the authentication tag FIRST, then decrypts. If tag is invalid, raises InvalidTag exception without returning plaintext."
                        },
                        {
                            "line": "associated_data=associated_data",
                            "explanation": "AAD must EXACTLY match what was used during encryption. Even one bit difference will cause authentication failure."
                        },
                        {
                            "line": "except Exception as e:",
                            "explanation": "Always handle decryption errors. Tag verification failures indicate tampering or corruption - NEVER use the data!"
                        }
                    ],
                    visual_aid="""
Decryption Workflow:

Input:
┌──────────────┐
│ Ciphertext   │──┐
└──────────────┘  │
                  │
┌──────────────┐  │
│   Auth Tag   │──┤
└──────────────┘  │
                  │
┌──────────────┐  │           [Tag Valid?]
│     Key      │──┼──→ [AES-GCM] ─→ Yes ──→ Plaintext ✓
└──────────────┘  │    Decrypt      │
                  │                 No ──→ Exception ✗
┌──────────────┐  │                        (REJECT DATA)
│    Nonce     │──┘
└──────────────┘

Security Guarantee:
If decrypt() returns data, it is GUARANTEED to be:
✓ Authentic (created by someone with the key)
✓ Intact (not modified)
✓ Fresh (associated data matches)
""",
                    common_mistakes=[
                        "Using plaintext even after tag verification fails",
                        "Not handling decryption exceptions properly",
                        "Using wrong nonce for decryption",
                        "Mismatched associated data between encryption/decryption",
                        "Continuing operation after detecting tampering"
                    ],
                    troubleshooting=[
                        {
                            "error": "InvalidTag exception during decryption",
                            "solution": "Check: (1) Correct key, (2) Correct nonce, (3) Matching AAD, (4) Ciphertext not corrupted"
                        },
                        {
                            "error": "UnicodeDecodeError when converting to string",
                            "solution": "Ensure the decrypted bytes are valid UTF-8: plaintext.decode('utf-8', errors='replace')"
                        }
                    ],
                    quiz_questions=[
                        {
                            "question": "What should you do if decrypt() raises an InvalidTag exception?",
                            "options": [
                                "Try decrypting again with a different nonce",
                                "Use the plaintext anyway, it's probably fine",
                                "Discard the data and log a security event",
                                "Ask the user to re-send the data"
                            ],
                            "correct": 2,
                            "explanation": "InvalidTag means tampering or corruption. NEVER use the data - discard it and investigate."
                        }
                    ]
                ),
                TutorialStep(
                    step=6,
                    title="Complete Implementation: Putting It All Together",
                    description="Build a production-ready encryption/decryption system",
                    learning_objectives=[
                        "Implement proper error handling",
                        "Create reusable encryption functions",
                        "Handle edge cases correctly",
                        "Follow security best practices"
                    ],
                    code_example="""import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typing import Tuple, Optional
import secrets
import json
import base64

class SecureMessenger:
    \"\"\"Production-ready AES-GCM encryption system\"\"\"

    def __init__(self, key: Optional[bytes] = None):
        \"\"\"Initialize with existing key or generate new one\"\"\"
        if key is None:
            self.key = secrets.token_bytes(32)  # 256-bit key
        else:
            if len(key) not in [16, 24, 32]:
                raise ValueError("Key must be 16, 24, or 32 bytes")
            self.key = key

        self.cipher = AESGCM(self.key)

    def encrypt_message(self,
                       plaintext: bytes,
                       associated_data: Optional[bytes] = None) -> dict:
        \"\"\"
        Encrypt a message with AES-GCM

        Returns:
            dict with 'nonce', 'ciphertext', 'tag' (all base64-encoded)
        \"\"\"
        # Generate unique nonce
        nonce = os.urandom(12)

        # Encrypt with authentication
        ciphertext_with_tag = self.cipher.encrypt(
            nonce=nonce,
            plaintext=plaintext,
            associated_data=associated_data
        )

        # Separate ciphertext and tag for clarity
        ciphertext = ciphertext_with_tag[:-16]
        tag = ciphertext_with_tag[-16:]

        # Return as dictionary (easy to serialize to JSON)
        return {
            'nonce': base64.b64encode(nonce).decode('ascii'),
            'ciphertext': base64.b64encode(ciphertext).decode('ascii'),
            'tag': base64.b64encode(tag).decode('ascii'),
            'aad': base64.b64encode(associated_data).decode('ascii') if associated_data else None
        }

    def decrypt_message(self, encrypted_data: dict) -> bytes:
        \"\"\"
        Decrypt and verify a message

        Raises:
            ValueError: If authentication fails or data is corrupted
        \"\"\"
        try:
            # Decode from base64
            nonce = base64.b64decode(encrypted_data['nonce'])
            ciphertext = base64.b64decode(encrypted_data['ciphertext'])
            tag = base64.b64decode(encrypted_data['tag'])
            aad = base64.b64decode(encrypted_data['aad']) if encrypted_data.get('aad') else None

            # Combine ciphertext and tag
            ciphertext_with_tag = ciphertext + tag

            # Decrypt and verify
            plaintext = self.cipher.decrypt(
                nonce=nonce,
                ciphertext=ciphertext_with_tag,
                associated_data=aad
            )

            return plaintext

        except Exception as e:
            raise ValueError(f"Decryption failed - possible tampering: {e}")

    def export_key(self) -> str:
        \"\"\"Export key as base64 (store securely!)\"\"\"
        return base64.b64encode(self.key).decode('ascii')

    @classmethod
    def from_key(cls, key_b64: str):
        \"\"\"Create instance from base64-encoded key\"\"\"
        key = base64.b64decode(key_b64)
        return cls(key)


# Example Usage
if __name__ == "__main__":
    print("=== Secure Messenger Demo ===\\n")

    # Create messenger (generates new key)
    messenger = SecureMessenger()
    print(f"Generated key: {messenger.export_key()[:32]}...")

    # Encrypt a message
    message = b"This is a confidential message!"
    metadata = b"sender=alice,recipient=bob,priority=high"

    encrypted = messenger.encrypt_message(message, metadata)
    print(f"\\nEncrypted message:")
    print(json.dumps(encrypted, indent=2))

    # Decrypt the message
    decrypted = messenger.decrypt_message(encrypted)
    print(f"\\nDecrypted: {decrypted.decode()}")

    # Demonstrate tampering detection
    print("\\n--- Tampering Detection ---")
    tampered = encrypted.copy()
    tampered['ciphertext'] = base64.b64encode(
        bytes([b ^ 1 for b in base64.b64decode(encrypted['ciphertext'])])
    ).decode()

    try:
        messenger.decrypt_message(tampered)
        print("ERROR: Failed to detect tampering!")
    except ValueError as e:
        print(f"✓ Tampering detected: {e}")

    print("\\n✓ All security checks passed!")
""",
                    practice_exercise="""
**Final Exercise: Secure File Encryption**

Create a command-line tool that:

1. **Encrypt files**:
   - Accept filename as input
   - Read file contents
   - Encrypt with AES-GCM
   - Save as .encrypted file with metadata (nonce, tag)

2. **Decrypt files**:
   - Read .encrypted file
   - Verify authenticity
   - Restore original file

3. **Key management**:
   - Generate and store key securely
   - Support key rotation
   - Export/import keys

4. **Advanced features**:
   - Progress bar for large files
   - Chunked encryption (for files >1GB)
   - Integrity verification
   - Secure key derivation from passphrase

Bonus challenges:
- Add compression before encryption
- Support directory encryption
- Implement key splitting (Shamir's Secret Sharing)
- Add metadata encryption
""",
                    validation_criteria=[
                        "Successfully encrypts and decrypts files",
                        "Detects any tampering or corruption",
                        "Keys are stored securely (not in plaintext)",
                        "Handles errors gracefully",
                        "Works with various file sizes",
                        "Proper nonce management (no reuse)",
                        "Clean code with documentation"
                    ]
                )
            ],
            real_world_applications=[
                "HTTPS/TLS 1.3 - AES-GCM is the most common cipher suite",
                "SSH - Secure shell uses AES-GCM for session encryption",
                "VPNs - WireGuard and IPsec use ChaCha20-Poly1305 or AES-GCM",
                "Disk encryption - LUKS and BitLocker support AES-GCM",
                "Messaging apps - Signal, WhatsApp use AEAD modes",
                "Cloud storage - AWS S3, Google Cloud use AES-GCM for encryption at rest",
                "Payment systems - PCI DSS requires authenticated encryption"
            ],
            security_considerations=[
                "Nonce uniqueness is CRITICAL - use counters for high-volume systems",
                "Key rotation: Change keys periodically (every 2^32 encryptions max for random nonces)",
                "Key storage: Use HSMs or KMS for production systems",
                "Side-channel attacks: Consider constant-time implementations for sensitive applications",
                "Cryptographic agility: Design systems to support algorithm changes",
                "Audit logging: Log all encryption/decryption operations (but NOT keys!)",
                "Disaster recovery: Securely backup encryption keys with access controls"
            ],
            performance_tips=[
                "Hardware acceleration: Use AES-NI CPU instructions (10-20x faster)",
                "Batch operations: Encrypt multiple messages with same setup",
                "Chunking: For large files, encrypt in 64KB chunks",
                "Asynchronous operations: Use async/await for I/O-bound encryption",
                "Memory management: Reuse buffers to reduce allocations",
                "Profile first: Measure before optimizing - crypto is usually not the bottleneck"
            ],
            additional_resources=[
                {
                    "title": "Coursera - Cryptography I (Stanford)",
                    "url": "https://www.coursera.org/learn/crypto",
                    "type": "Course"
                },
                {
                    "title": "Serious Cryptography by Jean-Philippe Aumasson",
                    "url": "https://nostarch.com/seriouscrypto",
                    "type": "Book"
                },
                {
                    "title": "NIST Cryptographic Standards",
                    "url": "https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines",
                    "type": "Reference"
                }
            ],
            example_requirements="Python 3.8+, cryptography>=3.4",
            expected_output={
                "encrypted": True,
                "decrypted": True,
                "authentication_verified": True,
                "tampering_detected": True,
                "key_size_bits": 256
            }
        )

        # Additional tutorials would be enhanced similarly...
        # For brevity, I'll add headers for other tutorials

        tutorials["advanced_key_management"] = Tutorial(
            id="advanced_key_management",
            title="Advanced Key Management and Rotation",
            description="Master secure key generation, storage, rotation, and lifecycle management for production systems.",
            difficulty="intermediate",
            duration_minutes=30,
            prerequisites=["Understanding of symmetric/asymmetric encryption", "Completed Getting Started tutorial"],
            learning_outcomes=[
                "Implement secure key generation and storage",
                "Design key rotation strategies",
                "Use key derivation functions (HKDF, PBKDF2)",
                "Integrate with key management services (KMS)",
                "Implement multi-tenant key isolation"
            ],
            steps=[],  # Would be populated with detailed steps
            real_world_applications=[
                "AWS KMS, Azure Key Vault, Google Cloud KMS",
                "HashiCorp Vault",
                "Database encryption key management",
                "Multi-tenant SaaS applications"
            ]
        )

        tutorials["cryptographic_protocols"] = Tutorial(
            id="cryptographic_protocols",
            title="Building Secure Cryptographic Protocols",
            description="Learn to design and implement secure communication protocols, including handshakes, perfect forward secrecy, and mutual authentication.",
            difficulty="advanced",
            duration_minutes=45,
            prerequisites=["Key management", "AEAD encryption", "Digital signatures"],
            learning_outcomes=[
                "Design secure handshake protocols",
                "Implement perfect forward secrecy (PFS)",
                "Understand and prevent cryptographic protocol attacks",
                "Build mutual authentication systems",
                "Implement secure session management"
            ],
            steps=[],  # Would be populated
            real_world_applications=[
                "TLS 1.3 handshake",
                "SSH protocol",
                "Signal Protocol (Double Ratchet)",
                "Noise Protocol Framework"
            ]
        )

        return tutorials

    def validate_tutorial_completion(self, tutorial_id: str, user_output: Dict) -> Dict[str, Any]:
        """Enhanced validation with detailed feedback"""
        tutorial = self.get_tutorial(tutorial_id)

        if not tutorial:
            return {"valid": False, "error": f"Tutorial '{tutorial_id}' not found"}

        # Comprehensive validation logic
        results = {
            "tutorial_id": tutorial_id,
            "tutorial_title": tutorial.title,
            "passed": True,
            "score": 0,
            "max_score": len(tutorial.expected_output),
            "checks": [],
            "feedback": [],
            "next_recommended": []
        }

        # Validate each expected output
        for key, expected in tutorial.expected_output.items():
            actual = user_output.get(key)
            passed = actual == expected

            results["checks"].append({
                "item": key,
                "expected": expected,
                "actual": actual,
                "passed": passed
            })

            if passed:
                results["score"] += 1
            else:
                results["passed"] = False
                results["feedback"].append(f"❌ {key}: Expected {expected}, got {actual}")

        # Calculate percentage
        results["percentage"] = (results["score"] / results["max_score"] * 100) if results["max_score"] > 0 else 0

        # Provide feedback
        if results["passed"]:
            results["feedback"].insert(0, f"🎉 Congratulations! You've completed '{tutorial.title}'")
            results["next_recommended"] = self._suggest_next_tutorials(tutorial)
        elif results["percentage"] >= 70:
            results["feedback"].insert(0, "👍 Good progress! Review the failed items.")
        else:
            results["feedback"].insert(0, "📚 Keep learning! Review the tutorial carefully.")

        return results

    def _suggest_next_tutorials(self, completed: Tutorial) -> List[str]:
        """Suggest next tutorials based on progression"""
        suggestions = []

        # Difficulty progression
        if completed.difficulty == "beginner":
            suggestions.extend([t.id for t in self.get_tutorials_by_difficulty("intermediate")][:2])
        elif completed.difficulty == "intermediate":
            suggestions.extend([t.id for t in self.get_tutorials_by_difficulty("advanced")][:2])

        return suggestions

    def get_tutorial_summary(self) -> Dict[str, Any]:
        """Get comprehensive tutorial statistics"""
        return {
            "total_tutorials": len(self.tutorials),
            "total_steps": sum(len(t.steps) for t in self.tutorials.values()),
            "total_duration_minutes": sum(t.duration_minutes for t in self.tutorials.values()),
            "by_difficulty": {
                level: len(self.get_tutorials_by_difficulty(level))
                for level in ["beginner", "intermediate", "advanced"]
            },
            "tutorials": [
                {
                    "id": t.id,
                    "title": t.title,
                    "difficulty": t.difficulty,
                    "duration": t.duration_minutes,
                    "steps": len(t.steps),
                    "prerequisites": len(t.prerequisites),
                    "learning_outcomes": len(t.learning_outcomes)
                }
                for t in self.tutorials.values()
            ]
        }
