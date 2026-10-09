# Secret Management Guide for MitoCube

## Overview

This guide explains how to securely manage secrets for MitoCube deployments. The system provides:

- **Development**: Simple `.env` file usage (unchanged from before)
- **Production**: Encrypted `.env` files with optional secret validation
- **Security**: No hardcoded defaults, validation on startup

---

## Quick Start

### Development (No Changes Required)

```bash
# 1. Copy the example configuration
cp .env.example .env

# 2. Edit with your values
nano .env

# 3. Start the application (unchanged)
python -m uvicorn src.app:app --reload
```

That's it! Development workflow is **completely unchanged**.

---

### Production Deployment

For production, follow these steps to encrypt your secrets:

```bash
# 1. Generate encryption key (SAVE THIS SECURELY!)
python -c "from config.secrets.encryption import EnvFileEncryptor; print(EnvFileEncryptor().get_key())"

# Example output: "kF3n...=" - Copy this and store it securely!

# 2. Create your .env file
cp .env.example .env
nano .env  # Fill in production values

# 3. Encrypt it
export ENCRYPTION_KEY="your-key-from-step-1"
python -c "from config.secrets.encryption import EnvFileEncryptor; EnvFileEncryptor('$ENCRYPTION_KEY').encrypt_file('.env')"

# 4. Remove plaintext .env (keep the encrypted .env.enc)
rm .env

# 5. Deploy
export ENCRYPTION_KEY="your-key-from-step-1"
python deploy.py
```

---

## Detailed Production Setup

### Step 1: Understand the Requirements

MitoCube requires several secrets for production operation:

| Secret | Purpose | Requirements |
|--------|---------|--------------|
| `JWT_KEY` | JWT token signing | >= 32 characters, random |
| `JWT_SHARE_KEY` | Share token signing | >= 32 characters, random |
| `NEO4J_PASSWORD` | Neo4j database | >= 12 chars, complex* |
| `MONGO_PASSWORD` | MongoDB (AI features) | >= 12 chars, complex* |
| `MAIL_PASSWORD` | Email server | >= 12 chars, complex* |
| `SHARE_TOKEN_PW` | Share token authentication | >= 12 chars, complex* |
| `MFA_ENCRYPTION_KEY` | MFA encryption | >= 32 characters |

*Complex password requirements: uppercase, lowercase, digit, special character

### Step 2: Generate Secure Secrets

Use the built-in generator to create compliant secrets:

```bash
# Generate ALL required secrets at once
python -m config.secrets.generator --all

# Output:
# JWT_KEY: abc123...xyz
# JWT_SHARE_KEY: def456...uvw
# NEO4J_PASSWORD: P@ssw0rd!WithAllReqs
# MONGO_PASSWORD: AnotherS3cur3P@ss
# MAIL_PASSWORD: EmailP@ssw0rd123
# SHARE_TOKEN_PW: Sh@reT0kenP@ss1
# OPENAI_API_KEY: sk-abc123...

# Or generate specific types:
python -m config.secrets.generator --jwt
python -m config.secrets.generator --password --length 24
python -m config.secrets.generator --api-key

# Get output as .env format (for easy copy/paste):
python -m config.secrets.generator --all --format env
```

### Step 3: Create `.env` File

```bash
# Start from the template
cp .env.example .env

# Edit with your values
nano .env

# Or generate and append:
python -m config.secrets.generator --all --format env >> .env
```

**Important**: Review the `.env` file and:
- Set database connection strings correctly
- Set email server details
- Set application-specific values (app name, version, etc.)

### Step 4: Test Locally (Optional)

Before encrypting, test that your configuration works:

```bash
# Start with your .env file
python -m uvicorn src.app:app

# Check logs for:
# "All required secrets are valid"
# No errors on startup
```

If you see errors about missing secrets, double-check your `.env` file.

### Step 5: Encrypt for Production

