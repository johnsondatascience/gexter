# GEX (Gamma Exposure) Data Collector

A production-ready system for collecting SPX option chain data and calculating gamma exposure with comprehensive technical analysis.

## Project Structure

```
gextr/
├── src/                          # Source code
│   ├── api/                      # API client modules
│   │   ├── tradier_api.py       # Production Tradier API client
│   │   └── tradier_funcs.py     # Legacy API functions
│   ├── calculations/            # Calculation modules
│   │   └── greek_diff_calculator.py  # Greek differences
│   ├── indicators/              # Technical indicators
│   │   └── technical_indicators.py   # EMA and positioning analysis
│   ├── utils/                   # Utility modules
│   │   ├── logger.py           # Logging configuration
│   │   ├── notifications.py    # Alert system
│   │   └── scheduler.py        # Task scheduling
│   ├── config.py               # Configuration management
│   └── gex_collector.py        # Main collector class
├── tests/                       # Test scripts
├── scripts/                     # Utility scripts
├── docs/                        # Documentation
├── data/                        # Database and data files
├── output/                      # CSV exports and results
├── logs/                        # Log files
├── config/                      # Configuration files
├── run_gex_collector.py         # Main entry point
├── run_scheduler.py             # Scheduler entry point
└── requirements.txt             # Dependencies
```

## Features

- **Real-time SPX option data collection** from Tradier API
- **Gamma exposure calculation** for each strike and expiration
- **Greek differences tracking** (24 comparison metrics)
- **SPX price integration** with OHLC intraday data
- **Technical indicators**: 8-period and 21-period EMAs (30-minute timeframe)
- **SPX price estimation** using SPY conversion (99.17% accuracy)
- **Volume analysis** using SPY ETF as proxy
- **Production deployment** with error handling and monitoring
- **Hourly scheduling** during trading sessions
- **CSV exports** for dashboard integration

## Quick Start

1. **Setup environment:**
   ```bash
   # Copy example environment file and edit with your Tradier API credentials
   cp .env.example .env

   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Run data collection:**
   ```bash
   # Single run (manual execution)
   python run_gex_collector.py
   ```

3. **Run with scheduler:**
   ```bash
   # Continuous execution with hourly schedule
   python run_scheduler.py
   ```

## File Locations

After reorganization, all generated files are organized by type:

- **Output CSVs**: [output/](output/) - `gex.csv`, `gex_summary.csv`, `spx_indicators.csv`, etc.
- **Database**: [data/gex_data.db](data/gex_data.db)
- **Logs**: [logs/gex_collector.log](logs/gex_collector.log)
- **Source Code**: [src/](src/) - All Python modules organized by function

## Configuration

Set the following environment variables in `.env`:
- `TRADIER_API_KEY`: Your Tradier API key
- `TRADIER_ACCOUNT_ID`: Your Tradier account ID
- `DATABASE_PATH`: SQLite database path (default: data/gex_data.db)
- `LOG_LEVEL`: Logging level (default: INFO)

## Output Files

- **`output/gex.csv`**: Complete dataset with GEX, Greeks, and indicators
- **`output/spx_indicators.csv`**: Technical indicators only
- **`output/spx_prices.csv`**: SPX OHLC price data
- **`logs/gex_collector.log`**: Application logs

## Technical Details

- **SPY-SPX conversion ratio**: 10.029114 (0.0998% stability)
- **Estimation accuracy**: 99.17% average
- **Data collection**: Hourly during market hours (9:30 AM - 4:00 PM ET)
- **Database**: SQLite with 24 Greek difference columns
- **Error handling**: Comprehensive logging and retry mechanisms