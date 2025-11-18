# Trading Signals Guide

Comprehensive guide to the GEX-based trading signal system.

## Overview

The trading signal system generates actionable buy/sell signals based on:

1. **Gamma Exposure (GEX)** - Dealer/market-maker positioning
2. **Technical Analysis** - EMAs using Fibonacci sequence (8, 21, 55)
3. **Multi-timeframe Analysis** - Intraday changes and trends
4. **Support/Resistance** - Derived from GEX concentration levels

## Signal Types

### Signal Strength
- **STRONG_BUY**: High-confidence bullish signal
- **BUY**: Bullish bias, consider long positions
- **NEUTRAL**: No clear directional bias
- **SELL**: Bearish bias, consider short positions
- **STRONG_SELL**: High-confidence bearish signal

### Signal Sources

#### 1. GEX Positioning
Analyzes dealer positioning relative to spot price.

**Key Concepts:**
- **Zero GEX Level**: Where net GEX crosses zero
  - **Below Zero GEX**: Market is volatile, dealers are long gamma (momentum regime)
  - **Above Zero GEX**: Market is pinned, dealers are short gamma (range-bound)

- **Net GEX at Spot**:
  - **Positive GEX**: Call resistance, ceiling effect
  - **Negative GEX**: Put support, floor effect

**Trading Rules:**
```
IF price < zero_gex AND net_gex < 0:
    → BUY (Put support + volatile regime)

IF price < zero_gex AND net_gex > 0:
    → SELL (Call resistance in volatile regime)

IF price > zero_gex:
    → NEUTRAL (Range-bound, expect pinning)
```

#### 2. GEX Change Signals
Tracks intraday changes in GEX (dealer repositioning).

**Interpretation:**
- **Increasing GEX** (+): More call buying or put selling → Bullish
- **Decreasing GEX** (-): More put buying or call selling → Bearish
- **Change > 10%**: High conviction signal
- **Change < 5%**: Noise, ignore

#### 3. EMA Positioning
Classical technical analysis using Fibonacci EMAs.

**Signals:**
- **Price > EMA8 > EMA21**: Strong uptrend → BUY
- **Price < EMA8 < EMA21**: Strong downtrend → SELL
- **EMA8 crosses above EMA21**: Bullish crossover → STRONG_BUY
- **EMA8 crosses below EMA21**: Bearish crossover → STRONG_SELL
- **Price between EMAs**: Consolidation → NEUTRAL

## Running the Signal Generator

### From Docker
```bash
# Run signal generator inside Docker container
docker exec gex_collector python /app/scripts/generate_signals.py
```

### From Host Machine
```bash
# Requires Python environment with dependencies
python scripts/generate_signals.py
```

### Output
Signals are displayed in the terminal and saved to:
- **JSON**: `output/trading_signals.json`

## Example Output

```
================================================================================
SPX TRADING SIGNALS GENERATOR
================================================================================
Generated at: 2025-11-18 14:30:00

================================================================================
📊 MARKET OVERVIEW
================================================================================
Timestamp: 2025-11-18 14:28:45
SPX Price: 5985.42
Zero GEX Level: 5950.00
Net GEX at Price: -1,234,567

================================================================================
🎯 KEY LEVELS
================================================================================
Resistance (Call Walls):
  • 6000
  • 6050
  • 6100

Support (Put Walls):
  • 5950
  • 5900
  • 5850

================================================================================
📡 INDIVIDUAL SIGNALS
================================================================================

🟢 GEX_POSITIONING
   Signal: BUY
   Confidence: 70%
   Below zero GEX (5950), negative GEX at spot = put support.
   Expect volatile moves with momentum.

🟢 GEX_CHANGE
   Signal: BUY
   Confidence: 65%
   GEX increased 12.3% - bullish repositioning detected

🟢 EMA_POSITIONING
   Signal: BUY
   Confidence: 75%
   Strong uptrend: Price (5985.42) > EMA8 (5978.20) > EMA21 (5965.10)

================================================================================
🎲 COMPOSITE SIGNAL
================================================================================
Signal: BUY
Confidence: 70%

================================================================================
💡 RECOMMENDATION
================================================================================
🟢 BUY signal (Confidence: 70%)
Bullish bias. Consider long positions on pullbacks.

Current SPX: 5985.42
Zero GEX: 5950.00 (SPX is above)
Resistance levels: 6000, 6050, 6100
Support levels: 5950, 5900, 5850
```

