# MitoCube Documentation

Welcome to the MitoCube Backend documentation! This directory contains comprehensive guides for setting up, configuring, and deploying MitoCube.

---

## 📚 **Documentation Overview**

| Document | Purpose | Audience |
|----------|---------|----------|
| [Production Setup Guide](PRODUCTION_SETUP.md) | Complete step-by-step production deployment | System administrators, DevOps |
| [Secret Management Guide](SECRET_MANAGEMENT.md) | Secure secret management for all environments | Developers, System administrators |
| [Deployment Checklist](DEPLOYMENT_CHECKLIST.md) | Complete checklist for deployment verification | DevOps, System administrators |

---

## 🎯 **Quick Start**

### For Development (No Changes Required)

```bash
# 1. Copy the example configuration
cp .env.example .env

# 2. Edit with your values
nano .env

# 3. Start the application
python -m uvicorn src.app:app --reload
```

**That's it!** Development workflow is completely unchanged.

---

### For Production (New Setup)

Follow the **[Production Setup Guide](PRODUCTION_SETUP.md)** for a complete step-by-step guide.

**Quick Overview:**

1. **Install dependencies** - Python, Neo4j, MongoDB (optional)
2. **Configure secrets** - Generate and encrypt your `.env` file
3. **Set up databases** - Neo4j and MongoDB
4. **Configure Nginx** - Reverse proxy with SSL
5. **Create systemd service** - For automatic startup
6. **Deploy** - Start MitoCube with `deploy.py`

---

## 🔐 **Secret Management**

MitoCube now has a **complete secret management system** that works without external services.

### Key Features
- ✅ **No hardcoded defaults** - All secrets must be provided
- ✅ **Encrypted `.env` files** - Protect secrets at rest
- ✅ **Validation on startup** - Fails fast on bad configuration
- ✅ **Secure secret generation** - CLI tool for compliant secrets
- ✅ **Production deployment script** - Handles decryption and validation

### Learn More
- **[Secret Management Guide](SECRET_MANAGEMENT.md)** - Complete guide to the secret management system

---

## 🚀 **Production Deployment**

Deploying MitoCube to production involves several steps. The **[Production Setup Guide](PRODUCTION_SETUP.md)** provides detailed instructions for:

### Prerequisites
- System requirements (Ubuntu/CentOS, Python 3.10+, 16GB RAM)
- Required services (Neo4j, MongoDB, Email Server, Nginx)
- Dependencies installation

### Setup Steps (14 Total)
1. **Install MitoCube** - Clone repository, create virtual environment
2. **Configure Secrets** - Generate encryption key, create `.env`, encrypt it
3. **Configure Neo4j** - Install, configure, set passwords
4. **Configure MongoDB** - Install, configure (optional for AI features)
5. **Configure Email** - SMTP server settings
6. **Configure Nginx** - Reverse proxy with SSL
7. **Configure Systemd** - Service for automatic startup
8. **Configure Firewall** - Open required ports
9. **Final Configuration** - Trusted proxies, rate limiting
10. **Test Production Setup** - Verify everything works
11. **Set Up Monitoring** - Health checks, logging
12. **Backup Strategy** - Regular backups of data and configuration
13. **Security Hardening** - SSH, Fail2Ban
14. **Update and Maintenance** - Procedures for updates

### Verification
Use the **[Deployment Checklist](DEPLOYMENT_CHECKLIST.md)** to verify all steps are completed correctly.

---

## ✅ **Deployment Checklist**

The **[Deployment Checklist](DEPLOYMENT_CHECKLIST.md)** is a comprehensive checklist covering:

### Pre-Deployment
- System requirements verification
- Dependencies installation

### Secret Management
- Encryption key generation and backup
- `.env` file creation and encryption
- Secret validation

### Database Setup
- Neo4j installation and configuration
- MongoDB installation and configuration (optional)

### Network Configuration
- Reverse proxy (Nginx) setup
- SSL certificate configuration
- Firewall configuration

### Application Setup
- Installation
- Systemd service creation

### Security
- SSH hardening
- Fail2Ban configuration
- Rate limiting setup

### Testing
- Service tests
- Connection tests
- API tests
- Frontend tests

### Maintenance
- Backup strategy
- Monitoring setup
- Update procedures

### Go-Live
- Final verification
- Go-live checklist
- Post-deployment checklist

**Perfect for:** Tracking deployment progress, team coordination, audit purposes

---

## 📋 **Documentation Structure**

