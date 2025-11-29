# GEX Trading Strategy Development Guide

## Your Data Collection System (Now Running in Production!)

Your Digital Ocean deployment is collecting:
- **SPX option chains** every 5 minutes during market hours
- **100+ data points** per option (Greeks, prices, volumes)
- **Greek differences** (tracking dealer repositioning)
- **SPX intraday prices** synchronized with options data
- **Market internals** (breadth, volume, TICK/TRIN)

Data is stored in PostgreSQL and ready for analysis!

---

## 5 Ways to Develop Trading Strategies RIGHT NOW

### 1. **Generate Trading Signals from Your Existing Data**

Run the signal generator to see what your system can do:

```bash
# Option A: Run from your local machine (connecting to cloud DB)
python scripts/generate_signals.py

# Option B: Run inside your cloud container
ssh root@your_droplet_ip
docker exec gex_collector python /app/scripts/generate_signals.py
```

**What you'll get:**
- Current SPX price
- Zero GEX level (volatility regime indicator)
- Support/Resistance levels (put/call walls)
- BUY/SELL/NEUTRAL signals with confidence levels
- EMA trend analysis
- Actionable recommendations

**Output saved to:** `output/trading_signals.json`

---

### 2. **Analyze 0DTE (Same-Day Expiration) Opportunities**

0DTE options have unique GEX characteristics - massive gamma concentration creates predictable price pinning.

```bash
python scripts/generate_0dte_signals.py
```

**Key 0DTE Concepts:**
- **Max GEX Strike**: Price gravitates toward this level
- **Gamma Pinning**: Dealers hedge by buying/selling at specific strikes
- **Time Decay**: Accelerates dramatically in final hours
- **Strategy**: Sell premium at max GEX strikes, buy away from GEX concentration

---

### 3. **Combine GEX with Market Internals**

Get multi-factor signals that consider market-wide breadth and volume:

```bash
python scripts/generate_combined_signals.py
```

**What this analyzes:**
- **GEX signals** (from options positioning)
- **Market breadth** (advancing vs declining stocks)
- **Volume analysis** (up volume vs down volume)
- **Signal alignment** (-1 to +1 conviction score)
- **Conviction levels**: VERY_HIGH, HIGH, MODERATE, LOW, CONFLICTING

**Use case:** Filter out false GEX signals when market breadth is weak.

---

### 4. **Connect to Your Cloud Database for Custom Analysis**

Access your PostgreSQL database to run custom queries:

#### Connection Details:
```python
# Create .env file locally with these variables:
POSTGRES_HOST=your_droplet_ip
POSTGRES_PORT=5432
POSTGRES_DB=gexdb
POSTGRES_USER=gexuser
POSTGRES_PASSWORD=your_password
```

#### Example Python Script:
```python
import psycopg2
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

# Connect to your cloud database
conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST'),
    port=5432,
    database='gexdb',
    user='gexuser',
    password=os.getenv('POSTGRES_PASSWORD')
)

# Example: Find current zero GEX level
query = """
WITH latest_time AS (
    SELECT MAX("greeks.updated_at") as ts FROM gex_table
),
net_gex AS (
    SELECT
        strike,
        SUM(gex) as net_gex,
        LAG(SUM(gex)) OVER (ORDER BY strike) as prev_net_gex
    FROM gex_table
    WHERE "greeks.updated_at" = (SELECT ts FROM latest_time)
    GROUP BY strike
)
SELECT strike, net_gex, prev_net_gex
FROM net_gex
WHERE SIGN(net_gex) != SIGN(prev_net_gex)
ORDER BY ABS(net_gex)
LIMIT 1;
"""

df = pd.read_sql(query, conn)
print("Zero GEX Level:", df['strike'].iloc[0])
conn.close()
```

---

### 5. **Use Jupyter Notebook for Interactive Analysis**

Open the pre-built notebook with visualizations:

```bash
jupyter notebook docs/gexter.ipynb
```

**What's in the notebook:**
- GEX distribution charts
- Support/Resistance visualizations
- Greek changes over time
- EMA trend analysis
- Customizable analysis cells

---

## Strategy Ideas to Backtest

### Strategy 1: **GEX Regime Trading**
**Concept:** Trade differently based on volatility regime.

```
IF SPX < Zero_GEX:
    → Use momentum strategies (trend following)
    → Wider stops (high volatility)
    → Breakout trades

IF SPX > Zero_GEX:
    → Use mean-reversion (range trading)
    → Tighter stops (low volatility)
    → Fade extremes
```

### Strategy 2: **Call/Put Wall Bounces**
**Concept:** Buy support at put walls, sell resistance at call walls.

