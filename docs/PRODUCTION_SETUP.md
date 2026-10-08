# Production Setup Guide for MitoCube

## Overview

This guide walks you through setting up MitoCube in a **production environment** with proper security configurations.

---

## Prerequisites

Before starting, ensure you have:

### System Requirements
- **Operating System**: Ubuntu 22.04/24.04 LTS or CentOS 8/9 (recommended)
- **Python**: 3.10 or higher
- **Memory**: 16GB+ (for Neo4j and application)
- **Disk Space**: 100GB+ (depending on data size)
- **CPU**: 4+ cores

### Required Services
- **Neo4j**: Graph database (version 5.x recommended)
- **MongoDB**: For AI agent features (optional, but recommended)
- **Email Server**: For user notifications (SMTP)
- **Reverse Proxy**: Nginx or Apache (for HTTPS and load balancing)

### Dependencies
```bash
# System packages
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git nginx

# For CentOS/RHEL:
sudo yum install -y python3 python3-pip git nginx
```

---

## Step 1: Install MitoCube

### Clone the Repository

```bash
# Clone to /opt/mitocube
sudo mkdir -p /opt
sudo chown $USER:$USER /opt
cd /opt
git clone https://github.com/hnolCol/mitocube-backend.git mitocube
cd mitocube
```

### Create Virtual Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# For AI features (optional)
pip install -r requirements-ai.txt
```

### Create User for MitoCube

```bash
# Create a dedicated user
sudo adduser --system --group --shell /bin/false mitocube
sudo chown -R mitocube:mitocube /opt/mitocube
```

---

## Step 2: Configure Secrets

### Generate Encryption Key

```bash
# Generate a secure encryption key
python -c "from config.secrets.encryption import EnvFileEncryptor; print(EnvFileEncryptor().get_key())"

# Example output: "kF3n...XyZ="
# COPY THIS AND STORE IT SECURELY!
```

### Store Encryption Key

**Recommended**: Store in `/etc/mitocube/encryption_key`

```bash
# Create secure directory
sudo mkdir -p /etc/mitocube
sudo chmod 700 /etc/mitocube

# Store the key (replace with your actual key)
echo "kF3n...XyZ=" | sudo tee /etc/mitocube/encryption_key
sudo chmod 600 /etc/mitocube/encryption_key

# Verify
sudo cat /etc/mitocube/encryption_key
```

### Generate Secure Secrets

```bash
# Generate all required secrets
python -m config.secrets.generator --all --format env > .env

# Or generate individually and edit .env manually
python -m config.secrets.generator --jwt
python -m config.secrets.generator --password --length 24
```

### Edit `.env` File

```bash
# Copy template
cp .env.example .env

# Edit with nano or vim
nano .env
```

**Required settings to configure**:

```ini
# ===== REQUIRED SECRETS =====
# (Generated above, but verify they're set)

JWT_KEY=your-generated-jwt-key
JWT_SHARE_KEY=your-generated-jwt-share-key
NEO4J_PASSWORD=your-neo4j-password
MONGO_PASSWORD=your-mongodb-password
MAIL_PASSWORD=your-email-password
SHARE_TOKEN_PW=your-share-token-password
MFA_ENCRYPTION_KEY=your-mfa-encryption-key

# ===== DATABASE =====
DB_URI=bolt://localhost:7687
DB_USER=neo4j
DB_NAME=neo4j

# ===== EMAIL =====
MAIL_SERVER=your-smtp-server.com
MAIL_PORT=587
MAIL_USERNAME=your-email@domain.com
MAIL_DEFAULT_SENDER=mitocube@your-domain.com
MAIL_TEMPLATE_DIR=/opt/mitocube/src/config/settings/email/templates

# ===== APPLICATION =====
APP_NAME=MitoCube
VERSION=0.1
LEAD_CONTACT=admin@your-domain.com
ATTRIBUTE_FILE=/opt/mitocube/resources/attributes/attributes.json
FRONTEND_BUILD=/opt/mitocube/frontend/build
FRONTEND_BUILD_ASSETS=/opt/mitocube/frontend/build/assets

# ===== ALLOWED EMAIL DOMAINS =====
# Restrict registration to specific domains
ALLOWED_EMAIL_DOMAINS=["@your-domain.com", "@partner-domain.com"]
```

### Encrypt `.env` for Production

```bash
# Encrypt the .env file
python -c "from config.secrets.encryption import EnvFileEncryptor, get_encryption_key; e = EnvFileEncryptor(get_encryption_key()); e.encrypt_file('.env')"

