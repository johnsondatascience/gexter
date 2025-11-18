-- SPX Price Tracking Query Examples
-- These queries demonstrate how to use the new SPX price columns in gex_table

-- =============================================================================
-- 1. CHECK SPX PRICE DATA AVAILABILITY
-- =============================================================================

-- See how many records have SPX price data
SELECT
    COUNT(*) as total_records,
    COUNT(spx_price) as with_spx_price,
    ROUND(COUNT(spx_price) * 100.0 / COUNT(*), 2) as pct_coverage
FROM gex_table;

-- Get date range of SPX price data
SELECT
    MIN("greeks.updated_at") as earliest_spx_data,
    MAX("greeks.updated_at") as latest_spx_data,
    COUNT(DISTINCT "greeks.updated_at") as unique_timestamps
FROM gex_table
WHERE spx_price IS NOT NULL;

-- =============================================================================
-- 2. VIEW SPX PRICE HISTORY
-- =============================================================================

-- See SPX price at each data collection time
SELECT DISTINCT
    "greeks.updated_at" as timestamp,
    spx_price,
    spx_open,
    spx_high,
    spx_low,
    spx_change,
    spx_change_pct,
    COUNT(*) OVER (PARTITION BY "greeks.updated_at") as num_options
FROM gex_table
WHERE spx_price IS NOT NULL
ORDER BY "greeks.updated_at" DESC
LIMIT 20;

-- Track SPX intraday movement
SELECT DISTINCT
    DATE("greeks.updated_at") as date,
    TIME("greeks.updated_at") as time,
    spx_price,
    spx_change_pct
FROM gex_table
WHERE
    spx_price IS NOT NULL
    AND DATE("greeks.updated_at") = DATE('now')
ORDER BY "greeks.updated_at" DESC;

-- =============================================================================
-- 3. OPTIONS WITH SPX CONTEXT
-- =============================================================================

-- Get top GEX strikes with SPX price context
SELECT
    "greeks.updated_at",
    strike,
    option_type,
    gex,
    open_interest,
    greeks.gamma,
    spx_price,
    ROUND(((strike - spx_price) / spx_price) * 100, 2) as strike_pct_from_spot
FROM gex_table
WHERE
    "greeks.updated_at" = (SELECT MAX("greeks.updated_at") FROM gex_table WHERE spx_price IS NOT NULL)
    AND spx_price IS NOT NULL
ORDER BY ABS(gex) DESC
LIMIT 20;

-- Find ATM options (strikes near SPX price)
SELECT
    "greeks.updated_at",
    expiration_date,
    strike,
    option_type,
    last,
    bid,
    ask,
    open_interest,
    greeks.delta,
    greeks.gamma,
    gex,
    spx_price,
    ABS(strike - spx_price) as distance_from_spot
FROM gex_table
WHERE
    spx_price IS NOT NULL
    AND "greeks.updated_at" = (SELECT MAX("greeks.updated_at") FROM gex_table WHERE spx_price IS NOT NULL)
    AND ABS(strike - spx_price) < 50  -- Within $50 of spot
ORDER BY distance_from_spot ASC
LIMIT 10;

-- =============================================================================
-- 4. CORRELATE GEX WITH SPX MOVEMENT
-- =============================================================================

-- Find when large GEX changes occurred with SPX moves
SELECT
    "greeks.updated_at",
    strike,
    option_type,
    gex,
    gex_diff,
    gex_pct_change,
    spx_price,
    spx_change,
    spx_change_pct
FROM gex_table
WHERE
    ABS(gex_pct_change) > 50
    AND spx_price IS NOT NULL
    AND has_previous_data = 1
ORDER BY ABS(gex_pct_change) DESC
LIMIT 25;

-- Aggregate GEX by SPX price levels
SELECT
    ROUND(spx_price / 10) * 10 as spx_price_bucket,
    COUNT(*) as num_records,
    SUM(CASE WHEN option_type = 'call' THEN gex ELSE 0 END) as call_gex,
    SUM(CASE WHEN option_type = 'put' THEN gex ELSE 0 END) as put_gex,
    SUM(gex) as net_gex
FROM gex_table
WHERE spx_price IS NOT NULL
GROUP BY spx_price_bucket
ORDER BY spx_price_bucket DESC
LIMIT 20;

-- =============================================================================
-- 5. ANALYZE GREEKS VS SPX MOVEMENT
-- =============================================================================

-- Delta changes when SPX moved significantly
SELECT
    "greeks.updated_at",
    strike,
    option_type,
    greeks.delta,
    "greeks.delta_diff",
    "greeks.delta_pct_change",
    spx_price,
    spx_change_pct,
    prev_timestamp
