"""
Encrypt and decrypt .env files for production deployments.
Uses Fernet symmetric encryption (AES-128 in CBC mode).

This allows you to store your .env file encrypted on disk,
protecting your secrets even if the server is compromised.

Usage:
    # Generate a new encryption key (SAVE THIS SECURELY!)
    from config.secrets.encryption import EnvFileEncryptor
    key = EnvFileEncryptor().get_key()
    print(f"Your encryption key: {key}")
    
    # Encrypt your .env file
    encryptor = EnvFileEncryptor(key)
    encryptor.encrypt_file('.env', '.env.enc')
    
    # Decrypt for deployment
    encryptor.decrypt_file('.env.enc', '.env')
"""

from cryptography.fernet import Fernet
from pathlib import Path
import os
import base64
import hashlib
import logging

logger = logging.getLogger(__name__)


SALT_HEADER = "MCENV1"
PBKDF2_ITERATIONS = 600_000


def _is_fernet_key(key: str) -> bool:
    """Return True if key is a valid 32-byte url-safe base64 Fernet key."""
    if not isinstance(key, str) or len(key) != 44 or not key.endswith("="):
        return False
    try:
        return len(base64.urlsafe_b64decode(key.encode())) == 32
    except (ValueError, TypeError):
        return False


def _derive_fernet_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 32-byte Fernet key from a passphrase using PBKDF2-HMAC-SHA256."""
    derived = hashlib.pbkdf2_hmac(
        "sha256", passphrase.encode(), salt, PBKDF2_ITERATIONS
    )
    return base64.urlsafe_b64encode(derived)


def _legacy_fernet_key(key: str) -> bytes:
    """Legacy key derivation (space-padded/truncated) used only to decrypt
    files encrypted by previous versions of this module."""
    return base64.urlsafe_b64encode(key.ljust(32)[:32].encode())


class EnvFileEncryptor:
    """Encrypt and decrypt .env files using Fernet symmetric encryption.

    Key handling:
    - No key: a full-entropy Fernet key is generated (get_key() returns it;
      store it verbatim and pass it back for decryption).
    - Fernet key (44-char url-safe base64): used directly.
    - Any other string is treated as a passphrase and stretched with
      PBKDF2-HMAC-SHA256 (600k iterations) using a per-file random salt.
      The salt is stored alongside the ciphertext in a versioned header.
    """

    def __init__(self, key: str = None):
        """
        Initialize with encryption key.
        If no key provided, generates a new one.

        Args:
            key: Encryption key as string. If None, generates new key.
        """
        if key is None:
            self.key = Fernet.generate_key()
            self.cipher = Fernet(self.key)
        elif _is_fernet_key(key):
            self.key = key.encode()
            self.cipher = Fernet(self.key)
        else:
            self.key = key.encode()
            self.cipher = None

    def get_key(self) -> str:
        """Get the encryption key as a string (for secure storage)."""
        return self.key.decode()

    def _encrypt_bytes(self, plaintext: bytes) -> bytes:
        if self.cipher is not None:
            return self.cipher.encrypt(plaintext)
        salt = os.urandom(16)
        cipher = Fernet(_derive_fernet_key(self.key.decode(), salt))
        token = cipher.encrypt(plaintext)
        return (
            f"{SALT_HEADER}:{base64.urlsafe_b64encode(salt).decode()}".encode()
            + b":"
            + token
        )

    def _decrypt_bytes(self, data: bytes) -> bytes:
        if self.cipher is not None:
            return self.cipher.decrypt(data)
        parts = data.split(b":", 2)
        if len(parts) == 3 and parts[0] == SALT_HEADER.encode():
            salt = base64.urlsafe_b64decode(parts[1])
            cipher = Fernet(_derive_fernet_key(self.key.decode(), salt))
            return cipher.decrypt(parts[2])
        return Fernet(_legacy_fernet_key(self.key.decode())).decrypt(data)

    def encrypt_file(self, input_path: str, output_path: str = None):
        """
        Encrypt a .env file.
        
        Args:
            input_path: Path to plaintext .env file
            output_path: Path to save encrypted file (defaults to input_path.enc)
            
        Returns:
            Path to encrypted file
        """
        input_path = Path(input_path)
        if output_path is None:
            output_path = Path(f"{input_path}.enc")
        else:
            output_path = Path(output_path)
        
        with open(input_path, 'rb') as f:
            plaintext = f.read()

        encrypted = self._encrypt_bytes(plaintext)

        with open(output_path, 'wb') as f:
            f.write(encrypted)

        logger.info(f"Encrypted {input_path} -> {output_path}")
        return output_path

    def decrypt_file(self, input_path: str, output_path: str = None):
        """
        Decrypt an encrypted .env file.
        
        Args:
            input_path: Path to encrypted .env file
            output_path: Path to save decrypted file (defaults to .env)
            
        Returns:
            Path to decrypted file
        """
        input_path = Path(input_path)
        if output_path is None:
            output_path = Path('.env')
        else:
            output_path = Path(output_path)
        
        with open(input_path, 'rb') as f:
            encrypted = f.read()

        decrypted = self._decrypt_bytes(encrypted)

        with open(output_path, 'wb') as f:
            f.write(decrypted)

        logger.info(f"Decrypted {input_path} -> {output_path}")
        return output_path

    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt a string."""
        return self._encrypt_bytes(plaintext.encode()).decode()

    def decrypt_string(self, ciphertext: str) -> str:
        """Decrypt a string."""
        return self._decrypt_bytes(ciphertext.encode()).decode()


def get_encryption_key() -> str:
    """
    Get encryption key from environment or file.
    
    Priority:
    1. ENCRYPTION_KEY_FILE environment variable (path to file containing key)
    2. ENCRYPTION_KEY environment variable
    3. /etc/mitocube/encryption_key (default location)
    
    Returns:
        Encryption key as string
        
    Raises:
        ValueError: If no key is found
    """
    # Check for key file path
    key_file = os.environ.get("ENCRYPTION_KEY_FILE", "/etc/mitocube/encryption_key")
    if Path(key_file).exists():
        with open(key_file, 'r') as f:
            return f.read().strip()
    
    # Check for key in environment
    key = os.environ.get("ENCRYPTION_KEY")
    if key:
        return key
    
    raise ValueError(
        "No encryption key found. "
        "Set ENCRYPTION_KEY environment variable or "
        "create /etc/mitocube/encryption_key file."
    )
