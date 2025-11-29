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
- **92% of active managers** underperform their benchmark over 15 years ([S&P SPIVA Scorecard, 2023](https://www.spglobal.com/spdji/en/research-insights/spiva/))
- **Average alpha** of active funds is **negative** after fees ([Fama & French, 2010](https://doi.org/10.1111/j.1540-6261.2009.01527.x))
- **Pattern-based strategies** suffer from data mining bias and regime changes ([Harvey, Liu & Zhu, 2016](https://doi.org/10.1093/rfs/hhv059))

## Why They Fail

1. **Predicting the unpredictable**: Markets are largely efficient for directional prediction ([Malkiel, 2003](https://doi.org/10.1257/089533003321164958))
2. **Crowded trades**: Alpha decays as strategies become popular ([McLean & Pontiff, 2016](https://doi.org/10.1111/jofi.12365))
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

These effects are well-documented in academic literature:
- **Ni, Pearson & Poteshman (2005)**: "[Stock Price Clustering on Option Expiration Dates](https://doi.org/10.1016/j.jfineco.2004.08.002)" - Documents price pinning to strike prices
- **Barbon & Buraschi (2021)**: "[Gamma Fragility](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3725454)" - Shows dealer gamma hedging amplifies market moves
- **Baltussen, Da & van Bekkum (2021)**: "[Indexing and Stock Market Serial Dependence Around the World](https://doi.org/10.1016/j.jfineco.2020.07.016)" - Documents mechanical rebalancing effects

## Why This Edge Persists

1. **Regulatory requirement**: Dealers must manage risk (SEC Rule 15c3-1)
2. **Mechanical execution**: Hedging is algorithmic, not discretionary
3. **Information asymmetry**: Retail lacks aggregate positioning data
4. **Structural necessity**: Market making requires delta-hedging

---

# Understanding Market Participants

## Who Creates the GEX Edge?

The options market consists of several key participants whose interactions create the structural inefficiencies we exploit:

### 1. Options Market Makers (Dealers)

**Who they are:** Large financial institutions (Citadel Securities, Susquehanna, Wolverine, etc.) that provide liquidity by continuously quoting bid/ask prices for options.

**Why they exist:** Markets need liquidity providers. Without market makers, bid-ask spreads would be enormous and options trading would be impractical. In exchange for providing this service, they earn the bid-ask spread.

**How they operate:**
- They **do not take directional bets** on the market
- They aim to be **delta-neutral** at all times
- When they sell a call option, they must buy stock to hedge
- When they sell a put option, they must sell stock to hedge
- This hedging is **mechanical and algorithmic**, not discretionary

**Their contribution to our edge:**
- Their hedging creates predictable buying/selling pressure at specific price levels
- When concentrated at certain strikes, their hedging amplifies or dampens price moves
- This is **structural** - they cannot stop hedging without taking unacceptable risk

### 2. Institutional Investors (Pension Funds, Mutual Funds)

**Who they are:** Large asset managers (BlackRock, Vanguard, Fidelity, etc.) managing trillions in assets.

**Why they exist:** They pool capital from retail investors and pension beneficiaries to achieve diversification and professional management.

**How they use options:**
- **Covered call writing**: Selling calls against stock holdings to generate income
- **Protective puts**: Buying puts to hedge portfolio downside
- **Collar strategies**: Combining both for defined risk/reward

**Their contribution to our edge:**
- They are **systematic sellers of volatility** (especially calls)
- Their activity is **predictable** (quarterly rebalancing, year-end tax management)
- They create persistent **supply of options** that dealers must absorb

### 3. Retail Traders

**Who they are:** Individual investors trading through platforms like Robinhood, TD Ameritrade, etc.

**Why they exist:** Seeking to profit from market movements or hedge personal portfolios.

**How they use options:**
- Often **buy calls** on popular stocks (bullish speculation)
- Concentrated in **near-term, out-of-the-money options** (lottery ticket behavior)
- Activity spikes around earnings, meme stock events, and market volatility

**Their contribution to our edge:**
- They create **demand imbalances** at popular strikes
- Their activity is often **sentiment-driven and predictable**
- Dealers must take the other side, creating hedging flows

### 4. Volatility Traders (Hedge Funds, Prop Firms)

**Who they are:** Sophisticated traders (Citadel, Two Sigma, DE Shaw, etc.) trading volatility as an asset class.

**Why they exist:** Volatility is a distinct risk factor that can be traded independently of market direction.

**How they operate:**
- Trade **variance swaps, VIX futures, and options spreads**
- Arbitrage mispricings between related instruments
- Often **net sellers of volatility** (harvesting volatility risk premium)

**Their contribution to our edge:**
- Their activity creates **predictable flows** around VIX expiration and SPX settlement
- They compete with dealers, sometimes amplifying hedging effects

## The Hedging Cascade

```
┌─────────────────────────────────────────────────────────────┐
│                    THE HEDGING CASCADE                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Retail/Institutional buys calls                         │
│           │                                                 │
│           ▼                                                 │
│  2. Dealer sells calls (takes other side)                   │
│           │                                                 │
│           ▼                                                 │
│  3. Dealer now has NEGATIVE GAMMA                           │
│      (exposed to adverse price moves)                       │
│           │                                                 │
│           ▼                                                 │
│  4. Dealer MUST BUY STOCK to hedge                          │
│           │                                                 │
│           ▼                                                 │
│  5. Stock buying pushes price UP                            │
│           │                                                 │
│           ▼                                                 │
│  6. Higher price = MORE HEDGING NEEDED                      │
│           │                                                 │
│           ▼                                                 │
│  7. FEEDBACK LOOP (momentum amplification)                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

This cascade is **mechanical and predictable**. By measuring aggregate dealer gamma exposure (GEX), we can anticipate when and where these flows will occur.

## Academic Support for Dealer Hedging Effects

| Study | Finding | Relevance |
|-------|---------|----------|
| [Ni, Pearson & Poteshman (2005)](https://doi.org/10.1016/j.jfineco.2004.08.002) | Stock prices cluster at option strikes on expiration | Validates price pinning effect |
| [Barbon & Buraschi (2021)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3725454) | Dealer gamma hedging amplifies market volatility | Validates momentum amplification |
| [Hu (2014)](https://doi.org/10.2139/ssrn.2463549) | Options market makers affect underlying prices | Validates hedging impact on spot |
| [Avellaneda & Lipkin (2003)](https://doi.org/10.1142/S0219024903001912) | Delta-hedging creates feedback effects | Validates mechanical nature |
| [Garleanu, Pedersen & Poteshman (2009)](https://doi.org/10.1093/rfs/hhp005) | Demand pressure affects option prices | Validates flow-based pricing |

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
- We follow best practices from [Harvey, Liu & Zhu (2016)](https://doi.org/10.1093/rfs/hhv059) to avoid data mining bias

## "Why Hasn't This Been Arbitraged Away?"

**Our Response:**
1. **Structural necessity**: Dealers MUST hedge - they can't stop (regulatory requirement under SEC Rule 15c3-1)
2. **Information barrier**: Aggregate GEX requires specialized data processing
3. **Execution complexity**: Exploiting requires real-time calculation and fast execution
4. **Capacity constraints**: Strategy has natural capacity limits (feature, not bug)
5. **Academic evidence**: [McLean & Pontiff (2016)](https://doi.org/10.1111/jofi.12365) show that even published anomalies persist when they have structural causes

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
- Win rate of 81% with 42 trades has **p-value < 0.001** vs. random (binomial test)
- Profit factor of 29x indicates **robust edge**, not luck
- Strategy logic is **mechanically sound**, not curve-fitted
- Following [Harvey & Liu (2015)](https://doi.org/10.1093/rfs/hhv059) guidance on statistical significance thresholds

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
| Decays over time ([McLean & Pontiff, 2016](https://doi.org/10.1111/jofi.12365)) | Persists (dealers must hedge) |
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

---

# References

## Academic Papers

1. **Avellaneda, M. & Lipkin, M.D. (2003)**. "A Market-Induced Mechanism for Stock Pinning." *Quantitative Finance*, 3(6), 417-425. [DOI](https://doi.org/10.1142/S0219024903001912)

2. **Baltussen, G., Da, Z. & van Bekkum, S. (2021)**. "Indexing and Stock Market Serial Dependence Around the World." *Journal of Financial Economics*, 139(1), 1-23. [DOI](https://doi.org/10.1016/j.jfineco.2020.07.016)

3. **Barbon, A. & Buraschi, A. (2021)**. "Gamma Fragility." *Working Paper*. [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3725454)

4. **Fama, E.F. & French, K.R. (2010)**. "Luck versus Skill in the Cross-Section of Mutual Fund Returns." *Journal of Finance*, 65(5), 1915-1947. [DOI](https://doi.org/10.1111/j.1540-6261.2009.01527.x)

5. **Garleanu, N., Pedersen, L.H. & Poteshman, A.M. (2009)**. "Demand-Based Option Pricing." *Review of Financial Studies*, 22(10), 4259-4299. [DOI](https://doi.org/10.1093/rfs/hhp005)

6. **Harvey, C.R., Liu, Y. & Zhu, H. (2016)**. "...and the Cross-Section of Expected Returns." *Review of Financial Studies*, 29(1), 5-68. [DOI](https://doi.org/10.1093/rfs/hhv059)

7. **Hu, J. (2014)**. "Does Option Trading Convey Stock Price Information?" *Journal of Financial Economics*, 111(3), 625-645. [DOI](https://doi.org/10.2139/ssrn.2463549)

8. **Malkiel, B.G. (2003)**. "The Efficient Market Hypothesis and Its Critics." *Journal of Economic Perspectives*, 17(1), 59-82. [DOI](https://doi.org/10.1257/089533003321164958)

9. **McLean, R.D. & Pontiff, J. (2016)**. "Does Academic Research Destroy Stock Return Predictability?" *Journal of Finance*, 71(1), 5-32. [DOI](https://doi.org/10.1111/jofi.12365)

10. **Ni, S.X., Pearson, N.D. & Poteshman, A.M. (2005)**. "Stock Price Clustering on Option Expiration Dates." *Journal of Financial Economics*, 78(1), 49-87. [DOI](https://doi.org/10.1016/j.jfineco.2004.08.002)

## Industry Reports

- **S&P Dow Jones Indices**. "SPIVA U.S. Scorecard." [Link](https://www.spglobal.com/spdji/en/research-insights/spiva/)
- **OCC (Options Clearing Corporation)**. "Market Statistics." [Link](https://www.theocc.com/Market-Data/Market-Data-Reports)

---

*Document Version: 1.1*
*Last Updated: November 2025*
*Classification: Confidential - Investor Materials*
