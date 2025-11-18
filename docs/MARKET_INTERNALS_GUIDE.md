# Market Internals Trading Signals Guide

## Overview

The Market Internals module analyzes breadth, volume, and momentum indicators to generate trading signals based on overall market health and participation.

## Key Concepts

### 1. Market Breadth

**What it measures:** The number of stocks participating in a market move

**Metrics:**
- **Advance/Decline Ratio**: Ratio of advancing stocks to declining stocks
- **Breadth Ratio**: Normalized ratio from -1 (all declining) to +1 (all advancing)
- **Cumulative A/D Line**: Running total of net advances/declines

**Trading Rules:**
- **Breadth > 70%**: Strong bullish signal - broad market participation
- **Breadth > 60%**: Bullish signal - good participation
- **Breadth 40-60%**: Neutral - mixed market
- **Breadth < 40%**: Bearish signal - weak participation
- **Breadth < 30%**: Strong bearish signal - very weak participation

**Why it matters:**
- Healthy rallies require broad participation
- Narrow rallies (few stocks advancing) are fragile
- Strong breadth confirms trend strength
- Divergences warn of reversals

### 2. Up Volume / Down Volume

**What it measures:** Distribution of trading volume between advancing and declining stocks

**Metrics:**
- **Up/Down Volume Ratio**: Ratio of volume in advancing vs declining stocks
- **Volume Ratio**: Normalized from -1 (all volume in declining) to +1 (all volume in advancing)

**Trading Rules:**
- **Up Volume > 80%**: Strong buying pressure
- **Up Volume > 65%**: Good buying pressure
- **Up Volume 45-55%**: Balanced
- **Down Volume > 65%**: Strong selling pressure
- **Down Volume > 80%**: Overwhelming selling pressure

**Why it matters:**
- Volume confirms price action
- High up-volume validates bullish moves
- High down-volume confirms bearish moves
- Volume-price divergences signal weakness

### 3. NYSE TICK (if available)

**What it measures:** Net number of stocks upticking vs downticking

**Typical Range:** -2000 to +2000

**Trading Rules:**
- **TICK > +1000**: Extreme bullish momentum
- **TICK > +600**: Strong bullish momentum
- **TICK +200 to +600**: Moderate bullish
- **TICK -200 to +200**: Neutral
- **TICK < -600**: Strong bearish momentum
- **TICK < -1000**: Extreme bearish momentum

**Why it matters:**
- Shows real-time market momentum
- Extremes often mark short-term reversals
- Sustained direction indicates strong trend

### 4. NYSE TRIN (Arms Index)

**What it measures:** (Advances/Declines) / (Up Volume/Down Volume)

**Interpretation:**
- **TRIN < 0.50**: Very low selling pressure (bullish)
- **TRIN < 0.80**: Low selling pressure (bullish)
- **TRIN 0.80-1.20**: Balanced
- **TRIN > 2.00**: High selling pressure (bearish)
- **TRIN > 3.00**: Extreme selling pressure (very bearish)

**Why it matters:**
- Measures quality of advance/decline
- Low TRIN = strong buying, weak selling
- High TRIN = weak buying, strong selling

## Signal Generation

The module generates signals from multiple sources and combines them into a composite signal:

### Individual Signals

1. **Breadth Analysis** (35% weight)
   - Analyzes advance/decline metrics
   - Generates STRONG_BUY, BUY, NEUTRAL, SELL, or STRONG_SELL

2. **Volume Analysis** (30% weight)
   - Analyzes up/down volume distribution
   - Confirms or contradicts price action

3. **TICK Analysis** (20% weight, if available)
   - Analyzes short-term momentum
   - Best for intraday trading

4. **TRIN Analysis** (15% weight, if available)
   - Analyzes buying/selling pressure quality
   - Validates trend sustainability

### Composite Signal

Signals are weighted and combined into a composite score from -1 to +1:

- **Score > 0.6**: STRONG_BUY - High conviction bullish
- **Score > 0.2**: BUY - Moderate bullish bias
- **Score -0.2 to 0.2**: NEUTRAL - No clear direction
- **Score < -0.2**: SELL - Moderate bearish bias
- **Score < -0.6**: STRONG_SELL - High conviction bearish

## Usage

### Collect Current Market Internals

```bash
# Use default watchlist (150 stocks)
python scripts/collect_market_internals.py

# Use custom watchlist
python scripts/collect_market_internals.py --watchlist my_stocks.txt

# Save signals to JSON
python scripts/collect_market_internals.py --output output/internals.json

# Don't save to database (analysis only)
python scripts/collect_market_internals.py --no-save
```

### Create Custom Watchlist

Create a text file with one symbol per line:

```
# my_stocks.txt
AAPL
MSFT
GOOGL
AMZN
...
```

### Query Historical Internals

```sql
-- Latest market internals
SELECT * FROM market_internals
ORDER BY timestamp DESC
LIMIT 1;

-- Breadth over last trading day
SELECT
    timestamp,
    advances,
    declines,
    breadth_ratio,
    volume_ratio
FROM market_internals
WHERE timestamp >= CURRENT_DATE
ORDER BY timestamp;

-- Strong breadth days (>60% advancing)
SELECT
    DATE(timestamp) as date,
    AVG(breadth_ratio) as avg_breadth,
    AVG(volume_ratio) as avg_volume_ratio
FROM market_internals
WHERE breadth_ratio > 0.60
GROUP BY DATE(timestamp)
ORDER BY date DESC;

-- Cumulative A/D Line trend
SELECT
    timestamp,
    cumulative_ad_line,
    breadth_ratio
FROM market_internals
ORDER BY timestamp DESC
LIMIT 100;
```

