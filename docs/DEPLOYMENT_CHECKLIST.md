# Deployment Checklist for MitoCube

## 📋 Pre-Deployment Checklist

Complete this checklist **before** deploying MitoCube to production.

---

## ⚙️ System Requirements

- [ ] **Operating System**: Ubuntu 22.04/24.04 or CentOS 8/9
- [ ] **Python**: 3.10 or higher installed
- [ ] **Memory**: 16GB+ available
- [ ] **Disk Space**: 100GB+ available
- [ ] **CPU**: 4+ cores
- [ ] **Dependencies**: git, nginx, curl installed

---

## 🔐 Secret Management

### Encryption Key
- [ ] Generated encryption key: `python -c "from config.secrets.encryption import EnvFileEncryptor; print(EnvFileEncryptor().get_key())"`
- [ ] **Backed up encryption key** securely (password manager, encrypted file, or physical backup)
- [ ] Stored encryption key in secure location:
  - [ ] `/etc/mitocube/encryption_key` (recommended)
  - [ ] Environment variable in deployment system
  - [ ] Password manager

### `.env` File
- [ ] Copied `.env.example` to `.env`
- [ ] Filled in all **REQUIRED** secrets:
  - [ ] `JWT_KEY` (>= 32 characters)
  - [ ] `JWT_SHARE_KEY` (>= 32 characters)
  - [ ] `NEO4J_PASSWORD` (>= 12 characters, complex)
  - [ ] `MONGO_PASSWORD` (>= 12 characters, complex)
  - [ ] `MAIL_PASSWORD` (>= 12 characters, complex)
  - [ ] `SHARE_TOKEN_PW` (>= 12 characters, complex)
  - [ ] `MFA_ENCRYPTION_KEY` (>= 32 characters)
- [ ] Filled in all **OPTIONAL** settings:
  - [ ] Database configuration (DB_URI, DB_USER, DB_NAME)
  - [ ] Email configuration (MAIL_SERVER, MAIL_PORT, MAIL_USERNAME)
  - [ ] Application settings (APP_NAME, VERSION, LEAD_CONTACT)
  - [ ] File paths (ATTRIBUTE_FILE, FRONTEND_BUILD, etc.)
  - [ ] Allowed email domains (ALLOWED_EMAIL_DOMAINS)

### Encryption
- [ ] Encrypted `.env` file: `python -c "from config.secrets.encryption import EnvFileEncryptor, get_encryption_key; EnvFileEncryptor(get_encryption_key()).encrypt_file('.env')"`
- [ ] Verified `.env.enc` file exists
- [ ] Removed plaintext `.env` file
- [ ] Tested decryption: `python -c "from config.secrets.encryption import EnvFileEncryptor, get_encryption_key; EnvFileEncryptor(get_encryption_key()).decrypt_file('.env.enc', '.env')"`

---

## 🗄️ Database Setup

### Neo4j
- [ ] Neo4j installed (version 5.x recommended)
- [ ] Neo4j configuration updated:
  - [ ] Remote connections enabled (`dbms.connector.bolt.listen_address=0.0.0.0:7687`)
  - [ ] Authentication enabled (`dbms.security.auth_enabled=true`)
  - [ ] Memory settings configured appropriately
  - [ ] Import directory configured
- [ ] Neo4j user password set
- [ ] Dedicated user created for MitoCube (optional but recommended)
- [ ] Neo4j service enabled and running
- [ ] Neo4j starts on boot
- [ ] Tested Neo4j connection: `cypher-shell -u neo4j -p password "RETURN 1"`

### MongoDB (Optional - for AI Features)
- [ ] MongoDB installed
- [ ] MongoDB configuration updated:
  - [ ] Remote connections enabled
  - [ ] Authentication enabled
- [ ] MongoDB user created for AI agent
- [ ] MongoDB databases created (mongodb, auth)
- [ ] MongoDB service enabled and running
- [ ] MongoDB starts on boot
- [ ] Tested MongoDB connection

---

## 📧 Email Configuration