```bash
# Generate encryption key (ONLY DO THIS ONCE)
python -c "from config.secrets.encryption import EnvFileEncryptor; print(EnvFileEncryptor().get_key())"

# Save the key in one of these secure locations:
# Option A: Environment variable in your deployment system
# Option B: File at /etc/mitocube/encryption_key (recommended)
# Option C: Password manager (Bitwarden, 1Password, KeePass)

# Encrypt your .env file
export ENCRYPTION_KEY="your-key-here"
python -c "from config.secrets.encryption import EnvFileEncryptor; EnvFileEncryptor('$ENCRYPTION_KEY').encrypt_file('.env')"

# Verify encrypted file exists
ls -la .env.enc

# Remove plaintext .env
rm .env
```

**⚠️ CRITICAL**: The encryption key is your **master key**. Without it, you cannot decrypt your `.env.enc` file. Store it securely!

### Step 6: Store Encryption Key Securely

Choose one of these secure storage methods:

#### Option A: Environment Variable (Simple)

```bash
# In your shell profile (~/.bashrc, ~/.zshrc):
echo 'export ENCRYPTION_KEY="your-key-here"' >> ~/.bashrc
source ~/.bashrc

# Or set temporarily for a session:
export ENCRYPTION_KEY="your-key-here"
```

#### Option B: File in Secure Location (Recommended)

```bash
# Create secure directory
sudo mkdir -p /etc/mitocube
sudo chmod 700 /etc/mitocube

# Store the key
echo "your-key-here" | sudo tee /etc/mitocube/encryption_key
sudo chmod 600 /etc/mitocube/encryption_key

# The deploy.py script automatically looks here
```

#### Option C: Environment Variable File

```bash
# Create a file with your key
echo "ENCRYPTION_KEY=your-key-here" > /opt/mitocube/secrets.env
chmod 600 /opt/mitocube/secrets.env

# Source it before running:
set -a && source /opt/mitocube/secrets.env && set +a
python deploy.py
```

#### Option D: Password Manager

Store the key in your password manager and retrieve it when needed:

```bash
# Example with pass (Unix password manager)
pass insert mitocube/encryption_key
export ENCRYPTION_KEY=$(pass mitocube/encryption_key)
python deploy.py
```

### Step 7: Deploy to Production

#### Using `deploy.py` (Recommended)

```bash
# Method 1: With environment variable
export ENCRYPTION_KEY="your-key-here"
python deploy.py

# Method 2: With key file (if stored at /etc/mitocube/encryption_key)
python deploy.py

# Method 3: With custom settings
export ENCRYPTION_KEY="your-key-here"
export UVICORN_HOST="0.0.0.0"
export UVICORN_PORT="8000"
export UVICORN_WORKERS="4"
python deploy.py
```

The `deploy.py` script will:
1. Decrypt `.env.enc` to `.env`
2. Validate all required secrets
3. Start the application

#### Using Systemd Service

Create a systemd service file:

```ini
# /etc/systemd/system/mitocube.service
[Unit]
Description=MitoCube Backend
After=network.target

[Service]
User=mitocube
WorkingDirectory=/opt/mitocube
Environment=ENCRYPTION_KEY=your-key-here
Environment=UVICORN_HOST=0.0.0.0
Environment=UVICORN_PORT=8000
ExecStart=/usr/bin/python /opt/mitocube/deploy.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable mitocube
sudo systemctl start mitocube

# Check status
sudo systemctl status mitocube

# View logs
sudo journalctl -u mitocube -f
```

#### Using Docker

```dockerfile
# Dockerfile
FROM python:3.12

WORKDIR /app
COPY . .

# Install dependencies
RUN pip install -r requirements.txt

# Create non-root user
RUN useradd -m mitocube
USER mitocube

# Store encryption key (in production, use Docker secrets or mounted volume)
# For development only:
ENV ENCRYPTION_KEY=your-key-here

EXPOSE 8000
CMD ["python", "deploy.py"]
```

Run with:

```bash
# Build
docker build -t mitocube .

# Run with encrypted .env
docker run -d \
  -p 8000:8000 \
  -e ENCRYPTION_KEY=your-key-here \
  -v $(pwd)/.env.enc:/app/.env.enc:ro \
  --name mitocube \
  mitocube
```

