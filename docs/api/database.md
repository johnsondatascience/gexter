# Database API Reference

The Database module provides the interface between GEXter and the PostgreSQL database.

## Module: `database`

::: src.database

## Overview

The database module uses SQLAlchemy for ORM functionality and includes:

- Connection pooling for performance
- Transaction management
- Query builders for common operations
- Schema migration support

## Connection Management

### Database Class

```python
class Database:
    """
    PostgreSQL database interface for GEXter.

    Handles all database operations including:
    - Connection pooling
    - Query execution
    - Transaction management
    - Data exports
    """

    def __init__(self):
        """Initialize database connection from environment variables."""
        self.connection_string = self._build_connection_string()
        self.engine = create_engine(self.connection_string)

    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from env vars."""
        return f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
```

## Core Functions

### Execute Query

```python
def execute(self, query: str, params: dict = None) -> List[dict]:
    """
    Execute a SQL query and return results.

    Args:
        query: SQL query string
        params: Optional query parameters

    Returns:
        List of result rows as dictionaries

    Example:
        >>> db = Database()
        >>> results = db.execute(
        ...     "SELECT * FROM gex_table WHERE strike = :strike",
        ...     {"strike": 4500}
        ... )
    """
```

### Insert Data

```python
def insert_gex_data(self, data: List[dict]) -> int:
    """
    Insert GEX data into the database.

    Args:
        data: List of dictionaries containing option data

    Returns:
        Number of rows inserted

    Example:
        >>> db = Database()
        >>> rows = db.insert_gex_data([
        ...     {
        ...         "strike": 4500,
        ...         "option_type": "call",
        ...         "gex": 1000000,
        ...         ...
        ...     }
        ... ])
    """
```

### Export to CSV

```python
def export_to_csv(self, query: str, filepath: str) -> bool:
    """
    Export query results to CSV file.

    Args:
        query: SQL query to execute
        filepath: Path to output CSV file

    Returns:
        True if export successful

    Example:
        >>> db = Database()
        >>> db.export_to_csv(
        ...     "SELECT * FROM gex_table WHERE greeks.updated_at > NOW() - INTERVAL '1 day'",
        ...     "output/gex.csv"
        ... )
    """
```

## Schema

### Main Table: `gex_table`

The primary table storing all option and GEX data:

```sql
CREATE TABLE gex_table (
    -- Composite Primary Key
    "greeks.updated_at" TIMESTAMP,
    expiration_date TEXT,
    option_type TEXT,
    strike REAL,

    -- Option Metadata
    symbol TEXT,
    description TEXT,
    expiration_type TEXT,
    root_symbol TEXT,
    underlying TEXT,

    -- Price Data
    last REAL,
    bid REAL,
    ask REAL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,

    -- Volume & Interest
    volume BIGINT,
    open_interest BIGINT,
    trade_date TEXT,
    last_volume BIGINT,

    -- Greeks
    delta REAL,
    gamma REAL,
    theta REAL,
    vega REAL,
    rho REAL,
    phi REAL,
    bid_iv REAL,
    mid_iv REAL,
    ask_iv REAL,
    smv_vol REAL,

    -- GEX Calculations
    gex REAL,
    net_gex REAL,

    -- Greek Differences (24 columns)
    delta_diff_abs REAL,
    delta_diff_pct REAL,
    gamma_diff_abs REAL,
    gamma_diff_pct REAL,
    theta_diff_abs REAL,
    theta_diff_pct REAL,
    vega_diff_abs REAL,
    vega_diff_pct REAL,
    rho_diff_abs REAL,
    rho_diff_pct REAL,
    phi_diff_abs REAL,
    phi_diff_pct REAL,
    bid_iv_diff_abs REAL,
    bid_iv_diff_pct REAL,
    mid_iv_diff_abs REAL,
    mid_iv_diff_pct REAL,
    ask_iv_diff_abs REAL,
    ask_iv_diff_pct REAL,
    smv_vol_diff_abs REAL,
    smv_vol_diff_pct REAL,
    oi_diff_abs BIGINT,
    oi_diff_pct REAL,
    volume_diff_abs BIGINT,
    volume_diff_pct REAL,

    -- SPX Price Tracking
    spx_price REAL,
    spx_open REAL,
    spx_high REAL,
    spx_low REAL,
    spx_close REAL,
    spx_volume BIGINT,

    -- Constraints
    PRIMARY KEY ("greeks.updated_at", expiration_date, option_type, strike)
);
```

