# Digital Ocean Deployment Guide

Complete guide for deploying the GEX Collector to Digital Ocean.

## Overview

This guide covers deploying the GEX Collector application to a Digital Ocean Droplet (VPS) using Docker Compose.

## Prerequisites

1. **Digital Ocean Account**: Sign up at https://www.digitalocean.com/
2. **Tradier API Credentials**: Get from https://developer.tradier.com/
3. **SSH Key**: Set up SSH key for secure access
4. **Domain (Optional)**: For easier access to services

## Step 1: Create a Digital Ocean Droplet

### 1.1 Create Droplet

1. Log into Digital Ocean: https://cloud.digitalocean.com/
2. Click **Create** → **Droplets**
3. Choose configuration:
   - **Image**: Ubuntu 22.04 (LTS) x64
   - **Plan**:
     - Basic: $12/month (2 GB RAM, 1 vCPU, 50 GB SSD) - Minimum
     - Basic: $24/month (4 GB RAM, 2 vCPU, 80 GB SSD) - Recommended
   - **Datacenter**: Choose closest to you (e.g., New York for EST trading hours)
   - **Authentication**: SSH Key (recommended) or Password
   - **Hostname**: `gex-collector` or similar

4. Click **Create Droplet**
5. Wait for droplet to be created (~60 seconds)
6. Copy the droplet's IP address

### 1.2 Connect to Droplet

```bash
ssh root@YOUR_DROPLET_IP
```

## Step 2: Run Automated Setup Script

### 2.1 Download and Run Setup Script

```bash
# Update system first
apt-get update && apt-get upgrade -y

# Create deployment directory
mkdir -p /opt/gexter
cd /opt/gexter

# Download the setup script from your repo
# Option A: If you have the script in your repo
git clone https://github.com/johnsondatascience/gexter.git /opt/gexter
chmod +x /opt/gexter/deploy_to_digitalocean.sh
./deploy_to_digitalocean.sh

# Option B: Manual setup (see Manual Setup section below)
```

The script will automatically:
- ✅ Install Docker and Docker Compose
- ✅ Install system dependencies
- ✅ Clone your repository
- ✅ Create environment configuration template
- ✅ Set up systemd service for auto-start
- ✅ Configure firewall
- ✅ Set up log rotation
- ✅ Create backup script

## Step 3: Configure Environment Variables

### 3.1 Edit Environment File

```bash
cd /opt/gexter
nano .env
```

Update the following required values:

```bash
# Required: Your Tradier API credentials
TRADIER_API_KEY=your_actual_api_key_here
TRADIER_ACCOUNT_ID=your_actual_account_id_here

# Required: Strong database password
POSTGRES_PASSWORD=YourSecurePasswordHere123!

# Optional: pgAdmin access (comment out if not needed)
PGADMIN_EMAIL=your_email@example.com
PGADMIN_PASSWORD=AnotherSecurePassword456!
```

**Save and exit**: Press `Ctrl+X`, then `Y`, then `Enter`

### 3.2 Secure the Environment File

```bash
chmod 600 /opt/gexter/.env
```

## Step 4: Start the Application

### 4.1 Build and Start Services

```bash
cd /opt/gexter
docker-compose up -d
```

### 4.2 Verify Services are Running

```bash
docker-compose ps
```

Expected output:
```
NAME            STATUS    PORTS
gex_postgres    healthy   0.0.0.0:5432->5432/tcp
gex_pgadmin     running   0.0.0.0:5050->80/tcp
gex_collector   running
```

### 4.3 Check Logs

```bash
# View all logs
docker-compose logs -f

# View collector logs only
docker-compose logs -f gex_collector

# View last 100 lines
docker-compose logs --tail=100 gex_collector
```

## Step 5: Enable Auto-Start on Reboot

```bash
sudo systemctl enable gex-collector.service
sudo systemctl start gex-collector.service
sudo systemctl status gex-collector.service
```

## Step 6: Access Your Services

### 6.1 pgAdmin (Database Management)

1. Open browser: `http://YOUR_DROPLET_IP:5050`
2. Login with credentials from `.env`:
   - Email: `PGADMIN_EMAIL`
   - Password: `PGADMIN_PASSWORD`

3. Add server connection:
   - **Host**: `postgres` (internal Docker network)
   - **Port**: `5432`
   - **Database**: `gexdb`
   - **Username**: `gexuser`
   - **Password**: `POSTGRES_PASSWORD` from `.env`

### 6.2 PostgreSQL Direct Access

From your local machine:
```bash
psql -h YOUR_DROPLET_IP -p 5432 -U gexuser -d gexdb
```

## Security Considerations

### 7.1 Firewall Configuration

The setup script configures UFW (Uncomplicated Firewall):

```bash
# View current rules
sudo ufw status

# If you DON'T need external database access, block PostgreSQL:
sudo ufw delete allow 5432/tcp

# If you DON'T need external pgAdmin access:
sudo ufw delete allow 5050/tcp

# Only allow from specific IP:
sudo ufw allow from YOUR_IP_ADDRESS to any port 5432
```