```
Entry:
- Price approaches major put wall (support)
- GEX signal = BUY
- EMA8 > EMA21 (uptrend)

Exit:
- Price reaches call wall (resistance)
- OR signal flips to SELL
```

### Strategy 3: **Dealer Repositioning**
**Concept:** Follow the smart money (dealers).

```
IF gex_pct_change > +10%:
    → Dealers buying calls or selling puts (Bullish)
    → Go LONG

IF gex_pct_change < -10%:
    → Dealers buying puts or selling calls (Bearish)
    → Go SHORT or exit longs
```

### Strategy 4: **EMA + GEX Confluence**
**Concept:** Only trade when technicals AND GEX align.

```
LONG Entry:
- Price > EMA8 > EMA21 (uptrend)
- SPX < Zero_GEX (momentum regime)
- Net GEX at spot < 0 (put support)
- Composite signal = BUY or STRONG_BUY

SHORT Entry:
- Price < EMA8 < EMA21 (downtrend)
- Price approaching call wall resistance
- GEX change < -5%
- Composite signal = SELL or STRONG_SELL
```

### Strategy 5: **0DTE Gamma Pinning**
**Concept:** Exploit same-day option expiration mechanics.

```
Morning (9:30-11:00 AM):
- Identify max GEX strike for 0DTE options
- Trade in direction TOWARD max GEX
- Expect price to pin near that level

Afternoon (2:00-3:30 PM):
- If price is AT max GEX: Sell straddles/strangles
- If price is AWAY from max GEX: Buy toward max GEX
- Exit ALL positions by 3:50 PM
```

---

## Data Available for Backtesting

Your database contains everything you need:

### Greek Data (11 metrics × 3 views = 33 columns)
- **Current values**: delta, gamma, theta, vega, rho, phi, IVs
- **Absolute changes**: delta_diff, gamma_diff, etc.
- **Percentage changes**: delta_pct_change, gamma_pct_change, etc.

### Price Data
- **Option prices**: last, bid, ask, OHLC
- **SPX prices**: spx_price, spx_open, spx_high, spx_low, spx_close
- **Changes**: change, change_percentage, spx_change, spx_change_pct

### Volume & Interest
- volume, open_interest, last_volume

### Calculated Metrics
- **GEX**: strike × gamma × open_interest × 100
- **GEX changes**: gex_diff, gex_pct_change
- **Technical indicators**: EMAs (8, 21, 55), trend signals

---

## Backtesting Framework

### Step 1: Extract Historical Data
```python
query = """
SELECT
    "greeks.updated_at" as timestamp,
    strike,
    option_type,
    gex,
    "greeks.gamma",
    "greeks.delta",
    open_interest,
    spx_price,
    gex_pct_change
FROM gex_table
WHERE "greeks.updated_at" >= '2025-01-01'
ORDER BY "greeks.updated_at", strike
"""
df = pd.read_sql(query, conn)
```

### Step 2: Calculate Zero GEX Over Time
```python
zero_gex_levels = []
for timestamp in df['timestamp'].unique():
    snapshot = df[df['timestamp'] == timestamp]
    net_gex = snapshot.groupby('strike')['gex'].sum().reset_index()

    # Find where GEX crosses zero
    for i in range(len(net_gex) - 1):
        if (net_gex['gex'].iloc[i] < 0 and net_gex['gex'].iloc[i+1] > 0):
            zero_strike = net_gex['strike'].iloc[i]
            zero_gex_levels.append({'timestamp': timestamp, 'zero_gex': zero_strike})
            break

zero_gex_df = pd.DataFrame(zero_gex_levels)
```

### Step 3: Generate Signals
```python
signals = []
for idx, row in zero_gex_df.iterrows():
    spx = df[df['timestamp'] == row['timestamp']]['spx_price'].iloc[0]
    zero = row['zero_gex']

    if spx < zero:
        signals.append({'timestamp': row['timestamp'], 'signal': 'MOMENTUM', 'spx': spx, 'zero': zero})
    else:
        signals.append({'timestamp': row['timestamp'], 'signal': 'RANGE', 'spx': spx, 'zero': zero})

signals_df = pd.DataFrame(signals)
```

