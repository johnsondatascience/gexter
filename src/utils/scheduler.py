#!/usr/bin/env python3
"""
GEX Data Collection Scheduler

Provides scheduling functionality for the GEX data collector with proper timezone handling.
Can be used with Windows Task Scheduler, cron, or as a standalone service.
"""

import os
import sys
import time
import signal
import schedule
from datetime import datetime, time as dt_time
import pytz
from dotenv import load_dotenv

from ..config import Config
from .logger import GEXLogger
from ..gex_collector import GEXCollector


class GEXScheduler:
    """Scheduler for GEX data collection with timezone-aware scheduling"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = GEXLogger(config)
        self.collector = GEXCollector(config)
        self.running = True

        # Collection interval (minutes)
        self.collection_interval = int(os.getenv('COLLECTION_INTERVAL_MINUTES', '15'))

        # Pre-market and post-market options
        self.collect_premarket = os.getenv('COLLECT_PREMARKET', 'false').lower() == 'true'
        self.collect_postmarket = os.getenv('COLLECT_POSTMARKET', 'false').lower() == 'true'

        # Get local timezone for display
        try:
            import tzlocal
            self.local_tz = tzlocal.get_localzone()
        except:
            # Fallback to Pacific for California users
            self.local_tz = pytz.timezone('America/Los_Angeles')

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def collect_job(self):
        """Job function for scheduled data collection with timezone-aware checks"""
        try:
            # Check if it's a trading day
            if not self.config.is_trading_day():
                self.logger.logger.info("Skipping collection - not a trading day (weekend)")
                return

            # Get current time in ET
            now_et = datetime.now(self.config.timezone)
            current_time = now_et.time()

            # Determine if we should collect
            should_collect = False
            collection_type = ""

            # Market hours (9:30 AM - 4:00 PM ET)
            if self.config.is_trading_hours():
                should_collect = True
                collection_type = "MARKET HOURS"

            # Pre-market (7:00 AM - 9:30 AM ET)
            elif self.collect_premarket and dt_time(7, 0) <= current_time < self.config.trading_hours_start:
                should_collect = True
                collection_type = "PRE-MARKET"

            # Post-market (4:00 PM - 8:00 PM ET)
            elif self.collect_postmarket and self.config.trading_hours_end <= current_time < dt_time(20, 0):
                should_collect = True
                collection_type = "POST-MARKET"

            if not should_collect:
                self.logger.logger.info(f"Skipping collection at {now_et.strftime('%H:%M:%S %Z')} - outside collection hours")
                return

            # Show time in both ET and local timezone
            now_local = now_et.astimezone(self.local_tz)
            self.logger.logger.info("=" * 60)
            self.logger.logger.info(f"Starting {collection_type} collection")
            self.logger.logger.info(f"Time: {now_et.strftime('%H:%M:%S %Z')} (Market Time)")
            if now_local.tzinfo != now_et.tzinfo:
                self.logger.logger.info(f"      {now_local.strftime('%H:%M:%S %Z')} (Your Local Time)")
            self.logger.logger.info("=" * 60)

            success = self.collector.collect_data()
            if success:
                self.logger.logger.info(f"✓ Collection completed successfully")
            else:
                self.logger.logger.error(f"✗ Collection failed")

        except Exception as e:
            self.logger.log_error("scheduled data collection", e)
    
    def setup_schedule(self):
        """Set up the collection schedule using interval-based approach"""
        # Use interval-based scheduling instead of hardcoded times
        # The collect_job method handles timezone-aware checks internally
        schedule.every(self.collection_interval).minutes.do(self.collect_job)

        self.logger.logger.info("=" * 80)
        self.logger.logger.info("GEX COLLECTION SCHEDULER CONFIGURATION")
        self.logger.logger.info("=" * 80)
        self.logger.logger.info(f"Collection Interval: Every {self.collection_interval} minutes")
        self.logger.logger.info(f"Market Timezone: {self.config.timezone}")
        self.logger.logger.info(f"Your Local Timezone: {self.local_tz}")
        self.logger.logger.info(f"")
        self.logger.logger.info(f"Market Hours (ET):  {self.config.trading_hours_start} - {self.config.trading_hours_end}")

        # Calculate market hours in local time for display
        now_et = datetime.now(self.config.timezone)
        # Create timezone-aware datetime for market open/close in ET
        market_open_et = self.config.timezone.localize(
            datetime.combine(now_et.date(), dt_time(9, 30))
        )
        market_close_et = self.config.timezone.localize(
            datetime.combine(now_et.date(), dt_time(16, 0))
        )
        market_open_local = market_open_et.astimezone(self.local_tz)
        market_close_local = market_close_et.astimezone(self.local_tz)

        self.logger.logger.info(f"Market Hours (Local): {market_open_local.strftime('%H:%M')} - {market_close_local.strftime('%H:%M')} {str(self.local_tz).split('/')[-1]}")
        self.logger.logger.info(f"")
        self.logger.logger.info(f"Pre-Market Collection: {'ENABLED' if self.collect_premarket else 'DISABLED'} (7:00-9:30 AM ET)")
        self.logger.logger.info(f"Post-Market Collection: {'ENABLED' if self.collect_postmarket else 'DISABLED'} (4:00-8:00 PM ET)")
        self.logger.logger.info("=" * 80)
    
    def run(self):
        """Run the scheduler"""
        self.logger.logger.info("=" * 80)
        self.logger.logger.info("GEX DATA COLLECTION SCHEDULER STARTING")
        self.logger.logger.info("=" * 80)
        self.setup_schedule()

        # Run initial collection
        self.logger.logger.info("\nRunning initial collection check...")
        self.collect_job()

        # Main scheduler loop
        self.logger.logger.info(f"\nScheduler is running. Will check every {self.collection_interval} minutes.")
        self.logger.logger.info("Press Ctrl+C to stop.\n")

        while self.running:
            try:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.log_error("scheduler main loop", e)
                time.sleep(60)  # Continue after error

        self.logger.logger.info("=" * 80)
        self.logger.logger.info("GEX Data Collection Scheduler stopped")
        self.logger.logger.info("=" * 80)


def main():
    """Main entry point for scheduler"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GEX Data Collection Scheduler')
    parser.add_argument('--env-file', default='.env',
                       help='Path to environment file (default: .env)')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon (background process)')
    
    args = parser.parse_args()
    
    # Load environment variables
    if os.path.exists(args.env_file):
        load_dotenv(args.env_file)
    else:
        print(f"Warning: Environment file {args.env_file} not found")
    
    try:
        # Initialize configuration and scheduler
        config = Config()
        scheduler = GEXScheduler(config)
        
        if args.daemon:
            # For daemon mode, you might want to use python-daemon library
            # For now, just run normally
            print("Running in daemon mode...")
        
        scheduler.run()
        
    except KeyboardInterrupt:
        print("\nScheduler stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()