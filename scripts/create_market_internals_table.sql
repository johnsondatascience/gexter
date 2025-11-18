-- Create market internals table for storing breadth and volume data

CREATE TABLE IF NOT EXISTS market_internals (
    timestamp TIMESTAMP PRIMARY KEY,

    -- Breadth metrics
    advances INTEGER NOT NULL,
    declines INTEGER NOT NULL,
    unchanged INTEGER NOT NULL,
    advance_decline_ratio REAL NOT NULL,
    breadth_ratio REAL NOT NULL,

    -- Volume metrics
    up_volume BIGINT NOT NULL,
    down_volume BIGINT NOT NULL,
    up_down_volume_ratio REAL NOT NULL,
    volume_ratio REAL NOT NULL,

    -- Market indices (optional)
    tick REAL,
    trin REAL,
    add_index REAL,

    -- Derived metrics
    cumulative_ad_line REAL,
    breadth_thrust REAL,

    -- Metadata
    data_source TEXT DEFAULT 'calculated',  -- 'calculated' or 'index'
    stock_universe_size INTEGER,  -- Number of stocks analyzed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_market_internals_timestamp ON market_internals(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_market_internals_breadth ON market_internals(breadth_ratio);
CREATE INDEX IF NOT EXISTS idx_market_internals_volume ON market_internals(volume_ratio);
CREATE INDEX IF NOT EXISTS idx_market_internals_created ON market_internals(created_at DESC);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE market_internals TO gexuser;

-- Comments
COMMENT ON TABLE market_internals IS 'Market breadth and volume internals for trading signal generation';
COMMENT ON COLUMN market_internals.breadth_ratio IS 'Normalized breadth: (ADV - DEC) / (ADV + DEC), range -1 to 1';
COMMENT ON COLUMN market_internals.volume_ratio IS 'Normalized volume: (UP_VOL - DOWN_VOL) / TOTAL_VOL, range -1 to 1';
COMMENT ON COLUMN market_internals.cumulative_ad_line IS 'Cumulative advance/decline line for trend analysis';
COMMENT ON COLUMN market_internals.breadth_thrust IS 'Breadth thrust indicator (0-1), >0.615 is bullish thrust';
