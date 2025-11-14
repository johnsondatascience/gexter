# GEX Database Analysis and Unification Plan

## Database Structure Overview

The SQLite database at `data/gex_data.db` contains **THREE separate tables** with different schemas and data ranges:

### Table Comparison

| Table Name | Row Count | Date Range | Column Count | Schema Version |
|------------|-----------|------------|--------------|----------------|
| `gex_table` | 4,547,942 | 2025-03-18 to 2025-11-14 | 70 columns | **Latest (Enhanced)** |
| `dgex_table` | 65,974 | 2025-03-18 to 2025-03-19 | 46 columns | **Basic** |
| `default.gex_table` | 13,936 | 2025-03-18 only | 46 columns | **Basic** |

## Schema Differences

### Common Base Columns (All 3 Tables)
All tables share the first 46 columns:
- Primary identifiers: `greeks.updated_at`, `expiration_date`, `option_type`, `strike`
- Option metadata: `symbol`, `description`, `type`, `underlying`, `root_symbol`
- Price data: `last`, `bid`, `ask`, `open`, `high`, `low`, `close`, `prevclose`
- Volume data: `volume`, `open_interest`, `average_volume`, `last_volume`
- Greeks: `greeks.delta`, `greeks.gamma`, `greeks.theta`, `greeks.vega`, `greeks.rho`, `greeks.phi`
- Implied volatility: `greeks.bid_iv`, `greeks.mid_iv`, `greeks.ask_iv`, `greeks.smv_vol`
- Calculated: `gex` (Gamma Exposure)

### Enhanced Columns (Only in `gex_table`)
The `gex_table` has **24 additional columns** for tracking Greek differences:

#### Difference Columns (11 metrics):
- `greeks.delta_diff`, `greeks.delta_pct_change`
- `greeks.gamma_diff`, `greeks.gamma_pct_change`
- `greeks.theta_diff`, `greeks.theta_pct_change`
- `greeks.vega_diff`, `greeks.vega_pct_change`
- `greeks.rho_diff`, `greeks.rho_pct_change`
- `greeks.phi_diff`, `greeks.phi_pct_change`
- `greeks.bid_iv_diff`, `greeks.bid_iv_pct_change`
- `greeks.mid_iv_diff`, `greeks.mid_iv_pct_change`
- `greeks.ask_iv_diff`, `greeks.ask_iv_pct_change`
- `greeks.smv_vol_diff`, `greeks.smv_vol_pct_change`
- `gex_diff`, `gex_pct_change`

#### Metadata Columns:
- `prev_timestamp` - Timestamp of previous data point for difference calculation
- `has_previous_data` - Boolean flag indicating if difference data is available

## Data Distribution Analysis

### Primary Data: `gex_table`
- **4.5M+ rows** spanning 8 months (March 18 to November 14, 2025)
- Contains complete historical data with Greek difference calculations
- This is the **active production table** used by the application
- References: [src/gex_collector.py:73](src/gex_collector.py#L73), [src/gex_collector.py:98](src/gex_collector.py#L98)

### Legacy Data: `dgex_table`
- **~66K rows** spanning only 2 days (March 18-19, 2025)
- Basic schema without difference calculations
- Appears to be an early test or migration table
- Referenced in: [data/gex_data.session.sql:1](data/gex_data.session.sql#L1)

### Legacy Data: `default.gex_table`
- **~14K rows** from a single timestamp (March 18, 2025)
- Basic schema without difference calculations
- Likely an initial data load or migration artifact
- Referenced in IDE metadata: [.idea/dataSources/*.xml](.idea/dataSources/5d49c6b0-0305-4faa-8f66-b5e45bf35131.xml#L1595)

## Issues Identified

1. **Schema Fragmentation**: Three tables with different schemas create confusion
2. **Duplicate Data**: March 18 data exists in all three tables
3. **Codebase References**: Code only references `gex_table`, but other tables exist
4. **SQL Session File**: Points to `dgex_table` which is outdated
5. **Migration Artifacts**: `default.gex_table` and `dgex_table` appear to be migration leftovers

## Unification Strategy

### Recommended Approach: Clean Up Legacy Tables

Since `gex_table` contains:
- All historical data (March 18 - November 14)
- Enhanced schema with difference calculations
- All data from the legacy tables (their date ranges are subsets)

**Recommended Actions:**

1. ✅ **Keep**: `gex_table` (primary production table)
2. ❌ **Drop**: `dgex_table` (superseded by gex_table)
3. ❌ **Drop**: `default.gex_table` (migration artifact)
4. 🔧 **Update**: SQL session file to reference `gex_table`
5. 🔧 **Clean**: Empty database file at root (`gex_data.db` - 0 bytes)

### Data Overlap Analysis Results

**IMPORTANT FINDINGS:**

✅ **default.gex_table**: All 13,936 records are already in `gex_table` - **safe to drop**

⚠️  **dgex_table**: Contains **2,508 unique records** NOT in `gex_table` - **requires migration**

The unique records in `dgex_table` are all from timestamp `2025-03-18 20:00:10` and represent options that were not captured in the initial `gex_table` load.

### Automated Unification Script

A complete unification script has been created at [scripts/unify_database.py](scripts/unify_database.py) that performs:

1. **Backup Creation**: Automatic timestamped backup before any changes
2. **Data Migration**: Migrates 2,508 unique records from `dgex_table` to `gex_table`
3. **Table Cleanup**: Drops legacy tables (`dgex_table`, `default.gex_table`)
4. **Space Reclamation**: Runs VACUUM to reclaim disk space
5. **Verification**: Validates migration success before dropping tables

**To run the unification:**
```bash
python scripts/unify_database.py
```

The script includes safety checks and will create a backup before making any changes.

## Database File Cleanup

There are also two database files:
- `data/gex_data.db` (2.5 GB) - **Active database**
- `gex_data.db` (0 bytes) - **Empty file to remove**

## Benefits of Unification

1. **Simplified Schema**: Single table with consistent structure
2. **Reduced Confusion**: Clear which table is authoritative
3. **Smaller Database**: Removing duplicate data and vacuuming
4. **Code Clarity**: All references point to same table
5. **Better Performance**: Fewer tables to index and query

## Actions Completed

✅ **Analysis Scripts Created**:
- [scripts/analyze_table_differences.py](scripts/analyze_table_differences.py) - Detailed table comparison
- [scripts/unify_database.py](scripts/unify_database.py) - Automated unification with backup

✅ **SQL Session File Updated**:
- [data/gex_data.session.sql](data/gex_data.session.sql) - Now references `gex_table` instead of `dgex_table`

✅ **Documentation Created**:
- This analysis document with complete findings

## Next Steps to Execute Unification

### Step 1: Run the Unification Script
```bash
python scripts/unify_database.py
```

This will:
- Create automatic backup
- Migrate 2,508 unique records
- Drop legacy tables
- Vacuum database
- Show final statistics

### Step 2: Remove Empty Database File
```bash
# After verifying the unified database works correctly
rm gex_data.db  # The 0-byte file in root directory
```

### Step 3: Verify Application
```bash
# Test the application to ensure it works with the unified database
python run_gex_collector.py --force
```

## Post-Unification Benefits

Once completed, you will have:
- ✅ Single unified `gex_table` with all historical data
- ✅ ~2,508 additional records from March 18
- ✅ Smaller database file (after VACUUM)
- ✅ Clear, consistent schema
- ✅ Automatic backup for safety
- ✅ Updated SQL references