### Step 4: Simulate Trades
```python
# Example: Buy when signal = MOMENTUM, sell when signal = RANGE
positions = []
entry_price = None

for idx, row in signals_df.iterrows():
    if row['signal'] == 'MOMENTUM' and entry_price is None:
        # Enter long
        entry_price = row['spx']
        entry_time = row['timestamp']
    elif row['signal'] == 'RANGE' and entry_price is not None:
        # Exit long
        exit_price = row['spx']
        exit_time = row['timestamp']
        pnl = exit_price - entry_price
        positions.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl
        })
        entry_price = None

trades_df = pd.DataFrame(positions)
print(f"Total trades: {len(trades_df)}")
print(f"Win rate: {(trades_df['pnl'] > 0).mean():.1%}")
print(f"Total PnL: {trades_df['pnl'].sum():.2f} points")
```

---

## Next Steps

### Immediate (This Week):
1. ✅ Run `python scripts/generate_signals.py` to see current signals
2. ✅ Open `docs/gexter.ipynb` and explore visualizations
3. ✅ Review `docs/TRADING_SIGNALS_GUIDE.md` for signal interpretation
4. ✅ Check `output/trading_signals.json` for programmatic access

### Short-term (Next 2 Weeks):
1. Extract 1 month of historical data from your PostgreSQL database
2. Backtest Strategy #1 (GEX Regime Trading)
3. Calculate performance metrics (Sharpe, max drawdown, win rate)
4. Paper trade signals in real-time to validate

### Medium-term (Next Month):
1. Build automated backtesting framework
2. Test all 5 strategy concepts
3. Optimize parameters (EMA periods, GEX thresholds)
4. Add risk management rules (position sizing, stops)
5. Create alert system for high-conviction signals

### Long-term (Ongoing):
1. Machine learning on historical signals
2. Multi-asset expansion (SPY, QQQ, IWM)
3. Real-time alert webhooks
4. Automated execution (if desired)

---

## Key Resources

### Documentation:
- [TRADING_SIGNALS_GUIDE.md](docs/TRADING_SIGNALS_GUIDE.md) - Signal interpretation
- [MARKET_INTERNALS_GUIDE.md](docs/MARKET_INTERNALS_GUIDE.md) - Breadth analysis
- [README_greek_differences.md](docs/README_greek_differences.md) - Greek tracking
- [SPX_TRACKING_IMPLEMENTATION.md](docs/SPX_TRACKING_IMPLEMENTATION.md) - Price data

### Analysis Tools:
- `scripts/generate_signals.py` - Main signal generator
- `scripts/generate_0dte_signals.py` - 0DTE analysis
- `scripts/generate_combined_signals.py` - Multi-factor signals
- `docs/gexter.ipynb` - Jupyter notebook
- `docs/SPX_TRACKING_QUERIES.sql` - Example SQL queries

### Data Access:
- PostgreSQL: `localhost:5432` (via SSH tunnel) or `droplet_ip:5432` (direct)
- pgAdmin: http://your_droplet_ip:5050
- CSV exports: `output/*.csv` (auto-generated)

---

## Important Reminders

### Risk Warnings:
- **Backtest before live trading**: Past performance ≠ future results
- **Position sizing**: Never risk more than 1-2% per trade
- **Stop losses**: Always use stops, especially in volatile regimes
- **News events**: GEX signals don't account for FOMC, earnings, geopolitical events

### GEX Limitations:
- Only captures dealer hedging, not actual directional flow
- Assumes dealers are delta-neutral (may not always be true)
- 0DTE effects are strongest near expiration (last 2 hours)
- Low liquidity can break GEX relationships

### Best Practices:
- Combine GEX with market internals (breadth, volume)
- Use multiple timeframes (don't rely on single signal)
- Trade with the trend (EMA alignment)
- Size smaller in high-volatility regimes (below zero GEX)

---

## Questions to Explore

As you analyze your data, consider:

1. **What's the win rate of trades taken only when ALL signals align?**
2. **How accurate is zero GEX as a support/resistance level?**
3. **Do GEX changes predict SPX moves over the next 30/60/120 minutes?**
4. **What's the optimal EMA period for your trading timeframe?**
5. **How do signals perform during different VIX regimes?**
6. **Are there specific times of day when signals work best?**
7. **What's the ideal stop loss distance from put/call walls?**
8. **How long do GEX levels remain relevant (1 hour? 1 day?)?**

Your data can answer all of these questions!

---

## Get Started Now

```bash
# 1. Generate your first signals
python scripts/generate_signals.py

# 2. Open the analysis notebook
jupyter notebook docs/gexter.ipynb

# 3. Review the signals guide
cat docs/TRADING_SIGNALS_GUIDE.md

# 4. Check what data you have
ssh root@your_droplet_ip
docker exec -it gex_postgres psql -U gexuser -d gexdb -c "SELECT COUNT(*), MIN(\"greeks.updated_at\"), MAX(\"greeks.updated_at\") FROM gex_table;"
```

Happy trading! 🚀
