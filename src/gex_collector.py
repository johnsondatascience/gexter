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
from sqlalchemy import create_engine

from .config import Config
from .utils.logger import GEXLogger
from .api.tradier_api import TradierAPI
from .calculations.greek_diff_calculator import GreekDifferenceCalculator
from .calculations.black_scholes import BlackScholesCalculator
from .indicators.technical_indicators import SPXIndicatorCalculator


class GEXCollector:
    """Main GEX data collection and processing class"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = GEXLogger(config)
        self.api = TradierAPI(config.tradier_api_key)
        self.db_path = config.database_path

        # Initialize database engine/connection based on type
        if config.database_type == 'postgresql':
            conn_string = (
                f"postgresql://{config.postgres_user}:{config.postgres_password}@"
                f"{config.postgres_host}:{config.postgres_port}/{config.postgres_db}"
            )
            self.db_engine = create_engine(conn_string)
            self.greek_calculator = GreekDifferenceCalculator(
                db_engine=self.db_engine,
                db_type='postgresql'
            )
        else:
            self.db_engine = None
            self.greek_calculator = GreekDifferenceCalculator(
                db_path=config.database_path,
                db_type='sqlite'
            )

        self.indicator_calculator = SPXIndicatorCalculator(self.api)

        # Initialize Black-Scholes calculator for real-time greek calculations
        if config.calculate_greeks:
            self.bs_calculator = BlackScholesCalculator(
                risk_free_rate=config.risk_free_rate,
                dividend_yield=config.dividend_yield
            )
            self.logger.logger.info(f"Black-Scholes calculator enabled (r={config.risk_free_rate:.3f}, q={config.dividend_yield:.3f}, IV source={config.greek_iv_source})")
        else:
            self.bs_calculator = None
            self.logger.logger.info("Black-Scholes calculator disabled - using Tradier greeks only")

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
                # Use PostgreSQL with SQLAlchemy
                query = 'SELECT MAX("greeks.updated_at") AS max_updated_at FROM gex_table'
                result = pd.read_sql(query, self.db_engine)
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
            # Drop raw 'greeks' column if it exists (from json_normalize)
            # We only want the individual greeks.* columns
            if 'greeks' in df.columns:
                df = df.drop(columns=['greeks'])
                self.logger.logger.debug("Dropped raw 'greeks' column before database save")

            index_columns = ["greeks.updated_at", "expiration_date", "option_type", "strike"]

            # Check database type
            if self.config.database_type == 'postgresql':
                # Use PostgreSQL with existing engine

                # Remove duplicates within the DataFrame
                df_dedup = df.drop_duplicates(subset=index_columns, keep='last')

                if len(df) != len(df_dedup):
                    self.logger.logger.warning(f"Removed {len(df) - len(df_dedup)} duplicate records before saving")

                # Get existing records from database to avoid duplicates
                try:
                    existing_query = 'SELECT DISTINCT "greeks.updated_at", expiration_date, option_type, strike FROM gex_table'
                    existing_df = pd.read_sql(existing_query, self.db_engine)

                    if not existing_df.empty:
                        # Create a set of existing keys for fast lookup
                        existing_keys = set(
                            existing_df.apply(
                                lambda row: (row['greeks.updated_at'], row['expiration_date'],
                                           row['option_type'], row['strike']),
                                axis=1
                            )
                        )

                        # Filter out records that already exist
                        df_new = df_dedup[
                            df_dedup.apply(
                                lambda row: (row['greeks.updated_at'], row['expiration_date'],
                                           row['option_type'], row['strike']) not in existing_keys,
                                axis=1
                            )
                        ]

                        if len(df_dedup) != len(df_new):
                            self.logger.logger.warning(
                                f"Filtered out {len(df_dedup) - len(df_new)} records that already exist in database"
                            )
                        df_dedup = df_new
                except Exception as e:
                    self.logger.logger.warning(f"Could not check for existing records: {e}. Proceeding with save.")

                if df_dedup.empty:
                    self.logger.logger.info("No new records to save after filtering")
                    return True

                # Set index for proper database structure
                df_dedup.set_index(index_columns, inplace=True)

                # Save to database
                df_dedup.to_sql('gex_table', self.db_engine, if_exists='append', index=True)

                self.logger.logger.info(f"Saved {len(df_dedup)} records to PostgreSQL database")
                return True
            else:
                # Use SQLite (original code)
                conn = sqlite3.connect(self.db_path)

                # Remove duplicates within the DataFrame
                df_dedup = df.drop_duplicates(subset=index_columns, keep='last')

                if len(df) != len(df_dedup):
                    self.logger.logger.warning(f"Removed {len(df) - len(df_dedup)} duplicate records before saving")

                # Set index for proper database structure
                df_dedup.set_index(index_columns, inplace=True)

                # Save to database
                df_dedup.to_sql('gex_table', conn, if_exists='append', index=True)
                conn.close()

                self.logger.logger.info(f"Saved {len(df_dedup)} records to SQLite database")
                return True

        except Exception as e:
            self.logger.log_error("saving data to database", e)
            return False
    
    def export_to_csv(self) -> bool:
        """Export current database snapshot to CSV for dashboard"""
        try:
            # Get the most recent complete snapshot
            if self.config.database_type == 'postgresql':
                # PostgreSQL query - last 5 days
                query = """
                SELECT * FROM gex_table
                WHERE "greeks.updated_at" >= (
                    SELECT MAX("greeks.updated_at") - INTERVAL '5 days' FROM gex_table
                )
                ORDER BY option_type, strike, expiration_date
                """
                df = pd.read_sql(query, self.db_engine)
            else:
                # SQLite query
                conn = sqlite3.connect(self.db_path)
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
            # Get current price data for all configured underlying symbols
            underlying_prices = {}
            for symbol in self.config.underlying_symbols:
                price_data = self.get_current_underlying_price(symbol)
                if price_data:
                    underlying_prices[symbol] = price_data
                    self.save_spx_price_to_csv(price_data)

                    # Calculate technical indicators (SPX only for now)
                    if symbol == 'SPX':
                        self.logger.logger.info("Calculating SPX technical indicators...")
                        spx_indicators = self.indicator_calculator.calculate_spx_indicators(price_data['last'])
                        self.current_spx_indicators = spx_indicators

                        # Save indicators to dedicated CSV
                        self.indicator_calculator.save_indicators_to_csv(spx_indicators)

            # Get expiration dates for the next 30 days
            expiration_dates = self.get_trading_days_ahead(30)
            self.logger.logger.info(f"Collecting data for {len(expiration_dates)} expiration dates")

            all_chains = pd.DataFrame()

            # Collect option chains for each underlying symbol
            for symbol in self.config.underlying_symbols:
                self.logger.logger.info(f"Collecting {symbol} option chains...")

                for date in expiration_dates:
                    self.logger.logger.debug(f"Fetching option chain for {symbol} {date}")
                    chains = self.api.get_chains(symbol, date)
                
                    if not chains.empty:
                        # Add underlying symbol to identify the source
                        chains['underlying_symbol'] = symbol

                        # Calculate GEX
                        chains = self.calculate_gex(chains)

                        # Add price data for this underlying
                        price_data = underlying_prices.get(symbol)
                        if price_data:
                            # Current price
                            chains['spx_price'] = price_data.get('last')

                            # Daily OHLC
                            chains['spx_daily_open'] = price_data.get('daily_open')
                            chains['spx_daily_high'] = price_data.get('daily_high')
                            chains['spx_daily_low'] = price_data.get('daily_low')
                            chains['spx_daily_close'] = price_data.get('daily_close')

                            # Intraday 15-min bar OHLC
                            chains['spx_intraday_open'] = price_data.get('intraday_open')
                            chains['spx_intraday_high'] = price_data.get('intraday_high')
                            chains['spx_intraday_low'] = price_data.get('intraday_low')
                            chains['spx_intraday_close'] = price_data.get('intraday_close')

                            # Legacy columns for backward compatibility
                            chains['spx_open'] = price_data.get('open')
                            chains['spx_high'] = price_data.get('high')
                            chains['spx_low'] = price_data.get('low')
                            chains['spx_close'] = price_data.get('close')

                            # Other data
                            chains['spx_bid'] = price_data.get('bid')
                            chains['spx_ask'] = price_data.get('ask')
                            chains['spx_change'] = price_data.get('change')
                            chains['spx_change_pct'] = price_data.get('change_percentage')
                            chains['spx_prevclose'] = price_data.get('prevclose')

                        all_chains = pd.concat([all_chains, chains], ignore_index=True)
                    else:
                        self.logger.logger.warning(f"No option chain data for {symbol} {date}")
            
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

            # Note: Price data for each underlying is now added in the collection loop above

            # Calculate fresh greeks using Black-Scholes if enabled
            if self.bs_calculator and self.config.calculate_greeks:
                iv_column = f'greeks.{self.config.greek_iv_source}'
                self.logger.logger.info(f"Calculating fresh greeks using Black-Scholes with {iv_column}...")
                all_chains = self.bs_calculator.calculate_greeks_for_dataframe(
                    all_chains,
                    underlying_price_col='spx_price',
                    iv_col=iv_column,
                    prefix='calc_greeks.'
                )
                self.logger.logger.info("Fresh greeks calculation complete")

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
        """Get current SPX price data with both daily and intraday OHLC

        Note: This method is maintained for backward compatibility.
        Use get_current_underlying_price('SPX') for new code.
        """
        return self.get_current_underlying_price('SPX')

    def get_current_underlying_price(self, symbol: str) -> Optional[Dict]:
        """Get current underlying price data with both daily and intraday OHLC

        Args:
            symbol: The underlying symbol (e.g., 'SPX', 'XSP')

        Returns:
            Dictionary containing price data
        """
        try:
            self.logger.logger.info(f"Fetching current {symbol} price data...")

            # Get current quote for daily OHLC and current price
            quote = self.api.get_current_quote(symbol)

            if quote.empty:
                self.logger.logger.warning(f"No {symbol} price data received")
                return None

            # Extract daily OHLC data
            quote_data = quote.iloc[0]

            price_data = {
                'symbol': symbol,
                'timestamp': datetime.now(self.config.timezone).isoformat(),
                'last': quote_data.get('last'),
                # Daily OHLC
                'daily_open': quote_data.get('open'),
                'daily_high': quote_data.get('high'),
                'daily_low': quote_data.get('low'),
                'daily_close': quote_data.get('close'),
                # Keep old keys for backward compatibility
                'open': quote_data.get('open'),
                'high': quote_data.get('high'),
                'low': quote_data.get('low'),
                'close': quote_data.get('close'),
                'volume': quote_data.get('volume', 0),
                'change': quote_data.get('change'),
                'change_percentage': quote_data.get('change_percentage'),
                'prevclose': quote_data.get('prevclose'),
                'bid': quote_data.get('bid'),
                'ask': quote_data.get('ask')
            }

            # Fetch recent intraday bar for 15-minute OHLC
            try:
                intraday_data = self.api.get_intraday_data(symbol, interval='15min', days_back=1)
                if not intraday_data.empty:
                    # Get the most recent bar
                    latest_bar = intraday_data.iloc[-1]
                    price_data['intraday_open'] = latest_bar.get('open')
                    price_data['intraday_high'] = latest_bar.get('high')
                    price_data['intraday_low'] = latest_bar.get('low')
                    price_data['intraday_close'] = latest_bar.get('close')
                    self.logger.logger.debug(f"Fetched intraday bar: {latest_bar['datetime']}")
                else:
                    self.logger.logger.warning("No intraday bar data available")
                    price_data['intraday_open'] = None
                    price_data['intraday_high'] = None
                    price_data['intraday_low'] = None
                    price_data['intraday_close'] = None
            except Exception as e:
                self.logger.logger.warning(f"Failed to fetch intraday bar: {e}")
                price_data['intraday_open'] = None
                price_data['intraday_high'] = None
                price_data['intraday_low'] = None
                price_data['intraday_close'] = None

            # Store for use in CSV exports (maintain backward compatibility)
            if symbol == 'SPX':
                self.current_spx_price = price_data

            # Use the enhanced logging
            self.logger.log_spx_price(price_data)

            return price_data

        except Exception as e:
            self.logger.log_error(f"fetching {symbol} price data", e)
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