- [ ] Email server details configured in `.env`:
  - [ ] `MAIL_SERVER`
  - [ ] `MAIL_PORT`
  - [ ] `MAIL_USERNAME`
  - [ ] `MAIL_PASSWORD`
  - [ ] `MAIL_DEFAULT_SENDER`
  - [ ] `MAIL_FROM_NAME`
- [ ] Email template directory configured: `MAIL_TEMPLATE_DIR`
- [ ] Tested email sending (see Production Setup guide)

---

## 🌐 Network Configuration

### Reverse Proxy (Nginx)
- [ ] Nginx installed
- [ ] SSL certificate obtained:
  - [ ] Let's Encrypt (recommended)
  - [ ] Self-signed (testing only)
  - [ ] Commercial certificate
- [ ] Nginx configuration created:
  - [ ] HTTP to HTTPS redirect
  - [ ] SSL configuration
  - [ ] Proxy to MitoCube (port 5002)
  - [ ] Static files configuration
  - [ ] Security headers
  - [ ] X-Forwarded-For header for rate limiting
- [ ] Nginx configuration tested: `sudo nginx -t`
- [ ] Nginx service enabled and running
- [ ] Nginx starts on boot

### Firewall
- [ ] Firewall enabled (UFW or firewalld)
- [ ] Required ports open:
  - [ ] 22 (SSH)
  - [ ] 80 (HTTP - redirects to HTTPS)
  - [ ] 443 (HTTPS)
  - [ ] 7687 (Neo4j Bolt)
  - [ ] 7474 (Neo4j HTTP - optional)
  - [ ] 27017 (MongoDB - optional)

---

## 🚀 Application Setup

### Installation
- [ ] Repository cloned to `/opt/mitocube`
- [ ] Virtual environment created: `python3 -m venv venv`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] AI dependencies installed (if needed): `pip install -r requirements-ai.txt`
- [ ] Dedicated user created: `sudo adduser --system --group mitocube`
- [ ] Ownership set: `sudo chown -R mitocube:mitocube /opt/mitocube`

### Systemd Service
- [ ] Systemd service file created: `/etc/systemd/system/mitocube.service`
- [ ] Service configuration includes:
  - [ ] Correct user/group (mitocube)
  - [ ] Working directory (/opt/mitocube)
  - [ ] Environment variables (UVICORN_HOST, UVICORN_PORT, etc.)
  - [ ] Encryption key configuration
  - [ ] Restart policy (always, 5 seconds delay)
  - [ ] Security settings (PrivateTmp, ProtectSystem, etc.)
- [ ] Service enabled: `sudo systemctl enable mitocube`
- [ ] Service started: `sudo systemctl start mitocube`
- [ ] Service status checked: `sudo systemctl status mitocube`

---

## 🔒 Security

### SSH Hardening
- [ ] Root login disabled
- [ ] Password authentication disabled
- [ ] SSH port changed (optional)
- [ ] SSH users restricted
- [ ] Empty passwords disabled
- [ ] Strong encryption ciphers configured

### Fail2Ban
- [ ] Fail2Ban installed
- [ ] Fail2Ban configured for SSH
- [ ] Fail2Ban enabled and running

### Rate Limiting
- [ ] Trusted proxy IPs configured in `.env`: `TRUSTED_PROXY_IPS`
- [ ] Login rate limit configured:
  - [ ] `LOGIN_RATE_LIMIT_MAX_ATTEMPTS`
  - [ ] `LOGIN_RATE_LIMIT_WINDOW_MINUTES`
- [ ] MFA settings configured:
  - [ ] `MFA_MAX_ATTEMPTS`
  - [ ] `MFA_LOCKOUT_MINUTES`

### Application Security
- [ ] All hardcoded defaults removed
- [ ] Secret validation enabled
- [ ] Encrypted `.env` file in production
- [ ] No plaintext secrets in repository

---

## 📊 Testing