## Key GEX Levels Explained

### Zero GEX Level
The strike where net GEX = 0 (calls cancel puts).

**Significance:**
- Acts as a volatility regime indicator
- Below = High volatility, strong momentum moves
- Above = Low volatility, range-bound trading

**Trading Application:**
- Use as a dynamic support/resistance level
- Adjust position sizing based on distance from zero GEX
- Expect breakouts when price crosses zero GEX with volume

### Call Walls (Resistance)
Strikes with large positive GEX (heavy call open interest).

**Why it matters:**
- Dealers are short calls → must sell stock as price rises (negative gamma)
- Creates resistance, price tends to stall below these levels
- Breaking through a call wall = strong bullish signal

### Put Walls (Support)
Strikes with large negative GEX (heavy put open interest).

**Why it matters:**
- Dealers are short puts → must buy stock as price falls (negative gamma)
- Creates support, price tends to bounce above these levels
- Breaking through a put wall = strong bearish signal

## Integration with Trading Strategy

### 1. Entry Signals
**Long Entry:**
- Composite signal = BUY or STRONG_BUY
- Price > EMA8 > EMA21 (or recent bullish crossover)
- Below zero GEX with negative net GEX at spot
- Above key put wall support

**Short Entry:**
- Composite signal = SELL or STRONG_SELL
- Price < EMA8 < EMA21 (or recent bearish crossover)
- Below key call wall resistance
- Large GEX decrease (>10%)

### 2. Exit Signals
**Exit Longs:**
- Composite signal shifts to SELL/STRONG_SELL
- Price approaches call wall resistance
- EMA8 crosses below EMA21
- Large GEX decrease

**Exit Shorts:**
- Composite signal shifts to BUY/STRONG_BUY
- Price approaches put wall support
- EMA8 crosses above EMA21
- Large GEX increase

### 3. Position Sizing
Adjust size based on:
- **Signal Confidence**: Higher confidence = larger position
- **Distance from Zero GEX**: Closer = more volatile = smaller size
- **Multiple Signals Agreeing**: All bullish = higher conviction

### 4. Risk Management
**Stop Losses:**
- Place stops below put walls for longs
- Place stops above call walls for shorts
- Tighten stops when approaching zero GEX (volatility risk)

**Profit Targets:**
- First target: Next GEX level (call wall for longs, put wall for shorts)
- Second target: Following GEX level
- Trail stops when in profit and EMAs remain favorable

## SQL Queries for Manual Analysis

### Find Current Zero GEX Level
```sql
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
SELECT
    strike,
    net_gex,
    prev_net_gex
FROM net_gex
WHERE SIGN(net_gex) != SIGN(prev_net_gex)
ORDER BY ABS(net_gex);
```

### Find Strongest Call/Put Walls
```sql
WITH latest_time AS (
    SELECT MAX("greeks.updated_at") as ts FROM gex_table
),
latest_price AS (
    SELECT AVG(spx_price) as price
    FROM gex_table
    WHERE "greeks.updated_at" = (SELECT ts FROM latest_time)
)
SELECT
    strike,
    SUM(gex) as net_gex,
    SUM(CASE WHEN option_type = 'call' THEN gex ELSE 0 END) as call_gex,
    SUM(CASE WHEN option_type = 'put' THEN gex ELSE 0 END) as put_gex,
    CASE
        WHEN strike > (SELECT price FROM latest_price) THEN 'Resistance'
        ELSE 'Support'
    END as level_type
FROM gex_table
WHERE "greeks.updated_at" = (SELECT ts FROM latest_time)
GROUP BY strike
ORDER BY ABS(SUM(gex)) DESC
LIMIT 10;
```

