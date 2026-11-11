# Systemd Deployment Guide: Secrets via EnvironmentFile

## Overview

This guide covers production deployments where a systemd unit (`mitocube.service`)
starts uvicorn directly — no `deploy.py` involved. Secrets are stored in a
plaintext env file **outside the repository**, protected by file permissions,
and injected into the service by systemd at start time.

How it works:

- systemd reads `/etc/mitocube/env` and passes every `KEY=VALUE` line to the
  service as real environment variables.
- pydantic-settings reads actual environment variables **before** falling back
  to `.env` files, so no `.env` file is needed in the repo directory at all.
- The repo directory stays free of secrets; a backup copy can additionally be
  kept encrypted (`.env.enc`) using `config.secrets.encryption`.

---

## Step 1 — Create the secrets directory

```bash
sudo mkdir -p /etc/mitocube
sudo chmod 755 /etc/mitocube
```

## Step 2 — Create the env file from the example

```bash
sudo cp .env.example /etc/mitocube/env
sudo nano /etc/mitocube/env
```

Fill in all REQUIRED values (marked `# REQUIRED` in the example). To generate
compliant secrets:

```bash
python -m config.secrets.generator --all
```

## Step 3 — Lock down the file

```bash
sudo chown root:root /etc/mitocube/env
sudo chmod 600 /etc/mitocube/env
```

Only `root` can read it now. systemd reads it as root before dropping to the
service user.

## Step 4 — Point the service at it

Edit `/etc/systemd/system/mitocube.service` and add `EnvironmentFile=` to the
`[Service]` section:

```ini
[Service]
EnvironmentFile=/etc/mitocube/env
WorkingDirectory=/opt/mitocube-backend
ExecStart=/opt/mitocube-backend/.venv/bin/python -m uvicorn src.app:app --host 0.0.0.0 --port 5002 --proxy-headers
User=mitocube
Group=mitocube

# Optional hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/opt/mitocube-backend
```

Adjust `WorkingDirectory` and the python/uvicorn path to your installation.

## Step 5 — Reload and (re)start

```bash
sudo systemctl daemon-reload
sudo systemctl restart mitocube.service
sudo systemctl status mitocube.service
```

## Step 6 — Verify

```bash
# Service running and no secret-validation errors:
journalctl -u mitocube.service -n 50 --no-pager

# The app found no .env in the repo dir (expected) and used the
# systemd-provided environment variables instead.
```

If startup fails with a missing-secret `ValueError`, systemd did not pass the
file — check `systemctl show mitocube.service -p Environment` (shown only to
root) and confirm `EnvironmentFile=` points to the right path.

---

## Updating secrets later

```bash
sudo nano /etc/mitocube/env
sudo systemctl restart mitocube.service
```

## Optional: keep an encrypted backup copy

The plaintext file on the server is protected by permissions, but backups
should not contain plaintext secrets:

```bash
# One-time: generate a full-entropy key and store it in a password manager
python -c "from config.secrets.encryption import EnvFileEncryptor; print(EnvFileEncryptor().get_key())"

# Encrypt the env file for backup
python -c "from config.secrets.encryption import EnvFileEncryptor as E; E('<your-key>').encrypt_file('/etc/mitocube/env', '/safe/location/env.enc')"

# Restore later
python -c "from config.secrets.encryption import EnvFileEncryptor as E; E('<your-key>').decrypt_file('/safe/location/env.enc', '/etc/mitocube/env')"
sudo chown root:root /etc/mitocube/env && sudo chmod 600 /etc/mitocube/env
```

See `docs/SECRET_MANAGEMENT.md` for the full secret-management model.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Service fails secret validation at startup | `EnvironmentFile=` missing or wrong path in the unit |
| `Permission denied` reading the env file | File owner/mode wrong — must be `root:root 600` |
| Changes to secrets not applied | `systemctl restart` not run after editing |
| Values with `#` or spaces behave oddly | Quote them: `MAIL_PASSWORD="my#pass word"` |
