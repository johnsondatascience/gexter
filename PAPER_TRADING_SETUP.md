# Paper Trading Setup Guide - Monday, December 2, 2024

## Overview

Your paper trading system is ready to trade the **hedged strangle strategy** starting Monday morning. The system will monitor the market in real-time, execute trades based on GEX signals, and track all positions and P&L.

---

## What You Have

### 1. Paper Trading Engine
**File**: [scripts/paper_trade_hedged.py](scripts/paper_trade_hedged.py)

**What it does**:
- Monitors market every 5 minutes during trading hours (9:30 AM - 4:00 PM ET)
- Uses real-time GEX data from your PostgreSQL database
- Implements the exact hedged strangle strategy from your backtests
- Enters calls on BUY signals
- Enters puts as hedges when holding calls OR on SELL signals
- Exits positions at profit targets (25%) or stop losses (40%)
- **PDT Protected**: No same-day round trips
- Closes overnight positions at market open
- Logs all decisions with reasoning
- Saves positions to `output/paper_trading_positions.json`

### 2. Daily Reporting
**File**: [scripts/paper_trade_report.py](scripts/paper_trade_report.py)

**What it does**:
- Generates comprehensive performance reports
- Shows active positions and P&L
- Analyzes performance by leg type, signal, and exit reason
- Exports detailed CSV reports

---

## Pre-Market Checklist (Sunday Evening / Monday Morning)

### Step 1: Verify GEX Collector is Running

Your GEX collector must be running to provide real-time data for paper trading.

```bash
# Check if collector is running
docker-compose ps

# If not running, start it
docker-compose up -d
```

**Verify data collection**:
```bash
# Check recent data
python scripts/check_historical_data.py
```

You should see snapshots from recent trading days.

### Step 2: Create Logs Directory

```bash
# Create logs directory if it doesn't exist
mkdir -p logs
```

### Step 3: Test Database Connection

```bash
# Quick test - should show recent data
python -c "import psycopg2; from dotenv import load_dotenv; import os; load_dotenv(); conn = psycopg2.connect(host=os.getenv('POSTGRES_HOST'), port=5432, database=os.getenv('POSTGRES_DB'), user=os.getenv('POSTGRES_USER'), password=os.getenv('POSTGRES_PASSWORD')); print('Database connected successfully'); conn.close()"
```

### Step 4: Review Strategy Parameters

The paper trading engine uses these settings (matching your best backtest results):

- **Strategy**: Hedged Strangle (Independent Leg Timing)
- **Expiration**: 0-1 DTE (same day or next day expiration)
- **Entry Logic**:
  - Enter calls on BUY signals (SPX > Zero GEX)
  - Enter puts on SELL signals (SPX < Zero GEX)
  - Enter opposite leg as hedge when only holding one side
- **Exit Logic**:
  - Profit Target: +25%
  - Stop Loss: -40%
  - Overnight: Close all positions at market open
  - PDT Protection: No same-day exits
- **Strike Selection**:
  - Calls: Call wall (max positive GEX above price)
  - Puts: Put wall (max negative GEX below price)

---

## Monday Morning - Launch Procedure

### 9:00 AM ET - Pre-Market Setup

1. **Open two terminal windows**

**Terminal 1 - Monitor GEX Collector Logs**:
```bash
# Watch the GEX collector to ensure data is flowing
docker-compose logs -f gex-collector
```

You should see it collecting option data every few minutes.

**Terminal 2 - Paper Trading Engine**:
```bash
# Start the paper trading engine
python scripts/paper_trade_hedged.py
```

This will:
- Wait until market open (9:30 AM)
- Close any overnight positions from Friday
- Begin monitoring for entry signals
- Log all activity to console and `logs/paper_trading.log`

### 9:30 AM ET - Market Open

The paper trading engine will automatically:
1. Close any overnight positions from previous day
2. Start monitoring market snapshots
3. Look for entry signals based on GEX
4. Execute trades when conditions are met

### Expected First Trade

Based on your backtests, you'll likely see:
- **First signal**: BUY (if SPX > Zero GEX)
- **First entry**: CALL at call wall strike
- **Typical entry price**: $0.30 - $5.00 (depends on market)
- **Example log**:
  ```
  2024-12-02 10:15:23 - INFO - Market snapshot: SPX=$6850.00, Zero GEX=$6800.00, Signal=BUY
  2024-12-02 10:15:24 - INFO - ENTER CALL $6900.0: $2.50 (SPX=$6850.00, Signal=BUY)
  ```

