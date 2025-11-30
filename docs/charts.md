# Charts & Analysis

This section contains visualizations and analysis charts for GEXter data and trading strategies.

## Investor Charts

Interactive charts and analysis are available in the Jupyter notebook:

- [Investor Charts Notebook](charts/investor_charts.ipynb)

## Chart Categories

### Strategy Performance
Charts showing backtest results and strategy performance metrics:

- **Strangle Strategy Results**: Historical performance of the strangle strategy
- **0DTE Signal Performance**: Win rate and P&L distribution for 0DTE signals
- **Greek Difference Correlation**: How Greek changes correlate with price movements

### Market Analysis
GEX distribution and market positioning charts:

- **GEX Levels by Strike**: Current gamma exposure across strike prices
- **GEX vs Price Action**: Historical relationship between GEX levels and SPX moves
- **Dealer Positioning**: Net dealer gamma and its implications

### Technical Indicators
Charts for technical analysis:

- **EMA Crossovers**: 8-period and 21-period EMA signals
- **Volume Analysis**: Option volume patterns around key GEX strikes
- **Implied Volatility**: IV trends and term structure

## Generating Charts

Charts can be generated using the `make_charts.py` script:

```bash
python make_charts.py
```

This will create charts in the `docs/charts/` directory.

## Available Chart Files

The following chart images are available:

```
docs/charts/
├── strategy_performance.png
├── gex_distribution.png
├── greek_differences.png
└── technical_indicators.png
```

## Tableau Integration

GEXter also exports data to Tableau workbooks:

- `gexter.twbx` - Main analysis workbook
- `gexterPG.twbx` - PostgreSQL connected workbook

These provide interactive dashboards for:
- Real-time GEX monitoring
- Historical pattern analysis
- Strategy performance tracking
- Risk management metrics

## Updating Charts

To update charts with the latest data:

1. Ensure the database is up to date
2. Run the data collection: `python run_gex_collector.py`
3. Generate new charts: `python make_charts.py`
4. Refresh Tableau dashboards

---

*For more information on the underlying data, see the [Market Mechanics](MARKET_MECHANICS_TECHNICAL.md) documentation.*
