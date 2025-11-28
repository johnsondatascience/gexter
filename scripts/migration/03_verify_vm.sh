#!/bin/bash
################################################################################
# Verification Script - Run on the VM
#
# This script verifies that the GEX collector is properly set up and running
# on the DigitalOcean VM.
#
# Usage:
#   ssh gex@your-vm-ip
#   cd /home/gex/gextr
#   ./scripts/migration/03_verify_vm.sh
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=================================="
echo "GEX COLLECTOR - VM VERIFICATION"
echo "=================================="
echo ""

ERRORS=0
WARNINGS=0

# Check 1: Docker is running
echo "1. Checking Docker..."
if systemctl is-active --quiet docker; then
    echo -e "   ${GREEN}✓${NC} Docker service is running"
else
    echo -e "   ${RED}✗${NC} Docker service is not running"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Docker Compose is installed
echo ""
echo "2. Checking Docker Compose..."
if docker compose version &>/dev/null; then
    VERSION=$(docker compose version --short)
    echo -e "   ${GREEN}✓${NC} Docker Compose installed (v${VERSION})"
else
    echo -e "   ${RED}✗${NC} Docker Compose not found"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Project directory exists
echo ""
echo "3. Checking project directory..."
if [ -d "/home/gex/gextr" ]; then
    echo -e "   ${GREEN}✓${NC} Project directory exists"
    cd /home/gex/gextr
else
    echo -e "   ${RED}✗${NC} Project directory not found"
    ERRORS=$((ERRORS + 1))
    exit 1
fi

# Check 4: .env file exists
echo ""
echo "4. Checking configuration..."
if [ -f ".env" ]; then
    echo -e "   ${GREEN}✓${NC} .env file exists"

    # Check required variables
    REQUIRED_VARS=("TRADIER_API_KEY" "DATABASE_TYPE" "POSTGRES_USER" "POSTGRES_PASSWORD")
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}=" .env; then
            echo -e "   ${GREEN}✓${NC} ${var} is set"
        else
            echo -e "   ${RED}✗${NC} ${var} is missing"
            ERRORS=$((ERRORS + 1))
        fi
    done
else
    echo -e "   ${RED}✗${NC} .env file not found"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Docker containers
echo ""
echo "5. Checking Docker containers..."
if docker compose ps &>/dev/null; then
    RUNNING=$(docker compose ps --status running --format "{{.Service}}" | wc -l)
    TOTAL=$(docker compose ps --format "{{.Service}}" | wc -l)

    if [ $RUNNING -eq $TOTAL ] && [ $RUNNING -gt 0 ]; then
        echo -e "   ${GREEN}✓${NC} All containers running (${RUNNING}/${TOTAL})"
        docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
    elif [ $RUNNING -gt 0 ]; then
        echo -e "   ${YELLOW}⚠${NC} Some containers not running (${RUNNING}/${TOTAL})"
        docker compose ps
        WARNINGS=$((WARNINGS + 1))
    else
        echo -e "   ${RED}✗${NC} No containers running"
        echo "   Start with: docker compose up -d"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "   ${YELLOW}⚠${NC} No containers found"
    echo "   Start with: docker compose up -d"
    WARNINGS=$((WARNINGS + 1))
fi

# Check 6: PostgreSQL connectivity
echo ""
echo "6. Checking PostgreSQL..."
if docker compose ps postgres --status running &>/dev/null; then
    if docker exec gextr-postgres-1 pg_isready -U gexuser &>/dev/null; then
        echo -e "   ${GREEN}✓${NC} PostgreSQL is running and accepting connections"

        # Check if database has data
        RECORD_COUNT=$(docker exec gextr-postgres-1 psql -U gexuser -d gexdb -t -c "SELECT COUNT(*) FROM gex_table" 2>/dev/null | xargs || echo "0")

        if [ "$RECORD_COUNT" -gt 0 ]; then
            echo -e "   ${GREEN}✓${NC} Database has data: ${RECORD_COUNT} records"

            # Check last update time
            LAST_UPDATE=$(docker exec gextr-postgres-1 psql -U gexuser -d gexdb -t -c "SELECT MAX(\"greeks.updated_at\") FROM gex_table" 2>/dev/null | xargs || echo "None")
            echo "   Last data collection: ${LAST_UPDATE}"

            # Check if recent (within last 24 hours)
            if [ "$LAST_UPDATE" != "None" ]; then
                LAST_EPOCH=$(date -d "$LAST_UPDATE" +%s 2>/dev/null || echo 0)
                NOW_EPOCH=$(date +%s)
                HOURS_AGO=$(( (NOW_EPOCH - LAST_EPOCH) / 3600 ))

                if [ $HOURS_AGO -lt 24 ]; then
                    echo -e "   ${GREEN}✓${NC} Data is recent (${HOURS_AGO} hours ago)"
                else
                    echo -e "   ${YELLOW}⚠${NC} Data is old (${HOURS_AGO} hours ago)"
                    WARNINGS=$((WARNINGS + 1))
                fi
            fi
        else
            echo -e "   ${YELLOW}⚠${NC} Database is empty (no records yet)"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        echo -e "   ${RED}✗${NC} PostgreSQL not accepting connections"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "   ${RED}✗${NC} PostgreSQL container not running"
    ERRORS=$((ERRORS + 1))