### Indexes

Optimized indexes for common query patterns:

```sql
-- Time-based queries
CREATE INDEX idx_gex_timestamp ON gex_table ("greeks.updated_at");

-- Strike-based queries
CREATE INDEX idx_gex_strike ON gex_table (strike);

-- GEX magnitude queries
CREATE INDEX idx_gex_value ON gex_table (gex);

-- Expiration queries
CREATE INDEX idx_gex_expiration ON gex_table (expiration_date);

-- SPX price queries
CREATE INDEX idx_spx_price ON gex_table (spx_price);
```

## Common Queries

### Get Latest GEX Snapshot

```python
def get_latest_gex(self) -> List[dict]:
    """Get the most recent GEX data for all strikes."""
    query = """
        SELECT strike, option_type, gex, open_interest, delta, gamma
        FROM gex_table
        WHERE "greeks.updated_at" = (
            SELECT MAX("greeks.updated_at") FROM gex_table
        )
        ORDER BY ABS(gex) DESC
    """
    return self.execute(query)
```

### Get 0DTE Options

```python
def get_0dte_options(self) -> List[dict]:
    """Get options expiring today (0DTE)."""
    query = """
        SELECT *
        FROM gex_table
        WHERE expiration_date = CURRENT_DATE
        AND "greeks.updated_at" = (
            SELECT MAX("greeks.updated_at") FROM gex_table
        )
        ORDER BY strike
    """
    return self.execute(query)
```

### Get Historical GEX at Strike

```python
def get_gex_history(self, strike: float, days: int = 7) -> List[dict]:
    """Get historical GEX data for a specific strike."""
    query = """
        SELECT "greeks.updated_at", gex, open_interest, gamma
        FROM gex_table
        WHERE strike = :strike
        AND "greeks.updated_at" > NOW() - INTERVAL ':days days'
        ORDER BY "greeks.updated_at"
    """
    return self.execute(query, {"strike": strike, "days": days})
```

## Performance Optimization

### Connection Pooling

```python
# Configure connection pool
engine = create_engine(
    connection_string,
    pool_size=10,          # Max connections
    max_overflow=20,       # Extra connections allowed
    pool_pre_ping=True,    # Test connections before use
    pool_recycle=3600      # Recycle connections hourly
)
```

### Batch Inserts

```python
def batch_insert(self, data: List[dict], batch_size: int = 1000):
    """
    Insert data in batches for better performance.

    Args:
        data: List of records to insert
        batch_size: Number of records per batch
    """
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        self.insert_gex_data(batch)
```

## Error Handling

```python
from sqlalchemy.exc import IntegrityError, OperationalError

try:
    db.insert_gex_data(data)
except IntegrityError:
    # Duplicate key - data already exists
    logger.warning("Duplicate data, skipping insert")
except OperationalError as e:
    # Database connection issue
    logger.error(f"Database connection failed: {e}")
    # Retry logic
```

## Configuration

Environment variables for database configuration:

```bash
# PostgreSQL Connection
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gexdb
DB_USER=gexuser
DB_PASS=your_secure_password

# Connection Pool
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
```

## Migrations

Database schema migrations are managed via SQL scripts in `init.sql`:

```sql
-- Initial schema
\i init.sql

-- Migrations (future versions)
-- \i migrations/001_add_column.sql
-- \i migrations/002_add_index.sql
```

## See Also

- [GEX Collector](gex_collector.md) - Data collection module
- [SPX Tracking Queries](../SPX_TRACKING_QUERIES.sql) - Example SQL queries
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
