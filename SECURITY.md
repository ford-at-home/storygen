# Security Documentation
## Richmond Storyline Generator - Security Implementation

### 🔐 Security Overview

The Richmond Storyline Generator has been comprehensively secured with enterprise-grade security measures. This document outlines all security features, deployment procedures, and maintenance requirements.

### 🛡️ Security Features Implemented

#### 1. Authentication & Authorization
- **JWT-based Authentication**: Secure token-based authentication with access and refresh tokens
- **User Registration & Login**: Secure user management with encrypted password storage
- **Session Management**: Redis-based secure session storage with encryption
- **Account Lockout**: Automatic account lockout after failed login attempts
- **Token Blacklisting**: Ability to revoke tokens immediately

#### 2. Secrets Management
- **AWS Secrets Manager Integration**: Secure storage of API keys and credentials
- **Local Encryption Fallback**: Encrypted local storage when AWS is unavailable
- **Environment Variable Security**: Secure handling of sensitive configuration
- **Key Rotation**: Support for regular credential rotation

#### 3. Input Validation & Sanitization
- **Comprehensive Input Validation**: All user inputs are validated and sanitized
- **SQL Injection Prevention**: Pattern-based SQL injection detection and blocking
- **XSS Protection**: HTML entity encoding and content sanitization
- **File Upload Security**: Strict file type validation and content scanning
- **Request Size Limiting**: Protection against oversized requests

#### 4. Rate Limiting & DDoS Protection
- **Redis-based Rate Limiting**: Scalable rate limiting with multiple time windows
- **IP-based Blocking**: Automatic blocking of suspicious IPs
- **Endpoint-specific Limits**: Different limits for different API endpoints
- **Attack Detection**: Automatic detection and mitigation of potential attacks

#### 5. File Upload Security
- **Virus Scanning**: ClamAV integration for malware detection
- **File Type Validation**: Strict whitelist-based file type checking
- **Content Validation**: Deep content inspection for malicious payloads
- **Quarantine System**: Automatic quarantine of suspicious files
- **Secure Storage**: Encrypted file storage with access controls

#### 6. Security Headers & HTTPS
- **Comprehensive Security Headers**: CSP, HSTS, X-Frame-Options, etc.
- **HTTPS Enforcement**: Automatic HTTPS redirection in production
- **CORS Configuration**: Secure cross-origin resource sharing
- **Cookie Security**: Secure cookie flags and SameSite protection

### 🚀 Deployment Guide

#### Prerequisites
1. **Redis Server**: Required for session storage and rate limiting
2. **ClamAV**: Required for virus scanning (optional but recommended)
3. **AWS Account**: Required for Secrets Manager and Bedrock
4. **SSL Certificate**: Required for HTTPS in production

#### Step 1: Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install Redis
# Ubuntu/Debian: sudo apt-get install redis-server
# MacOS: brew install redis
# Docker: docker run -d -p 6379:6379 redis:latest

# Install ClamAV (optional)
# Ubuntu/Debian: sudo apt-get install clamav clamav-daemon
# MacOS: brew install clamav
# Update virus definitions: sudo freshclam
```

#### Step 2: Configuration
```bash
# Generate secure configuration template
python secure_config.py

# Create environment file
cp .env.example .env

# Generate secure keys
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('SESSION_ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('LOCAL_ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
```

#### Step 3: AWS Secrets Manager Setup
```bash
# Create secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name "storygen-api-keys" \
  --description "API keys for Richmond Storyline Generator" \
  --secret-string '{
    "pinecone_api_key": "your_pinecone_key",
    "openai_api_key": "your_openai_key",
    "aws_access_key_id": "your_aws_key",
    "aws_secret_access_key": "your_aws_secret"
  }'

aws secretsmanager create-secret \
  --name "storygen-jwt" \
  --description "JWT configuration" \
  --secret-string '{
    "secret_key": "your_jwt_secret_key"
  }'
```

#### Step 4: Production Deployment
```bash
# Set production environment
export FLASK_ENV=production
export SECURITY_ENABLED=true
export FORCE_HTTPS=true

# Run with secure application
python secure_app.py
```

### 🔧 Configuration Reference

#### Required Environment Variables
```bash
# Security
JWT_SECRET_KEY=your_jwt_secret_key
ENCRYPTION_KEY=your_encryption_key
SESSION_ENCRYPTION_KEY=your_session_encryption_key
LOCAL_ENCRYPTION_KEY=your_local_encryption_key

# API Keys (or use AWS Secrets Manager)
PINECONE_API_KEY=your_pinecone_key
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
OPENAI_API_KEY=your_openai_key

# Redis
REDIS_URL=redis://localhost:6379

# Application
FLASK_ENV=production
SECURITY_ENABLED=true
FORCE_HTTPS=true
```

#### Optional Configuration
```bash
# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE=redis

