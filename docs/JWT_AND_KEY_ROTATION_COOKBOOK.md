# JWT & Key Rotation Cookbook (MitoCube)

A hands-on guide for rotating the cryptographic keys used by the backend: which
keys exist, how to change them safely, what breaks, and — most importantly —
**what does NOT need to be done** (passwords).

---

## 1. Overview: which secrets are involved

| Secret (env var)            | Used for                                      | Defined in                                  | If rotated…                                                        |
| --------------------------- | --------------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------ |
| `JWT_KEY`                   | Signing/verifying user login tokens (HS256)   | `src/config/settings/token.py` (`UserToken`)| All outstanding user tokens become invalid → users must re-login.   |
| `JWT_SHARE_KEY`             | Signing/verifying share tokens (HS256)        | `ShareToken`                                | All outstanding share tokens become invalid → admins must re-issue.|
| `MFA_ENCRYPTION_KEY`        | Fernet-encryption of stored TOTP secrets     | `MFASettings`                               | **Stored MFA secrets become undecryptable** → users must reset MFA.|
| `SHARE_TOKEN_PW`            | Plain comparison password for issuing shares | `ShareToken`                               | Only affects issuing new share tokens.                             |
| `HASH_ALGORITHM` (bcrypt…)  | Password hashing (passlib)                    | `src/config/settings/encryption.py`         | See §6 — passlib self-identifies hashes, migration is incremental. |

Token creation/verification lives in `src/services/encryption.py`
(`create_access_token`, `create_share_token`, `decode_token`).

---

## 2. FAQ first: do passwords need to be updated when the JWT key changes?

**No.** This is the most common misconception:

- JWTs are **signed**, not encrypted with user passwords. The signing key
  (`JWT_KEY`) only proves a token was issued by us. Passwords are stored as
  **salted bcrypt hashes** (passlib, `src/services/encryption.py`) and have
  **no relationship to the JWT key**.
- Rotating `JWT_KEY` therefore only invalidates **outstanding tokens**.
  Bcrypt password hashes in the database keep working unchanged.
- The only key that touches **stored user data** is `MFA_ENCRYPTION_KEY`
  (Fernet-encrypted TOTP secrets). See §5.

**Rule of thumb:**
- Key that *signs tokens* → rotate freely, users just re-login.
- Key that *encrypts stored data* → rotation requires data migration.

---

## 3. Cookbook: rotating `JWT_KEY` (user login tokens)

### Step 1 — Generate a new key

```bash
python -m config.secrets.generator --jwt
```

(Or any ≥32-byte high-entropy secret. Validation rules:
`src/config/secrets/validation.py::validate_jwt_key`.)

### Step 2 — Deploy with the new key

Replace `JWT_KEY` in your `.env` (dev) or encrypted env file (prod, see
`docs/SECRET_MANAGEMENT.md`) and restart the app.

### Step 3 — What happens automatically

- `decode_token` fails with `JWTError` → the API answers
  `401 Token not valid. Please login again.`
- There is **no server-side token state**: no blocklist, no revocation DB,
  nothing to clean up. Sessions live entirely in the user's browser.
- MFA-challenge state (`mfa_runtime`, Mongo-backed) is keyed by user tag, not by
  token, so pending email challenges survive rotation — but the pending JWT
  pointing at them does not, so users effectively redo the full login flow.

### Step 4 — Communicate

Tell users: "You will be logged out once; log in again."

### Optional: zero-downtime rotation (grace period)

The current `decode_token` accepts exactly one key. If you need an overlap
window, add a `JWT_KEY_PREVIOUS` setting and try both keys in `decode_token`
(previous only for verification, never for signing), then remove it after
`expires_after_hours` (48h default) has elapsed.

---

## 4. Cookbook: rotating `JWT_SHARE_KEY` (share tokens)

Same procedure as §3 with one difference: share tokens are long-lived
(`SHARE_EXPIRES_AFTER_HOURS`, default 120 days ≈ 4 months).

- **Implication:** any script/client pushing QC runs with an old share token
  gets `401` until an admin issues a new one via `POST /api/auth/token/share`
  (requires admin rights + `SHARE_TOKEN_PW`).
- **Recommended:** before rotating, collect the consumers that hold tokens and
  plan re-issuing; or implement the `JWT_KEY_PREVIOUS` overlap trick of §3
  with a window of at least the longest token lifetime you care about.

---

## 5. Cookbook: rotating `MFA_ENCRYPTION_KEY` (⚠️ the one that matters)

TOTP secrets are stored Fernet-encrypted in the user collection:

```python
# src/routers/authentication/token.py
fernet = Fernet(MFA_SETTINGS.MFA_ENCRYPTION_KEY.get_secret_value())
db_user.mfa_secret = fernet.decrypt(db_user.mfa_secret.encode()).decode()
```

If you rotate this key, **every existing `mfa_secret` becomes unreadable** and
MFA verification raises an error for all MFA-enabled users.

### Option A — Migrate (no user impact)

1. Keep the old key available (e.g. `MFA_ENCRYPTION_KEY_OLD`).
2. Run a one-off migration: decrypt each user's `mfa_secret` with the old key,
   re-encrypt with the new key, write back.
3. Verify a sample of users can log in, then remove the old key from the
   environment.

### Option B — Reset (simple, disruptive)

1. Deploy the new key.
2. Clear `mfa_enabled` / `mfa_secret` for affected users.
3. Users go through first-login MFA setup again (the app already emails a
   setup code when `mfa_enabled` is false).

**Never** rotate `MFA_ENCRYPTION_KEY` without choosing A or B explicitly.

---

## 6. Cookbook: changing the password hash algorithm

`HASH_ALGORITHM` (`src/config/settings/encryption.py`) currently allows
`bcrypt`, `pbkdf2_sha256`, `pbkdf2_sha512`. Passlib embeds the algorithm
identifier in each hash, and `CryptContext(deprecated="auto")` is already
configured — this gives you lazy migration for free:

1. Change `HASH_ALGORITHM` in settings (e.g. to `pbkdf2_sha256`).
2. Restart. Old bcrypt hashes **still verify** (passlib detects the scheme from
   the hash string).
3. Optional lazy upgrade: on successful login, when
   `pwd_context.needs_update(hash)` is true, re-hash the just-verified
   plaintext password and store the new hash.
4. No "update all passwords" step is required or possible — you never have the
   plaintexts.

---

## 7. Rotation checklist (print me)

```text
[ ] Backup current .env / encrypted env
[ ] Generate new secret(s): python -m config.secrets.generator --jwt
[ ] JWT_KEY only?            → no DB work, users re-login
[ ] JWT_SHARE_KEY?           → notify share-token consumers, re-issue tokens
[ ] MFA_ENCRYPTION_KEY?      → choose migrate (Option A) or reset (Option B)
[ ] HASH_ALGORITHM?          → nothing required; optional lazy re-hash on login
[ ] Restart app and run smoke test: login + token validation
[ ] Verify docs/DEPLOYMENT_CHECKLIST.md secrets checklist still passes
```

---

## 8. Related docs

- `docs/SECRET_MANAGEMENT.md` — env file encryption and secret validation
- `docs/DEPLOYMENT_CHECKLIST.md` — pre-deploy security checks
- `src/config/secrets/validation.py` — minimum secret quality rules
