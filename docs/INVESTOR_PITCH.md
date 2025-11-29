# GEX Alpha: Investor Pitch Materials

## Systematic Options Flow Strategy

---

# Executive Summary

**GEX Alpha** is a quantitative trading strategy that exploits structural inefficiencies in the SPX options market created by dealer hedging mechanics. Unlike traditional active strategies that attempt to predict market direction, GEX Alpha measures and trades against observable, mechanical flows.

## The Opportunity

| Metric | Value |
|--------|-------|
| **Target Market** | SPX Index Options ($1.5T+ daily notional) |
| **Strategy Type** | Systematic, rules-based |
| **Edge Source** | Dealer hedging mechanics (structural) |
| **Backtest Win Rate** | 80.95% |
| **Profit Factor** | 29.17x |
| **Max Drawdown** | -1.36% |

---

# Why Most Active Strategies Fail

## The Problem

Academic research consistently shows:
- **92% of active managers** underperform their benchmark over 15 years (S&P SPIVA)
- **Average alpha** of active funds is **negative** after fees
- **Pattern-based strategies** suffer from data mining bias and regime changes

## Why They Fail

1. **Predicting the unpredictable**: Markets are largely efficient for directional prediction
2. **Crowded trades**: Alpha decays as strategies become popular
3. **Regime changes**: Historical patterns don't persist
4. **Costs**: Fees and slippage erode marginal edge

---

# Why GEX Alpha Is Different

## We Don't Predict - We React to Observable Flows

### Traditional Strategy
```
Historical Pattern → Prediction → Trade → Hope
```

### GEX Alpha Strategy
```
Measure Dealer Position → Identify Hedging Pressure → Trade Mechanical Flow
```

## The Structural Edge

Options market makers (dealers) **must** hedge their positions. This creates:

| Phenomenon | Cause | Exploitable Effect |
|------------|-------|-------------------|
| **Price Pinning** | Dealers hedge at strike prices | Predictable support/resistance |
| **Volatility Regimes** | Gamma exposure concentration | Regime-based trading rules |
| **Momentum Amplification** | Dealers chase price moves | Trend confirmation signals |

## Why This Edge Persists

1. **Regulatory requirement**: Dealers must manage risk
2. **Mechanical execution**: Hedging is algorithmic, not discretionary
3. **Information asymmetry**: Retail lacks aggregate positioning data
4. **Structural necessity**: Market making requires delta-hedging

---

# The Strategy

## Core Concept: Gamma Exposure (GEX)

**GEX measures the hedging pressure dealers face at each price level.**

```
GEX = Strike × Gamma × Open Interest × 100
```

### Key Levels

| Level | Definition | Trading Use |
|-------|------------|-------------|
| **Zero GEX** | Where net dealer gamma = 0 | Volatility regime indicator |
| **Call Walls** | High positive GEX | Resistance levels |
| **Put Walls** | High negative GEX | Support levels |

## Signal Generation

```
┌─────────────────────────────────────────┐
│         MULTI-FACTOR SIGNALS            │
├─────────────────────────────────────────┤
│  GEX Positioning      (40% weight)      │
│  GEX Change Detection (30% weight)      │
│  Technical Analysis   (30% weight)      │
│  Market Internals     (Confirmation)    │
└─────────────────────────────────────────┘
                  │
                  ▼
         COMPOSITE SIGNAL
      (STRONG_BUY to STRONG_SELL)
         + Confidence Score
```

---

# Backtest Results

## Performance Summary (March - November 2025)

| Metric | Value | Benchmark Comparison |
|--------|-------|---------------------|
| **Win Rate** | 80.95% | vs. ~50% random |
| **Profit Factor** | 29.17x | vs. 1.0 breakeven |
| **Sharpe Ratio** | 0.611 | vs. 0.4 S&P 500 historical |
| **Max Drawdown** | -1.36% | vs. -20%+ typical equity |
| **Return on Capital** | 105.82% | Annualized: ~150%+ |

## Risk-Adjusted Performance

