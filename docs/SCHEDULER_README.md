# GEX Collector Scheduler Guide

## Overview
The scheduler automatically collects GEX data during market hours with proper timezone handling for California (PST/PDT) users.

## Quick Start

### Run the Scheduler
```bash
python run_scheduler.py
```

The scheduler will:
- ✅ Automatically detect you're in California (Pacific Time)
- ✅ Convert market hours (9:30 AM - 4:00 PM ET) to your local time (6:30 AM - 1:00 PM PT)
- ✅ Only collect during actual market hours
- ✅ Skip weekends automatically

## Configuration

Edit your `.env` file:

```bash
# Market timezone - MUST be America/New_York
TIMEZONE=America/New_York

# How often to collect during market hours (in minutes)
COLLECTION_INTERVAL_MINUTES=15

# Optional: Collect outside market hours
COLLECT_PREMARKET=false   # 7:00-9:30 AM ET (4:00-6:30 AM PT)
COLLECT_POSTMARKET=false  # 4:00-8:00 PM ET (1:00-5:00 PM PT)
```

## Your Schedule (California Time)

| Market Event | Eastern Time | Your Pacific Time |
|--------------|-------------|-------------------|
| Pre-Market Start | 7:00 AM ET | 4:00 AM PT |
| Market Open | 9:30 AM ET | **6:30 AM PT** ✅ |
| Market Close | 4:00 PM ET | **1:00 PM PT** ✅ |
| Post-Market End | 8:00 PM ET | 5:00 PM PT |

**Default:** Collects every 15 minutes during market hours (6:30 AM - 1:00 PM PT)

## Running as Windows Service

### Method 1: Task Scheduler (Recommended)

1. Open Windows Task Scheduler
2. Create a new task:
   - **Name:** GEX Collector Scheduler
   - **Trigger:** At log on (or at startup)
   - **Action:** Start a program
     - Program: `python`
     - Arguments: `C:\Users\johnsnmi\gextr\run_scheduler.py`
     - Start in: `C:\Users\johnsnmi\gextr`
3. Settings:
   - ✅ Run whether user is logged on or not
   - ✅ Run with highest privileges
   - ✅ Allow task to be run on demand

### Method 2: Command Line (Simple)

Just run in a terminal and minimize:
```bash
python run_scheduler.py
```

Press `Ctrl+C` to stop.

## Logs

Check `logs/scheduler.log` for detailed collection history:
```bash
tail -f logs/scheduler.log
```

## Testing

Test a single collection manually:
```bash
python run_gex_collector.py
```

## Troubleshooting

### "Collection happening 3 hours late"
- ✅ **FIXED!** The scheduler now properly converts ET to PT

### "Not collecting during market hours"
- Check `.env` has `TIMEZONE=America/New_York`
- Verify you're running Monday-Friday
- Check current time is 6:30 AM - 1:00 PM PT

### "Want more frequent collections"
- Edit `.env`: `COLLECTION_INTERVAL_MINUTES=5` (every 5 minutes)
- Restart scheduler

## Daily Signals

You can still run signals manually anytime:
```bash
# Full combined signals (GEX + Internals + 0DTE)
python ./scripts/generate_combined_signals.py

# 0DTE focus only
python ./scripts/generate_0dte_signals.py
```

## Recommended Setup

**For California traders:**
1. Run scheduler on startup: `COLLECTION_INTERVAL_MINUTES=15`
2. Generate signals at market open (6:30 AM PT):
   ```bash
   python ./scripts/generate_combined_signals.py
   ```
3. Check 0DTE signals multiple times during day:
   ```bash
   python ./scripts/generate_0dte_signals.py
   ```

