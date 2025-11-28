# XSP (Micro SPX) Implementation Guide

## Executive Summary

**XSP is fully supported by Tradier API** and has **sufficient liquidity** for GEX analysis (42k+ open interest on 0DTE options).

**Key Benefits**:
- **10x smaller contract size**: $68k vs $682k
- **10x lower margin**: ~$3,400 vs ~$34,000
- **Same underlying**: S&P 500 index exposure
- **Cash settled**: No assignment risk
- **60/40 tax treatment**: Like SPX

**Recommendation**: **Track both SPX and XSP** for research and trading flexibility.

---

## Test Results

```
XSP (MICRO SPX) SUPPORT TEST
============================================================

✓ XSP quote available: $681.93 (10x smaller than SPX)
✓ Option expirations: 44 available
✓ Option chain: 482 contracts for next expiration
✓ Greeks: 100% of contracts have Greeks
✓ Open Interest: 42,970 contracts
✓ Put/Call Ratio: 1.65
✓ Liquidity Rating: HIGH - sufficient for GEX analysis
```

---

## Implementation Options

### Option 1: Replace SPX with XSP (Simple - 30 min)

**When to use**: You only want to track XSP going forward

**Steps**:
1. Add to `.env`:
   ```bash
   COLLECT_SPX=false
   COLLECT_XSP=true
   ```

2. Restart collector:
   ```bash
   docker compose restart scheduler
   ```

**Pros**: Simple, immediate
**Cons**: Lose SPX data collection, can't compare

---

### Option 2: Track Both SPX + XSP (RECOMMENDED - 2 hours)

**When to use**: Research value + trading flexibility

**Steps**:

#### Step 1: Run Database Migration (5 min)

```bash
python scripts/add_xsp_support.py --yes
```

This adds `underlying_symbol` column to track multiple indices.

#### Step 2: Update .env Configuration (1 min)

Add to your `.env` file:
```bash
# Underlying symbols to collect
COLLECT_SPX=true   # Continue SPX for research/reference
COLLECT_XSP=true   # Add XSP for trading
```

#### Step 3: Update Collector Code (30 min)

The collector needs to loop through `config.underlying_symbols` instead of hardcoding 'SPX'.

**Key changes needed in `src/gex_collector.py`**:

```python
# OLD (line ~352):
# Get current SPX price data first
self.current_spx_price = self.get_current_spx_price()

# NEW:
# Get current price data for all configured underlyings
self.current_underlying_prices = {}
for symbol in self.config.underlying_symbols:
    self.current_underlying_prices[symbol] = self.get_current_underlying_price(symbol)
```

```python
# OLD (line ~373):
chains = self.api.get_chains("SPX", date)

# NEW - collect for each underlying:
all_chains = []
for symbol in self.config.underlying_symbols:
    chains = self.api.get_chains(symbol, date)
    if not chains.empty:
        chains['underlying_symbol'] = symbol  # Tag with symbol
        # Add price data for this underlying
        underlying_price = self.current_underlying_prices.get(symbol)
        if underlying_price:
            # Add price columns...
        all_chains.append(chains)

# Combine all
all_chains = pd.concat(all_chains, ignore_index=True)
```

#### Step 4: Restart Collector (1 min)

```bash
docker compose restart scheduler
```

#### Step 5: Verify Collection (5 min)

```bash
# Watch logs
docker compose logs -f scheduler

# Check database
docker exec -it gextr-postgres-1 psql -U gexuser -d gexdb

-- Verify both symbols collecting
SELECT
    underlying_symbol,
    COUNT(*) as records,
    MAX("greeks.updated_at") as last_collection
FROM gex_table
GROUP BY underlying_symbol
ORDER BY underlying_symbol;
```

**Pros**: Best research value, compare effectiveness, trade XSP with SPX reference
**Cons**: 2x API calls (still well within rate limits), 2x storage

---

### Option 3: Configurable (Switch between SPX/XSP - 1 hour)

