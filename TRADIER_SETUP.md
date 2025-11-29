# Tradier Paper Trading Setup Guide

## Overview

This guide explains how to use the Tradier-integrated paper trading system for the hedged strangle strategy. Unlike the simple paper trading system, this version places actual orders through Tradier's sandbox API, providing realistic order execution, fills, and position tracking.

## Prerequisites

1. **Tradier Sandbox Account**
   - Account: VA86061098
   - API key stored in `.env` as `TRADIER_SANDBOX_API_KEY`
   - Starting balance: $200,000

2. **GEX Data Collection**
   - PostgreSQL database running
   - GEX collector running and populating data
   - Recent snapshots available in `gex_table`

3. **Python Dependencies**
   ```bash
   pip install psycopg2-binary pandas numpy python-dotenv requests
   ```

## Files

### Core Trading Engine
- **`paper_trade_tradier.py`** - Main trading engine
  - Monitors GEX signals every 5 minutes
  - Places orders through Tradier API
  - Manages positions with PDT protection
  - Implements hedged strangle strategy

### Utilities
- **`test_tradier_connection.py`** - Verify API connection
- **`tradier_report.py`** - View performance and positions
- **`start_tradier_trading.bat`** - Quick launcher (Windows)

### Data Files
- **`tradier_positions.json`** - Position tracking (auto-created)
- **`logs/tradier_trading.log`** - Trading activity log
- **`output/tradier_trades.csv`** - Exported trade history

## Strategy Parameters

The system uses the **Hedged Strangle Strategy**:

### Entry Rules
1. **Calls**: Enter on BUY signals (SPX > Zero GEX) OR when we have puts but no calls
2. **Puts**: Enter on SELL signals (SPX < Zero GEX) OR when we have calls but no puts

### Exit Rules
- **Profit Target**: 25% gain
- **Stop Loss**: 40% loss
- **PDT Protection**: No same-day exits (prevents pattern day trader violations)

### Position Sizing
- 1 contract per leg
- Uses 0DTE options (same-day expiration)
- Independent timing for each leg

## Setup Steps

### 1. Verify Tradier Connection

First, test that your API connection is working:

```bash
python test_tradier_connection.py
```

Expected output:
```
============================================================
TRADIER API CONNECTION TEST
============================================================
...
CONNECTION SUCCESSFUL!
```

### 2. Check Database Connection

Verify GEX data is available:

```bash
python -c "import psycopg2; from dotenv import load_dotenv; import os; load_dotenv(); conn = psycopg2.connect(host=os.getenv('DB_HOST'), database=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD')); print('Database OK'); conn.close()"
```

### 3. Start Trading

Use the launcher script:

```bash
start_tradier_trading.bat
```

Or run directly:

```bash
python paper_trade_tradier.py
```

### 4. Monitor Performance

While trading is running, open a new terminal and run:

```bash
python tradier_report.py
```

This shows:
- Current account balance
- Live positions from Tradier
- Closed trades and P&L
- Performance by leg type, signal, and exit reason

## Trading Schedule

### Pre-Market (Before 9:30 AM ET)
1. Start GEX collector (if not already running)
2. Verify database has recent data
3. Test Tradier connection
4. Review previous day's performance

### Market Open (9:30 AM ET)
1. Launch trading engine: `start_tradier_trading.bat`
2. Engine begins monitoring every 5 minutes
3. Watches for entry signals and exit conditions

### During Trading Day
- Engine runs automatically
- Logs all activity to `logs/tradier_trading.log`
- Positions saved to `tradier_positions.json`
- Check status anytime: `python tradier_report.py`

### Market Close (4:00 PM ET)
- Engine stops checking for new signals
- Overnight positions remain open
- Will be evaluated next trading day

### After Market Close
1. Run performance report: `python tradier_report.py`
2. Review trades in `output/tradier_trades.csv`
3. Check logs for any errors or issues

## How It Works

### Market Monitoring Loop

Every 5 minutes during market hours (9:30 AM - 4:00 PM ET):

1. **Check Order Fills**
   - Query Tradier for pending order status
   - Update local tracking when filled
   - Calculate P&L for closed positions

2. **Get Latest GEX Data**
   - Query PostgreSQL for most recent snapshot
   - Filter for 0DTE options (same-day expiration)

3. **Calculate Signals**
   - Zero GEX level (volatility regime indicator)
   - GEX Signal (BUY/SELL based on SPX vs Zero GEX)
   - Call Wall (resistance level)
   - Put Wall (support level)