---

## During Trading Day

### What You'll See

The engine logs every action:

**Entry Signal**:
```
INFO - Market snapshot: SPX=$6850.00, Zero GEX=$6800.00, Signal=BUY
INFO - ENTER CALL $6900.0: $2.50 (SPX=$6850.00, Signal=BUY)
INFO - Active positions: 1
INFO -   CALL $6900.0: $2.50 -> $2.50 = +0.0%
```

**Position Update (every 5 min)**:
```
INFO - Market snapshot: SPX=$6870.00, Zero GEX=$6800.00, Signal=BUY
INFO - Active positions: 1
INFO -   CALL $6900.0: $2.50 -> $3.80 = +52.0%
```

**Exit Signal (Profit Target)**:
```
INFO - EXIT CALL $6900.0: $2.50 -> $3.15 = +26.0% (profit_target_26.0pct)
```

**Hedge Entry**:
```
INFO - ENTER PUT $6800.0: $1.20 (HEDGE) (SPX=$6870.00, Signal=BUY)
```

### Monitoring Tools

**Check current status**:
```bash
# View recent logs
tail -50 logs/paper_trading.log

# Generate current performance report
python scripts/paper_trade_report.py
```

**Check positions file directly**:
```bash
# View raw positions
cat output/paper_trading_positions.json
```

---

## End of Day (4:00 PM ET)

### After Market Close

1. **The engine will continue running** but stop trading activity
2. **Generate final daily report**:
   ```bash
   python scripts/paper_trade_report.py
   ```

3. **Review the day**:
   - Check `output/paper_trading_report_YYYYMMDD.csv`
   - Review `logs/paper_trading.log`
   - Analyze what worked and what didn't

4. **Optional: Stop the engine**:
   - Press `Ctrl+C` in the paper trading terminal
   - Or leave it running overnight (it will auto-close positions Tuesday morning)

### Expected Results (Based on Backtests)

From your backtests, you should expect:
- **2-4 trades per day** (calls and puts)
- **Win rate**: ~56%
- **Profit factor**: ~11x
- **Average win**: $37
- **Average loss**: -$4

**Example Day**:
```
Total Trades: 3
  - 2 CALLS: $25.00 profit, $-5.00 loss = +$20.00
  - 1 PUT: $8.00 profit
  - Total: +$28.00
```

---

## Daily Routine

### Monday - Friday Schedule

**9:00 AM**:
- Check GEX collector is running
- Start paper trading engine

**During Day**:
- Monitor logs for trades
- Review positions every few hours

**4:00 PM**:
- Generate daily report
- Review performance

**Evening**:
- Compare to backtests
- Adjust if needed (but give it 20+ trades first)

---

## Important Notes

### PDT Protection

The engine **will NOT exit positions on the same day they were entered**. This means:
- Enter Monday morning → Exit Tuesday morning (overnight)
- Enter Monday afternoon → Exit Tuesday anytime

This protects you from Pattern Day Trader violations.

**Example**:
```
Monday 10:00 AM - ENTER CALL $6900
Monday 2:00 PM  - CALL up 30% (profit target hit)
                  → System HOLDS (no same-day exit)
Tuesday 9:35 AM - CLOSE CALL at market open (overnight close)
```

### Position Sizing

The paper trading system tracks **per-option P&L**, not position size. When you go live:
- **Small account (<$10k)**: 1 contract per trade
- **Medium account ($10k-50k)**: 2-5 contracts per trade
- **Large account (>$50k)**: 5-10 contracts per trade

Rule of thumb: Risk 1-2% of portfolio per trade.

### Data Requirements

The paper trading engine needs:
- Real-time GEX data (from your collector)
- Updated every 5 minutes minimum
- 0DTE and 1DTE options available

If data is stale or missing, the engine will skip that cycle and wait for the next snapshot.

### What Could Go Wrong

**Issue**: "No market data available"
- **Cause**: GEX collector not running or database connection issue
- **Fix**: Check `docker-compose ps` and restart if needed

**Issue**: "No tradeable options (0-1 DTE)"
- **Cause**: Market has no 0DTE or 1DTE options today (e.g., holiday, early close)
- **Fix**: Normal - engine will skip today

**Issue**: No trades all day
- **Cause**: No BUY/SELL signals, or already holding positions at those strikes
- **Fix**: Normal - some days have no signals. Backtest showed ~42 trades over 64 days (not every day trades)

---

## Validation Period

### First 20 Trades (Recommended)

