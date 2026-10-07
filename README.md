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
If the you leave this empty, in prinicple everyone can register and have access to the data. Hence, for security reasons, this should not be an empty list. 
## Dependencies

Core dependencies live in `requirements.txt`. The optional AI agent stack
(langchain/langgraph/openai) is split into `requirements-ai.txt` — install
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
errors until it recovers — check the logs at startup to see which
dependencies are reachable.