4. **Check Exits** (PDT Protected)
   - For each filled leg (except today's entries):
     - Get current option quote from Tradier
     - Check profit target (25%) or stop loss (40%)
     - Place exit order if triggered

5. **Check Entries**
   - Determine if we need calls or puts
   - Build OCC option symbol (e.g., SPX251231C06000000)
   - Get quote from Tradier
   - Place limit order at mid price

### Order Execution

All orders are placed as **limit orders** at the bid/ask midpoint:
- Better chance of favorable fills
- Avoids market order slippage
- More realistic than simple paper trading

Order types:
- **Entry**: `buy_to_open` at mid price
- **Exit**: `sell_to_close` at mid price

### Position Tracking

Two sources of truth:

1. **Tradier API** - Live positions
   - Real-time from brokerage
   - Confirms actual fills
   - Used for validation

2. **Local JSON** - Strategy tracking
   - Entry/exit signals
   - GEX context at entry
   - P&L calculations
   - Performance analytics

## Example Session

```
============================================================
TRADIER PAPER TRADING ENGINE STARTED
============================================================
Account: VA86061098
Check Interval: 300s
Starting Balance: $200,000.00

[2025-11-29 09:30:15] [INFO] SPX: 6050.25 | Zero GEX: 6025 | Signal: BUY | Walls: C=6100 P=6000
[2025-11-29 09:30:18] [INFO] Placed ENTRY order for CALL @ 6100.0 (Order ID: 12345)

[2025-11-29 09:35:22] [INFO] ENTRY filled for CALL @ 6100.0: $15.50
[2025-11-29 09:35:25] [INFO] Placed ENTRY order for PUT @ 6000.0 (Order ID: 12346)
[2025-11-29 09:40:30] [INFO] ENTRY filled for PUT @ 6000.0: $12.25

[2025-11-29 10:15:45] [INFO] SPX: 6075.50 | Zero GEX: 6025 | Signal: BUY | Walls: C=6100 P=6000
[2025-11-29 10:15:48] [INFO] Placed EXIT order for CALL @ 6100.0 (Reason: PROFIT_TARGET, Order ID: 12347)
[2025-11-29 10:20:51] [INFO] EXIT filled for CALL @ 6100.0: $19.75 (P&L: $425.00)
```

## Troubleshooting

### Connection Issues

**Problem**: `ERROR: Failed to get option chain`
**Solution**:
- Check API key in `.env`
- Verify sandbox account is active
- Check network connection

**Problem**: `No GEX data available`
**Solution**:
- Ensure GEX collector is running
- Check database connection
- Verify data is recent (< 5 minutes old)

### Order Issues

**Problem**: `ENTRY rejected for CALL`
**Solution**:
- Check option symbol formatting
- Verify sufficient buying power
- Review Tradier logs for rejection reason

**Problem**: Orders not filling
**Solution**:
- In sandbox, fills may be simulated
- Check if bid/ask spread is reasonable
- Consider switching to market orders (edit code)

### Data Issues

**Problem**: No 0DTE options available
**Solution**:
- Check if market is open
- Verify expiration dates in database
- Ensure collector is fetching SPX data

## Performance Expectations

Based on backtest results (hedged strategy):

- **Total Legs**: ~100-120 per month
- **Win Rate**: ~56%
- **Profit Factor**: ~11x
- **Average P&L**: ~$20 per leg
- **Monthly Target**: ~$2,000 (from backtest)

**Important**: Live results will differ due to:
- Realistic order fills
- Slippage and spreads
- Market conditions
- Execution timing

## Validation Criteria

Before switching to live trading, ensure:

1. **Minimum 20 trades completed** in sandbox
2. **Win rate > 50%**
3. **No system errors** in logs
4. **Position tracking accurate** (Tradier API vs local JSON match)
5. **PDT protection working** (no same-day exits)
6. **Overnight positions handled correctly**

## Next Steps

1. **Week 1**: Run in sandbox, monitor daily
2. **Week 2**: Analyze performance, tune parameters if needed
3. **Week 3**: Final validation, prepare for live
4. **Week 4**: Consider live trading if all criteria met

## Key Differences from Simple Paper Trading

| Feature | Simple Paper Trading | Tradier Integration |
|---------|---------------------|---------------------|
| Order Execution | Instant fill at mid price | Real limit orders, actual fills |
| Position Tracking | Local JSON only | Tradier API + local JSON |
| Slippage | None (unrealistic) | Yes (more realistic) |
| Rejection Handling | No rejections | Orders can be rejected |
| API Dependency | None | Requires Tradier API |
| Validation | Manual | Against live brokerage positions |

## Support

For issues:
1. Check logs: `logs/tradier_trading.log`
2. Run diagnostics: `python test_tradier_connection.py`
3. Review positions: `python tradier_report.py`
4. Check database: Ensure GEX collector is running

## Configuration

Edit in `paper_trade_tradier.py`:

```python
# Strategy parameters
self.profit_target_pct = 25.0  # Profit target %
self.stop_loss_pct = 40.0      # Stop loss %
self.contracts_per_leg = 1     # Contracts per leg

# In run() method
check_interval_seconds = 300   # How often to check market (seconds)
```

## Important Notes

1. **PDT Protection**: Engine will NOT exit positions on the same day they were entered
2. **Overnight Positions**: Held overnight, evaluated next trading day
3. **0DTE Only**: Currently uses same-day expiration options
4. **Market Hours**: Only trades 9:30 AM - 4:00 PM ET
5. **Sandbox Mode**: All trades are simulated, no real money at risk

---

**Ready to start?** Run `start_tradier_trading.bat` and monitor with `python tradier_report.py`!