# Verify encrypted file exists
ls -la .env.enc

# Remove plaintext .env
rm .env
```

---

## Step 3: Configure Neo4j

### Install Neo4j

```bash
# For Ubuntu/Debian
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable 5' | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt update
sudo apt install -y neo4j

# For CentOS/RHEL
sudo rpm --import https://debian.neo4j.com/neotechnology.gpg.key
sudo yum-config-manager --add-repo https://yum.neo4j.com/stable/5
sudo yum install -y neo4j
```

### Configure Neo4j

```bash
# Edit Neo4j configuration
sudo nano /etc/neo4j/neo4j.conf
```

**Required changes**:

```ini
# Enable remote connections
dbms.connector.bolt.listen_address=0.0.0.0:7687
dbms.connector.http.listen_address=0.0.0.0:7474

# Authentication
dbms.security.auth_enabled=true

# Memory settings (adjust based on available RAM)
dbms.memory.heap.initial_size=4g
dbms.memory.heap.max_size=8g
dbms.memory.pagecache.size=2g

# Allow loading from custom path
dbms.directories.import=import
```

### Set Neo4j Password

```bash
# Start Neo4j
sudo systemctl start neo4j

# Set password for neo4j user (use the password from your .env)
cypher-shell -u neo4j -p neo4j "ALTER USER neo4j SET PASSWORD 'your-neo4j-password'"

# Or use Neo4j Browser at http://localhost:7474
```

### Create Database User (Optional)

```bash
# Connect to Neo4j
cypher-shell -u neo4j -p your-neo4j-password

# Create a dedicated user for MitoCube
CREATE USER mitocube SET PASSWORD 'your-neo4j-password' CHANGE NOT REQUIRED;
GRANT ALL PRIVILEGES ON DATABASE neo4j TO mitocube;
:exit

# Update .env to use this user
# DB_USER=mitocube
# NEO4J_PASSWORD=your-neo4j-password
```

### Enable Neo4j to Start on Boot

```bash
sudo systemctl enable neo4j
sudo systemctl start neo4j
```

---

## Step 4: Configure MongoDB (Optional - for AI Features)

### Install MongoDB

```bash
# For Ubuntu/Debian
sudo apt install -y mongodb-org

# For CentOS/RHEL
sudo yum install -y mongodb-org
```

### Configure MongoDB

```bash
# Edit MongoDB configuration
sudo nano /etc/mongod.conf
```

**Required changes**:

```yaml
# Enable remote connections
net:
  bindIp: 0.0.0.0
  port: 27017

# Enable authentication
security:
  authorization: enabled
```

### Set MongoDB Password

```bash
# Start MongoDB
sudo systemctl start mongod

# Connect and create user
mongo

# In MongoDB shell:
use admin
db.createUser({
  user: "ai",
  pwd: "your-mongodb-password",
  roles: ["root"]
})

# Create databases for AI and MFA
db = db.getSiblingDB("mongodb")
db.createUser({
  user: "ai",
  pwd: "your-mongodb-password",
  roles: ["readWrite"]
})

db = db.getSiblingDB("auth")
db.createUser({
  user: "ai",
  pwd: "your-mongodb-password",
  roles: ["readWrite"]
})

exit
```

### Enable MongoDB to Start on Boot

```bash
sudo systemctl enable mongod
sudo systemctl start mongod
```

---

## Step 5: Configure Email

### Email Server Configuration

Configure your SMTP server in `.env`:

```ini
MAIL_SERVER=smtp.your-domain.com
MAIL_PORT=587
MAIL_USERNAME=mitocube@your-domain.com
MAIL_PASSWORD=your-email-password
MAIL_USE_TLS_SSL=False
MAIL_START_TLS=True
MAIL_DEFAULT_SENDER=mitocube@your-domain.com
MAIL_FROM_NAME=MitoCube Support
MAIL_TEMPLATE_DIR=/opt/mitocube/src/config/settings/email/templates
MAIL_VALIDATE_CERTS=False
```

### Test Email Configuration

```bash
# Create a test script
cat > test_email.py << 'EOF'
import os
os.environ['MAIL_SERVER'] = 'your-smtp-server'
os.environ['MAIL_PORT'] = '587'
os.environ['MAIL_USERNAME'] = 'your-email'
os.environ['MAIL_PASSWORD'] = 'your-password'
os.environ['MAIL_DEFAULT_SENDER'] = 'mitocube@your-domain.com'

