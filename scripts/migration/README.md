# GEX Collector - Cloud Migration Guide

This guide will help you migrate your GEX collector from your laptop to a DigitalOcean VM for reliable 24/7 data collection.

## Overview

**Time Required**: 1-2 hours
**Cost**: $24/month (DigitalOcean 2GB droplet)
**Difficulty**: Beginner-friendly

## What You'll Need

- [ ] DigitalOcean account (or any cloud provider)
- [ ] SSH client (Windows 10+ has this built-in)
- [ ] Your laptop with the current GEX collector running
- [ ] ~30 minutes of your time

## Migration Steps

### Step 1: Create DigitalOcean Droplet

1. **Sign up for DigitalOcean** (if you don't have an account):
   - Go to https://www.digitalocean.com
   - New users often get $200 credit for 60 days

2. **Create a new Droplet**:
   - Click "Create" → "Droplets"
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic
   - **CPU options**: Regular (2 GB RAM / 1 CPU - $24/mo) ← **RECOMMENDED**
   - **Datacenter**: Choose closest to you (or New York for market hours)
   - **Authentication**: SSH Key (recommended) or Password
   - **Hostname**: `gex-collector` (or whatever you prefer)
   - Click "Create Droplet"

3. **Note your droplet's IP address** - you'll need this!
   - Example: `164.92.123.45`

4. **Test SSH connection**:
   ```bash
   ssh root@YOUR_DROPLET_IP
   ```

### Step 2: Setup the VM

1. **Copy the setup script to your VM**:
   ```bash
   # SSH into your droplet
   ssh root@YOUR_DROPLET_IP

   # Download the setup script
   curl -O https://raw.githubusercontent.com/YOUR_USERNAME/gextr/main/scripts/migration/01_setup_vm.sh

   # Or copy-paste the script content manually
   nano 01_setup_vm.sh
   # Paste the content from 01_setup_vm.sh
   # Press Ctrl+X, then Y, then Enter to save

   # Make it executable
   chmod +x 01_setup_vm.sh

   # Run it
   ./01_setup_vm.sh
   ```

2. **Wait for setup to complete** (~5 minutes)
   - Installs Docker, Docker Compose
   - Creates `gex` user
   - Configures firewall
   - Sets up swap space
   - Sets timezone to America/New_York

3. **Exit and test the new user**:
   ```bash
   exit
   ssh gex@YOUR_DROPLET_IP
   ```

### Step 3: Migrate Your Project

**Option A: Windows (PowerShell)**

1. Open PowerShell in your project directory:
   ```powershell
   cd c:\Users\johnsnmi\gextr
   .\scripts\migration\02_migrate_to_vm.ps1 -VMIp "YOUR_DROPLET_IP"
   ```

2. The script will:
   - Test SSH connection
   - Archive your project (excluding data/logs)
   - Transfer files to VM
   - Export your PostgreSQL database
   - Transfer database to VM
   - Import database on VM
   - Set up environment

**Option B: Linux/Mac/WSL (Bash)**

1. Open terminal in your project directory:
   ```bash
   cd /path/to/gextr
   ./scripts/migration/02_migrate_to_vm.sh YOUR_DROPLET_IP
   ```

### Step 4: Start the Collector on VM

1. **SSH into your VM**:
   ```bash
   ssh gex@YOUR_DROPLET_IP
   ```

2. **Navigate to project directory**:
   ```bash
   cd /home/gex/gextr
   ```

3. **Verify .env file** (especially important if you started fresh):
   ```bash
   cat .env
   ```

   Make sure these are set:
   - `TRADIER_API_KEY` - Your API key
   - `DATABASE_TYPE=postgresql`
   - `POSTGRES_*` - Database credentials

4. **Start all services**:
   ```bash
   docker compose up -d
   ```

5. **Check that containers are running**:
   ```bash
   docker compose ps
   ```

   You should see:
   - `gextr-postgres-1` - Running
   - `gextr-scheduler-1` - Running
   - `gextr-pgadmin-1` - Running (optional)

6. **Watch the logs**:
   ```bash
   docker compose logs -f scheduler
   ```

   Press `Ctrl+C` to stop watching

### Step 5: Verify Everything Works

Run the verification script:

```bash
cd /home/gex/gextr
./scripts/migration/03_verify_vm.sh
```

This checks:
- ✓ Docker is running
- ✓ Containers are healthy
- ✓ PostgreSQL has data
- ✓ Recent data collection occurred
- ✓ Disk space is adequate
- ✓ Firewall is configured
- ✓ Timezone is correct

### Step 6: Access pgAdmin (Optional)

Since PostgreSQL isn't exposed to the internet (security!), use an SSH tunnel:

**From your laptop**:
```bash
ssh -L 5050:localhost:5050 gex@YOUR_DROPLET_IP
```

Keep this terminal open, then open your browser:
```
http://localhost:5050
```

Login with credentials from your `.env` file:
- Email: `PGADMIN_EMAIL`
- Password: `PGADMIN_PASSWORD`

## Verification Checklist

After migration, verify these work:

### Database Check
```bash
ssh gex@YOUR_DROPLET_IP
docker exec -it gextr-postgres-1 psql -U gexuser -d gexdb

-- Run these queries:
SELECT COUNT(*) FROM gex_table;
SELECT COUNT(DISTINCT "greeks.updated_at") FROM gex_table;
SELECT MAX("greeks.updated_at") FROM gex_table;

\q
```

### Recent Data Collection
```bash
# Check last 3 collection timestamps
docker exec gextr-postgres-1 psql -U gexuser -d gexdb -c \
  "SELECT DISTINCT \"greeks.updated_at\", COUNT(*)
   FROM gex_table
   GROUP BY \"greeks.updated_at\"
   ORDER BY \"greeks.updated_at\" DESC
   LIMIT 3;"
```

If data collection is working, you should see new timestamps being added every 15 minutes during market hours (9:30 AM - 4:00 PM ET).

## Monitoring & Maintenance

### Check Container Status
```bash
ssh gex@YOUR_DROPLET_IP
docker compose ps
```

### View Logs
```bash
# All services
docker compose logs -f

# Just scheduler
docker compose logs -f scheduler

# Last 100 lines
docker compose logs --tail=100 scheduler
```

### Restart Services
```bash
# Restart all
docker compose restart

# Restart just scheduler
docker compose restart scheduler
```

### Stop Everything
```bash
docker compose down
```

### Start Everything
```bash
docker compose up -d
```

## Troubleshooting

### Can't SSH into VM
```bash
# Check if VM is running
ping YOUR_DROPLET_IP

# Check firewall allows SSH (on VM)
sudo ufw status

# Ensure port 22 is allowed
sudo ufw allow 22/tcp
```

### Containers Won't Start
```bash
# Check Docker service
sudo systemctl status docker

# Check logs for errors
docker compose logs

# Try rebuilding
docker compose down
docker compose up -d --build
```

### No Data Being Collected

1. **Check if it's market hours** (9:30 AM - 4:00 PM ET):
   ```bash
   date  # Should show EST/EDT time
   ```

2. **Check scheduler logs**:
   ```bash
   docker compose logs scheduler | tail -50
   ```

3. **Verify Tradier API key**:
   ```bash
   cat .env | grep TRADIER_API_KEY
   ```

4. **Test API connection manually**:
   ```bash
   docker exec -it gextr-scheduler-1 python3 -c "
   from src.api.tradier_api import TradierAPI
   from src.config import Config
   config = Config()
   api = TradierAPI(config.tradier_api_key)
   quote = api.get_current_quote('SPX')
   print(quote)
   "
   ```

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker exec gextr-postgres-1 pg_isready -U gexuser

# Check if database exists
docker exec -it gextr-postgres-1 psql -U gexuser -l

# Check table exists
docker exec -it gextr-postgres-1 psql -U gexuser -d gexdb -c "\dt"
```

### High Memory Usage
```bash
# Check memory usage
free -h

# Check which containers are using memory
docker stats --no-stream

# If needed, increase VM size to 4GB RAM ($48/mo)
```

## Cost Optimization

### Current Setup ($24/month)
- DigitalOcean 2GB droplet: $24/mo
- Bandwidth: Included (2TB)
- Backups: Not enabled (manual only)

### With Backups ($25/month)
- Add S3-compatible storage: ~$1/mo
- Automated daily backups
- 90-day retention

### When to Upgrade ($48/month)
Consider upgrading to 4GB RAM if:
- You add more features (backtesting, API server)
- You're collecting multiple tickers
- You're running analysis queries
- Memory usage consistently >80%

## Security Best Practices

### Implemented ✓
- [x] SSH key authentication
- [x] Firewall enabled (UFW)
- [x] PostgreSQL not exposed to internet
- [x] Non-root user for running services
- [x] Docker log rotation

### Recommended Next Steps
- [ ] Disable password SSH authentication
- [ ] Set up automatic security updates
- [ ] Enable DigitalOcean backups ($4.80/mo)
- [ ] Set up monitoring/alerts (Phase 2)
- [ ] Rotate API keys periodically

## Next Steps

After successful migration:

1. **Monitor for 1 week** to ensure stable collection
2. **Set up backups** (see Phase 2 guide)
3. **Configure alerts** for failures
4. **Stop your laptop collector** once VM is stable

## Phase 2: Production Hardening

Once you've verified the VM is collecting data reliably for a week, proceed to Phase 2:

- Automated PostgreSQL backups to S3
- Health monitoring with UptimeRobot
- Alert notifications via email/SMS
- Log aggregation with Grafana
- Database read replicas for analytics

See `PHASE2_PRODUCTION.md` for details (coming soon).

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Run the verification script: `./scripts/migration/03_verify_vm.sh`
3. Check logs: `docker compose logs`
4. Review DigitalOcean's community tutorials

## Migration Rollback

If you need to roll back to your laptop:

1. Your laptop's database was not modified (only exported)
2. Simply stop the VM and restart your laptop collector:
   ```bash
   cd c:\Users\johnsnmi\gextr
   docker compose up -d
   ```

3. The VM can be destroyed without losing your original data

---

**Estimated Total Time**: 1-2 hours for complete migration
**Downtime**: ~5-10 minutes during database transfer
**Difficulty**: ⭐⭐☆☆☆ (2/5 - Beginner friendly)

Good luck! Your GEX collector will be running 24/7 in the cloud shortly.