FROM gex_table
WHERE
    spx_price IS NOT NULL
    AND has_previous_data = 1
    AND ABS(spx_change_pct) > 1.0  -- SPX moved more than 1%
    AND ABS("greeks.delta_pct_change") > 10  -- Delta changed significantly
ORDER BY "greeks.updated_at" DESC, ABS("greeks.delta_pct_change") DESC
LIMIT 25;

-- Gamma changes near ATM strikes during SPX movement
SELECT
    "greeks.updated_at",
    strike,
    option_type,
    greeks.gamma,
    "greeks.gamma_diff",
    "greeks.gamma_pct_change",
    spx_price,
    ABS(strike - spx_price) as distance_from_atm,
    spx_change_pct
FROM gex_table
WHERE
    spx_price IS NOT NULL
    AND has_previous_data = 1
    AND ABS(strike - spx_price) < 100  -- Near the money
    AND ABS("greeks.gamma_pct_change") > 5
ORDER BY "greeks.updated_at" DESC, ABS("greeks.gamma_pct_change") DESC
LIMIT 25;

-- =============================================================================
-- 6. TIME-BASED ANALYSIS
-- =============================================================================

-- Compare morning vs afternoon SPX prices and GEX
SELECT
    DATE("greeks.updated_at") as date,
    CASE
        WHEN CAST(strftime('%H', "greeks.updated_at") AS INTEGER) < 12 THEN 'Morning'
        ELSE 'Afternoon'
    END as session,
    AVG(spx_price) as avg_spx,
    AVG(spx_change_pct) as avg_change_pct,
    SUM(gex) as total_gex,
    COUNT(DISTINCT "greeks.updated_at") as num_snapshots
FROM gex_table
WHERE spx_price IS NOT NULL
GROUP BY date, session
ORDER BY date DESC, session;

-- Track SPX volatility (high-low range) over time
SELECT DISTINCT
    DATE("greeks.updated_at") as date,
    MAX(spx_high) as daily_high,
    MIN(spx_low) as daily_low,
    MAX(spx_high) - MIN(spx_low) as intraday_range,
    AVG(spx_price) as avg_price,
    ROUND(((MAX(spx_high) - MIN(spx_low)) / AVG(spx_price)) * 100, 2) as range_pct
FROM gex_table
WHERE spx_price IS NOT NULL
GROUP BY date
ORDER BY date DESC
LIMIT 30;

-- =============================================================================
-- 7. EXPORT QUERIES FOR ANALYSIS
-- =============================================================================

-- Export complete dataset with SPX context for latest timestamp
SELECT
    "greeks.updated_at",
    expiration_date,
    option_type,
    strike,
    last,
    bid,
    ask,
    open_interest,
    volume,
    greeks.delta,
    greeks.gamma,
    greeks.theta,
    greeks.vega,
    gex,
    spx_price,
    spx_open,
    spx_high,
    spx_low,
    spx_change,
    spx_change_pct
FROM gex_table
WHERE "greeks.updated_at" = (SELECT MAX("greeks.updated_at") FROM gex_table WHERE spx_price IS NOT NULL)
ORDER BY option_type, strike, expiration_date;

-- Export SPX price timeline
SELECT DISTINCT
    "greeks.updated_at",
    spx_price,
    spx_open,
    spx_high,
    spx_low,
    spx_change,
    spx_change_pct,
    spx_bid,
    spx_ask,
    spx_prevclose
FROM gex_table
WHERE spx_price IS NOT NULL
ORDER BY "greeks.updated_at" DESC;

-- =============================================================================
-- 8. DATA QUALITY CHECKS
-- =============================================================================

-- Check for any NULL SPX prices in recent data
SELECT
    "greeks.updated_at",
    COUNT(*) as records,
    COUNT(spx_price) as with_price,
    COUNT(*) - COUNT(spx_price) as missing_price
FROM gex_table
WHERE "greeks.updated_at" >= DATE('now', '-7 days')
GROUP BY "greeks.updated_at"
HAVING missing_price > 0
ORDER BY "greeks.updated_at" DESC;

-- Verify SPX price consistency within each timestamp
SELECT
    "greeks.updated_at",
    COUNT(DISTINCT spx_price) as unique_prices,
    MIN(spx_price) as min_price,
    MAX(spx_price) as max_price,
    COUNT(*) as total_records
FROM gex_table
WHERE spx_price IS NOT NULL
GROUP BY "greeks.updated_at"
HAVING unique_prices > 1  -- Should be 1 price per timestamp
ORDER BY "greeks.updated_at" DESC;
