"""
Generate secure secrets for MitoCube configuration.

This module provides utilities to generate cryptographically secure
secrets for all your configuration needs.

Usage:
    # Generate all secrets for .env file
    python -m config.secrets.generator --all
    
    # Generate specific secrets
    python -m config.secrets.generator --jwt
    python -m config.secrets.generator --password --length 32
    
    # Use programmatically
    from config.secrets.generator import generate_jwt_key, generate_password
    jwt_key = generate_jwt_key()
    password = generate_password(24)
"""

import secrets
import string
import argparse
import sys


def generate_jwt_key(length: int = 32) -> str:
    """
    Generate a secure JWT key.
    
    JWT keys should be long, random strings. This generates a
    URL-safe base64-encoded random string suitable for JWT signing.
    
    Args:
        length: Number of random bytes to use (default: 32)
        
    Returns:
        Secure JWT key string
    """
    # Generate random bytes and encode as URL-safe base64
    random_bytes = secrets.token_bytes(length)
    return secrets.token_urlsafe(length)


def generate_password(length: int = 24) -> str:
    """
    Generate a secure password.
    
    Passwords meet the following requirements:
    - At least the specified length
    - Contains uppercase letters
    - Contains lowercase letters
    - Contains digits
    - Contains special characters
    
    Args:
        length: Minimum password length (default: 24)
        
    Returns:
        Secure password string
    """
    if length < 12:
        raise ValueError("Password length must be at least 12")
    
    # Define character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special = "!@#$%^&*(),.?\":{}|<>"
    all_chars = uppercase + lowercase + digits + special
    
    # Ensure we have at least one of each character type
    password = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits),
        secrets.choice(special),
    ]
    
    # Fill the rest with random characters
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))
    
    # Shuffle to avoid predictable patterns
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)


def generate_api_key(length: int = 32) -> str:
    """
    Generate a secure API key.
    
    API keys are typically long, random strings without special
    characters that might cause issues in URLs.
    
    Args:
        length: Number of characters (default: 32)
        
    Returns:
        Secure API key string
    """
    alphabet = string.ascii_letters + string.digits + "_-"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_random_string(length: int = 16) -> str:
    """
    Generate a random string.
    
    Args:
        length: Number of characters
        
    Returns:
        Random string
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def main():
    """Command-line interface for secret generation."""
    parser = argparse.ArgumentParser(
        description="Generate secure secrets for MitoCube"
    )
    parser.add_argument(
        "--jwt", 
        action="store_true", 
        help="Generate JWT key"
    )
    parser.add_argument(
        "--jwt-share", 
        action="store_true", 
        help="Generate JWT share key"
    )
    parser.add_argument(
        "--password", 
        action="store_true", 
        help="Generate password"
    )
    parser.add_argument(
        "--api-key", 
        action="store_true", 
        help="Generate API key"
    )
    parser.add_argument(
        "--all", 
        action="store_true", 
        help="Generate all secrets"
    )
    parser.add_argument(
        "--length", 
        type=int, 
        default=24, 
        help="Password length (default: 24)"
    )
    parser.add_argument(
        "--format", 
        choices=["text", "env", "json"],
        default="text",
        help="Output format (default: text)"
    )
    
    args = parser.parse_args()
    
    secrets_output = {}
    
    if args.all or args.jwt:
        secrets_output["JWT_KEY"] = generate_jwt_key()
    
    if args.all or args.jwt_share:
        secrets_output["JWT_SHARE_KEY"] = generate_jwt_key()
    
    if args.all or args.password:
        secrets_output["NEO4J_PASSWORD"] = generate_password(args.length)
        secrets_output["MONGO_PASSWORD"] = generate_password(args.length)
        secrets_output["MAIL_PASSWORD"] = generate_password(args.length)
        secrets_output["SHARE_TOKEN_PW"] = generate_password(args.length)
    
    if args.all or args.api_key:
        secrets_output["OPENAI_API_KEY"] = generate_api_key()
    
    if not secrets_output:
        # Default: generate all
        secrets_output = {
            "JWT_KEY": generate_jwt_key(),
            "JWT_SHARE_KEY": generate_jwt_key(),
            "NEO4J_PASSWORD": generate_password(args.length),
            "MONGO_PASSWORD": generate_password(args.length),
            "MAIL_PASSWORD": generate_password(args.length),
            "SHARE_TOKEN_PW": generate_password(args.length),
            "OPENAI_API_KEY": generate_api_key(),
        }
    
    # Output based on format
    if args.format == "json":
        import json
        print(json.dumps(secrets_output, indent=2))
    elif args.format == "env":
        for key, value in secrets_output.items():
            print(f"{key}={value}")
    else:  # text
        for key, value in secrets_output.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
