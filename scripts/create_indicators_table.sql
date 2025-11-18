-- Create SPX Indicators table for storing technical analysis data

CREATE TABLE IF NOT EXISTS spx_indicators (
    timestamp TIMESTAMP PRIMARY KEY,
    spx_price REAL NOT NULL,

    -- EMAs (Fibonacci sequence: 8, 21, 55)
    ema_8 REAL,
    ema_21 REAL,
    ema_55 REAL,

    -- Price positioning relative to EMAs (%)
    price_vs_ema8_pct REAL,
    price_vs_ema21_pct REAL,
    price_vs_ema55_pct REAL,

    -- EMA relationships (%)
    ema8_vs_ema21_pct REAL,
    ema21_vs_ema55_pct REAL,

    -- Signal
    ema_signal TEXT,  -- 'BULLISH', 'BEARISH', 'NEUTRAL'

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_spx_indicators_timestamp ON spx_indicators(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_spx_indicators_signal ON spx_indicators(ema_signal);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE spx_indicators TO gexuser;

COMMENT ON TABLE spx_indicators IS 'SPX technical indicators including EMAs and positioning signals';
COMMENT ON COLUMN spx_indicators.ema_signal IS 'EMA-based trend signal: BULLISH, BEARISH, or NEUTRAL';
