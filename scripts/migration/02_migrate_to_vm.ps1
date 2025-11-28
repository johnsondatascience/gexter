################################################################################
# Migration Script - Run from YOUR WINDOWS LAPTOP
#
# PowerShell version for Windows users
#
# This script transfers your GEX collector project to the DigitalOcean VM
# and migrates the PostgreSQL database.
#
# Prerequisites:
# - VM setup script (01_setup_vm.sh) has been run on the droplet
# - You have SSH access to the VM (OpenSSH client installed on Windows)
# - Docker Desktop is running locally with your data
#
# Usage:
#   .\02_migrate_to_vm.ps1 -VMIp "164.92.123.45"
#
################################################################################

param(
    [Parameter(Mandatory=$true)]
    [string]$VMIp
)

$ErrorActionPreference = "Stop"

$VMUser = "gex"
$VMHost = "$VMUser@$VMIp"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "GEX COLLECTOR - MIGRATION TO VM" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Target VM: $VMHost"
Write-Host ""

# Check if SSH is available
try {
    $null = Get-Command ssh -ErrorAction Stop
} catch {
    Write-Host "ERROR: SSH client not found" -ForegroundColor Red
    Write-Host "Please install OpenSSH client:"
    Write-Host "  Settings > Apps > Optional Features > Add a feature > OpenSSH Client"
    exit 1
}

# Test SSH connection
Write-Host "1. Testing SSH connection..." -ForegroundColor Yellow
try {
    $testResult = ssh -o ConnectTimeout=5 -o BatchMode=yes $VMHost "echo Connected" 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Connection failed"
    }
    Write-Host "   Connected successfully" -ForegroundColor Green
} catch {
    Write-Host "   Cannot connect to $VMHost" -ForegroundColor Red
    Write-Host "   Please ensure:"
    Write-Host "     - The VM IP is correct"
    Write-Host "     - You have SSH access (try: ssh $VMHost)"
    Write-Host "     - The setup script has been run on the VM"
    exit 1
}

# Get project directory
Write-Host ""
Write-Host "2. Creating project archive..." -ForegroundColor Yellow
$ProjectDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Write-Host "   Project directory: $ProjectDir"

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ArchiveName = "gextr_migration_$Timestamp.tar.gz"
$TempArchive = "$env:TEMP\$ArchiveName"

# Check if tar is available (Windows 10 1803+ has built-in tar)
try {
    $null = Get-Command tar -ErrorAction Stop

    # Create archive excluding unnecessary files
    Write-Host "   Creating $ArchiveName..."
    Push-Location $ProjectDir

    tar -czf $TempArchive `
        --exclude='data' `
        --exclude='logs' `
        --exclude='*.pyc' `
        --exclude='__pycache__' `
        --exclude='.git' `
        --exclude='*.log' `
        --exclude='backups' `
        --exclude='venv' `
        --exclude='.env.backup' `
        .

    Pop-Location

    $ArchiveSize = (Get-Item $TempArchive).Length / 1MB
    Write-Host "   Archive created: $([math]::Round($ArchiveSize, 2)) MB" -ForegroundColor Green
} catch {
    Write-Host "   ERROR: tar command not found" -ForegroundColor Red
    Write-Host "   Please install tar or use WSL to run the bash version"
    exit 1
}

# Transfer project files
Write-Host ""
Write-Host "3. Transferring project files to VM..." -ForegroundColor Yellow
scp $TempArchive "${VMHost}:/home/gex/"
Write-Host "   Transfer complete" -ForegroundColor Green

# Extract on VM
Write-Host ""
Write-Host "4. Extracting files on VM..." -ForegroundColor Yellow
ssh $VMHost "cd /home/gex/gextr && tar -xzf /home/gex/$ArchiveName"
ssh $VMHost "rm /home/gex/$ArchiveName"
Write-Host "   Files extracted" -ForegroundColor Green

# Check for database
Write-Host ""
Write-Host "5. Checking if database export is needed..." -ForegroundColor Yellow

$DockerContainers = docker ps --format "{{.Names}}" 2>$null
$HasPostgres = $DockerContainers -match "postgres"