For production Docker, use Docker secrets:

```bash
echo "your-key-here" | docker secret create encryption_key -
docker service create \
  --name mitocube \
  --secret encryption_key \
  -p 8000:8000 \
  mitocube
```

---

## Encryption Key Management

### Backup Your Key

**⚠️ CRITICAL**: Backup your encryption key immediately after generating it!

If you lose the key, you **cannot** decrypt your `.env.enc` file, and you'll need to:
1. Generate a new key
2. Create a new `.env` file
3. Re-encrypt it
4. Redeploy

**Backup methods**:

1. **Password Manager** (Recommended)
   - Bitwarden
   - 1Password
   - KeePassXC

2. **Encrypted File**
   ```bash
   echo "your-key-here" | gpg --encrypt --recipient your-email@example.com > encryption_key.gpg
   ```

3. **Paper Backup**
   - Print and store in a secure physical location
   - Use a QR code for easy retrieval

4. **Multiple Secure Locations**
   - Store in at least 2 different secure locations
   - Never store only on the server

### Rotate Encryption Key

To rotate your encryption key:

```bash
# 1. Generate new key
NEW_KEY=$(python -c "from config.secrets.encryption import EnvFileEncryptor; print(EnvFileEncryptor().get_key())")

# 2. Decrypt with old key
export ENCRYPTION_KEY="old-key-here"
python -c "from config.secrets.encryption import EnvFileEncryptor; EnvFileEncryptor('$ENCRYPTION_KEY').decrypt_file('.env.enc', '.env')"

# 3. Encrypt with new key
export ENCRYPTION_KEY="$NEW_KEY"
python -c "from config.secrets.encryption import EnvFileEncryptor; EnvFileEncryptor('$ENCRYPTION_KEY').encrypt_file('.env')"

# 4. Update your deployment with new key
# 5. Backup new key securely
# 6. Remove old key from all locations
```

### Recover from Lost Key

If you lose your encryption key:

1. **Don't panic** - Your data is safe, just inaccessible
2. Create a new `.env` file from scratch
3. Generate a new encryption key
4. Encrypt the new `.env`
5. Update your deployment

---

## Secret Rotation

### JWT Keys

JWT keys should be rotated periodically (every 90-180 days):

```bash
# Generate new JWT keys
NEW_JWT_KEY=$(python -m config.secrets.generator --jwt)
NEW_JWT_SHARE_KEY=$(python -m config.secrets.generator --jwt)

# Update .env with new keys
# Then re-encrypt
```

**Important**: When rotating JWT keys:
- Old tokens will become invalid
- Users will need to log in again
- Consider doing this during low-traffic periods

### Database Passwords

Database passwords should be rotated every 180 days:

```bash
# 1. Generate new password
NEW_PASSWORD=$(python -m config.secrets.generator --password)

# 2. Update database user password
# (Use your database admin tools)

# 3. Update .env with new password

# 4. Re-encrypt and deploy
```

### Email Passwords

Email passwords should be rotated according to your email provider's policy:

```bash
# 1. Update email account password
# 2. Update .env with new password
# 3. Re-encrypt and deploy
```

---

## Security Best Practices

### 1. Never Commit Secrets

```bash
# Check for accidentally committed secrets
git grep -n "password\|secret\|token\|key" -- "*.py" "*.env"

# If you accidentally commit a secret:
# 1. Remove from git history
# 2. Rotate the secret immediately
# 3. Force push the cleaned history
```

### 2. Limit Access

- Only allow trusted users to access the server
- Use SSH key authentication (disable password login)
- Set up a firewall to restrict access to necessary ports
- Use fail2ban to prevent brute force attacks

### 3. Use HTTPS

Always use HTTPS in production. Configure your reverse proxy (nginx, Apache) with:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. Regular Backups

Back up your encrypted `.env.enc` file and encryption key:

```bash
# Backup .env.enc
cp .env.enc /backup/mitocube/.env.enc-$(date +%Y%m%d)

# Backup encryption key (if stored in file)
cp /etc/mitocube/encryption_key /backup/mitocube/encryption_key-$(date +%Y%m%d)

# Secure the backups
chmod 600 /backup/mitocube/*
```

