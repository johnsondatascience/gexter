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


class GEXScheduler:
    """Scheduler for GEX data collection"""

    def __init__(self, interval_minutes: int = 30):
        """
        Initialize the scheduler

        Args:
            interval_minutes: How often to run the collector (default: 30 minutes)
        """
        self.config = Config()
        self.logger = GEXLogger(self.config)
        self.collector = GEXCollector(self.config)
        self.interval_minutes = interval_minutes
        self.running = True

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
                self.collector.collect_data(force=False)
            else:
                trading_status = "outside trading hours" if is_trading_day else "not a trading day"
                self.logger.logger.info(f"[{current_time}] Skipping collection ({trading_status})")

        except Exception as e:
            self.logger.log_error("scheduled collection", e)

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
