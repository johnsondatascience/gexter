# Quick Start: Migrate GEX Collector to Cloud

**Time**: 1 hour | **Cost**: $24/month | **Difficulty**: Easy

## Prerequisites Checklist
- [ ] DigitalOcean account created
- [ ] Docker running on your laptop
- [ ] Current GEX data you want to keep (optional)

## 3-Step Migration

### Step 1: Create Droplet (10 min)

1. Go to https://cloud.digitalocean.com/droplets/new
2. Select:
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: $24/mo (2GB RAM, 50GB SSD)
   - **Datacenter**: New York 1
   - **Authentication**: Add your SSH key or use password
   - **Hostname**: `gex-collector`
3. Click **Create Droplet**
4. **Copy the IP address** (e.g., `164.92.123.45`)

### Step 2: Setup VM (5 min)

```bash
# SSH into droplet as root
ssh root@YOUR_DROPLET_IP

# Run setup (copy/paste this entire block)
curl -fsSL https://raw.githubusercontent.com/docker/docker-install/master/install.sh | sh
apt-get install -y docker-compose-plugin postgresql-client
useradd -m -s /bin/bash gex
usermod -aG docker gex
mkdir -p /home/gex/{gextr,backups,logs}
chown -R gex:gex /home/gex
timedatectl set-timezone America/New_York
ufw allow 22/tcp && ufw allow 8080/tcp && ufw --force enable
echo "Setup complete!"
exit
```

### Step 3: Migrate from Laptop (45 min)

**Windows (PowerShell)**:
```powershell
cd c:\Users\johnsnmi\gextr
.\scripts\migration\02_migrate_to_vm.ps1 -VMIp "YOUR_DROPLET_IP"
```

**Linux/Mac**:
```bash
cd ~/gextr
./scripts/migration/02_migrate_to_vm.sh YOUR_DROPLET_IP
```

**What happens**:
- ✓ Packages your project
- ✓ Transfers to VM (~1 min)
- ✓ Exports database (~5 min)
- ✓ Imports on VM (~15 min)
- ✓ Starts collector

### Step 4: Verify (5 min)

```bash
# SSH into VM
ssh gex@YOUR_DROPLET_IP

# Check status
cd /home/gex/gextr
docker compose ps

# Watch it collect data
docker compose logs -f scheduler

# Check database
docker exec gextr-postgres-1 psql -U gexuser -d gexdb -c \
  "SELECT COUNT(*), MAX(\"greeks.updated_at\") FROM gex_table;"
```

## Success Criteria

You should see:
- ✓ 3 containers running (postgres, scheduler, pgadmin)
- ✓ Scheduler logs show "Collection starting..."
- ✓ Database query returns your record count
- ✓ New timestamps appear every 15 min (during market hours)

## Common Issues

### "Cannot connect to VM"
```bash
# Check VM is running
ping YOUR_DROPLET_IP

# Ensure SSH key is loaded (Windows)
Get-Service ssh-agent | Set-Service -StartupType Automatic
Start-Service ssh-agent
ssh-add ~/.ssh/id_rsa
```

### "Permission denied" on scripts
```bash
ssh gex@YOUR_DROPLET_IP
cd /home/gex/gextr
chmod +x scripts/*.py scripts/migration/*.sh
```

### "Database import failed"
```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Restart and try again
docker compose restart postgres
sleep 10
# Re-run migration script
```

## Daily Operations

### Check Status (from laptop)
```bash
ssh gex@YOUR_DROPLET_IP 'cd gextr && docker compose ps'
```

### View Logs (from laptop)
```bash
ssh gex@YOUR_DROPLET_IP 'cd gextr && docker compose logs --tail=50 scheduler'
```

### Access pgAdmin
```bash
# On laptop, create tunnel
ssh -L 5050:localhost:5050 gex@YOUR_DROPLET_IP

# Open browser: http://localhost:5050
```

### Restart Collector
```bash
ssh gex@YOUR_DROPLET_IP
cd /home/gex/gextr
docker compose restart scheduler
```

## What's Collected

During market hours (9:30 AM - 4:00 PM ET):
- Every **15 minutes**: Full SPX option chain with Greeks
- **~5,000 records per collection** (varies by strikes/expirations)
- **~500MB/month** database growth (varies by market activity)

Outside market hours:
- No collection (scheduler idles)
- Zero API calls

## Cost Breakdown

| Item | Cost/Month |
|------|------------|
| DigitalOcean Droplet (2GB) | $24.00 |
| Bandwidth (included 2TB) | $0.00 |
| **Total** | **$24.00** |

Additional costs if needed:
- 4GB RAM upgrade: +$24/mo
- Automated backups: +$4.80/mo
- S3 backup storage: ~$1/mo

## Next Steps After Migration

**Week 1**:
- [ ] Monitor daily to ensure stable collection
- [ ] Verify data quality in database
- [ ] Set up automated backups (Phase 2)

**Week 2**:
- [ ] Configure monitoring alerts
- [ ] Stop laptop collector (no longer needed!)
- [ ] Document any issues/learnings

**Month 1**:
- [ ] Review first month of continuous data
- [ ] Begin preliminary analysis
- [ ] Plan backtesting infrastructure

**Month 6**:
- [ ] Sufficient data for meaningful backtesting
- [ ] Evaluate trading strategies
- [ ] Consider Phase 3 scaling if strategy validates

## Emergency Contacts

**DigitalOcean Support**:
- Dashboard: https://cloud.digitalocean.com/support
- Docs: https://docs.digitalocean.com

**Rollback to Laptop**:
If VM fails and you need to revert:
```bash
# On laptop
cd c:\Users\johnsnmi\gextr
docker compose up -d
# Your original data was never modified
```

## File Reference

Migration scripts location:
```
c:\Users\johnsnmi\gextr\scripts\migration\
├── README.md              ← Detailed guide
├── QUICKSTART.md          ← This file
├── 01_setup_vm.sh         ← VM setup (run on droplet)
├── 02_migrate_to_vm.sh    ← Migration (run on laptop)
├── 02_migrate_to_vm.ps1   ← Migration (Windows PowerShell)
└── 03_verify_vm.sh        ← Verification (run on VM)
```

## Help

If stuck:
1. Read detailed guide: `README.md`
2. Run verification: `./scripts/migration/03_verify_vm.sh`
3. Check logs: `docker compose logs`
4. Review troubleshooting section in README.md

---

**Ready?** Start with Step 1 above. Good luck! 🚀