### 5. Monitor for Breaches

Set up monitoring to detect:
- Multiple failed login attempts
- Unusual access patterns
- File changes in sensitive directories

---

## Troubleshooting

### Error: "Missing required secret: X"

**Cause**: A required secret is not set in your `.env` file.

**Solution**:
1. Check `.env.example` for the required secret
2. Add it to your `.env` file
3. Generate a secure value: `python -m config.secrets.generator --type`

### Error: "Secret validation failed"

**Cause**: A secret doesn't meet the requirements (e.g., password too short).

**Solution**:
1. Check the error message for which secret failed
2. Generate a compliant secret: `python -m config.secrets.generator --password`
3. Update your `.env` file

### Error: "Failed to decrypt .env.enc"

**Cause**: Wrong encryption key or corrupted file.

**Solution**:
1. Verify your `ENCRYPTION_KEY` is correct
2. Check that `.env.enc` exists and isn't corrupted
3. Try decrypting manually:
   ```bash
   python -c "from config.secrets.encryption import EnvFileEncryptor; EnvFileEncryptor('$ENCRYPTION_KEY').decrypt_file('.env.enc', '.env')"
   ```

### Error: "No encryption key found"

**Cause**: `ENCRYPTION_KEY` environment variable not set, and no key file at `/etc/mitocube/encryption_key`.

**Solution**:
1. Set the environment variable: `export ENCRYPTION_KEY="your-key"`
2. Or create the key file: `echo "your-key" | sudo tee /etc/mitocube/encryption_key`

### Tests Failing with Secret Validation Errors

**Cause**: Tests are running without the skip flag.

**Solution**:
1. Ensure `MITOCUBE_SKIP_SECRET_VALIDATION=1` is set in test environment
2. Check `tests/conftest.py` for the test environment setup

---

## Migration from Previous Versions

### If You Had Hardcoded Passwords

Previous versions had hardcoded defaults like:
```python
MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD", "password")
```

**Action Required**:
1. You **MUST** set `MONGO_PASSWORD` in your `.env` file
2. The hardcoded default is now **removed**
3. Generate a secure password: `python -m config.secrets.generator --password`

### If You Were Using Plaintext `.env`

**Recommended**: Encrypt your `.env` file for production:

```bash
# Generate key
KEY=$(python -c "from config.secrets.encryption import EnvFileEncryptor; print(EnvFileEncryptor().get_key())")

# Encrypt
export ENCRYPTION_KEY="$KEY"
python -c "from config.secrets.encryption import EnvFileEncryptor; EnvFileEncryptor('$ENCRYPTION_KEY').encrypt_file('.env')"

# Deploy with deploy.py
export ENCRYPTION_KEY="$KEY"
python deploy.py
```

You can continue using plaintext `.env` for development, but **encrypt for production**.

---

## API Reference

### Secret Generator

```bash
# Generate all secrets
python -m config.secrets.generator --all

# Generate specific types
python -m config.secrets.generator --jwt
python -m config.secrets.generator --jwt-share
python -m config.secrets.generator --password --length 24
python -m config.secrets.generator --api-key

# Output formats
python -m config.secrets.generator --all --format text    # Default
python -m config.secrets.generator --all --format env     # .env format
python -m config.secrets.generator --all --format json    # JSON format
```

### Encryption Utility

```python
from config.secrets.encryption import EnvFileEncryptor

# Create encryptor
enryptor = EnvFileEncryptor("your-key")  # Or EnvFileEncryptor() for new key

# Get the key (for storage)
key = encryptor.get_key()

# Encrypt a file
enryptor.encrypt_file(".env", ".env.enc")

# Decrypt a file
enryptor.decrypt_file(".env.enc", ".env")

# Encrypt a string
encrypted = encryptor.encrypt_string("my-secret")

# Decrypt a string
decrypted = encryptor.decrypt_string(encrypted)
```

### Validation Utility