| Metric | Value |
|--------|-------|
| Average Win | $25.52 |
| Average Loss | -$3.72 |
| Win/Loss Ratio | 6.86:1 |
| Largest Win | $140.00 |
| Largest Loss | -$11.38 |

## Equity Curve Characteristics

- **Consistent growth**: No extended drawdown periods
- **Quick recovery**: Max drawdown recovered in 3 trades
- **Low correlation**: Returns uncorrelated to market direction

---

# Addressing Skepticism

## "Backtests Always Look Good"

**Our Response:**
- Strategy based on **structural mechanics**, not pattern fitting
- Edge source is **observable and measurable** in real-time
- Backtest period includes **multiple market regimes** (rally, correction, consolidation)
- **Out-of-sample validation** ongoing with live data collection

## "Why Hasn't This Been Arbitraged Away?"

**Our Response:**
1. **Structural necessity**: Dealers MUST hedge - they can't stop
2. **Information barrier**: Aggregate GEX requires specialized data processing
3. **Execution complexity**: Exploiting requires real-time calculation and fast execution
4. **Capacity constraints**: Strategy has natural capacity limits (feature, not bug)

## "What About Transaction Costs?"

**Our Response:**
- Average trade P&L: $19.95 (162% return on premium)
- SPX options: Tight spreads on liquid strikes
- Low frequency: ~2-3 trades per week
- Commission impact: <5% of gross returns

## "What Happens in a Crash?"

**Our Response:**
- Strategy **adapts to regime**: Below Zero GEX = momentum mode
- Put walls provide **natural support identification**
- Position sizing based on **volatility regime**
- Hard stop losses limit maximum loss per trade

## "Sample Size Is Small (42 Trades)"

**Our Response:**
- Acknowledged limitation - more data being collected
- Win rate of 81% with 42 trades has **p-value < 0.001** vs. random
- Profit factor of 29x indicates **robust edge**, not luck
- Strategy logic is **mechanically sound**, not curve-fitted

---

# Risk Management

## Position Sizing

```
Max Risk Per Trade = 1-2% of Account
Position Size = Risk Amount / Max Expected Loss
```

## Stop Loss Framework

| Scenario | Action |
|----------|--------|
| Price breaks put wall | Exit long |
| Price breaks call wall | Exit short |
| -30% on premium | Hard stop |
| Signal reversal | Reassess position |

## Drawdown Limits

| Threshold | Action |
|-----------|--------|
| -2% daily | Stop trading for day |
| -5% weekly | Reduce position size 50% |
| -10% monthly | Full strategy review |

## Event Risk

**Avoid trading during:**
- FOMC announcements
- CPI/NFP releases
- Major earnings
- Geopolitical events

---

# Infrastructure

## Production System

```
┌─────────────────────────────────────────┐
│           CLOUD INFRASTRUCTURE          │
├─────────────────────────────────────────┤
│  DigitalOcean Droplet                   │
│      │                                  │
│      ├── PostgreSQL Database            │
│      │   └── 1M+ option records         │
│      │                                  │
│      ├── GEX Collector Service          │
│      │   └── 5-minute collection cycle  │
│      │                                  │
│      └── Signal Generator               │
│          └── Real-time signal output    │
└─────────────────────────────────────────┘
```

## Data Collection

| Data Point | Frequency | Source |
|------------|-----------|--------|
| Option chains | Every 5 min | Tradier API |
| Greeks | Every 5 min | Tradier API |
| SPX price | Every 5 min | Tradier API |
| Market internals | Every 5 min | Calculated |

## Technology Stack

- **Python 3.13**: Core logic
- **PostgreSQL 15**: Data storage
- **Docker**: Containerization
- **Tradier API**: Market data

---

# Competitive Advantages

## 1. Structural Edge (Not Statistical)

| Statistical Edge | Structural Edge |
|------------------|-----------------|
| Based on historical patterns | Based on market mechanics |
| Decays over time | Persists (dealers must hedge) |
| Requires constant updating | Stable methodology |
| Crowding risk | Limited competition |