```
docs/
├── README.md                    # This file - Documentation overview
├── PRODUCTION_SETUP.md          # Step-by-step production deployment
├── SECRET_MANAGEMENT.md         # Complete secret management guide
└── DEPLOYMENT_CHECKLIST.md      # Complete deployment checklist
```

---

## 🔍 **Finding What You Need**

| Need | Document | Section |
|------|----------|---------|
| First production deployment | [Production Setup](PRODUCTION_SETUP.md) | All steps |
| Understanding secret management | [Secret Management](SECRET_MANAGEMENT.md) | Overview |
| Generating secure secrets | [Secret Management](SECRET_MANAGEMENT.md) | Secret Generation |
| Encrypting `.env` files | [Secret Management](SECRET_MANAGEMENT.md) | Encryption |
| Setting up Neo4j | [Production Setup](PRODUCTION_SETUP.md) | Step 3 |
| Setting up MongoDB | [Production Setup](PRODUCTION_SETUP.md) | Step 4 |
| Configuring Nginx | [Production Setup](PRODUCTION_SETUP.md) | Step 6 |
| Creating systemd service | [Production Setup](PRODUCTION_SETUP.md) | Step 7 |
| Firewall configuration | [Production Setup](PRODUCTION_SETUP.md) | Step 8 |
| Security hardening | [Production Setup](PRODUCTION_SETUP.md) | Step 13 |
| Backup strategy | [Production Setup](PRODUCTION_SETUP.md) | Step 12 |
| Monitoring setup | [Production Setup](PRODUCTION_SETUP.md) | Step 11 |
| Deployment verification | [Deployment Checklist](DEPLOYMENT_CHECKLIST.md) | All checklists |
| Troubleshooting | [Production Setup](PRODUCTION_SETUP.md) | Troubleshooting |
| Troubleshooting secrets | [Secret Management](SECRET_MANAGEMENT.md) | Troubleshooting |

---

## 💡 **Best Practices**

### Development
1. **Use `.env` file** - Copy from `.env.example`
2. **Never commit `.env`** - It's in `.gitignore`
3. **Generate secure secrets** - Use `python -m config.secrets.generator`
4. **Test locally** - Before committing changes

### Production
1. **Always encrypt `.env`** - Use `deploy.py` with encrypted files
2. **Backup encryption key** - Store securely in multiple locations
3. **Use HTTPS** - Always, with valid certificates
4. **Hardened SSH** - Disable password login, use keys only
5. **Monitor everything** - Services, logs, performance
6. **Regular backups** - Data and configuration
7. **Test backups** - Verify restore procedures

---

## 🆘 **Troubleshooting**

### Common Issues

| Issue | Solution | Document |
|-------|----------|----------|
| Service won't start | Check logs, verify secrets | [Production Setup](PRODUCTION_SETUP.md) |
| Database connection issues | Test connections, verify credentials | [Production Setup](PRODUCTION_SETUP.md) |
| Encryption key issues | Verify key, test decryption | [Secret Management](SECRET_MANAGEMENT.md) |
| Missing required secret | Check `.env`, generate secret | [Secret Management](SECRET_MANAGEMENT.md) |
| Secret validation failed | Check secret format, regenerate | [Secret Management](SECRET_MANAGEMENT.md) |

### Getting Help

1. **Check the relevant documentation** above
2. **Review logs**: `sudo journalctl -u mitocube -n 100`
3. **Test connections** to databases and services
4. **Verify configuration** in `.env` or `.env.enc`

---

## 📊 **Version Information**

| Component | Version | Notes |
|-----------|---------|-------|
| MitoCube Backend | 0.1 | Current version |
| Python | 3.10+ | Required |
| Neo4j | 5.x | Recommended |
| MongoDB | 6.x | Optional (for AI) |
| Nginx | Latest | Recommended |

---

## 🔗 **Related Resources**

- **[Main README](../README.md)** - Project overview, quick start
- **[Setup Documentation](../docs/SETUP.md)** - Database setup and migration
- **[GitHub Repository](https://github.com/hnolCol/mitocube-backend)** - Source code
- **[Issues](https://github.com/hnolCol/mitocube-backend/issues)** - Report issues

---

## 📝 **Changelog**

| Date | Changes |
|------|---------|
| 2024-10-08 | Added comprehensive production documentation |
| 2024-10-08 | Added secret management system |
| 2024-10-08 | Removed all hardcoded defaults |

---

## 🤝 **Contributing**

If you find issues or have suggestions for the documentation:

1. **Check existing issues** on GitHub
2. **Create a new issue** with details
3. **Submit a PR** with improvements

---

*Last updated: 2024-10-08*