```python
from config.secrets.validation import (
    check_secrets_on_startup,
    validate_required_secrets,
    validate_optional_secrets,
    get_missing_secrets,
)

# Check all secrets (raises ValueError if invalid)
check_secrets_on_startup()

# Validate without raising
errors = validate_required_secrets()
if errors:
    print("Missing secrets:", errors)

# Get list of missing secrets
missing = get_missing_secrets()
```

---

## Configuration Reference

### `.env` File Structure

```ini
# Required Secrets (NO DEFAULTS)
JWT_KEY=your-jwt-key-here
JWT_SHARE_KEY=your-jwt-share-key-here
NEO4J_PASSWORD=your-neo4j-password-here
MONGO_PASSWORD=your-mongodb-password-here
MAIL_PASSWORD=your-email-password-here
SHARE_TOKEN_PW=your-share-token-password-here
MFA_ENCRYPTION_KEY=your-mfa-encryption-key-here

# Optional Settings (with defaults)
JWT_ALGORITHM=HS256
EXPIRES_AFTER_HOURS=48
EXPIRES_AFTER_MINUTES=15
SHARE_EXPIRES_AFTER_HOURS=2880

# Database Configuration
DB_HANDLER=neo4j
DB_URI=bolt://localhost:7687
DB_USER=neo4j
DB_NAME=neo4j
DB_MAX_DATASET_CACHED=100

# Email Configuration
MAIL_SERVER=mail.example.com
MAIL_PORT=587
MAIL_USERNAME=your-email@example.com
MAIL_USE_TLS_SSL=False
MAIL_START_TLS=True
MAIL_DEFAULT_SENDER=mitocube@example.com
MAIL_USE_CRENDENTIALS=True
MAIL_VALIDATE_CERTS=False
MAIL_FROM_NAME=MitoCube Support
MAIL_TEMPLATE_DIR=/path/to/templates

# MFA Configuration
MFA_MONGO_DB_NAME=mfa_db
MFA_MAX_ATTEMPTS=5
MFA_LOCKOUT_MINUTES=15
LOGIN_RATE_LIMIT_MAX_ATTEMPTS=10
LOGIN_RATE_LIMIT_WINDOW_MINUTES=10
TRUSTED_PROXY_IPS=127.0.0.1,::1

# AI Agent Configuration (optional)
AGENT_MONGO_DB_NAME=mongodb
MONGO_USER=ai
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_AUTH_DB=admin

# Application Settings
APP_NAME=MitoCube
VERSION=0.1
LEAD_CONTACT=admin@example.com
DESCRIPTION=MitoCube offers protein-centric searches...
ALLOWED_EMAIL_DOMAINS=["@example.com"]
ATTRIBUTE_FILE=/path/to/attributes.json
FRONTEND_BUILD=/path/to/frontend/build
FRONTEND_BUILD_ASSETS=/path/to/frontend/build/assets
```

### Environment Variables for Deployment

| Variable | Purpose | Required |
|----------|---------|----------|
| `ENCRYPTION_KEY` | Encryption key for .env.enc | Yes (if using encrypted file) |
| `ENCRYPTION_KEY_FILE` | Path to file containing key | No (default: /etc/mitocube/encryption_key) |
| `UVICORN_HOST` | Host to bind to | No (default: 0.0.0.0) |
| `UVICORN_PORT` | Port to bind to | No (default: 5002) |
| `UVICORN_WORKERS` | Number of worker processes | No (default: 1) |
| `MITOCUBE_SKIP_SECRET_VALIDATION` | Skip validation | No (default: not set) |

---

## Support

If you encounter issues with secret management:

1. **Check this documentation** for common issues
2. **Review your `.env` file** for missing values
3. **Verify your encryption key** is correct and accessible
4. **Check logs** for detailed error messages
5. **Generate new secrets** if validation fails

For security-related questions, contact your system administrator.

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-10-08 | Initial secret management implementation |
| 1.0 | 2024-10-08 | Added encryption, validation, generator |
| 1.0 | 2024-10-08 | Removed all hardcoded defaults |

---

*Last updated: 2024-10-08*
