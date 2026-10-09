#!/usr/bin/env python3
"""
Production deployment script for MitoCube Backend.

This script:
1. Decrypts .env.enc using encryption key from environment
2. Validates all required secrets
3. Starts the application

Usage:
    # For production with encrypted .env
    export ENCRYPTION_KEY="your-encryption-key-here"
    python deploy.py
    
    # For development (uses .env directly)
    python deploy.py
    
    # With custom encryption key file
    export ENCRYPTION_KEY_FILE="/path/to/keyfile"
    python deploy.py

Environment Variables:
    ENCRYPTION_KEY:        Encryption key as string
    ENCRYPTION_KEY_FILE:   Path to file containing encryption key (default: /etc/mitocube/encryption_key)
    UVICORN_HOST:          Host to bind to (default: 0.0.0.0)
    UVICORN_PORT:          Port to bind to (default: 5002)
    UVICORN_WORKERS:       Number of worker processes (default: 1)
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.secrets.encryption import EnvFileEncryptor, get_encryption_key
from config.secrets.validation import check_secrets_on_startup


def get_encryption_key_safe() -> Optional[str]:
    """
    Try to get encryption key, return None if not available.
    This allows development mode without encryption.
    """
    try:
        return get_encryption_key()
    except ValueError:
        return None


def decrypt_env_if_exists():
    """
    Decrypt .env.enc to .env if encrypted file exists.
    Returns True if decryption was performed, False otherwise.
    """
    enc_file = Path(".env.enc")
    env_file = Path(".env")
    
    if not enc_file.exists():
        # No encrypted file, check if .env exists
        if env_file.exists():
            print("✅ Using existing .env file")
        else:
            print("⚠️  No .env or .env.enc found. Using environment variables only.")
        return False
    
    # Encrypted file exists, try to decrypt
    enc_key = get_encryption_key_safe()
    if not enc_key:
        print("❌ ERROR: .env.enc exists but ENCRYPTION_KEY not set")
        print("   Set ENCRYPTION_KEY environment variable or create /etc/mitocube/encryption_key")
        sys.exit(1)
    
    try:
        encryptor = EnvFileEncryptor(enc_key)
        encryptor.decrypt_file(".env.enc", ".env")
        print("✅ Decrypted .env.enc -> .env")
        return True
    except Exception as e:
        print(f"❌ ERROR: Failed to decrypt .env.enc: {e}")
        sys.exit(1)


def validate_environment():
    """Validate that all required environment variables are set."""
    try:
        check_secrets_on_startup()
    except ValueError as e:
        print(f"❌ ERROR: {e}")
        print("\nTo fix this:")
        print("1. Make sure .env file exists (or .env.enc with ENCRYPTION_KEY)")
        print("2. All required secrets are present in .env")
        print("3. Run: python -m config.secrets.generator --all")
        print("   to generate secure secrets for your .env file")
        sys.exit(1)


def get_uvicorn_args():
    """Get uvicorn arguments from environment."""
    host = os.environ.get("UVICORN_HOST", "0.0.0.0")
    port = int(os.environ.get("UVICORN_PORT", "5002"))
    workers = int(os.environ.get("UVICORN_WORKERS", "1"))
    
    args = [
        "python",
        "-m",
        "uvicorn",
        "src.app:app",
        "--host", host,
        "--port", str(port),
        "--proxy-headers",
    ]
    
    if workers > 1:
        args.extend(["--workers", str(workers)])
    
    # Check if we're in development mode
    if os.environ.get("MITOCUBE_DEV", "").lower() in ("true", "1", "yes"):
        args.append("--reload")
    
    return args


def main():
    """Main deployment function."""
    print("=" * 60)
    print("MitoCube Backend - Production Deployment")
    print("=" * 60)
    
    # Step 1: Decrypt .env if needed
    decrypted = decrypt_env_if_exists()
    
    # Step 2: Validate secrets
    print("\n🔍 Validating secrets...")
    validate_environment()
    
    # Step 3: Start the application
    print("\n🚀 Starting MitoCube Backend...")
    print(f"   Host: {os.environ.get('UVICORN_HOST', '0.0.0.0')}")
    print(f"   Port: {os.environ.get('UVICORN_PORT', '5002')}")
    
    args = get_uvicorn_args()
    print(f"   Command: {' '.join(args)}")
    print("\n" + "=" * 60)
    
    # Execute uvicorn
    os.execvp(args[0], args)


if __name__ == "__main__":
    main()