### 7.2 SSH Security

```bash
# Disable password authentication (SSH key only)
sudo nano /etc/ssh/sshd_config

# Set these values:
PasswordAuthentication no
PermitRootLogin no

# Restart SSH
sudo systemctl restart sshd
```

### 7.3 Automatic Security Updates

```bash
# Install unattended-upgrades
sudo apt-get install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

## Monitoring and Maintenance

### 8.1 View Application Logs

```bash
# Real-time logs
docker-compose logs -f gex_collector

# Logs in container
docker exec gex_collector tail -f /app/logs/scheduler.log

# System logs
journalctl -u gex-collector.service -f
```

### 8.2 Database Backups

Automatic daily backups are configured via cron:

```bash
# Manual backup
/usr/local/bin/backup-gex.sh

# View backup files
ls -lh /opt/gexter/backups/

# Restore from backup
gunzip < /opt/gexter/backups/gexdb_20250128_020000.sql.gz | \
  docker exec -i gex_postgres psql -U gexuser -d gexdb
```

### 8.3 Update Application

```bash
cd /opt/gexter

# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Verify
docker-compose logs -f gex_collector
```

### 8.4 Monitor Resource Usage

```bash
# View resource usage
docker stats

# System resources
htop

# Disk usage
df -h
du -sh /opt/gexter/
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is healthy
docker-compose ps postgres

# Test connection from collector
docker exec gex_collector python -c "from src.database import get_postgres_connection; print(get_postgres_connection())"

# Check PostgreSQL logs
docker-compose logs postgres
```

### Collector Not Running

```bash
# Check environment variables
docker exec gex_collector env | grep TRADIER

# Check if in trading hours
docker exec gex_collector python -c "from src.config import Config; from src.gex_collector import is_trading_day, is_trading_hours; print(f'Trading day: {is_trading_day()}, Trading hours: {is_trading_hours()}')"

# Force run outside trading hours
docker exec gex_collector python -m src.gex_collector --force
```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean up Docker
docker system prune -a --volumes

# Clean up old logs
find /opt/gextr/logs -name "*.log" -mtime +30 -delete
```

## Cost Optimization

### Droplet Sizing Recommendations

| Droplet Size | RAM | vCPU | Storage | Monthly Cost | Recommended For |
|--------------|-----|------|---------|--------------|-----------------|
| Basic | 2 GB | 1 | 50 GB | $12 | Testing/Light use |
| Basic | 4 GB | 2 | 80 GB | $24 | Production (Recommended) |
| Basic | 8 GB | 4 | 160 GB | $48 | Heavy data collection |

### Managed Database Alternative

Consider using Digital Ocean Managed PostgreSQL if:
- You want automatic backups and updates
- You need high availability
- You prefer not to manage database infrastructure

Cost: Starting at $15/month (more expensive but managed)

## Advanced: Custom Domain Setup

### 9.1 Add Domain to Digital Ocean

1. Go to **Networking** → **Domains**
2. Add your domain
3. Update nameservers at your registrar to Digital Ocean's:
   - `ns1.digitalocean.com`
   - `ns2.digitalocean.com`
   - `ns3.digitalocean.com`

### 9.2 Create DNS Records

- **A Record**: `@` → `YOUR_DROPLET_IP`
- **A Record**: `pgadmin` → `YOUR_DROPLET_IP`

### 9.3 Install SSL with Let's Encrypt (Optional)

```bash
# Install Nginx and Certbot
sudo apt-get install nginx certbot python3-certbot-nginx

# Configure Nginx as reverse proxy for pgAdmin
sudo nano /etc/nginx/sites-available/pgadmin

# Get SSL certificate
sudo certbot --nginx -d pgadmin.yourdomain.com
```

## Manual Setup (Alternative to Script)

If the automated script fails, follow these manual steps:

### Install Docker

```bash
# Update packages
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and back in for group changes to take effect
exit
```

### Clone Repository and Configure

```bash
# Create directory
sudo mkdir -p /opt/gexter
sudo chown $USER:$USER /opt/gexter

# Clone repo
cd /opt/gexter
git clone https://github.com/johnsondatascience/gexter.git .

# Copy and edit environment file
cp .env.production.example .env
nano .env

# Start services
docker-compose up -d
```

## Support and Resources

- **Digital Ocean Documentation**: https://docs.digitalocean.com/
- **Docker Documentation**: https://docs.docker.com/
- **Tradier API Docs**: https://developer.tradier.com/documentation

## Next Steps

After deployment:
1. ✅ Set up monitoring alerts
2. ✅ Configure automated backups
3. ✅ Test data collection during market hours
4. ✅ Set up notifications (Slack/Email)
5. ✅ Document your custom configurations
6. ✅ Create a disaster recovery plan

---

*Last updated: 2025-01-28*
