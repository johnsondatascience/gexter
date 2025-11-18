# GEX (Gamma Exposure) Data Collector

A production-ready containerized system for collecting SPX option chain data and calculating gamma exposure with comprehensive technical analysis.

## Features

- **Real-time SPX option data collection** from Tradier API
- **Gamma exposure calculation** for each strike and expiration
- **Greek differences tracking** (24 comparison metrics)
- **SPX price integration** with OHLC intraday data
- **Technical indicators**: 8-period and 21-period EMAs (30-minute timeframe)
- **PostgreSQL database** with optimized schema and indexing
- **Docker deployment** with Docker Compose orchestration
- **Automated scheduling** with configurable collection intervals
- **pgAdmin integration** for database management
- **CSV exports** for dashboard integration (Tableau)

## Architecture

### Services (Docker Compose)

- **postgres**: PostgreSQL 15 database with performance tuning
- **pgadmin**: Web-based database administration interface
- **gex_collector**: Scheduled data collection service

### Project Structure

```
gextr/
├── src/                              # Source code
│   ├── api/                          # API clients
│   │   └── tradier_api.py           # Tradier API client
│   ├── calculations/                 # Calculation modules
│   │   └── greek_diff_calculator.py # Greek differences
│   ├── indicators/                   # Technical indicators
│   │   └── technical_indicators.py  # EMA calculations
│   ├── utils/                        # Utilities
│   │   ├── logger.py                # Logging
│   │   └── notifications.py         # Alerts
│   ├── config.py                    # Configuration
│   ├── database.py                  # Database interface
│   ├── gex_collector.py             # Main collector
│   └── scheduler.py                 # Collection scheduler
├── config/                           # Configuration files
│   └── postgres.conf                # PostgreSQL tuning
├── docs/                             # Documentation
├── scripts/                          # Utility scripts
├── docker-compose.yml                # Docker orchestration
├── Dockerfile                        # Container image
├── init.sql                          # Database schema
├── requirements.txt                  # Python dependencies
└── .env                             # Environment variables
```

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Tradier API credentials ([Get API key](https://developer.tradier.com/))

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd gextr
   ```

2. **Configure environment variables:**

   Edit the `.env` file with your credentials:
   ```bash
   # Tradier API Configuration
   TRADIER_API_KEY=your_api_key_here
   TRADIER_ACCOUNT_ID=your_account_id_here

   # PostgreSQL Configuration
   POSTGRES_PASSWORD=your_secure_password

   # pgAdmin Credentials
   PGADMIN_EMAIL=admin@example.com
   PGADMIN_PASSWORD=admin123

   # Collection Settings (optional)
   COLLECTION_INTERVAL_MINUTES=5  # Run every 5 minutes
   TRADING_HOURS_START=09:30      # Market open (ET)
   TRADING_HOURS_END=16:00        # Market close (ET)
   ```

3. **Start the services:**
   ```bash
   docker-compose up -d
   ```

4. **Verify services are running:**
   ```bash
   docker-compose ps
   ```

   Expected output:
   ```
   NAME            STATUS    PORTS
   gex_postgres    healthy   5432
   gex_pgadmin     running   5050
   gex_collector   running
   ```

## Usage

### Accessing Services

- **pgAdmin**: http://localhost:5050
  - Login with `PGADMIN_EMAIL` and `PGADMIN_PASSWORD` from `.env`
  - Connect to database using:
    - Host: `postgres`
    - Port: `5432`
    - Database: `gexdb`
    - User: `gexuser`
    - Password: `POSTGRES_PASSWORD` from `.env`

- **PostgreSQL**: Direct connection on `localhost:5432`

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f gex_collector
docker-compose logs -f postgres
docker-compose logs -f pgadmin
```

### Data Collection

The collector runs automatically during trading hours based on the schedule:
- **Interval**: Every 5 minutes (configurable)
- **Trading hours**: 9:30 AM - 4:00 PM ET
- **Trading days**: Monday-Friday only
- **Smart detection**: Skips collection if no new data available

### Managing Services

```bash
# Stop all services
docker-compose down

# Restart all services
docker-compose restart

# Rebuild collector after code changes
docker-compose build gex_collector
docker-compose up -d gex_collector

# View resource usage
docker stats
```

## Database Schema

The `gex_table` stores option chain data with:

**Primary Key (Composite)**:
- `greeks.updated_at` (timestamp)
- `expiration_date` (text)
- `option_type` (text)
- `strike` (real)

**Columns**: ~100 columns including:
- Option metadata (symbol, description, expiration type)
- Price data (last, bid, ask, OHLC)
- Volume and open interest
- Greeks (delta, gamma, theta, vega, rho, phi, IV)
- GEX calculations
- Greek differences (absolute and percentage)
- SPX price tracking (10 columns)

**Indexes**: Optimized for query performance on timestamp, expiration, strike, GEX, and SPX price.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TRADIER_API_KEY` | Tradier API key | Required |
| `TRADIER_ACCOUNT_ID` | Tradier account ID | Required |
| `POSTGRES_PASSWORD` | PostgreSQL password | changeme123 |
| `PGADMIN_EMAIL` | pgAdmin login email | admin@example.com |
| `PGADMIN_PASSWORD` | pgAdmin password | admin123 |
| `COLLECTION_INTERVAL_MINUTES` | Collection frequency | 5 |
| `TRADING_HOURS_START` | Market open time (ET) | 09:30 |
| `TRADING_HOURS_END` | Market close time (ET) | 16:00 |
| `TIMEZONE` | Timezone for scheduling | America/New_York |
| `LOG_LEVEL` | Logging level | INFO |

### PostgreSQL Performance Tuning

The database is pre-configured with performance optimizations in `config/postgres.conf`:
- Shared buffers: 256MB
- Effective cache size: 1GB
- Work memory: 16MB
- Max connections: 100

## Data Export

CSV files are automatically generated in the collector container:
- **`output/gex.csv`**: Complete dataset with all columns
- **`output/gex_summary.csv`**: Top GEX changes summary
- **`output/spx_intraday_prices.csv`**: SPX OHLC price data
- **`output/spx_indicators.csv`**: Technical indicators (EMAs)

To access exports from the container:
```bash
docker cp gex_collector:/app/output/gex.csv ./gex.csv
```

## Troubleshooting

### Collector Not Running

```bash
# Check logs
docker-compose logs gex_collector

# Verify environment variables are set
docker exec gex_collector env | grep TRADIER
```

### Database Connection Issues

```bash
# Check PostgreSQL is healthy
docker-compose ps postgres

# Test connection
docker exec gex_postgres psql -U gexuser -d gexdb -c "SELECT COUNT(*) FROM gex_table;"
```

### pgAdmin Email Error

If you see email validation errors, ensure `PGADMIN_EMAIL` uses a valid domain (not `.local`).

## Development

### Running Tests

```bash
# Run specific test scripts
docker exec gex_collector python scripts/verify_postgres_setup.py
```

### Database Queries

Example queries are available in `docs/SPX_TRACKING_QUERIES.sql`.

### Modifying Collection Logic

1. Edit source files in `src/`
2. Rebuild the collector:
   ```bash
   docker-compose build gex_collector
   docker-compose up -d gex_collector
   ```

## Technical Details

- **Database**: PostgreSQL 15 with composite primary key preventing duplicates
- **Data collection**: Configurable interval during market hours only
- **SPY-SPX conversion**: SPX estimated using SPY ETF prices
- **Greek calculations**: Provided by Tradier API, tracked over time
- **Error handling**: Comprehensive logging and graceful failure recovery
- **Scheduling**: Python `schedule` library with timezone awareness

## Documentation

- **Greek Differences**: [docs/README_greek_differences.md](docs/README_greek_differences.md)
- **SPX Tracking**: [docs/SPX_TRACKING_IMPLEMENTATION.md](docs/SPX_TRACKING_IMPLEMENTATION.md)
- **Deployment Guide**: [docs/deployment_guide.md](docs/deployment_guide.md)

## License

This project is for personal use. Tradier API usage subject to their terms of service.

## Credits

Built with:
- Python 3.13
- PostgreSQL 15
- Docker & Docker Compose
- Tradier API
- pandas, SQLAlchemy, psycopg2
