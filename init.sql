-- GEX PostgreSQL Database Initialization
-- This script creates the schema for the GEX data collection system

-- Create the main gex_table with proper schema
CREATE TABLE IF NOT EXISTS gex_table (
    -- Primary key columns (composite index)
    "greeks.updated_at" TIMESTAMP NOT NULL,
    expiration_date TEXT NOT NULL,
    option_type TEXT NOT NULL,
    strike REAL NOT NULL,

    -- Option metadata
    symbol TEXT,
    description TEXT,
    exch TEXT,
    type TEXT,
    underlying TEXT,
    expiration_type TEXT,
    root_symbol TEXT,

    -- Price data
    last REAL,
    change REAL,
    open TEXT,
    high TEXT,
    low TEXT,
    close TEXT,
    bid REAL,
    ask REAL,
    prevclose REAL,
    change_percentage REAL,
    week_52_high REAL,
    week_52_low REAL,

    -- Volume data
    volume INTEGER,
    average_volume INTEGER,
    last_volume INTEGER,
    open_interest INTEGER,

    -- Bid/Ask details
    bidsize INTEGER,
    bidexch TEXT,
    bid_date TIMESTAMP,
    asksize INTEGER,
    askexch TEXT,
    ask_date TIMESTAMP,

    -- Timestamps
    trade_date TIMESTAMP,

    -- Contract details
    contract_size INTEGER,

    -- Greeks
    "greeks.delta" REAL,
    "greeks.gamma" REAL,
    "greeks.theta" REAL,
    "greeks.vega" REAL,
    "greeks.rho" REAL,
    "greeks.phi" REAL,
    "greeks.bid_iv" REAL,
    "greeks.mid_iv" REAL,
    "greeks.ask_iv" REAL,
    "greeks.smv_vol" REAL,

    -- Calculated GEX
    gex REAL,

    -- Greek differences (absolute)
    "greeks.delta_diff" REAL,
    "greeks.gamma_diff" REAL,
    "greeks.theta_diff" REAL,
    "greeks.vega_diff" REAL,
    "greeks.rho_diff" REAL,
    "greeks.phi_diff" REAL,
    "greeks.bid_iv_diff" REAL,
    "greeks.mid_iv_diff" REAL,
    "greeks.ask_iv_diff" REAL,
    "greeks.smv_vol_diff" REAL,
    gex_diff REAL,

    -- Greek differences (percentage)
    "greeks.delta_pct_change" REAL,
    "greeks.gamma_pct_change" REAL,
    "greeks.theta_pct_change" REAL,
    "greeks.vega_pct_change" REAL,
    "greeks.rho_pct_change" REAL,
    "greeks.phi_pct_change" REAL,
    "greeks.bid_iv_pct_change" REAL,
    "greeks.mid_iv_pct_change" REAL,
    "greeks.ask_iv_pct_change" REAL,
    "greeks.smv_vol_pct_change" REAL,
    gex_pct_change REAL,

    -- Metadata for differences
    prev_timestamp TIMESTAMP,
    has_previous_data BOOLEAN,

    -- SPX price tracking (10 columns)
    spx_price REAL,
    spx_open REAL,
    spx_high REAL,
    spx_low REAL,
    spx_close REAL,
    spx_bid REAL,
    spx_ask REAL,
    spx_change REAL,
    spx_change_pct REAL,
    spx_prevclose REAL,

    -- Composite primary key
    PRIMARY KEY ("greeks.updated_at", expiration_date, option_type, strike)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_gex_table_updated_at ON gex_table("greeks.updated_at");
CREATE INDEX IF NOT EXISTS idx_gex_table_expiration ON gex_table(expiration_date);
CREATE INDEX IF NOT EXISTS idx_gex_table_strike ON gex_table(strike);
CREATE INDEX IF NOT EXISTS idx_gex_table_option_type ON gex_table(option_type);
CREATE INDEX IF NOT EXISTS idx_gex_table_gex ON gex_table(gex);
CREATE INDEX IF NOT EXISTS idx_gex_table_spx_price ON gex_table(spx_price);

-- Create composite index matching the original SQLite index
CREATE INDEX IF NOT EXISTS idx_gex_table_composite
ON gex_table("greeks.updated_at", expiration_date, option_type, strike);

-- Add comments for documentation
COMMENT ON TABLE gex_table IS 'Main table storing SPX option chain data with Greeks and GEX calculations';
COMMENT ON COLUMN gex_table."greeks.updated_at" IS 'Timestamp when Greek values were calculated';
COMMENT ON COLUMN gex_table.gex IS 'Gamma Exposure: Strike * Gamma * Open Interest * 100 (negative for puts)';
COMMENT ON COLUMN gex_table.spx_price IS 'SPX spot price at time of Greek calculation';

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE gex_table TO gexuser;
