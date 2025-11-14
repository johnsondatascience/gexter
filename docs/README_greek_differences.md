# Greek Differences Feature

## Overview

The Greek Differences feature calculates the change in Greeks (Delta, Gamma, Theta, Vega, etc.) and GEX between the current option data and the most recent available data for each option type/strike/expiration combination.

## Features Added

### 🔢 Calculated Differences
For each Greek metric, the system now calculates:
- **Absolute Difference**: Current value - Previous value
- **Percentage Change**: ((Current - Previous) / Previous) × 100
- **Metadata**: Previous timestamp and availability flag

### 📊 Greek Metrics Tracked
- `greeks.delta` - Option sensitivity to underlying price
- `greeks.gamma` - Rate of change of delta
- `greeks.theta` - Time decay
- `greeks.vega` - Volatility sensitivity
- `greeks.rho` - Interest rate sensitivity
- `greeks.phi` - Dividend sensitivity
- `greeks.bid_iv` - Bid implied volatility
- `greeks.mid_iv` - Mid implied volatility
- `greeks.ask_iv` - Ask implied volatility
- `greeks.smv_vol` - Smooth volatility
- `gex` - Gamma exposure (calculated metric)

### 🗄️ Database Schema
New columns added to `gex_table`:

**Difference Columns (11):**
- `greeks.delta_diff`
- `greeks.gamma_diff`
- `greeks.theta_diff`
- `greeks.vega_diff`
- `greeks.rho_diff`
- `greeks.phi_diff`
- `greeks.bid_iv_diff`
- `greeks.mid_iv_diff`
- `greeks.ask_iv_diff`
- `greeks.smv_vol_diff`
- `gex_diff`

**Percentage Change Columns (11):**
- `greeks.delta_pct_change`
- `greeks.gamma_pct_change`
- `greeks.theta_pct_change`
- `greeks.vega_pct_change`
- `greeks.rho_pct_change`
- `greeks.phi_pct_change`
- `greeks.bid_iv_pct_change`
- `greeks.mid_iv_pct_change`
- `greeks.ask_iv_pct_change`
- `greeks.smv_vol_pct_change`
- `gex_pct_change`

**Metadata Columns (2):**
- `prev_timestamp` - Timestamp of the previous data used for comparison
- `has_previous_data` - Boolean flag indicating if previous data was available

## Usage

### Automatic Integration
Greek differences are automatically calculated during data collection:

```bash
python gex_collector.py
```

The system will:
1. Fetch new option chain data
2. Calculate GEX for each option
3. **Calculate Greek differences vs. previous data**
4. Save all data including differences to database
5. Export comprehensive report to `greek_differences_latest.csv`

### Manual Calculation
You can also calculate differences for existing data:

```python
from greek_diff_calculator import GreekDifferenceCalculator
import pandas as pd

# Initialize calculator
calculator = GreekDifferenceCalculator('gex_data.db')

# Calculate differences for a dataframe
result_df = calculator.calculate_differences(your_dataframe)

# Get summary statistics
stats = calculator.get_summary_statistics(result_df)

# Find significant changes
significant = calculator.get_significant_changes(result_df)

# Export report
calculator.export_difference_report(result_df, 'my_report.csv')
```

### Analysis Examples

**Find options with largest GEX changes:**
```sql
SELECT option_type, strike, expiration_date, gex, gex_diff, gex_pct_change
FROM gex_table 
WHERE has_previous_data = 1 
ORDER BY ABS(gex_pct_change) DESC 
LIMIT 10;
```

**Find options with significant delta changes:**
```sql
SELECT option_type, strike, expiration_date, 
       [greeks.delta], [greeks.delta_diff], [greeks.delta_pct_change]
FROM gex_table 
WHERE ABS([greeks.delta_pct_change]) > 10.0 
ORDER BY ABS([greeks.delta_pct_change]) DESC;
```

**Track gamma changes over time:**
```sql
SELECT [greeks.updated_at], option_type, strike, 
       [greeks.gamma], [greeks.gamma_diff]
FROM gex_table 
WHERE option_type = 'call' 
AND strike = 5800 
AND expiration_date = '2025-11-01'
ORDER BY [greeks.updated_at] DESC;
```

## Reports Generated

### 1. Live Differences Report
- **File**: `greek_differences_latest.csv`
- **Generated**: Every data collection run
- **Content**: All options with their Greek differences
- **Sorting**: By absolute GEX percentage change (largest first)

### 2. Custom Reports
Use the `export_difference_report()` method to create custom reports with specific filtering or sorting.

## Significant Change Detection

The system can identify options with significant changes based on configurable thresholds:

**Default Thresholds:**
- Delta: 10% change
- Gamma: 15% change  
- Theta: 20% change
- Vega: 15% change
- GEX: 25% change

**Usage:**
```python
# Find significant changes with default thresholds
significant_changes = calculator.get_significant_changes(df)

# Use custom thresholds
custom_thresholds = {
    'greeks.delta': 5.0,  # 5% threshold for delta
    'gex': 15.0           # 15% threshold for GEX
}
significant_changes = calculator.get_significant_changes(df, custom_thresholds)
```

## Performance Notes

- **First Run**: No differences calculated (no previous data)
- **Subsequent Runs**: Differences calculated for matching options
- **Database Size**: Added ~24 columns, expect ~50% increase in database size
- **Query Performance**: Difference calculations use indexed columns for optimal performance

## Monitoring

The system logs Greek difference statistics during each collection:

```
INFO: Greek differences calculated: 2847/3150 options have previous data
INFO: Greek difference statistics calculated
DEBUG: gex_diff_stats: mean=1247.3456, std=8234.5677
```

## Data Quality

- **Missing Previous Data**: Difference columns will be `NULL` for new options
- **Zero Division**: Percentage changes handle zero/null previous values gracefully  
- **Data Validation**: System validates timestamp consistency and data integrity

## Integration with Dashboards

The enhanced CSV exports include all difference columns, making it easy to create dashboards showing:

- **Heat Maps**: Options with largest changes
- **Time Series**: Greek evolution over time
- **Alerts**: Options exceeding change thresholds
- **Comparison Views**: Current vs. previous snapshots

---

*This feature enhances the GEX collector with comprehensive Greek change tracking for better options market analysis.*