$ImportDB = $false
if ($HasPostgres) {
    Write-Host "   PostgreSQL container found locally"
    Write-Host "   Creating database dump..."

    $DbDumpName = "gexdb_dump_$Timestamp.sql"
    $TempDump = "$env:TEMP\$DbDumpName"

    # Export database
    docker exec gextr-postgres-1 pg_dump -U gexuser gexdb | Out-File -FilePath $TempDump -Encoding utf8

    $DumpSize = (Get-Item $TempDump).Length / 1MB
    Write-Host "   Database dump created: $([math]::Round($DumpSize, 2)) MB" -ForegroundColor Green

    # Compress using tar
    Write-Host "   Compressing..."
    Push-Location $env:TEMP
    tar -czf "$DbDumpName.tar.gz" $DbDumpName
    Pop-Location

    $CompressedSize = (Get-Item "$env:TEMP\$DbDumpName.tar.gz").Length / 1MB
    Write-Host "   Compressed: $([math]::Round($CompressedSize, 2)) MB" -ForegroundColor Green

    # Transfer database
    Write-Host ""
    Write-Host "6. Transferring database to VM..." -ForegroundColor Yellow
    scp "$env:TEMP\$DbDumpName.tar.gz" "${VMHost}:/home/gex/backups/"
    Write-Host "   Database transferred" -ForegroundColor Green

    $ImportDB = $true

    # Cleanup local dump
    Remove-Item $TempDump -Force
    Remove-Item "$env:TEMP\$DbDumpName.tar.gz" -Force
} else {
    Write-Host "   No local PostgreSQL container found" -ForegroundColor Yellow
    Write-Host "   Skipping database migration (will start fresh on VM)"
    Write-Host ""
    Write-Host "6. Skipping database transfer" -ForegroundColor Yellow
}

# Setup environment on VM
Write-Host ""
Write-Host "7. Setting up environment on VM..." -ForegroundColor Yellow
ssh $VMHost @"
cd /home/gex/gextr
mkdir -p data logs output
chmod +x scripts/*.py scripts/migration/*.sh 2>/dev/null || true
if [ ! -f .env ]; then
    echo '   WARNING: .env file not found!'
else
    echo '   .env file found'
fi
echo '   Environment setup complete'
"@

# Import database if needed
if ($ImportDB) {
    Write-Host ""
    Write-Host "8. Importing database on VM..." -ForegroundColor Yellow
    Write-Host "   This may take several minutes..."

    ssh $VMHost @"
cd /home/gex/gextr
docker compose up -d postgres
echo '   Waiting for PostgreSQL to start...'
sleep 10
DB_DUMP=\`$(ls -t /home/gex/backups/gexdb_dump_*.sql.tar.gz | head -1)\`
if [ -z "\$DB_DUMP" ]; then
    echo '   ERROR: Database dump not found'
    exit 1
fi
echo "   Importing from: \$DB_DUMP"
tar -xzOf "\$DB_DUMP" | docker exec -i gextr-postgres-1 psql -U gexuser -d gexdb
echo '   Database import complete'
RECORD_COUNT=\`$(docker exec gextr-postgres-1 psql -U gexuser -d gexdb -t -c 'SELECT COUNT(*) FROM gex_table')\`
echo "   Records in database: \$(echo \$RECORD_COUNT | xargs)"
"@

    Write-Host "   Database imported successfully" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "8. No database to import (starting fresh)" -ForegroundColor Yellow
}

# Cleanup
Write-Host ""
Write-Host "9. Cleaning up local temporary files..." -ForegroundColor Yellow
Remove-Item $TempArchive -Force
Write-Host "   Cleanup complete" -ForegroundColor Green

# Success message
Write-Host ""
Write-Host "==================================" -ForegroundColor Green
Write-Host "MIGRATION COMPLETE!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your GEX collector is now on the VM at: $VMIp"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. SSH into the VM:"
Write-Host "     ssh $VMHost"
Write-Host ""
Write-Host "  2. Verify the .env file:"
Write-Host "     cd /home/gex/gextr"
Write-Host "     cat .env"
Write-Host ""
Write-Host "  3. Start the GEX collector:"
Write-Host "     docker compose up -d"
Write-Host ""
Write-Host "  4. Check logs:"
Write-Host "     docker compose logs -f scheduler"
Write-Host ""
Write-Host "  5. Access pgAdmin via SSH tunnel:"
Write-Host "     ssh -L 5050:localhost:5050 $VMHost"
Write-Host "     Then open: http://localhost:5050"
Write-Host ""
Write-Host "  6. Verify data collection:"
Write-Host "     ssh $VMHost"
Write-Host "     docker exec -it gextr-postgres-1 psql -U gexuser -d gexdb"
Write-Host "     SELECT COUNT(*), MAX(\`"greeks.updated_at\`") FROM gex_table;"
Write-Host ""
Write-Host "Health check: http://${VMIp}:8080/health" -ForegroundColor Yellow
Write-Host ""
