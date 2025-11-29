#!/bin/bash
# GEX Collector - Digital Ocean Droplet Deployment Script
# This script sets up the GEX collector on a fresh Ubuntu 22.04 droplet

set -e  # Exit on error

echo "======================================"
echo "GEX Collector - Digital Ocean Setup"
echo "======================================"

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add current user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose (standalone)
echo "📦 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
echo "✅ Verifying installations..."
docker --version
docker-compose --version

# Install Git (if not already installed)
echo "📥 Installing Git..."
sudo apt-get install -y git

# Install other useful tools
echo "🛠️ Installing additional tools..."
sudo apt-get install -y \
    htop \
    vim \
    curl \
    wget \
    net-tools

# Create application directory
echo "📁 Setting up application directory..."
sudo mkdir -p /opt/gexter
sudo chown $USER:$USER /opt/gexter

# Clone repository (you'll need to provide the repo URL)
echo "📥 Cloning repository..."
read -p "Enter your GitHub repository URL (https://github.com/johnsondatascience/gexter.git): " REPO_URL
REPO_URL=${REPO_URL:-https://github.com/johnsondatascience/gexter.git}

cd /opt/gexter
git clone $REPO_URL .

# Create .env file from template
echo "⚙️ Setting up environment variables..."
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << 'EOF'
# Tradier API Configuration
TRADIER_API_KEY=your_api_key_here
TRADIER_ACCOUNT_ID=your_account_id_here

# PostgreSQL Configuration
POSTGRES_PASSWORD=change_this_secure_password

# pgAdmin Credentials (optional - comment out if not using)
PGADMIN_EMAIL=admin@example.com
PGADMIN_PASSWORD=change_this_admin_password

# Collection Settings
COLLECTION_INTERVAL_MINUTES=5
TRADING_HOURS_START=09:30
TRADING_HOURS_END=16:00
TIMEZONE=America/New_York
LOG_LEVEL=INFO

# Database Connection Pool
POSTGRES_POOL_SIZE=5
POSTGRES_MAX_OVERFLOW=10
EOF
    echo "⚠️  IMPORTANT: Edit /opt/gexter/.env with your actual credentials!"
    echo "    Run: nano /opt/gexter/.env"
else
    echo ".env file already exists, skipping..."
fi

# Set up systemd service for automatic startup
echo "🚀 Setting up systemd service..."
sudo tee /etc/systemd/system/gex-collector.service > /dev/null << EOF
[Unit]
Description=GEX Collector Service
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/gexter
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable gex-collector.service

# Set up UFW firewall
echo "🔒 Configuring firewall..."
sudo ufw --force enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 5432/tcp  # PostgreSQL (only if you need external access)
sudo ufw allow 5050/tcp  # pgAdmin (only if you need external access)
sudo ufw status

# Set up log rotation
echo "📝 Setting up log rotation..."
sudo tee /etc/logrotate.d/gex-collector > /dev/null << EOF
/opt/gexter/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 $USER $USER
    sharedscripts
    postrotate
        docker-compose -f /opt/gexter/docker-compose.yml restart gex_collector > /dev/null 2>&1 || true
    endscript
}
EOF

# Create backup script
echo "💾 Creating backup script..."
sudo tee /usr/local/bin/backup-gex.sh > /dev/null << 'EOF'
#!/bin/bash
# Backup script for GEX database

BACKUP_DIR="/opt/gexter/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="gexdb_${TIMESTAMP}.sql.gz"

mkdir -p $BACKUP_DIR

# Backup database
docker exec gex_postgres pg_dump -U gexuser gexdb | gzip > $BACKUP_DIR/$BACKUP_FILE

# Keep only last 30 days of backups
find $BACKUP_DIR -name "gexdb_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
EOF

sudo chmod +x /usr/local/bin/backup-gex.sh

# Set up daily backup cron job
echo "⏰ Setting up daily backup..."
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-gex.sh >> /var/log/gex-backup.log 2>&1") | crontab -

echo ""
echo "======================================"
echo "✅ Digital Ocean Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit environment variables:"
echo "   nano /opt/gexter/.env"
echo ""
echo "2. Start the application:"
echo "   cd /opt/gexter"
echo "   docker-compose up -d"
echo ""
echo "3. Check status:"
echo "   docker-compose ps"
echo "   docker-compose logs -f gex_collector"
echo ""
echo "4. Enable auto-start on reboot:"
echo "   sudo systemctl start gex-collector.service"
echo ""
echo "5. Access services:"
echo "   - pgAdmin: http://$(curl -s ifconfig.me):5050"
echo "   - PostgreSQL: $(curl -s ifconfig.me):5432"
echo ""
echo "6. Set up monitoring (recommended):"
echo "   - Install monitoring tools"
echo "   - Set up alerts for service failures"
echo ""
echo "⚠️  Security recommendations:"
echo "   - Update .env with strong passwords"
echo "   - Restrict firewall rules if not needing external access"
echo "   - Set up SSH key authentication"
echo "   - Consider using a VPN for database access"
echo ""
echo "📊 Useful commands:"
echo "   docker-compose logs -f              # View logs"
echo "   docker-compose restart              # Restart services"
echo "   docker-compose down                 # Stop services"
echo "   /usr/local/bin/backup-gex.sh        # Manual backup"
echo ""