**Do NOT go live until you have 20+ paper trades**. This validates:
- Strategy works in current market conditions
- GEX signals are still predictive
- Execution is feasible (liquidity, fills)
- Your systems are reliable

**What to track**:
- Win rate vs backtest (expect ~56%)
- Average P&L vs backtest (expect $19/trade)
- Profit factor vs backtest (expect ~11x)
- Entry/exit execution (are prices realistic?)

**Red flags to watch for**:
- Win rate < 40% (strategy may have degraded)
- Large losses (>$50 on single trade)
- Unable to get fills at reasonable prices
- Signals flip-flopping (market too choppy)

### After 20 Trades

If performance aligns with backtests:
1. Start with **1 contract per trade**
2. Scale up gradually after 10 successful live trades
3. Never risk more than 2% per trade

---

## Files Reference

### Scripts
- [scripts/paper_trade_hedged.py](scripts/paper_trade_hedged.py) - Main trading engine
- [scripts/paper_trade_report.py](scripts/paper_trade_report.py) - Performance reporting
- [scripts/check_historical_data.py](scripts/check_historical_data.py) - Verify data availability

### Backtests (for comparison)
- [scripts/backtest_strangle_hedged.py](scripts/backtest_strangle_hedged.py) - Original backtest
- [output/strangle_hedged_results.csv](output/strangle_hedged_results.csv) - Backtest results
- [output/strangle_hedged_performance.json](output/strangle_hedged_performance.json) - Backtest metrics

### Outputs
- `output/paper_trading_positions.json` - Current positions (auto-saved)
- `output/paper_trading_report_YYYYMMDD.csv` - Daily reports
- `logs/paper_trading.log` - Detailed trading log

---

## Quick Command Reference

```bash
# Start paper trading
python scripts/paper_trade_hedged.py

# Generate performance report
python scripts/paper_trade_report.py

# Check GEX collector status
docker-compose ps
docker-compose logs -f gex-collector

# View paper trading logs
tail -f logs/paper_trading.log

# Check recent market data
python scripts/check_historical_data.py

# Compare to backtests
python scripts/compare_strategies.py
```

---

## Support & Troubleshooting

### Common Questions

**Q: Can I run this overnight?**
A: Yes! The engine will sleep when market is closed and auto-resume at 9:30 AM.

**Q: What if I miss market open?**
A: Just start the engine anytime. It will begin trading from that point forward.

**Q: Can I modify the profit target or stop loss?**
A: Yes, edit lines 113-114 in `paper_trade_hedged.py`:
```python
self.profit_target_pct = 25.0  # Change this
self.stop_loss_pct = 40.0      # Change this
```

**Q: How do I reset and start fresh?**
A: Delete `output/paper_trading_positions.json` and it will start with a clean slate.

**Q: Can I paper trade multiple strategies?**
A: Yes, but you'll need to modify the script to use different position files for each strategy.

### Getting Help

If you encounter issues:
1. Check `logs/paper_trading.log` for errors
2. Verify GEX collector is running: `docker-compose logs gex-collector`
3. Test database connection
4. Review this guide's troubleshooting section

---

## Summary - Monday Morning Checklist

- [ ] **9:00 AM**: Verify GEX collector is running (`docker-compose ps`)
- [ ] **9:00 AM**: Create logs directory (`mkdir -p logs`)
- [ ] **9:00 AM**: Test database connection
- [ ] **9:15 AM**: Open two terminals (collector logs + paper trader)
- [ ] **9:20 AM**: Start paper trading engine (`python scripts/paper_trade_hedged.py`)
- [ ] **9:30 AM**: Watch for first signal
- [ ] **12:00 PM**: Check first performance report (`python scripts/paper_trade_report.py`)
- [ ] **4:00 PM**: Generate end-of-day report
- [ ] **4:30 PM**: Compare to backtest expectations

---

## Expected Monday Results

Based on recent market conditions and your backtests:
- **Likely first signal**: BUY (market typically opens above Zero GEX)
- **Likely first trade**: CALL at resistance level
- **Expected trades today**: 2-4 legs (mix of calls/puts)
- **Target P&L**: +$20 to +$50 (based on backtest avg)

---

**Good luck with your paper trading! Remember**:
- Start with paper trading for 20+ trades minimum
- Don't get discouraged by early losses (56% win rate means 44% will lose)
- Trust the strategy over many trades, not individual trades
- Monitor but don't over-trade or second-guess the system

**The hedged strategy averaged $2,051 profit over 107 trades in backtests. Give it time to prove itself!** 🚀