## Trading Strategies

### Strategy 1: Breadth Thrust

**Setup:**
- Breadth ratio increases from <0.40 to >0.615 within 10 days
- High volume confirming the move

**Signal:**
- Strong BUY signal
- Indicates powerful momentum shift
- Often marks start of new bull leg

**Entry:**
- Buy when breadth > 0.615 is confirmed
- Use pullbacks for better risk/reward

**Exit:**
- When breadth falls back below 0.50
- Or target is hit

### Strategy 2: Breadth Divergence

**Setup:**
- SPX making new highs but breadth declining
- Advance/Decline line not confirming new highs

**Signal:**
- Warning of potential reversal
- Narrow market leadership

**Action:**
- Reduce long exposure
- Tighten stops
- Wait for breadth to confirm or reject the move

### Strategy 3: Capitulation Detection

**Setup:**
- Breadth < -0.70 (>70% declining)
- Down volume > 80%
- TICK < -1000

**Signal:**
- Possible capitulation/washout
- Potential reversal setup

**Action:**
- Watch for reversal candles
- Look for breadth improvement
- Consider scaled entry on recovery

### Strategy 4: Confirmation Trading

**Setup:**
- Breadth > 0.60 (advancing)
- Volume ratio > 0.65 (up volume)
- TICK > +600

**Signal:**
- Strong trending environment
- High probability trend continuation

**Action:**
- Add to positions in direction of trend
- Use pullbacks to enter
- Trail stops

## Integration with GEX Signals

### Combining Internals with GEX

1. **Strong Bullish Setup:**
   - Breadth > 60% (broad participation)
   - Up volume > 65% (strong buying)
   - Price above Zero GEX (positive gamma)
   - **Action:** Aggressive long positioning

2. **Strong Bearish Setup:**
   - Breadth < 40% (weak participation)
   - Down volume > 65% (strong selling)
   - Price below Zero GEX (negative gamma)
   - **Action:** Reduce longs, consider hedges

3. **Divergence Warning:**
   - SPX rallying above resistance
   - Breadth deteriorating
   - GEX showing call wall resistance
   - **Action:** Take profits, avoid chasing

4. **Capitulation Buy:**
   - Extreme negative breadth (<-70%)
   - Price at strong put wall support
   - Volume showing exhaustion
   - **Action:** Scaled entry for reversal

## Example Output

```
================================================================================
MARKET INTERNALS SUMMARY
================================================================================
Timestamp: 2025-11-18 09:45:00
Universe: 150 stocks

Breadth:
  Advancing: 108
  Declining: 38
  Unchanged: 4
  Ratio: +46.67% (2.84:1)

Volume:
  Up Volume: 125,430,000
  Down Volume: 45,220,000
  Ratio: +47.01% (2.77:1)

Market Indices:
  TICK: +645.00
  TRIN: 0.68

================================================================================
COMPOSITE SIGNAL
================================================================================
Signal: BUY
Score: +0.52 (range: -1 to +1)
Confidence: 72%

================================================================================
RECOMMENDATION
================================================================================
Moderately bullish internals support upside bias. Strong breadth (70%+
advancing) and positive volume flow confirm broad participation. Look
for pullback entries on strong stocks. TICK showing good momentum.
```

## Best Practices

1. **Use During Market Hours:**
   - Internals are most meaningful during active trading
   - After-hours data may show neutral readings

2. **Combine Multiple Signals:**
   - Don't rely on breadth alone
   - Look for confirmation across breadth, volume, and GEX

3. **Watch for Divergences:**
   - Price vs breadth divergences are powerful
   - Cumulative A/D line vs price index

4. **Consider Market Phase:**
   - Bull markets: Look for breadth >50% to stay long
   - Bear markets: Look for breadth <50% to stay defensive
   - Transitions: Watch for persistent breadth shifts

5. **Timeframe Matters:**
   - Intraday: Use TICK for momentum
   - Daily: Use breadth and volume
   - Weekly: Use cumulative A/D line trend

## Limitations

1. **After-Hours Data:**
   - Less meaningful when markets are closed
   - Wait for market open for actionable signals

2. **Tradier API Limitations:**
   - May not provide direct access to $TICK, $TRIN
   - Module calculates from stock universe instead

3. **Sample Size:**
   - Larger universes (S&P 500) are more representative
   - Small watchlists may not capture full market

4. **Data Quality:**
   - Depends on real-time quote accuracy
   - Volume data may lag

## Future Enhancements

- Integration with additional data sources for official breadth indices
- Automatic watchlist updates (S&P 500 constituents)
- Sector-specific breadth analysis
- Breadth momentum indicators
- Alert system for extreme readings
- Historical breadth pattern recognition

## Support

For questions or issues with the market internals module, refer to:
- Main README.md for system setup
- This guide for strategy implementation
- Database schema in `scripts/create_market_internals_table.sql`