**When to use**: Want flexibility to switch but not track both

**Steps**: Same as Option 2, but set only one to `true` in `.env`

---

## Cost-Benefit Analysis

### Trading Capital Requirements

| Account Size | SPX Strategy | XSP Strategy |
|--------------|--------------|--------------|
| **$10,000** | ❌ Can't trade | ✅ 2-3 contracts |
| **$25,000** | ⚠️ 1 contract (risky) | ✅ 5-7 contracts |
| **$50,000** | ✅ 1-2 contracts | ✅ 10-15 contracts |
| **$100,000** | ✅ 2-4 contracts | ✅ 20-30 contracts |

### Data Collection Costs

| Metric | SPX Only | Both SPX + XSP | Increase |
|--------|----------|----------------|----------|
| **API calls/collection** | ~10-15 | ~20-30 | 2x |
| **Records/day** | ~2,500 | ~5,000 | 2x |
| **Database growth** | ~500 MB/mo | ~1 GB/mo | 2x |
| **Still within limits?** | ✅ Yes | ✅ Yes | N/A |

**Verdict**: Tracking both is easily affordable given Tradier's 120 req/min limit.

---

## GEX Signal Comparison Strategy

Once you're collecting both, you can research:

### Question 1: Do XSP GEX signals predict moves as well as SPX?

**Test**:
```sql
-- Compare prediction accuracy
WITH spx_signals AS (
    SELECT
        DATE("greeks.updated_at") as trade_date,
        total_gamma_dollars,
        -- Next day's move...
    FROM gex_table
    WHERE underlying_symbol = 'SPX'
),
xsp_signals AS (
    SELECT
        DATE("greeks.updated_at") as trade_date,
        total_gamma_dollars * 10 as normalized_gex,  -- Normalize to SPX equivalent
        -- Next day's move...
    FROM gex_table
    WHERE underlying_symbol = 'XSP'
)
SELECT
    correlation(spx_signals.total_gamma_dollars, xsp_signals.normalized_gex)
FROM spx_signals
JOIN xsp_signals USING (trade_date);
```

### Question 2: Does XSP have unique signals (retail-driven)?

If XSP diverges from SPX, it might indicate retail vs institutional positioning differences.

### Question 3: Which is more tradable for retail?

- **Liquidity**: Bid-ask spreads
- **Slippage**: Actual fill prices
- **Signal quality**: Win rate on same strategy

---

## Recommended Implementation Plan

### Phase 1: Database Setup (Today - 30 min)

```bash
# 1. Test XSP support
python scripts/test_xsp_support.py

# 2. Add database support
python scripts/add_xsp_support.py --yes

# 3. Update .env
echo "COLLECT_SPX=true" >> .env
echo "COLLECT_XSP=true" >> .env
```

### Phase 2: Collector Updates (This Week - 2 hours)

**Modify** `src/gex_collector.py`:
1. Change `get_current_spx_price()` → `get_current_underlying_price(symbol)`
2. Loop through `config.underlying_symbols` in collection
3. Tag each record with `underlying_symbol`
4. Update GEX calculations to handle both

### Phase 3: Start Collection (After Coding - immediate)

```bash
docker compose restart scheduler
```

### Phase 4: Validate (Week 1)

- Verify both symbols collecting every 15 minutes
- Check database storage growth (~1GB/month)
- Ensure no API rate limit issues
- Confirm Greeks quality for both

### Phase 5: Analysis (Month 1+)

- Compare GEX effectiveness
- Test strategies on both indices
- Determine which is more tradable
- Consider paper trading XSP

---

## FAQ

### Q: Will this double my API costs?

**A**: No, Tradier API is free with your brokerage account. You're well within rate limits (120 req/min).

### Q: Will I run out of disk space?

**A**: Database will grow ~1GB/month instead of 500MB/month. With 50GB VM, you have years of runway.

### Q: Should I backfill XSP historical data?

