#!/bin/bash
################################################################################
# DigitalOcean VM Setup Script
#
# Run this script on your NEW DigitalOcean droplet to set up the environment
# for running the GEX collector.
#
# Prerequisites:
# - Fresh Ubuntu 22.04 droplet (2GB RAM recommended, $24/mo)
# - SSH access as root or sudo user
#
# Usage:
#   ssh root@your-droplet-ip
#   curl -O https://raw.githubusercontent.com/your-repo/gextr/main/scripts/migration/01_setup_vm.sh
#   chmod +x 01_setup_vm.sh
#   ./01_setup_vm.sh
################################################################################

set -e  # Exit on any error

echo "=================================="
echo "GEX COLLECTOR - VM SETUP"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root or with sudo"
   exit 1
fi

echo "1. Updating system packages..."
apt-get update
apt-get upgrade -y

echo ""
echo "2. Installing required packages..."
apt-get install -y \
    curl \
    git \
    ca-certificates \
    gnupg \
    lsb-release \
    python3 \
    python3-pip \
    postgresql-client \
    awscli \
    ufw

echo ""
echo "3. Installing Docker..."
# Remove old versions
apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Add Docker's official GPG key
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start Docker service
systemctl start docker
systemctl enable docker

echo ""
echo "4. Creating gex user..."
# Create dedicated user for running the GEX collector
if id "gex" &>/dev/null; then
    echo "   User 'gex' already exists"
else
    useradd -m -s /bin/bash gex
    usermod -aG docker gex
    echo "   User 'gex' created"
fi

echo ""
echo "5. Setting up directories..."
sudo -u gex mkdir -p /home/gex/gextr
sudo -u gex mkdir -p /home/gex/backups
sudo -u gex mkdir -p /home/gex/logs

echo ""
echo "6. Configuring firewall..."
# Enable UFW
ufw --force enable

# Allow SSH (IMPORTANT!)
ufw allow 22/tcp comment 'SSH'

# Allow health check endpoint
ufw allow 8080/tcp comment 'Health Check'

# PostgreSQL should NOT be exposed publicly (only localhost)
# pgAdmin should NOT be exposed publicly (use SSH tunnel)

ufw status

echo ""
echo "7. Configuring Docker log rotation..."
cat > /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "5"
  }
}
EOF

systemctl restart docker

echo ""
echo "8. Setting up swap space (recommended for 2GB RAM)..."
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "   Swap enabled (2GB)"
else
    echo "   Swap already exists"
fi

echo ""
echo "9. Installing system monitoring tools..."
apt-get install -y htop iotop nethogs

echo ""
echo "10. Setting timezone to America/New_York..."
timedatectl set-timezone America/New_York

echo ""
echo -e "${GREEN}=================================="
echo "VM SETUP COMPLETE!"
echo -e "==================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Exit this SSH session and log back in to apply group changes"
echo "  2. Run the migration script from your LAPTOP to transfer files"
echo "  3. Start the GEX collector on this VM"
echo ""
echo "To access this VM:"
echo "  ssh gex@$(curl -s ifconfig.me)"
echo ""
echo "Security recommendations:"
echo "  - Set up SSH key authentication (disable password auth)"
echo "  - Use SSH tunnel for pgAdmin: ssh -L 5050:localhost:5050 gex@your-vm-ip"
echo "  - Never expose PostgreSQL port 5432 to the internet"
echo ""
