"""
Greek Difference Calculator

Calculates differences between current Greeks and the most recent available 
for each option type/strike/expiration combination.
"""

import pandas as pd
import sqlite3
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger('gex_collector')


class GreekDifferenceCalculator:
    """Calculate Greek differences for option data"""
    
    GREEK_COLUMNS = [
        'greeks.delta', 'greeks.gamma', 'greeks.theta', 'greeks.vega', 
        'greeks.rho', 'greeks.phi', 'greeks.bid_iv', 'greeks.mid_iv', 
        'greeks.ask_iv', 'greeks.smv_vol', 'gex'
    ]
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_previous_data(self, current_timestamp: str) -> pd.DataFrame:
        """Get the most recent data before the current timestamp for each option"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Query to get the most recent previous data for each option
            query = """
            WITH previous_data AS (
                SELECT 
                    option_type,
                    strike,
                    expiration_date,
                    MAX([greeks.updated_at]) as prev_timestamp
                FROM gex_table 
                WHERE [greeks.updated_at] < ?
                GROUP BY option_type, strike, expiration_date
            )
            SELECT g.*
            FROM gex_table g
            INNER JOIN previous_data p ON 
                g.option_type = p.option_type AND
                g.strike = p.strike AND
                g.expiration_date = p.expiration_date AND
                g.[greeks.updated_at] = p.prev_timestamp
            """
            
            # Convert timestamp to string if it's a pandas Timestamp
            if hasattr(current_timestamp, 'isoformat'):
                current_timestamp = current_timestamp.isoformat()
            elif not isinstance(current_timestamp, str):
                current_timestamp = str(current_timestamp)

            previous_df = pd.read_sql(query, conn, params=[current_timestamp])
            conn.close()
            
            logger.info(f"Retrieved {len(previous_df)} previous records for comparison")
            return previous_df
            
        except Exception as e:
            logger.error(f"Error retrieving previous data: {e}")
            return pd.DataFrame()
    
    def calculate_differences(self, current_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Greek differences for the current dataframe"""
        if current_df.empty:
            return current_df
        
        # Get the most recent timestamp from current data
        current_timestamp = current_df['greeks.updated_at'].max()
        logger.info(f"Calculating differences for timestamp: {current_timestamp}")
        
        # Get previous data for comparison
        previous_df = self.get_previous_data(current_timestamp)
        
        if previous_df.empty:
            logger.warning("No previous data found for comparison")
            # Add difference columns with None values
            for col in self.GREEK_COLUMNS:
                if col in current_df.columns:
                    current_df[f'{col}_diff'] = None
                    current_df[f'{col}_pct_change'] = None
            return current_df
        
        # Create merge keys
        merge_keys = ['option_type', 'strike', 'expiration_date']
        
        # Prepare previous data for merging
        prev_subset = previous_df[merge_keys + self.GREEK_COLUMNS + ['greeks.updated_at']].copy()
        prev_subset = prev_subset.add_suffix('_prev')
        
        # Rename merge keys back (remove suffix)
        for key in merge_keys:
            prev_subset[key] = prev_subset[f'{key}_prev']
            prev_subset.drop(f'{key}_prev', axis=1, inplace=True)
        
        # Merge current data with previous data
        merged_df = current_df.merge(prev_subset, on=merge_keys, how='left')
        
        # Calculate differences and percentage changes
        for col in self.GREEK_COLUMNS:
            if col in current_df.columns:
                current_col = col
                prev_col = f'{col}_prev'
                diff_col = f'{col}_diff'
                pct_change_col = f'{col}_pct_change'
                
                if prev_col in merged_df.columns:
                    # Calculate absolute difference
                    merged_df[diff_col] = merged_df[current_col] - merged_df[prev_col]
                    
                    # Calculate percentage change (handle division by zero)
                    merged_df[pct_change_col] = merged_df.apply(
                        lambda row: (
                            ((row[current_col] - row[prev_col]) / row[prev_col] * 100) 
                            if pd.notna(row[prev_col]) and row[prev_col] != 0 
                            else None
                        ), axis=1
                    )
                else:
                    # No previous data available
                    merged_df[diff_col] = None
                    merged_df[pct_change_col] = None
        
        # Add metadata about the comparison
        merged_df['prev_timestamp'] = merged_df.get('greeks.updated_at_prev', None)
        merged_df['has_previous_data'] = merged_df['prev_timestamp'].notna()
        
        # Clean up temporary columns
        columns_to_drop = [col for col in merged_df.columns if col.endswith('_prev')]
        merged_df.drop(columns=columns_to_drop, inplace=True)
        
        # Log statistics
        total_options = len(merged_df)
        options_with_prev = merged_df['has_previous_data'].sum()
        logger.info(f"Greek differences calculated: {options_with_prev}/{total_options} options have previous data")
        
        return merged_df
    
    def get_summary_statistics(self, df: pd.DataFrame) -> Dict:
        """Get summary statistics for Greek differences"""
        if df.empty:
            return {}
        
        stats = {}
        
        for col in self.GREEK_COLUMNS:
            diff_col = f'{col}_diff'
            pct_change_col = f'{col}_pct_change'
            
            if diff_col in df.columns:
                # Absolute difference statistics
                diff_data = df[diff_col].dropna()
                if not diff_data.empty:
                    stats[f'{col}_diff_stats'] = {
                        'count': len(diff_data),
                        'mean': diff_data.mean(),
                        'std': diff_data.std(),
                        'min': diff_data.min(),
                        'max': diff_data.max(),
                        'median': diff_data.median()
                    }
                
                # Percentage change statistics
                pct_data = df[pct_change_col].dropna()
                if not pct_data.empty:
                    stats[f'{col}_pct_change_stats'] = {
                        'count': len(pct_data),
                        'mean': pct_data.mean(),
                        'std': pct_data.std(),
                        'min': pct_data.min(),
                        'max': pct_data.max(),
                        'median': pct_data.median()
                    }
        
        return stats
    
    def get_significant_changes(self, df: pd.DataFrame, 
                              thresholds: Dict[str, float] = None) -> pd.DataFrame:
        """Identify options with significant Greek changes"""
        if df.empty:
            return df
        
        # Default thresholds for significant changes (percentage)
        if thresholds is None:
            thresholds = {
                'greeks.delta': 10.0,   # 10% change in delta
                'greeks.gamma': 15.0,   # 15% change in gamma
                'greeks.theta': 20.0,   # 20% change in theta
                'greeks.vega': 15.0,    # 15% change in vega
                'gex': 25.0             # 25% change in GEX
            }
        
        significant_changes = df.copy()
        
        # Create flags for significant changes
        for greek, threshold in thresholds.items():
            pct_change_col = f'{greek}_pct_change'
            flag_col = f'{greek}_significant_change'
            
            if pct_change_col in df.columns:
                significant_changes[flag_col] = (
                    df[pct_change_col].fillna(0).abs() >= threshold
                )
        
        # Filter to only rows with at least one significant change
        flag_columns = [col for col in significant_changes.columns if col.endswith('_significant_change')]
        if flag_columns:
            has_significant_change = significant_changes[flag_columns].any(axis=1)
            significant_changes = significant_changes[has_significant_change]
        
        return significant_changes
    
    def export_difference_report(self, df: pd.DataFrame, output_path: str = 'greek_differences_report.csv'):
        """Export a comprehensive Greek differences report"""
        if df.empty:
            logger.warning("No data to export for differences report")
            return False
        
        try:
            # Select relevant columns for the report
            report_columns = [
                'greeks.updated_at', 'expiration_date', 'option_type', 'strike',
                'prev_timestamp', 'has_previous_data'
            ]
            
            # Add all Greek columns and their differences
            for col in self.GREEK_COLUMNS:
                if col in df.columns:
                    report_columns.extend([col, f'{col}_diff', f'{col}_pct_change'])
            
            # Create report dataframe
            report_df = df[report_columns].copy()
            
            # Sort by absolute GEX change (descending)
            if 'gex_pct_change' in report_df.columns:
                report_df['abs_gex_pct_change'] = report_df['gex_pct_change'].fillna(0).abs()
                report_df = report_df.sort_values('abs_gex_pct_change', ascending=False)
                report_df.drop('abs_gex_pct_change', axis=1, inplace=True)
            
            # Export to CSV
            report_df.to_csv(output_path, index=False)
            logger.info(f"Greek differences report exported to {output_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting differences report: {e}")
            return False


def calculate_greek_differences_for_dataframe(df: pd.DataFrame, db_path: str) -> pd.DataFrame:
    """Convenience function to calculate Greek differences for a dataframe"""
    calculator = GreekDifferenceCalculator(db_path)
    return calculator.calculate_differences(df)