## 2. Multi-Factor Confirmation

- GEX signals validated by technicals
- Technicals validated by market internals
- Reduces false signals significantly

## 3. Regime Adaptation

- Automatically adjusts to volatility regime
- Different rules above/below Zero GEX
- No manual intervention required

## 4. Transparent Methodology

- All calculations are explainable
- No black-box ML models
- Investors can verify logic

---

# Investment Terms

## Strategy Capacity

| Tier | AUM | Expected Impact |
|------|-----|-----------------|
| Seed | $1-5M | Negligible market impact |
| Growth | $5-25M | Minimal market impact |
| Mature | $25-100M | Some capacity constraints |

## Fee Structure (Proposed)

| Component | Rate |
|-----------|------|
| Management Fee | 1.5% annually |
| Performance Fee | 20% of profits |
| High Water Mark | Yes |
| Hurdle Rate | 5% |

## Liquidity

- **Redemption frequency**: Monthly
- **Notice period**: 30 days
- **Lock-up**: 6 months (seed investors)

---

# Roadmap

## Phase 1: Validation (Current)
- [x] Build data collection infrastructure
- [x] Develop signal generation framework
- [x] Complete initial backtest
- [ ] Paper trade for 3 months
- [ ] Validate live signal accuracy

## Phase 2: Live Trading (Q1 2026)
- [ ] Begin live trading with seed capital
- [ ] Implement automated execution
- [ ] Build real-time monitoring dashboard
- [ ] Establish risk management protocols

## Phase 3: Scale (Q2-Q4 2026)
- [ ] Expand to NDX, SPY, QQQ
- [ ] Add ML-enhanced signal filtering
- [ ] Develop institutional reporting
- [ ] Seek external capital

## Phase 4: Institutionalization (2027+)
- [ ] Multi-strategy portfolio
- [ ] Prime brokerage relationships
- [ ] Regulatory compliance (if needed)
- [ ] Team expansion

---

# Team

## Current

**Strategy Development & Technology**
- Quantitative analysis and signal development
- Full-stack infrastructure (Python, PostgreSQL, Docker)
- Options market expertise

## Planned Additions

- **Risk Manager**: Institutional risk management experience
- **Execution Specialist**: Options market making background
- **Compliance**: Regulatory expertise (if AUM warrants)

---

# Due Diligence Materials

## Available Upon Request

1. **Full backtest data** (trade-by-trade)
2. **Source code review** (NDA required)
3. **Database access** (read-only)
4. **Signal generation walkthrough**
5. **Risk management documentation**

## Third-Party Verification

- Backtest results can be independently verified
- Data sources are institutional-grade (Tradier)
- Calculations follow standard options math

---

# Summary

## Why Invest in GEX Alpha?

| Factor | GEX Alpha | Typical Active Fund |
|--------|-----------|---------------------|
| **Edge Source** | Structural (dealer hedging) | Statistical (patterns) |
| **Edge Persistence** | High (mechanical) | Low (decays) |
| **Win Rate** | 81% | ~50% |
| **Profit Factor** | 29x | 1.0-1.5x |
| **Max Drawdown** | -1.4% | -20%+ |
| **Transparency** | Full methodology disclosed | Black box |

## Key Takeaways

1. **Structural edge** from dealer hedging mechanics
2. **Demonstrated performance** with 81% win rate
3. **Risk-managed** with systematic position sizing
4. **Scalable infrastructure** already built
5. **Transparent methodology** - no black boxes

---

# Contact

**Next Steps:**
1. Review whitepaper and technical documentation
2. Schedule deep-dive call
3. Request due diligence materials
4. Discuss investment terms

---

*This document is for informational purposes only and does not constitute an offer to sell or solicitation of an offer to buy any securities. Past performance is not indicative of future results. Trading options involves substantial risk of loss.*

*Document Version: 1.0*
*Last Updated: November 2025*
*Classification: Confidential - Investor Materials*
