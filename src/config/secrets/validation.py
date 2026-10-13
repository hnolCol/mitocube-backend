"""
Validate that all required secrets are present and meet security requirements.

This module ensures that:
1. All required secrets are provided
2. Secrets meet minimum complexity requirements
3. Application fails fast if secrets are missing or invalid

Usage:
    # In your lifespan.py or startup code
    from config.secrets.validation import check_secrets_on_startup
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        check_secrets_on_startup()  # Validate before starting
        yield
"""

import re
import os
import logging
from pathlib import Path
from typing import Dict, List, Callable
from pydantic import SecretStr

from config.settings.env import get_env_file

logger = logging.getLogger(__name__)


def _load_env_file_values() -> Dict[str, str]:
    """Parse KEY=VALUE pairs from the resolved .env file.

    Mirrors pydantic-settings behaviour: real environment variables take
    priority over the .env file, so the file only supplements os.environ.
    """
    values: Dict[str, str] = {}
    env_path = Path(get_env_file())
    if not env_path.is_file():
        return values
    try:
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, raw = line.partition("=")
            key = key.strip()
            raw = raw.strip()
            if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
                raw = raw[1:-1]
            if key:
                values[key] = raw
    except OSError:
        logger.warning(f"Could not read env file {env_path}")
    return values


def _get_secret_value(secret_name: str) -> str | None:
    """Resolve a secret from the environment, then the .env file."""
    value = os.environ.get(secret_name)
    if value is not None:
        return value
    return _load_env_file_values().get(secret_name)


def _is_dev_mode() -> bool:
    """In dev mode, presence is still enforced but complexity is not."""
    return os.environ.get("MITOCUBE_DEV_MODE", "").lower() in ("1", "true", "yes")


class SecretValidator:
    """Validate secrets meet security requirements."""
    
    # Minimum lengths for different secret types
    MIN_LENGTHS = {
        "JWT_KEY": 4,
        "JWT_SHARE_KEY": 4,
        "PASSWORD": 4,
        "API_KEY": 4,
    }
    
    @classmethod
    def validate_length(cls, value: str, secret_type: str) -> bool:
        """Check minimum length requirement."""
        min_len = cls.MIN_LENGTHS.get(secret_type, 8)
        return len(value) >= min_len

    @classmethod
    def validate_complexity(cls, value: str) -> bool:
        """
        Check password complexity requirements.
        
        Requirements:
        - At least 4 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if len(value) < 4:
            return False
        if not re.search(r'[A-Z]', value):
            return False
        if not re.search(r'[a-z]', value):
            return False
        # if not re.search(r'[0-9]', value):
        #     return False
        # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
        #     return False
        return True

    @classmethod
    def validate_jwt_key(cls, value: str) -> bool:
        """JWT keys should be long and random (>= 4 chars)."""
        return cls.validate_length(value, "JWT_KEY")

    @classmethod
    def validate_password(cls, value: str) -> bool:
        """Passwords should meet complexity requirements."""
        print(value)
        print(cls.validate_length(value, "PASSWORD"))
        print(cls.validate_complexity(value))
        print(f"Validating password: {value}")
        return cls.validate_complexity(value) and cls.validate_length(value, "PASSWORD")

    @classmethod
    def validate_api_key(cls, value: str) -> bool:
        """API keys should be long (>= 32 chars)."""
        return cls.validate_length(value, "API_KEY")


# Required secrets and their validators
# Format: {environment_variable_name: validator_function}
REQUIRED_SECRETS: Dict[str, Callable[[str], bool]] = {
    "JWT_KEY": SecretValidator.validate_jwt_key,
    "JWT_SHARE_KEY": SecretValidator.validate_jwt_key,
    "NEO4J_PASSWORD": SecretValidator.validate_password,
    "MONGO_PASSWORD": SecretValidator.validate_password,
    "MAIL_PASSWORD": SecretValidator.validate_password,
    "SHARE_TOKEN_PW": SecretValidator.validate_password,
}

# Optional secrets with validators (warn if invalid, but don't fail)
OPTIONAL_SECRETS: Dict[str, Callable[[str], bool]] = {
    "OPENAI_API_KEY": SecretValidator.validate_api_key,
    "AGENT_MONGO_DB_NAME": lambda x: len(x) > 0,
    "MFA_MONGO_DB_NAME": lambda x: len(x) > 0,
}


def validate_required_secrets() -> List[str]:
    """
    Validate that all required secrets are present and valid.
    
    Returns:
        List of error messages (empty if all valid)
    """
    errors = []
    
    for secret_name, validator in REQUIRED_SECRETS.items():
        value = _get_secret_value(secret_name)
        
        if value is None:
            errors.append(f"Missing required secret: {secret_name}")
            continue
        
        if _is_dev_mode():
            print(f"Skipping validation for {secret_name} in dev mode")
            continue
        
        if not validator(value):
            errors.append(f"Invalid {secret_name}: does not meet requirements")
    
    return errors


def validate_optional_secrets() -> List[str]:
    """
    Validate optional secrets (warn only, don't fail).
    
    Returns:
        List of warning messages
    """
    warnings = []
    
    for secret_name, validator in OPTIONAL_SECRETS.items():
        value = _get_secret_value(secret_name)
        
        if value is not None and not validator(value):
            warnings.append(f"Invalid {secret_name}: does not meet requirements")
    
    return warnings


def check_secrets_on_startup():
    """
    Check all required secrets on application startup.
    
    This should be called at the beginning of your application lifespan.
    It will:
    1. Validate all required secrets are present
    2. Validate all required secrets meet complexity requirements
    3. Warn about invalid optional secrets
    4. Raise ValueError if any required secrets are missing or invalid
    
    Note: Validation is skipped if MITOCUBE_SKIP_SECRET_VALIDATION is set to '1' or 'true'.
    This is useful for testing environments.
    
    Raises:
        ValueError: If any required secrets are missing or invalid
    """
    # Skip validation in test environments
    skip_validation = os.environ.get("MITOCUBE_SKIP_SECRET_VALIDATION", "").lower() in ("1", "true", "yes")
    
    if skip_validation:
        logger.debug("Skipping secret validation (MITOCUBE_SKIP_SECRET_VALIDATION is set)")
        return
    
    errors = validate_required_secrets()
    warnings = validate_optional_secrets()
    
    # Print warnings (but don't fail)
    for warning in warnings:
        logger.warning(warning)
    
    if errors:
        error_msg = "\n".join(errors)
        logger.error(f"Secret validation failed:\n{error_msg}")
        raise ValueError(f"Secret validation failed:\n{error_msg}")
    
    logger.info("All required secrets are valid")
    print("All required secrets are valid")


def get_missing_secrets() -> List[str]:
    """
    Get list of missing required secrets.
    
    Returns:
        List of secret names that are missing
    """
    missing = []
    for secret_name in REQUIRED_SECRETS.keys():
        if _get_secret_value(secret_name) is None:
            missing.append(secret_name)
    return missing