# File Upload
MAX_FILE_SIZE=26214400
ENABLE_VIRUS_SCAN=true
UPLOAD_DIRECTORY=./uploads
QUARANTINE_DIRECTORY=./quarantine

# CORS
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Session
SESSION_TIMEOUT_HOURS=24
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
```

### 📊 Security Monitoring

#### Health Checks
```bash
# Application health
curl https://your-domain.com/health

# Security status
curl https://your-domain.com/security-status
```

#### Log Monitoring
```bash
# Application logs
tail -f logs/storygen.log

# Security events
grep "SECURITY\|ATTACK\|BLOCKED" logs/storygen.log

# Failed authentication attempts
grep "Authentication failed" logs/storygen.log
```

#### Redis Monitoring
```bash
# Connect to Redis
redis-cli

# Check session storage
redis-cli -n 1 keys "session:*"

# Check rate limiting
redis-cli -n 2 keys "rate_limit:*"

# Check blocked IPs
redis-cli keys "blocked_ip:*"
```

### 🛠️ Maintenance Procedures

#### Daily Tasks
1. **Monitor Security Logs**: Check for suspicious activity
2. **Review Rate Limiting**: Analyze blocked requests
3. **Check File Uploads**: Review quarantined files
4. **Verify System Health**: Ensure all services are running

#### Weekly Tasks
1. **Clean Up Old Sessions**: Remove expired sessions
2. **Update Virus Definitions**: Refresh ClamAV database
3. **Review Security Metrics**: Analyze attack patterns
4. **Check Disk Space**: Monitor upload directory size

#### Monthly Tasks
1. **Rotate Secrets**: Update API keys and JWT secrets
2. **Security Audit**: Review access logs and permissions
3. **Update Dependencies**: Apply security patches
4. **Backup Configuration**: Backup secure configuration

### 🚨 Security Incident Response

#### Immediate Actions
1. **Identify the Threat**: Analyze logs and metrics
2. **Block Malicious IPs**: Use rate limiter to block attackers
3. **Revoke Compromised Tokens**: Blacklist affected JWT tokens
4. **Isolate Affected Systems**: Quarantine compromised files

#### Investigation Steps
1. **Collect Evidence**: Gather logs and system information
2. **Assess Impact**: Determine extent of compromise
3. **Identify Root Cause**: Analyze attack vectors
4. **Document Findings**: Create incident report

#### Recovery Actions
1. **Patch Vulnerabilities**: Apply security fixes
2. **Restore Services**: Bring systems back online
3. **Monitor for Reoccurrence**: Enhanced monitoring
4. **Update Security Measures**: Improve defenses

### 📋 Security Checklist

#### Pre-Deployment
- [ ] All secrets stored securely (AWS Secrets Manager)
- [ ] Strong cryptographic keys generated
- [ ] HTTPS certificate configured
- [ ] Rate limiting enabled
- [ ] Input validation implemented
- [ ] File upload security configured
- [ ] Security headers enabled
- [ ] Virus scanning operational
- [ ] Logging configured
- [ ] Monitoring setup

#### Post-Deployment
- [ ] Security status endpoint functional
- [ ] Rate limiting working correctly
- [ ] File upload restrictions enforced
- [ ] Authentication system operational
- [ ] Session management secure
- [ ] Security headers present
- [ ] HTTPS enforcement active
- [ ] Monitoring alerts configured
- [ ] Backup procedures tested

### 🔗 Security Resources

#### Tools Used
- **Flask-Talisman**: Security headers
- **Flask-JWT-Extended**: JWT authentication
- **Flask-Limiter**: Rate limiting
- **ClamAV**: Virus scanning
- **Redis**: Session storage and rate limiting
- **AWS Secrets Manager**: Secure credential storage
- **Cryptography**: Encryption and key management

#### Security Standards
- **OWASP Top 10**: Web application security risks
- **NIST Cybersecurity Framework**: Security guidelines
- **ISO 27001**: Information security management
- **SOC 2**: Security, availability, and confidentiality

### 📞 Support & Contact

For security issues or questions:
- **Security Team**: security@yourcompany.com
- **Emergency**: security-emergency@yourcompany.com
- **Documentation**: https://docs.yourcompany.com/security

### 📝 Change Log

#### Version 2.0.0 - Security Release
- Implemented comprehensive authentication system
- Added AWS Secrets Manager integration
- Deployed Redis-based session management
- Enhanced input validation and sanitization
- Added file upload security with virus scanning
- Implemented rate limiting and DDoS protection
- Added comprehensive security headers
- Configured HTTPS enforcement
- Added security monitoring and logging

---

**⚠️ IMPORTANT**: This security implementation must be reviewed and tested thoroughly before production deployment. Regular security audits and penetration testing are recommended.