from services.mail import send_email
send_email(
    to="test@example.com",
    subject="Test Email",
    body="This is a test email from MitoCube"
)
print("Email sent!")
EOF

# Run test
python test_email.py
rm test_email.py
```

---

## Step 6: Configure Reverse Proxy (Nginx)

### Install SSL Certificate

**Option A: Let's Encrypt (Recommended)**

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot certonly --nginx -d mitocube.your-domain.com

# Certificates are stored in /etc/letsencrypt/live/mitocube.your-domain.com/
```

**Option B: Self-Signed Certificate (Testing Only)**

```bash
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/mitocube.key \
  -out /etc/ssl/certs/mitocube.crt \
  -subj "/CN=mitocube.your-domain.com"
```

### Configure Nginx

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/mitocube
```

**Configuration**:

```nginx
upstream mitocube {
    server 127.0.0.1:5002;
}

server {
    listen 80;
    server_name mitocube.your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name mitocube.your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/mitocube.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mitocube.your-domain.com/privkey.pem;
    
    # SSL settings (recommended)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Proxy configuration
    location / {
        proxy_pass http://mitocube;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # Required for login rate limiting
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # Static files
    location /assets {
        alias /opt/mitocube/frontend/build/assets;
        expires 30d;
        access_log off;
    }
    
    # Health check endpoint
    location /api/health {
        proxy_pass http://mitocube;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
```

### Enable Nginx Configuration

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/mitocube /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Enable on boot
sudo systemctl enable nginx
```

---

## Step 7: Configure Systemd Service

### Create Systemd Service File

```bash
sudo nano /etc/systemd/system/mitocube.service
```

**Service Configuration**:

```ini
[Unit]
Description=MitoCube Backend
After=network.target neo4j.service mongod.service
Wants=neo4j.service mongod.service

[Service]
User=mitocube
Group=mitocube
WorkingDirectory=/opt/mitocube
Environment=PYTHONUNBUFFERED=1
Environment=UVICORN_HOST=0.0.0.0
Environment=UVICORN_PORT=5002
Environment=UVICORN_WORKERS=4
Environment=MITOCUBE_SKIP_SECRET_VALIDATION=0

# Encryption key (use file-based for security)
Environment=ENCRYPTION_KEY_FILE=/etc/mitocube/encryption_key

ExecStart=/opt/mitocube/venv/bin/python /opt/mitocube/deploy.py
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=mitocube

# Security
PrivateTmp=true
ProtectSystem=full
NoNewPrivileges=true
PrivateDevices=true
CapabilityBoundingSet=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
```

### Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable to start on boot
sudo systemctl enable mitocube

# Start the service
sudo systemctl start mitocube

# Check status
sudo systemctl status mitocube
```

### View Logs

```bash
# View application logs
sudo journalctl -u mitocube -f

# View specific number of lines
sudo journalctl -u mitocube -n 100

# View since specific time
sudo journalctl -u mitocube --since "2024-01-01 00:00:00"
```

---

## Step 8: Configure Firewall

### UFW (Ubuntu)

```bash
# Enable UFW
sudo ufw enable

# Allow necessary ports
sudo ufw allow 22/tcp       # SSH
sudo ufw allow 80/tcp       # HTTP (redirects to HTTPS)
sudo ufw allow 443/tcp      # HTTPS
sudo ufw allow 7687/tcp     # Neo4j Bolt
sudo ufw allow 7474/tcp     # Neo4j HTTP (optional)
sudo ufw allow 27017/tcp    # MongoDB (optional)

# Check status
sudo ufw status
```

### Firewalld (CentOS/RHEL)

```bash
# Enable firewalld
sudo systemctl enable firewalld
sudo systemctl start firewalld

# Allow necessary ports
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=7687/tcp
sudo firewall-cmd --permanent --add-port=7474/tcp
sudo firewall-cmd --permanent --add-port=27017/tcp

# Reload
sudo firewall-cmd --reload

# Check status
sudo firewall-cmd --list-ports
```

---

## Step 9: Final Configuration

### Set Trusted Proxy IPs

In your `.env` file, set the trusted proxy IPs for rate limiting:

```ini
# If using Nginx on the same server
TRUSTED_PROXY_IPS=127.0.0.1,::1

# If using a separate reverse proxy
TRUSTED_PROXY_IPS=127.0.0.1,::1,192.168.1.100
```

### Configure Rate Limiting

```ini
# In .env
LOGIN_RATE_LIMIT_MAX_ATTEMPTS=10
LOGIN_RATE_LIMIT_WINDOW_MINUTES=10
MFA_MAX_ATTEMPTS=5
MFA_LOCKOUT_MINUTES=15
```

---

## Step 10: Test Production Setup

### Test Database Connections

```bash
# Test Neo4j connection
cypher-shell -u neo4j -p your-neo4j-password "RETURN 1"

# Test MongoDB connection (if using AI features)
mongo --host localhost --port 27017 -u ai -p your-mongodb-password --eval "db.stats()"
```

### Test Application

```bash
# Check service status
sudo systemctl status mitocube

# Check logs for errors
sudo journalctl -u mitocube -n 50

# Test API health endpoint
curl http://localhost:5002/api/health

# Test through Nginx
curl https://mitocube.your-domain.com/api/health
```

### Test Frontend

Open your browser and navigate to:
```
https://mitocube.your-domain.com
```

You should see the MitoCube frontend loading.

---

## Step 11: Set Up Monitoring (Optional)

### Health Check Script

```bash
# Create health check script
sudo nano /usr/local/bin/mitocube-health-check
```

```bash
#!/bin/bash

# Check if service is running
if ! systemctl is-active --quiet mitocube; then
    echo "MitoCube service is not running"
    exit 1
fi

# Check Neo4j
if ! systemctl is-active --quiet neo4j; then
    echo "Neo4j service is not running"
    exit 1
fi

# Check MongoDB (if using AI features)
if ! systemctl is-active --quiet mongod; then
    echo "MongoDB service is not running"
    exit 1
fi

# Check Nginx
if ! systemctl is-active --quiet nginx; then
    echo "Nginx service is not running"
    exit 1
fi

# Test API health
if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:5002/api/health | grep -q "200"; then
    echo "MitoCube API health check failed"
    exit 1
fi

echo "All services are healthy"
exit 0
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/mitocube-health-check

# Test
mitocube-health-check
```

### Set Up Cron Job for Monitoring

```bash
# Edit crontab
sudo crontab -e
```

Add:

```cron
# Check health every 5 minutes
*/5 * * * * /usr/local/bin/mitocube-health-check >> /var/log/mitocube-health.log 2>&1
```

---

## Step 12: Backup Strategy

### Backup Configuration Files

```bash
# Create backup directory
sudo mkdir -p /backup/mitocube
sudo chown mitocube:mitocube /backup/mitocube
sudo chmod 700 /backup/mitocube

# Backup script
sudo nano /usr/local/bin/mitocube-backup
```

```bash
#!/bin/bash

# Date for backup
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backup/mitocube

# Create backup directory
mkdir -p $BACKUP_DIR/$DATE

# Backup .env.enc (if exists)
if [ -f /opt/mitocube/.env.enc ]; then
    cp /opt/mitocube/.env.enc $BACKUP_DIR/$DATE/
fi

# Backup encryption key (if file-based)
if [ -f /etc/mitocube/encryption_key ]; then
    cp /etc/mitocube/encryption_key $BACKUP_DIR/$DATE/
    chmod 600 $BACKUP_DIR/$DATE/encryption_key
fi

# Backup Neo4j data (optional)
# sudo systemctl stop neo4j
# sudo tar czf $BACKUP_DIR/$DATE/neo4j-data.tar.gz /var/lib/neo4j/data
# sudo systemctl start neo4j

# Backup MongoDB data (optional)
# mongodump --out $BACKUP_DIR/$DATE/mongodb

# Create tar of backups
cd $BACKUP_DIR
 tar czf mitocube-backup-$DATE.tar.gz $DATE
 rm -rf $DATE

# Keep only last 30 days of backups
find $BACKUP_DIR -name "mitocube-backup-*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/mitocube-backup-$DATE.tar.gz"
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/mitocube-backup

# Add to crontab (daily at 2am)
sudo crontab -e
```

Add:

```cron
# Daily backup at 2am
0 2 * * * /usr/local/bin/mitocube-backup
```

---

## Step 13: Security Hardening

### SSH Hardening

```bash
# Edit SSH configuration
sudo nano /etc/ssh/sshd_config
```

**Recommended settings**:

```ini
# Disable root login
PermitRootLogin no

# Disable password authentication (use SSH keys only)
PasswordAuthentication no

# Change default port (optional)
Port 2222

# Limit users who can SSH
AllowUsers your-username mitocube

# Disable empty passwords
PermitEmptyPasswords no

# Use stronger encryption
Ciphers aes256-ctr,aes256-gcm
MACs hmac-sha2-512,hmac-sha2-256
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group-exchange-sha256
```

```bash
# Restart SSH
sudo systemctl restart sshd
```

### Fail2Ban Configuration

```bash
# Install fail2ban
sudo apt install -y fail2ban

# Configure for SSH
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local
```

**Add to jail.local**:

```ini
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 1h
findtime = 10m
```

```bash
# Enable and start
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## Step 14: Update and Maintenance

### Update MitoCube

```bash
# Stop the service
sudo systemctl stop mitocube

# Pull latest changes
cd /opt/mitocube
git pull origin neo

# Update dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt
pip install --upgrade -r requirements-ai.txt

# If .env.example has changed, update your .env
# cp .env.example .env
# nano .env  # Update any new settings
# Then re-encrypt

# Restart service
sudo systemctl start mitocube
```

### Update System Packages

```bash
# Ubuntu/Debian
sudo apt update
sudo apt upgrade -y
sudo apt autoremove -y

# CentOS/RHEL
sudo yum update -y
```

### Rotate Logs

```bash
# View log size
sudo du -sh /var/log/syslog
sudo journalctl --disk-usage

# Configure log rotation
sudo nano /etc/logrotate.d/mitocube
```

```ini
/var/log/mitocube*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 mitocube mitocube
}
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status mitocube

# View logs
sudo journalctl -u mitocube -n 100

# Common issues:
# 1. Missing secrets in .env.enc
# 2. Wrong encryption key
# 3. Database not running
# 4. Port already in use
```

### Database Connection Issues

```bash
# Test Neo4j connection
cypher-shell -u neo4j -p your-password "RETURN 1"

# Test MongoDB connection
mongo --host localhost -u ai -p your-password --eval "db.stats()"

# Check if databases are running
sudo systemctl status neo4j
sudo systemctl status mongod
```

### Encryption Key Issues

```bash
# Verify key file exists
ls -la /etc/mitocube/encryption_key

# Verify key file permissions
ls -la /etc/mitocube/

# Test decryption manually
cd /opt/mitocube
python -c "from config.secrets.encryption import get_encryption_key, EnvFileEncryptor; e = EnvFileEncryptor(get_encryption_key()); e.decrypt_file('.env.enc', '.env')"
```

### Permission Issues

```bash
# Check ownership
ls -la /opt/mitocube/

# Fix ownership
sudo chown -R mitocube:mitocube /opt/mitocube

# Check permissions
ls -la /opt/mitocube/.env.enc
ls -la /etc/mitocube/encryption_key
```

### Port Already in Use

```bash
# Check what's using port 5002
sudo netstat -tulnp | grep 5002
sudo ss -tulnp | grep 5002

# Kill the process if needed
sudo kill -9 <PID>
```

---

## Checklist

Before going live, verify all items:

- [ ] Neo4j installed and running
- [ ] MongoDB installed and running (if using AI features)
- [ ] Email server configured
- [ ] `.env` file created and encrypted
- [ ] Encryption key stored securely
- [ ] Nginx configured with SSL
- [ ] Systemd service created and enabled
- [ ] Firewall configured
- [ ] SSH hardened
- [ ] Fail2Ban configured
- [ ] Backups configured
- [ ] Monitoring configured
- [ ] All services tested
- [ ] Frontend accessible via HTTPS
- [ ] API health endpoint working

---

## Next Steps

1. **Test thoroughly** - Try all features before going live
2. **Set up monitoring** - Use tools like Prometheus, Grafana
3. **Configure backups** - Regular backups of data and configuration
4. **Set up alerts** - Get notified of issues
5. **Document** - Create runbooks for your team

---

## Support

For issues with production setup:

1. **Check logs**: `sudo journalctl -u mitocube -n 100`
2. **Review this guide** for common issues
3. **Check Neo4j logs**: `sudo journalctl -u neo4j -n 100`
4. **Check MongoDB logs**: `sudo journalctl -u mongod -n 100`
5. **Check Nginx logs**: `sudo tail -n 100 /var/log/nginx/error.log`

For security issues, contact your system administrator immediately.

---

## Additional Resources

- [Secret Management Guide](SECRET_MANAGEMENT.md) - Detailed secret management
- [Neo4j Documentation](https://neo4j.com/docs/) - Neo4j configuration
- [MongoDB Documentation](https://docs.mongodb.com/) - MongoDB configuration
- [Nginx Documentation](https://nginx.org/en/docs/) - Nginx configuration
- [Systemd Documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html) - Service management

---

*Last updated: 2024-10-08*
