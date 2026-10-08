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
import logging

logger = logging.getLogger(__name__)


class EnvFileEncryptor:
    """Encrypt and decrypt .env files using Fernet symmetric encryption."""
    
    def __init__(self, key: str = None):
        """
        Initialize with encryption key.
        If no key provided, generates a new one.
        
        Args:
            key: Encryption key as string. If None, generates new key.
        """
        if key:
            # Pad key to 32 bytes if needed (Fernet requires 32 url-safe base64-encoded bytes)
            key = key.ljust(32)[:32]
            self.key = base64.urlsafe_b64encode(key.encode())
        else:
            self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def get_key(self) -> str:
        """Get the encryption key as a string (for secure storage)."""
        return self.key.decode()

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

        encrypted = self.cipher.encrypt(plaintext)

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

        decrypted = self.cipher.decrypt(encrypted)

        with open(output_path, 'wb') as f:
            f.write(decrypted)

        logger.info(f"Decrypted {input_path} -> {output_path}")
        return output_path

    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt a string."""
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt_string(self, ciphertext: str) -> str:
        """Decrypt a string."""
        return self.cipher.decrypt(ciphertext.encode()).decode()


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
