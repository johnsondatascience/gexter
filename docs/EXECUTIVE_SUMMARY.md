# GEX Alpha Strategy - Executive Summary

## One-Page Overview for Decision Makers

---

## What We Do

**GEX Alpha** exploits structural inefficiencies in the SPX options market created by dealer hedging mechanics. We measure aggregate dealer positioning (Gamma Exposure) and trade against their predictable, mechanical hedging flows.

---

## The Edge in 30 Seconds

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│   Options dealers MUST hedge their positions.                  │
│   This hedging is MECHANICAL and PREDICTABLE.                  │
│   We MEASURE their positioning and TRADE accordingly.          │
│                                                                │
│   This is NOT prediction. This is REACTION to observable flow. │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Performance Snapshot

| Metric | Value | Context |
|--------|-------|---------|
| **Win Rate** | 80.95% | vs. 50% random |
| **Profit Factor** | 29.17x | vs. 1.0 breakeven |
| **Max Drawdown** | -1.36% | vs. -20%+ typical |
| **Sharpe Ratio** | 0.611 | vs. 0.4 S&P historical |
| **Sample Size** | 42 trades | March-Nov 2025 |

---

## Why This Works

### Traditional Active Trading (Fails)
- Tries to **predict** market direction
- Based on **historical patterns** that decay
- **Crowded** strategies lose edge
- **No structural reason** for persistence

### GEX Alpha (Works)
- **Reacts** to observable dealer positioning
- Based on **market mechanics** (dealers must hedge)
- **Information asymmetry** (retail lacks data)
- **Structural edge** that persists

---

## Key Concepts

### Gamma Exposure (GEX)
Measures hedging pressure dealers face at each price level.

### Zero GEX Level
The price where dealer gamma exposure flips sign.
- **Above**: Low volatility, mean-reversion
- **Below**: High volatility, momentum

### Call/Put Walls
Strikes with concentrated GEX act as support/resistance.

---

## Signal Framework

```
GEX Positioning (40%) ─┐
                       │
GEX Change (30%) ──────┼──► COMPOSITE SIGNAL ──► Trade Decision
                       │    (BUY/SELL/NEUTRAL)
Technical (30%) ───────┘    + Confidence Score
```

---

## Risk Management

| Control | Threshold |
|---------|-----------|
| Per-trade risk | 1-2% of account |
| Daily loss limit | -2% |
| Weekly loss limit | -5% |
| Position sizing | Based on signal confidence |

---

## Infrastructure (Built & Running)

- **Cloud**: DigitalOcean production deployment
- **Database**: PostgreSQL with 1M+ option records
- **Collection**: Every 5 minutes during market hours
- **Signals**: Real-time generation

---

## Investment Highlights

| Factor | Assessment |
|--------|------------|
| Edge Source | Structural (dealer mechanics) |
| Edge Persistence | High (dealers must hedge) |
| Scalability | $1-25M with minimal impact |
| Transparency | Full methodology disclosed |
| Validation | Backtest + ongoing live collection |

---

## What We Need

1. **Validation Period**: 3 months paper trading
2. **Seed Capital**: $1-5M for live trading
3. **Team Expansion**: Risk manager, execution specialist

---

## Documents Available

| Document | Purpose | Length |
|----------|---------|--------|
| **Strategy Whitepaper** | Full strategy explanation | 15 pages |
| **Investor Pitch** | Investment case | 10 pages |
| **Market Mechanics** | Technical deep-dive | 12 pages |
| **Backtest Results** | Trade-by-trade data | Spreadsheet |

---

## Bottom Line

> **We don't predict markets. We measure dealer positioning and trade against their mechanical hedging flows. This structural edge has delivered 81% win rate with 29x profit factor in backtesting.**

---

## Quick Reference: Key Levels

### What to Watch

| Level | Meaning | Action |
|-------|---------|--------|
| **Zero GEX** | Volatility regime boundary | Adapt strategy |
| **Call Walls** | Resistance (dealers sell) | Take profits |
| **Put Walls** | Support (dealers buy) | Buy dips |

### Signal Interpretation

| Signal | Meaning | Position |
|--------|---------|----------|
| **STRONG_BUY** | High conviction bullish | Full long |
| **BUY** | Moderate bullish | Partial long |
| **NEUTRAL** | No clear direction | Flat/reduce |
| **SELL** | Moderate bearish | Partial short |
| **STRONG_SELL** | High conviction bearish | Full short |

---

## Contact & Next Steps

1. Review full whitepaper
2. Schedule technical deep-dive call
3. Request backtest data access
4. Discuss investment terms

---

*Version 1.0 | November 2025 | Confidential*
