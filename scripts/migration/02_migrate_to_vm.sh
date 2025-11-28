#!/bin/bash
################################################################################
# Migration Script - Run from YOUR LAPTOP (Windows/WSL)
#
# This script transfers your GEX collector project to the DigitalOcean VM
# and migrates the PostgreSQL database.
#
# Prerequisites:
# - VM setup script (01_setup_vm.sh) has been run on the droplet
# - You have SSH access to the VM
# - PostgreSQL is running locally with your data
#
# Usage:
#   ./02_migrate_to_vm.sh <vm-ip-address>
#
# Example:
#   ./02_migrate_to_vm.sh 164.92.123.45
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ $# -eq 0 ]; then
    echo -e "${RED}Error: VM IP address required${NC}"
    echo "Usage: $0 <vm-ip-address>"
    echo "Example: $0 164.92.123.45"
    exit 1
fi

VM_IP=$1
VM_USER="gex"
VM_HOST="${VM_USER}@${VM_IP}"

echo "=================================="
echo "GEX COLLECTOR - MIGRATION TO VM"
echo "=================================="
echo ""
echo "Target VM: ${VM_HOST}"
echo ""

# Check if we can connect
echo "1. Testing SSH connection..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes ${VM_HOST} echo "Connected" 2>/dev/null; then
    echo -e "${RED}Cannot connect to ${VM_HOST}${NC}"
    echo "Please ensure:"
    echo "  - The VM IP is correct"
    echo "  - You have SSH access (try: ssh ${VM_HOST})"
    echo "  - The setup script (01_setup_vm.sh) has been run on the VM"
    exit 1
fi
echo -e "${GREEN}   Connected successfully${NC}"

echo ""
echo "2. Creating project archive..."
# Get the project directory (where this script is located)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "   Project directory: ${PROJECT_DIR}"

cd "${PROJECT_DIR}"

# Create archive excluding large/unnecessary files
ARCHIVE_NAME="gextr_migration_$(date +%Y%m%d_%H%M%S).tar.gz"

echo "   Creating ${ARCHIVE_NAME}..."
tar -czf "/tmp/${ARCHIVE_NAME}" \
    --exclude='data' \
    --exclude='logs' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='*.log' \
    --exclude='backups' \
    --exclude='venv' \
    --exclude='.env.backup' \
    .

ARCHIVE_SIZE=$(du -h "/tmp/${ARCHIVE_NAME}" | cut -f1)
echo -e "${GREEN}   Archive created: ${ARCHIVE_SIZE}${NC}"

echo ""
echo "3. Transferring project files to VM..."
scp "/tmp/${ARCHIVE_NAME}" ${VM_HOST}:/home/gex/
echo -e "${GREEN}   Transfer complete${NC}"

echo ""
echo "4. Extracting files on VM..."
ssh ${VM_HOST} "cd /home/gex/gextr && tar -xzf /home/gex/${ARCHIVE_NAME}"
ssh ${VM_HOST} "rm /home/gex/${ARCHIVE_NAME}"
echo -e "${GREEN}   Files extracted${NC}"

echo ""
echo "5. Checking if database export is needed..."
if docker ps --format '{{.Names}}' | grep -q postgres; then
    echo "   PostgreSQL container found locally"
    echo "   Creating database dump..."

    # Export database
    DB_DUMP="gexdb_dump_$(date +%Y%m%d_%H%M%S).sql"
    docker exec gextr-postgres-1 pg_dump -U gexuser gexdb > "/tmp/${DB_DUMP}"

    DB_SIZE=$(du -h "/tmp/${DB_DUMP}" | cut -f1)
    echo -e "${GREEN}   Database dump created: ${DB_SIZE}${NC}"

    # Compress the dump
    gzip "/tmp/${DB_DUMP}"
    echo "   Compressing..."

    COMPRESSED_SIZE=$(du -h "/tmp/${DB_DUMP}.gz" | cut -f1)
    echo -e "${GREEN}   Compressed: ${COMPRESSED_SIZE}${NC}"

    echo ""
    echo "6. Transferring database to VM..."
    scp "/tmp/${DB_DUMP}.gz" ${VM_HOST}:/home/gex/backups/
    echo -e "${GREEN}   Database transferred${NC}"

    IMPORT_DB=true
