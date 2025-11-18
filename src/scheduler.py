#!/usr/bin/env python3
"""
GEX Collector Scheduler

Runs the GEX collector at regular intervals during trading hours.
Prevents continuous restarts and only collects data when appropriate.
"""

import time
import schedule
import signal
import sys
from datetime import datetime
from typing import Optional

from .config import Config
from .gex_collector import GEXCollector
from .utils.logger import GEXLogger
from .api.tradier_api import TradierAPI
from .signals.market_internals import MarketInternalsCollector


class GEXScheduler:
    """Scheduler for GEX data collection"""

    def __init__(self, interval_minutes: int = 30, collect_internals: bool = True):
        """
        Initialize the scheduler

        Args:
            interval_minutes: How often to run the collector (default: 30 minutes)
            collect_internals: Whether to collect market internals (default: True)
        """
        self.config = Config()
        self.logger = GEXLogger(self.config)
        self.collector = GEXCollector(self.config)
        self.interval_minutes = interval_minutes
        self.collect_internals = collect_internals
        self.running = True

        # Initialize internals collector if enabled
        if self.collect_internals:
            self.api = TradierAPI(self.config.tradier_api_key)
            self.internals_collector = MarketInternalsCollector(self.api)
            self.logger.logger.info("Market internals collection enabled")

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        sys.exit(0)

    def run_collection(self):
        """Run the data collection job"""
        try:
            # Check if we're in trading hours
            is_trading_day = self.config.is_trading_day()
            is_trading_hours = self.config.is_trading_hours()

            current_time = datetime.now(self.config.timezone).strftime('%Y-%m-%d %H:%M:%S %Z')

            if is_trading_day and is_trading_hours:
                self.logger.logger.info(f"[{current_time}] Running scheduled data collection...")

                # Collect GEX data
                self.collector.collect_data(force=False)

                # Collect market internals if enabled
                if self.collect_internals:
                    self._collect_market_internals()
            else:
                trading_status = "outside trading hours" if is_trading_day else "not a trading day"
                self.logger.logger.info(f"[{current_time}] Skipping collection ({trading_status})")

        except Exception as e:
            self.logger.log_error("scheduled collection", e)

    def _collect_market_internals(self):
        """Collect market internals and save to database"""
        try:
            from .signals.market_internals import MarketInternalsSignalGenerator
            import psycopg2

            # Default watchlist for internals
            watchlist = [
                'AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'JPM', 'BAC', 'UNH', 'JNJ', 'LLY',
                'AMZN', 'TSLA', 'HD', 'MCD', 'BA', 'CAT', 'XOM', 'CVX', 'LIN', 'NEE',
                'TMUS', 'VZ', 'PLD', 'AMT'
            ]

            self.logger.logger.info("Collecting market internals...")

            # Collect internals from stock universe
            internals = self.internals_collector.collect_from_stock_universe(watchlist)

            if not internals:
                self.logger.logger.warning("Failed to collect market internals")
                return

            # Collect sector breadth
            sector_breadth = self.internals_collector.collect_sector_breadth()
            if sector_breadth:
                internals.sector_breadth = sector_breadth

            # Try to get breadth indices
            indices = self.internals_collector.collect_from_indices()
            if indices:
                internals.tick = indices.get('tick')
                internals.trin = indices.get('trin')
                internals.add = indices.get('add')

            # Connect to database
            conn = psycopg2.connect(
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_db,
                user=self.config.postgres_user,
                password=self.config.postgres_password
            )

            # Calculate cumulative A/D line
            net_ad = internals.advances - internals.declines
            cumulative_ad = self.internals_collector.calculate_cumulative_ad_line(net_ad, conn)
            internals.cumulative_ad_line = cumulative_ad

            # Save to database
            self._save_internals_to_database(internals, conn, len(watchlist))

            # Log summary
            self.logger.logger.info(f"Market internals collected: "
                                  f"Breadth {internals.breadth_ratio:+.1%}, "
                                  f"Volume {internals.volume_ratio:+.1%}")

            if sector_breadth:
                self.logger.logger.info(f"Sector breadth: {sector_breadth.sector_breadth_ratio:+.1%}")

            conn.close()

        except Exception as e:
            self.logger.log_error("collecting market internals", e)

    def _save_internals_to_database(self, internals, conn, stock_universe_size: int):
        """Save market internals to database"""
        try:
            cursor = conn.cursor()

            query = """
            INSERT INTO market_internals (
                timestamp, advances, declines, unchanged,
                advance_decline_ratio, breadth_ratio,
                up_volume, down_volume, up_down_volume_ratio, volume_ratio,
                tick, trin, add_index,
                cumulative_ad_line, breadth_thrust,
                data_source, stock_universe_size
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (timestamp) DO UPDATE SET
                advances = EXCLUDED.advances,
                declines = EXCLUDED.declines,
                unchanged = EXCLUDED.unchanged,
                advance_decline_ratio = EXCLUDED.advance_decline_ratio,
                breadth_ratio = EXCLUDED.breadth_ratio,
                up_volume = EXCLUDED.up_volume,
                down_volume = EXCLUDED.down_volume,
                up_down_volume_ratio = EXCLUDED.up_down_volume_ratio,
                volume_ratio = EXCLUDED.volume_ratio,
                tick = EXCLUDED.tick,
                trin = EXCLUDED.trin,
                add_index = EXCLUDED.add_index,
                cumulative_ad_line = EXCLUDED.cumulative_ad_line,
                breadth_thrust = EXCLUDED.breadth_thrust,
                stock_universe_size = EXCLUDED.stock_universe_size
            """

            cursor.execute(query, (
                internals.timestamp,
                internals.advances,
                internals.declines,
                internals.unchanged,
                internals.advance_decline_ratio,
                internals.breadth_ratio,
                int(internals.up_volume),
                int(internals.down_volume),
                internals.up_down_volume_ratio,
                internals.volume_ratio,
                internals.tick,
                internals.trin,
                internals.add,
                internals.cumulative_ad_line,
                internals.breadth_thrust,
                'calculated',
                stock_universe_size
            ))

            conn.commit()
            cursor.close()

        except Exception as e:
            self.logger.logger.error(f"Error saving internals to database: {e}")
            conn.rollback()

    def run_scheduler(self):
        """Run the scheduler loop"""
        self.logger.logger.info(f"GEX Collector Scheduler started - running every {self.interval_minutes} minutes")
        self.logger.logger.info(f"Trading hours: {self.config.trading_hours_start} - {self.config.trading_hours_end} {self.config.timezone}")

        # Schedule the job
        schedule.every(self.interval_minutes).minutes.do(self.run_collection)

        # Run once immediately on startup
        self.logger.logger.info("Running initial data collection...")
        self.run_collection()

        # Keep running scheduled jobs
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
            except KeyboardInterrupt:
                self.logger.logger.info("Scheduler interrupted by user")
                break
            except Exception as e:
                self.logger.log_error("scheduler loop", e)
                time.sleep(60)  # Wait a minute before retrying

        self.logger.logger.info("Scheduler stopped")


def main():
    """Main entry point for scheduler"""
    import argparse
    import os
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description='GEX Collector Scheduler')
    parser.add_argument('--interval', type=int,
                       help='Collection interval in minutes (default: from env or 5)')
    parser.add_argument('--env-file', default='.env',
                       help='Path to environment file (default: .env)')

    args = parser.parse_args()

    # Load environment variables
    if os.path.exists(args.env_file):
        load_dotenv(args.env_file)
    else:
        print(f"Warning: Environment file {args.env_file} not found")

    # Determine interval: command line arg > env var > default
    interval = args.interval
    if interval is None:
        interval = int(os.getenv('COLLECTION_INTERVAL_MINUTES', '30'))

    try:
        scheduler = GEXScheduler(interval_minutes=interval)
        scheduler.run_scheduler()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