### Analyze GEX Changes (Dealer Repositioning)
```sql
WITH time_series AS (
    SELECT DISTINCT "greeks.updated_at" as ts
    FROM gex_table
    ORDER BY "greeks.updated_at" DESC
    LIMIT 5
),
gex_by_time AS (
    SELECT
        "greeks.updated_at",
        strike,
        SUM(gex) as net_gex
    FROM gex_table
    WHERE "greeks.updated_at" IN (SELECT ts FROM time_series)
    GROUP BY "greeks.updated_at", strike
)
SELECT
    strike,
    MAX(CASE WHEN "greeks.updated_at" = (SELECT MAX(ts) FROM time_series) THEN net_gex END) as current_gex,
    MAX(CASE WHEN "greeks.updated_at" = (SELECT MIN(ts) FROM time_series) THEN net_gex END) as previous_gex,
    MAX(CASE WHEN "greeks.updated_at" = (SELECT MAX(ts) FROM time_series) THEN net_gex END) -
    MAX(CASE WHEN "greeks.updated_at" = (SELECT MIN(ts) FROM time_series) THEN net_gex END) as gex_change
FROM gex_by_time
GROUP BY strike
HAVING ABS(
    MAX(CASE WHEN "greeks.updated_at" = (SELECT MAX(ts) FROM time_series) THEN net_gex END) -
    MAX(CASE WHEN "greeks.updated_at" = (SELECT MIN(ts) FROM time_series) THEN net_gex END)
) > 1000000
ORDER BY ABS(gex_change) DESC
LIMIT 20;
```

### EMA Analysis with Current Price
```sql
SELECT
    timestamp,
    spx_price,
    ema_8,
    ema_21,
    ema_55,
    price_vs_ema8_pct,
    price_vs_ema21_pct,
    ema_signal,
    CASE
        WHEN spx_price > ema_8 AND ema_8 > ema_21 THEN 'Strong Uptrend'
        WHEN spx_price < ema_8 AND ema_8 < ema_21 THEN 'Strong Downtrend'
        WHEN spx_price > ema_21 AND spx_price < ema_8 THEN 'Consolidation (Bullish)'
        WHEN spx_price < ema_21 AND spx_price > ema_8 THEN 'Consolidation (Bearish)'
        ELSE 'Mixed'
    END as trend_state
FROM spx_indicators
ORDER BY timestamp DESC
LIMIT 10;
```

## Advanced: 0DTE Strategy

For same-day expiration (0DTE) options:

1. **High GEX Concentration**: Look for strikes with massive GEX
2. **Pinning Effect**: Price tends to gravitate toward max GEX strikes
3. **Time Decay**: Accelerates rapidly in final hours
4. **Volatility**: Spikes near key GEX levels

**0DTE Rules:**
- Trade in direction of EMA trend
- Use GEX levels as profit targets
- Exit before 3:50 PM ET (gamma risk increases)
- Avoid holding through major news events

## Backtesting Considerations

When backtesting these signals:

1. **Lookback Bias**: Ensure GEX data is point-in-time
2. **Execution**: Account for slippage and commissions
3. **Market Regime**: Bull vs. bear markets behave differently
4. **Volatility**: VIX level affects GEX effectiveness
5. **Expiration Proximity**: Signals stronger near 0DTE

## Limitations

**What the Signals DON'T Account For:**
- News events and catalysts
- Macroeconomic data releases
- Federal Reserve policy changes
- Geopolitical events
- Market liquidity/volume
- Broader market breadth and internals

**Always combine GEX signals with:**
- Fundamental analysis
- Economic calendar awareness
- Risk management discipline
- Position sizing rules

## Next Steps

1. **Add Market Internals**: Breadth, A/D line, volume analysis
2. **Multi-Timeframe**: Weekly/daily context for hourly signals
3. **VIX Integration**: Volatility regime filtering
4. **ML Enhancement**: Pattern recognition on historical signals
5. **Real-time Alerts**: Webhook/email notifications for signal changes

## Resources

- Gamma Exposure Explained: [SpotGamma](https://spotgamma.com/education/)
- EMA Trading: Fibonacci EMAs in trending markets
- Options Greeks: Delta, gamma, and dealer hedging mechanics