else
    echo -e "${YELLOW}   No local PostgreSQL container found${NC}"
    echo "   Skipping database migration (will start fresh on VM)"
    IMPORT_DB=false
fi

echo ""
echo "7. Setting up environment on VM..."
ssh ${VM_HOST} << 'ENDSSH'
cd /home/gex/gextr

# Create necessary directories
mkdir -p data logs output

# Set permissions
chmod +x scripts/*.py scripts/migration/*.sh 2>/dev/null || true

# Verify .env file exists
if [ ! -f .env ]; then
    echo "   WARNING: .env file not found!"
    echo "   You'll need to create it manually"
else
    echo "   .env file found"
fi

echo "   Environment setup complete"
ENDSSH

echo ""
if [ "$IMPORT_DB" = true ]; then
    echo "8. Importing database on VM..."
    echo "   This may take several minutes..."

    ssh ${VM_HOST} << 'ENDSSH'
cd /home/gex/gextr

# Start PostgreSQL container
docker compose up -d postgres

# Wait for PostgreSQL to be ready
echo "   Waiting for PostgreSQL to start..."
sleep 10

# Find the database dump
DB_DUMP=$(ls -t /home/gex/backups/gexdb_dump_*.sql.gz | head -1)

if [ -z "$DB_DUMP" ]; then
    echo "   ERROR: Database dump not found"
    exit 1
fi

echo "   Importing from: $DB_DUMP"

# Decompress and import
gunzip -c "$DB_DUMP" | docker exec -i gextr-postgres-1 psql -U gexuser -d gexdb

echo "   Database import complete"

# Verify
RECORD_COUNT=$(docker exec gextr-postgres-1 psql -U gexuser -d gexdb -t -c "SELECT COUNT(*) FROM gex_table")
echo "   Records in database: $(echo $RECORD_COUNT | xargs)"
ENDSSH

    echo -e "${GREEN}   Database imported successfully${NC}"
else
    echo "8. No database to import (starting fresh)"
fi

echo ""
echo "9. Cleaning up local temporary files..."
rm -f "/tmp/${ARCHIVE_NAME}"
[ "$IMPORT_DB" = true ] && rm -f "/tmp/${DB_DUMP}.gz"
echo "   Cleanup complete"

echo ""
echo -e "${GREEN}=================================="
echo "MIGRATION COMPLETE!"
echo -e "==================================${NC}"
echo ""
echo "Your GEX collector is now on the VM at: ${VM_IP}"
echo ""
echo "Next steps:"
echo ""
echo "  1. SSH into the VM:"
echo "     ssh ${VM_HOST}"
echo ""
echo "  2. Verify the .env file (especially if starting fresh):"
echo "     cd /home/gex/gextr"
echo "     cat .env"
echo ""
echo "  3. Start the GEX collector:"
echo "     docker compose up -d"
echo ""
echo "  4. Check logs:"
echo "     docker compose logs -f scheduler"
echo ""
echo "  5. Access pgAdmin via SSH tunnel (from your laptop):"
echo "     ssh -L 5050:localhost:5050 ${VM_HOST}"
echo "     Then open: http://localhost:5050"
echo ""
echo "  6. Verify data collection is working:"
echo "     ssh ${VM_HOST}"
echo "     docker exec -it gextr-postgres-1 psql -U gexuser -d gexdb"
echo "     SELECT COUNT(*), MAX(\"greeks.updated_at\") FROM gex_table;"
echo ""
echo "Health check endpoint: http://${VM_IP}:8080/health"
echo ""