fi

# Check 7: Scheduler logs
echo ""
echo "7. Checking scheduler logs..."
if docker compose ps scheduler --status running &>/dev/null; then
    echo -e "   ${GREEN}✓${NC} Scheduler container is running"

    # Check for recent log activity
    LOG_LINES=$(docker compose logs --tail=10 scheduler 2>/dev/null | wc -l)
    if [ $LOG_LINES -gt 0 ]; then
        echo "   Recent log entries:"
        docker compose logs --tail=5 scheduler | sed 's/^/     /'
    else
        echo -e "   ${YELLOW}⚠${NC} No recent log entries"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "   ${YELLOW}⚠${NC} Scheduler container not running"
    WARNINGS=$((WARNINGS + 1))
fi

# Check 8: Disk space
echo ""
echo "8. Checking disk space..."
DISK_USAGE=$(df -h /home/gex | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo -e "   ${GREEN}✓${NC} Disk usage: ${DISK_USAGE}%"
else
    echo -e "   ${YELLOW}⚠${NC} Disk usage high: ${DISK_USAGE}%"
    WARNINGS=$((WARNINGS + 1))
fi

df -h / /home/gex | sed 's/^/     /'

# Check 9: Memory usage
echo ""
echo "9. Checking memory usage..."
MEM_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3/$2 * 100}')
if [ $MEM_USAGE -lt 90 ]; then
    echo -e "   ${GREEN}✓${NC} Memory usage: ${MEM_USAGE}%"
else
    echo -e "   ${YELLOW}⚠${NC} Memory usage high: ${MEM_USAGE}%"
    WARNINGS=$((WARNINGS + 1))
fi

free -h | sed 's/^/     /'

# Check 10: Firewall rules
echo ""
echo "10. Checking firewall..."
if ufw status | grep -q "Status: active"; then
    echo -e "   ${GREEN}✓${NC} Firewall is active"

    # Check SSH is allowed
    if ufw status | grep -q "22/tcp.*ALLOW"; then
        echo -e "   ${GREEN}✓${NC} SSH access allowed"
    else
        echo -e "   ${RED}✗${NC} SSH access not configured (you may lose access!)"
        ERRORS=$((ERRORS + 1))
    fi

    # Check PostgreSQL is NOT exposed
    if ufw status | grep -q "5432.*ALLOW"; then
        echo -e "   ${RED}✗${NC} PostgreSQL is exposed to internet (security risk!)"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "   ${GREEN}✓${NC} PostgreSQL not exposed (good)"
    fi
else
    echo -e "   ${YELLOW}⚠${NC} Firewall is not active"
    WARNINGS=$((WARNINGS + 1))
fi

# Check 11: System time/timezone
echo ""
echo "11. Checking system time..."
TIMEZONE=$(timedatectl | grep "Time zone" | awk '{print $3}')
if [ "$TIMEZONE" == "America/New_York" ]; then
    echo -e "   ${GREEN}✓${NC} Timezone: ${TIMEZONE}"
else
    echo -e "   ${YELLOW}⚠${NC} Timezone: ${TIMEZONE} (expected America/New_York)"
    WARNINGS=$((WARNINGS + 1))
fi

CURRENT_TIME=$(date "+%Y-%m-%d %H:%M:%S %Z")
echo "   Current time: ${CURRENT_TIME}"

# Summary
echo ""
echo "=================================="
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}ALL CHECKS PASSED!${NC}"
    echo "=================================="
    echo ""
    echo "Your GEX collector is properly configured and running."
    echo ""
    echo "Next steps:"
    echo "  - Monitor logs: docker compose logs -f scheduler"
    echo "  - Check data: docker exec -it gextr-postgres-1 psql -U gexuser -d gexdb"
    echo "  - Access pgAdmin: ssh -L 5050:localhost:5050 gex@$(curl -s ifconfig.me)"
    EXIT_CODE=0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}VERIFICATION COMPLETE WITH WARNINGS${NC}"
    echo "=================================="
    echo ""
    echo "Warnings: ${WARNINGS}"
    echo ""
    echo "Review the warnings above. The system should still work,"
    echo "but you may want to address these issues."
    EXIT_CODE=0
else
    echo -e "${RED}VERIFICATION FAILED${NC}"
    echo "=================================="
    echo ""
    echo "Errors: ${ERRORS}"
    echo "Warnings: ${WARNINGS}"
    echo ""
    echo "Please fix the errors above before proceeding."
    EXIT_CODE=1
fi

echo ""

exit $EXIT_CODE