**A**: No, start fresh. Historical XSP data is less important since you're validating the strategy now.

### Q: Can I trade XSP with my current account?

**A**: Check your broker's margin requirements. XSP typically needs:
- Cash: ~$3,400-6,800 per contract (spread dependent)
- Margin: ~$2,000-4,000 per contract
- Portfolio Margin: ~$500-1,500 per contract

### Q: Are XSP options as liquid as SPX?

**A**: Less liquid but still tradable:
- SPX 0DTE: ~2M open interest
- XSP 0DTE: ~40k open interest
- Ratio: SPX is 50x more liquid
- **Verdict**: XSP is liquid enough for retail trading

### Q: Do I need to change my backtesting code?

**A**: Yes, eventually. Add `WHERE underlying_symbol = 'XSP'` to queries when backtesting XSP strategies.

---

## Migration Checklist

- [ ] Test XSP API support (`python scripts/test_xsp_support.py`)
- [ ] Run database migration (`python scripts/add_xsp_support.py`)
- [ ] Update `.env` with `COLLECT_XSP=true`
- [ ] Modify `gex_collector.py` for multi-underlying
- [ ] Test locally before deploying to VM
- [ ] Restart collector: `docker compose restart scheduler`
- [ ] Verify logs show both SPX and XSP
- [ ] Check database has both symbols
- [ ] Monitor for 24 hours
- [ ] Validate data quality
- [ ] Update analysis scripts to filter by `underlying_symbol`

---

## Code Snippets

### Query XSP Data Only

```sql
SELECT
    "greeks.updated_at",
    symbol,
    strike,
    option_type,
    open_interest,
    "greeks.gamma",
    total_gamma_dollars
FROM gex_table
WHERE underlying_symbol = 'XSP'
ORDER BY "greeks.updated_at" DESC
LIMIT 100;
```

### Compare SPX vs XSP GEX

```sql
SELECT
    underlying_symbol,
    COUNT(*) as total_records,
    COUNT(DISTINCT "greeks.updated_at") as timestamps,
    SUM(total_gamma_dollars) / 1e9 as total_gex_billions,
    AVG(total_gamma_dollars) as avg_gex_per_record
FROM gex_table
GROUP BY underlying_symbol
ORDER BY underlying_symbol;
```

### Daily GEX Comparison

```sql
WITH daily_gex AS (
    SELECT
        DATE("greeks.updated_at") as trade_date,
        underlying_symbol,
        MAX(total_gamma_dollars) as max_gex,
        MIN(total_gamma_dollars) as min_gex,
        AVG(total_gamma_dollars) as avg_gex
    FROM gex_table
    GROUP BY DATE("greeks.updated_at"), underlying_symbol
)
SELECT
    spx.trade_date,
    spx.avg_gex as spx_gex,
    xsp.avg_gex * 10 as xsp_gex_normalized,
    (spx.avg_gex - xsp.avg_gex * 10) as difference
FROM daily_gex spx
JOIN daily_gex xsp ON spx.trade_date = xsp.trade_date
WHERE spx.underlying_symbol = 'SPX'
  AND xsp.underlying_symbol = 'XSP'
ORDER BY spx.trade_date DESC;
```

---

## Next Steps

1. **Today**: Run `python scripts/test_xsp_support.py` to verify
2. **This week**: Implement multi-underlying support
3. **Next week**: Start collecting both SPX and XSP
4. **Month 1**: Analyze correlation and effectiveness
5. **Month 3**: Determine which index to trade live
6. **Month 6**: Backtest with sufficient data

---

## Support

If you encounter issues:
- Check Tradier API status
- Verify `.env` configuration
- Review logs: `docker compose logs scheduler`
- Test API manually: `python scripts/test_xsp_support.py`

---

**Bottom Line**: XSP is fully supported, highly tradable, and **strongly recommended** for your account size. Implement multi-underlying support to compare effectiveness while maintaining SPX as reference data.
