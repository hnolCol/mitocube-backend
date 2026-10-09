"""
Secret Management for MitoCube Backend

This module provides secure secret management for self-hosted deployments.
It supports:
- Environment variables (for development and simple deployments)
- Encrypted .env files (for production)
- Secret validation on startup
- Secure secret generation

Usage:
    For development:
        1. Copy .env.example to .env
        2. Fill in your values
        3. Start the application normally

    For production:
        1. Generate encryption key: python -c "from config.secrets.encryption import EnvFileEncryptor; print(EnvFileEncryptor().get_key())"
        2. Store the key securely (password manager, /etc/mitocube/encryption_key)
        3. Encrypt your .env: python -c "from config.secrets.encryption import EnvFileEncryptor; e = EnvFileEncryptor(input('Key: ')); e.encrypt_file('.env')"
        4. Use deploy.py script with ENCRYPTION_KEY environment variable

All secrets must be provided via environment variables or encrypted files.
NO hardcoded defaults are allowed.
"""

from .encryption import EnvFileEncryptor
from .validation import check_secrets_on_startup, validate_required_secrets
from .generator import generate_jwt_key, generate_password, generate_api_key

__all__ = [
    'EnvFileEncryptor',
    'check_secrets_on_startup',
    'validate_required_secrets',
    'generate_jwt_key',
    'generate_password',
    'generate_api_key',
]
