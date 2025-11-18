#!/usr/bin/env python3
"""
GEX (Gamma Exposure) Data Collector - Production Version

This script collects SPX option chain data from Tradier API and calculates
gamma exposure for each strike and expiration date. Designed for production
deployment with error handling, logging, and scheduling capabilities.
"""

import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import argparse
from dotenv import load_dotenv

from .config import Config
from .utils.logger import GEXLogger
from .api.tradier_api import TradierAPI
from .calculations.greek_diff_calculator import GreekDifferenceCalculator
from .indicators.technical_indicators import SPXIndicatorCalculator


class GEXCollector:
    """Main GEX data collection and processing class"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = GEXLogger(config)
        self.api = TradierAPI(config.tradier_api_key)
        self.db_path = config.database_path
        self.greek_calculator = GreekDifferenceCalculator(config.database_path)
        self.indicator_calculator = SPXIndicatorCalculator(self.api)
        self.current_spx_price = None
        self.current_spx_indicators = None
    
    def get_trading_days_ahead(self, days: int = 30) -> List[str]:
        """Get list of trading days (weekdays) for the next N days"""
        trading_days = []
        current_date = datetime.now(self.config.timezone).date()
        
        for i in range(days):
            check_date = current_date + timedelta(days=i)
            # Skip weekends (Saturday=5, Sunday=6)
            if check_date.weekday() < 5:
                trading_days.append(check_date.strftime('%Y-%m-%d'))
        
        return trading_days
    
    def calculate_gex(self, chains_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate gamma exposure for option chains"""
        if chains_df.empty:
            return chains_df
        
        # Calculate GEX: Strike * Gamma * Open Interest * 100
        chains_df["gex"] = (
            chains_df["strike"] * 
            chains_df["greeks.gamma"] * 
            chains_df["open_interest"] * 100
        )
        
        # Put options have negative GEX
        chains_df.loc[chains_df["option_type"] == "put", "gex"] *= -1
        
        return chains_df
    
    def get_latest_timestamp_from_db(self) -> Optional[str]:
        """Get the most recent timestamp from the database"""
        try:
            if self.config.database_type == 'postgresql':
                # Use PostgreSQL
                import psycopg2
                conn = psycopg2.connect(
                    host=self.config.postgres_host,
                    port=self.config.postgres_port,
                    database=self.config.postgres_db,
                    user=self.config.postgres_user,
                    password=self.config.postgres_password
                )
                query = 'SELECT MAX("greeks.updated_at") AS max_updated_at FROM gex_table'
                result = pd.read_sql(query, conn)
                conn.close()
            else:
                # Use SQLite
                conn = sqlite3.connect(self.db_path)
                query = "SELECT MAX([greeks.updated_at]) AS max_updated_at FROM gex_table"
                result = pd.read_sql(query, conn)
                conn.close()

            if not result.empty and result['max_updated_at'].iloc[0]:
                return result['max_updated_at'].iloc[0]
        except Exception as e:
            self.logger.log_error("getting latest timestamp from database", e)

        return None
    
    def save_to_database(self, df: pd.DataFrame) -> bool:
        """Save dataframe to database (SQLite or PostgreSQL)"""
        if df.empty:
            self.logger.logger.warning("No data to save to database")
            return False

        try:
            # Check database type
            if self.config.database_type == 'postgresql':
                # Use PostgreSQL
                import psycopg2
                from sqlalchemy import create_engine

                # Create connection string
                conn_string = f"postgresql://{self.config.postgres_user}:{self.config.postgres_password}@{self.config.postgres_host}:{self.config.postgres_port}/{self.config.postgres_db}"
                engine = create_engine(conn_string)

                # Remove duplicates before setting index
                index_columns = ["greeks.updated_at", "expiration_date", "option_type", "strike"]
                df_dedup = df.drop_duplicates(subset=index_columns, keep='last')

                if len(df) != len(df_dedup):
                    self.logger.logger.warning(f"Removed {len(df) - len(df_dedup)} duplicate records before saving")

                # Set index for proper database structure
                df_dedup.set_index(index_columns, inplace=True)

                # Save to database
                df_dedup.to_sql('gex_table', engine, if_exists='append', index=True)
                engine.dispose()

                self.logger.logger.info(f"Saved {len(df_dedup)} records to PostgreSQL database")
                return True
            else:
                # Use SQLite (original code)
                conn = sqlite3.connect(self.db_path)

                # Set index for proper database structure
                index_columns = ["greeks.updated_at", "expiration_date", "option_type", "strike"]
                df.set_index(index_columns, inplace=True)

                # Save to database
                df.to_sql('gex_table', conn, if_exists='append', index=True)
                conn.close()

                self.logger.logger.info(f"Saved {len(df)} records to SQLite database")
                return True

        except Exception as e:
            self.logger.log_error("saving data to database", e)
            return False
    
    def export_to_csv(self) -> bool:
        """Export current database snapshot to CSV for dashboard"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get the most recent complete snapshot
            query = """
            SELECT * FROM gex_table 
            WHERE [greeks.updated_at] >= (
                SELECT DATE(MAX([greeks.updated_at]), '-5 days') FROM gex_table
            )
            ORDER BY option_type, strike, expiration_date
            """
            
            df = pd.read_sql(query, conn)
            conn.close()
            
            if df.empty:
                self.logger.logger.warning("No data found for CSV export")
                return False
            
            # Log snapshot information
            snapshot_timestamp = df['greeks.updated_at'].iloc[0]
            total_options = len(df)
            options_with_prev_data = df['has_previous_data'].sum() if 'has_previous_data' in df.columns else 0
            
            self.logger.logger.info(f"Exporting snapshot from {snapshot_timestamp}")
            self.logger.logger.info(f"Snapshot contains {total_options} options")
            if 'has_previous_data' in df.columns:
                self.logger.logger.info(f"Options with difference data: {options_with_prev_data}/{total_options}")
            
            # Add SPX price columns to the snapshot if available
            if self.current_spx_price:
                for key, value in self.current_spx_price.items():
                    if key != 'symbol':  # Don't override existing symbol column
                        df[f'spx_{key}'] = value
                
                self.logger.logger.info(f"Added SPX price data to snapshot: ${self.current_spx_price['last']:.2f}")
            
            # Add SPX technical indicators to the snapshot if available
            if self.current_spx_indicators:
                for key, value in self.current_spx_indicators.items():
                    df[key] = value
                
                indicators_count = len([k for k in self.current_spx_indicators.keys() if not pd.isna(self.current_spx_indicators[k])])
                self.logger.logger.info(f"Added {indicators_count} SPX technical indicators to snapshot")
            
            # Export full snapshot to CSV
            output_path = os.path.join('output', 'gex.csv')
            os.makedirs('output', exist_ok=True)
            df.to_csv(output_path, index=False)
            self.logger.logger.info(f"Exported snapshot with {len(df)} records to {output_path}")
            
            # Create a summary CSV with key metrics
            self.create_summary_csv(df)
            
            return True
            
        except Exception as e:
            self.logger.log_error("exporting to CSV", e)
            return False
    
    def create_summary_csv(self, df: pd.DataFrame) -> bool:
        """Create a summary CSV with key metrics and largest changes"""
        try:
            if df.empty:
                return False
            
            # Define key columns for summary
            key_columns = [
                'greeks.updated_at', 'expiration_date', 'option_type', 'strike',
                'last', 'bid', 'ask', 'open_interest', 'volume',
                'greeks.delta', 'greeks.gamma', 'greeks.theta', 'greeks.vega',
                'gex', 'has_previous_data'
            ]
            
            # Add SPX price columns if they exist
            spx_columns = [col for col in df.columns if col.startswith('spx_')]
            key_columns.extend(spx_columns)
            
            # Add SPX indicator columns if they exist
            indicator_columns = [col for col in df.columns if col.startswith('spx_') and ('ema' in col or 'above' in col or 'trend' in col)]
            # Only add if not already in spx_columns
            new_indicator_columns = [col for col in indicator_columns if col not in spx_columns]
            key_columns.extend(new_indicator_columns)
            
            # Add difference columns if they exist
            diff_columns = [col for col in df.columns if col.endswith('_diff') or col.endswith('_pct_change')]
            summary_columns = key_columns + diff_columns + ['prev_timestamp']
            
            # Filter to existing columns
            available_columns = [col for col in summary_columns if col in df.columns]
            
            # Create summary dataframe
            summary_df = df[available_columns].copy()
            
            # Sort by absolute GEX change if available, otherwise by GEX
            if 'gex_pct_change' in summary_df.columns:
                summary_df['abs_gex_pct_change'] = summary_df['gex_pct_change'].fillna(0).abs()
                summary_df = summary_df.sort_values('abs_gex_pct_change', ascending=False)
                summary_df.drop('abs_gex_pct_change', axis=1, inplace=True)
            else:
                summary_df = summary_df.sort_values('gex', key=lambda x: x.abs(), ascending=False)
            
            # Export summary
            summary_path = os.path.join('output', 'gex_summary.csv')
            summary_df.to_csv(summary_path, index=False)
            self.logger.logger.info(f"Exported summary with {len(summary_df)} records to {summary_path}")
            
            # Log top changes if difference data is available
            if 'gex_pct_change' in summary_df.columns:
                top_changes = summary_df[summary_df['has_previous_data'] == True].head(5)
                if not top_changes.empty:
                    self.logger.logger.info("Top 5 GEX changes:")
                    for idx, row in top_changes.iterrows():
                        change = row['gex_pct_change']
                        if pd.notna(change):
                            self.logger.logger.info(f"  {row['option_type']} {row['strike']} {row['expiration_date']}: {change:.1f}%")
            
            return True
            
        except Exception as e:
            self.logger.log_error("creating summary CSV", e)
            return False
    
    def collect_data(self, force: bool = False) -> bool:
        """Main data collection method"""
        self.logger.log_start("data collection")
        
        # Check if we're in trading hours (unless forced)
        if not force:
            is_trading_day = self.config.is_trading_day()
            is_trading_hours = self.config.is_trading_hours()
            self.logger.log_market_status(is_trading_hours, is_trading_day)
            
            # if not (is_trading_day and is_trading_hours):
            #     self.logger.logger.info("Outside trading hours, skipping data collection")
            #     return True
        
        try:
            # Get current SPX price data first
            spx_price_data = self.get_current_spx_price()
            if spx_price_data:
                self.save_spx_price_to_csv(spx_price_data)
                
                # Calculate technical indicators
                self.logger.logger.info("Calculating SPX technical indicators...")
                spx_indicators = self.indicator_calculator.calculate_spx_indicators(spx_price_data['last'])
                self.current_spx_indicators = spx_indicators
                
                # Save indicators to dedicated CSV
                self.indicator_calculator.save_indicators_to_csv(spx_indicators)
            
            # Get expiration dates for the next 30 days
            expiration_dates = self.get_trading_days_ahead(30)
            self.logger.logger.info(f"Collecting data for {len(expiration_dates)} expiration dates")
            
            all_chains = pd.DataFrame()
            
            for date in expiration_dates:
                self.logger.logger.debug(f"Fetching option chain for {date}")
                chains = self.api.get_chains("SPX", date)
                
                if not chains.empty:
                    # Calculate GEX
                    chains = self.calculate_gex(chains)
                    all_chains = pd.concat([all_chains, chains], ignore_index=True)
                else:
                    self.logger.logger.warning(f"No option chain data for {date}")
            
            if all_chains.empty:
                self.logger.logger.warning("No option chain data collected")
                return False
            
            # Check if we have new data compared to database
            latest_db_timestamp = self.get_latest_timestamp_from_db()
            if not all_chains.empty:
                latest_api_timestamp = all_chains['greeks.updated_at'].max()

                if latest_db_timestamp:
                    self.logger.logger.info(f"Latest DB timestamp: {latest_db_timestamp}")
                    self.logger.logger.info(f"Latest API timestamp: {latest_api_timestamp}")

                    if pd.to_datetime(latest_db_timestamp) >= pd.to_datetime(latest_api_timestamp):
                        self.logger.logger.info("No new data available - greeks.updated_at has not changed. Skipping collection.")
                        return True
                    else:
                        self.logger.logger.info("New data detected - greeks.updated_at has been updated. Proceeding with collection.")
                else:
                    self.logger.logger.info("No existing data in database. Proceeding with initial collection.")
            
            # Add SPX price data to all records
            if self.current_spx_price:
                self.logger.logger.info("Adding SPX price data to option chains...")
                all_chains['spx_price'] = self.current_spx_price.get('last')
                all_chains['spx_open'] = self.current_spx_price.get('open')
                all_chains['spx_high'] = self.current_spx_price.get('high')
                all_chains['spx_low'] = self.current_spx_price.get('low')
                all_chains['spx_close'] = self.current_spx_price.get('close')
                all_chains['spx_bid'] = self.current_spx_price.get('bid')
                all_chains['spx_ask'] = self.current_spx_price.get('ask')
                all_chains['spx_change'] = self.current_spx_price.get('change')
                all_chains['spx_change_pct'] = self.current_spx_price.get('change_percentage')
                all_chains['spx_prevclose'] = self.current_spx_price.get('prevclose')
                self.logger.logger.info(f"Added SPX price ${self.current_spx_price.get('last'):.2f} to {len(all_chains)} records")

            # Calculate Greek differences before saving
            self.logger.logger.info("Calculating Greek differences...")
            all_chains = self.greek_calculator.calculate_differences(all_chains)

            # Log Greek difference statistics
            stats = self.greek_calculator.get_summary_statistics(all_chains)
            if stats:
                self.logger.logger.info("Greek difference statistics calculated")
                for greek, stat_data in stats.items():
                    if 'mean' in stat_data:
                        self.logger.logger.debug(f"{greek}: mean={stat_data['mean']:.4f}, std={stat_data['std']:.4f}")

            # Export differences report
            self.greek_calculator.export_difference_report(all_chains, 'greek_differences_latest.csv')

            # Save new data
            success = self.save_to_database(all_chains)
            if success:
                # Export to CSV for dashboard
                self.export_to_csv()
                
                # Log completion with market context
                if self.current_spx_price:
                    self.logger.log_spx_price_summary(self.current_spx_price, len(all_chains))
                
                self.logger.log_completion("data collection", len(all_chains))
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.log_error("data collection", e)
            return False
    
    def update_spx_prices(self) -> bool:
        """Update SPX historical prices"""
        self.logger.log_start("SPX price update")
        
        try:
            # Get SPX prices for the last 6 months
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
            
            prices = self.api.get_historical_quotes(['SPX'], start_date, end_date, 'daily')
            
            if not prices.empty:
                # Clean up columns
                prices.drop(['symbol', 'volume'], axis=1, inplace=True, errors='ignore')
                output_path = os.path.join('output', 'spx_prices.csv')
                prices.to_csv(output_path, index=False)
                
                self.logger.log_completion("SPX price update", len(prices))
                return True
            else:
                self.logger.logger.warning("No SPX price data retrieved")
                return False
                
        except Exception as e:
            self.logger.log_error("SPX price update", e)
            return False
    
    def get_current_spx_price(self) -> Optional[Dict]:
        """Get current SPX OHLC price data"""
        try:
            self.logger.logger.info("Fetching current SPX price data...")
            
            spx_quote = self.api.get_current_quote('SPX')
            
            if spx_quote.empty:
                self.logger.logger.warning("No SPX price data received")
                return None
            
            # Extract OHLC data
            spx_data = spx_quote.iloc[0]
            
            price_data = {
                'symbol': 'SPX',
                'timestamp': datetime.now(self.config.timezone).isoformat(),
                'last': spx_data.get('last'),
                'open': spx_data.get('open'),
                'high': spx_data.get('high'), 
                'low': spx_data.get('low'),
                'close': spx_data.get('close'),
                'volume': spx_data.get('volume', 0),
                'change': spx_data.get('change'),
                'change_percentage': spx_data.get('change_percentage'),
                'prevclose': spx_data.get('prevclose'),
                'bid': spx_data.get('bid'),
                'ask': spx_data.get('ask')
            }
            
            # Store for use in CSV exports
            self.current_spx_price = price_data
            
            # Use the enhanced logging
            self.logger.log_spx_price(price_data)
            
            return price_data
            
        except Exception as e:
            self.logger.log_error("fetching SPX price data", e)
            return None
    
    def save_spx_price_to_csv(self, price_data: Dict) -> bool:
        """Save SPX price data to CSV file"""
        try:
            if not price_data:
                return False
            
            # Create DataFrame from price data
            price_df = pd.DataFrame([price_data])
            
            # Try to load existing data and append
            spx_file = os.path.join('output', 'spx_intraday_prices.csv')
            os.makedirs('output', exist_ok=True)
            try:
                existing_df = pd.read_csv(spx_file)
                combined_df = pd.concat([existing_df, price_df], ignore_index=True)
            except FileNotFoundError:
                combined_df = price_df

            # Keep only last 1000 records to prevent file from growing too large
            if len(combined_df) > 1000:
                combined_df = combined_df.tail(1000)

            # Save to CSV
            combined_df.to_csv(spx_file, index=False)
            
            self.logger.logger.info(f"SPX price data saved to {spx_file}")
            return True
            
        except Exception as e:
            self.logger.log_error("saving SPX price to CSV", e)
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='GEX Data Collector')
    parser.add_argument('--force', action='store_true', 
                       help='Force data collection outside trading hours')
    parser.add_argument('--prices-only', action='store_true',
                       help='Only update SPX prices')
    parser.add_argument('--env-file', default='.env',
                       help='Path to environment file (default: .env)')
    
    args = parser.parse_args()
    
    # Load environment variables
    if os.path.exists(args.env_file):
        load_dotenv(args.env_file)
    else:
        print(f"Warning: Environment file {args.env_file} not found")
    
    try:
        # Initialize configuration and collector
        config = Config()
        collector = GEXCollector(config)
        
        success = True
        
        if args.prices_only:
            success = collector.update_spx_prices()
        else:
            # Collect GEX data
            success = collector.collect_data(force=args.force)
            
            # Also update SPX prices
            if success:
                collector.update_spx_prices()
        
        if success:
            collector.logger.logger.info("All operations completed successfully")
            sys.exit(0)
        else:
            collector.logger.logger.error("One or more operations failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()