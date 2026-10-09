# mitocube-backend
 Backend for MitoCube Web Application


## Quick Start

- Edit configuration in folder ```config``` which are based on the ```pydantic``` BaseSettings. 
The config folder contains pydantic BaseSettings for the Database (db.py), the email settings and the files.
You will have to change the followings:

- attributes_file The file that contain all the attributes you would like to configure. 
```python
class DB(BaseSettings):
    """Base Settings"""

    attribute_file : FilePath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/attributes/attributes.json"
```
The file must exist otherwise the app wont start. 

## General Settings
The general settings allow you to specify the folliwng parameters. 

```python
class General(BaseSettings):
    """Class model for general settings"""
    app_name : str = "MitoCube"
    version : str = "0.1"
    lead_contact : EmailStr = "h.nolte@age.mpg.de"
    description : str = "MitoCube offers protein-centric searches to explore the expression of a protein in all acquired proteomic datasets."
    allowed_email_domains : List[str] = ["@age.mpg.de"]
```

Here you can specify if you would like to restrict the user registration to a certain domain of emails preventing users to use private emails using the ```allowed_email_domains``` parameter. 
If the you leave this empty, in principle everyone can register and have access to the data. Hence, for security reasons, this should not be an empty list. 

## Secret Management

MitoCube now includes a **complete secret management system** for secure production deployments.

### For Development (No Changes)
```bash
# Same as before - just copy .env.example and edit
cp .env.example .env
nano .env
python -m uvicorn src.app:app --reload
```

### For Production (Secure)
```bash
# Generate encryption key (SAVE THIS!)
python -c "from config.secrets.encryption import EnvFileEncryptor; print(EnvFileEncryptor().get_key())"

# Create .env, encrypt it, deploy
cp .env.example .env
nano .env  # Fill in production values
export ENCRYPTION_KEY="your-key"
python -c "from config.secrets.encryption import EnvFileEncryptor; EnvFileEncryptor('$ENCRYPTION_KEY').encrypt_file('.env')"
rm .env
python deploy.py
```

**See the [Secret Management Guide](docs/SECRET_MANAGEMENT.md) for complete details.**

## Database setup

Setting up the database and migrating data is documented in
[docs/SETUP.md](docs/SETUP.md) (steps, flags, common scenarios).

## Dependencies

Core dependencies live in `requirements.txt`. The optional AI agent stack
(langchain/langgraph/openai) is split into `requirements-ai.txt`  install
it only if you use the AI features:

```bash
pip install -r requirements.txt        # core backend
pip install -r requirements-ai.txt     # optional AI agent stack
```

### Login rate limiting

Failed logins are rate limited per email address and per client IP
(10 attempts / 10 minutes by default, configurable via
`LOGIN_RATE_LIMIT_MAX_ATTEMPTS` and `LOGIN_RATE_LIMIT_WINDOW_MINUTES`).
Exceeding the budget returns `429 Too Many Requests` with a
`Retry-After` header.

Since production runs behind nginx, the client IP is taken from
`X-Forwarded-For` **only** when the direct peer is a trusted proxy
(`TRUSTED_PROXY_IPS`, default `127.0.0.1,::1`). Set this to the IP your
nginx uses to reach uvicorn.

### Required nginx configuration

For the per-IP rate limit to see real client IPs, the nginx site config
**must** forward the original client address. Without the
`X-Forwarded-For` header, every user reaches the backend as the nginx
IP and all users share a single rate-limit budget. The essential
directive:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    # REQUIRED for login rate limiting:
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

A complete, commented example config is in
[`docs/nginx.conf.example`](docs/nginx.conf.example).

`pip-audit` runs on `requirements.txt` in CI (see
`.github/workflows/ci.yml`). Known advisories without an upstream fix
(currently transitive `ecdsa` via `python-jose`) are tracked until the
JWT library is migrated to a maintained alternative.

## Tests

A pytest suite lives in `tests/`. Unit tests cover password hashing, JWT
creation/decoding, login and role-gate logic in `services.users`, user model
validation and the MFA runtime (lockout + challenges). No database or network
access is required.

```bash
pip install -r requirements.txt pytest
python -m pytest
```

## Startup behavior (database health checks)

On startup, the application runs explicit health checks against its
dependencies: **Neo4j** (a connectivity probe plus a trivial `RETURN 1`
query) and the three **MongoDB**-backed runtimes (AI agent, MFA, query
cache; each sends a `ping` command). Both use **log-and-continue**
semantics:

- If a health check **passes**, startup proceeds normally.
- If a health check **fails**, the error (with full traceback) is logged
  as `ERROR: <dependency> startup FAILED ... Continuing anyway.`, and
  the application **still starts**.

The rationale: a transient database outage should not put the whole web
service down or cause restart loops under a process manager. The trade
off is that requests touching an unavailable dependency will return
errors until it recovers  check the logs at startup to see which
dependencies are reachable.

## Production Documentation

For complete production deployment guides, see:

- **[Secret Management Guide](docs/SECRET_MANAGEMENT.md)** - Complete guide for managing secrets securely
- **[Production Setup Guide](docs/PRODUCTION_SETUP.md)** - Step-by-step production deployment (14 steps)
- **[Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md)** - Complete checklist for deployment verification
- **[All Documentation](docs/README.md)** - Full documentation overview