### Service Tests
- [ ] All services running:
  - [ ] MitoCube: `sudo systemctl status mitocube`
  - [ ] Neo4j: `sudo systemctl status neo4j`
  - [ ] MongoDB: `sudo systemctl status mongod` (if using AI)
  - [ ] Nginx: `sudo systemctl status nginx`

### Connection Tests
- [ ] Neo4j connection tested
- [ ] MongoDB connection tested (if using AI)
- [ ] Database connections from application tested

### API Tests
- [ ] Health endpoint tested: `curl http://localhost:5002/api/health`
- [ ] Health endpoint tested through Nginx: `curl https://mitocube.your-domain.com/api/health`
- [ ] API returns expected responses

### Frontend Tests
- [ ] Frontend accessible via HTTPS: `https://mitocube.your-domain.com`
- [ ] Frontend loads without errors
- [ ] Static assets loading correctly

---

## 📝 Documentation

- [ ] Production setup documented
- [ ] Secret management documented
- [ ] Backup strategy documented
- [ ] Monitoring configured and documented
- [ ] Troubleshooting guide available
- [ ] Runbook created for operations team

---

## 🔄 Maintenance

### Backups
- [ ] Backup strategy documented
- [ ] Backup script created: `/usr/local/bin/mitocube-backup`
- [ ] Backup script tested
- [ ] Backup cron job configured
- [ ] Backup retention policy set (30 days recommended)
- [ ] Backup verification procedure in place

### Monitoring
- [ ] Health check script created: `/usr/local/bin/mitocube-health-check`
- [ ] Health check cron job configured
- [ ] Log rotation configured
- [ ] Monitoring tools installed (optional):
  - [ ] Prometheus
  - [ ] Grafana
  - [ ] Other monitoring tools

### Updates
- [ ] Update procedure documented
- [ ] Update testing procedure in place
- [ ] Rollback procedure documented

---

## ✅ Final Verification

Before going live, verify:

### Application
- [ ] Application starts without errors
- [ ] All required secrets are present and valid
- [ ] No validation errors on startup
- [ ] All API endpoints responding
- [ ] Frontend loading correctly

### Security
- [ ] No plaintext secrets in files
- [ ] No hardcoded passwords in code
- [ ] Encryption key stored securely
- [ ] All services using HTTPS
- [ ] Firewall configured correctly
- [ ] SSH hardened

### Performance
- [ ] Application responds within acceptable time
- [ ] Database queries performing well
- [ ] No memory leaks
- [ ] CPU usage acceptable

### Data
- [ ] All required data loaded
- [ ] Database connections working
- [ ] Data integrity verified

---

## 🎯 Go-Live Checklist

- [ ] **Pre-deployment checklist** completed
- [ ] **All tests** passed
- [ ] **Documentation** updated
- [ ] **Team** trained
- [ ] **Backup** verified
- [ ] **Monitoring** in place
- [ ] **Rollback plan** documented
- [ ] **Maintenance procedures** documented

---

## 📞 Post-Deployment

After going live:

### Immediate (First 24 Hours)
- [ ] Monitor application logs closely
- [ ] Verify all features working
- [ ] Check for errors or warnings
- [ ] Monitor performance metrics
- [ ] Verify backups are working

### First Week
- [ ] Review logs for any issues
- [ ] Check monitoring alerts
- [ ] Verify backup completion
- [ ] Test restore from backup
- [ ] Review security logs

### First Month
- [ ] Review all logs
- [ ] Check performance metrics
- [ ] Verify backup retention
- [ ] Test disaster recovery
- [ ] Review security

---

## 💡 Tips

1. **Start small**: Deploy to a staging environment first
2. **Test thoroughly**: Test all features before production
3. **Monitor closely**: Watch logs and metrics after deployment
4. **Document everything**: Keep documentation up to date
5. **Automate**: Automate backups, monitoring, and updates
6. **Security first**: Always prioritize security
7. **Plan for failure**: Have rollback and recovery plans

---

## 📚 References

- [Production Setup Guide](PRODUCTION_SETUP.md)
- [Secret Management Guide](SECRET_MANAGEMENT.md)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)

---

*Last updated: 2024-10-08*
