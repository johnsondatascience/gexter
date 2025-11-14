#!/usr/bin/env python3
"""
GEX Data Collection Scheduler

Provides scheduling functionality for the GEX data collector.
Can be used with Windows Task Scheduler, cron, or as a standalone service.
"""

import os
import sys
import time
import signal
import schedule
from datetime import datetime
from dotenv import load_dotenv

from ..config import Config
from .logger import GEXLogger
from ..gex_collector import GEXCollector


class GEXScheduler:
    """Scheduler for GEX data collection"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = GEXLogger(config)
        self.collector = GEXCollector(config)
        self.running = True
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def collect_job(self):
        """Job function for scheduled data collection"""
        self.logger.logger.info("Starting scheduled data collection")
        
        try:
            success = self.collector.collect_data()
            if success:
                self.logger.logger.info("Scheduled data collection completed successfully")
            else:
                self.logger.logger.error("Scheduled data collection failed")
        except Exception as e:
            self.logger.log_error("scheduled data collection", e)
    
    def setup_schedule(self):
        """Set up the collection schedule"""
        # Schedule data collection every hour during trading hours (9:30 AM - 4:00 PM ET)
        schedule.every().monday.at("09:30").do(self.collect_job)
        schedule.every().monday.at("10:30").do(self.collect_job)
        schedule.every().monday.at("11:30").do(self.collect_job)
        schedule.every().monday.at("12:30").do(self.collect_job)
        schedule.every().monday.at("13:30").do(self.collect_job)
        schedule.every().monday.at("14:30").do(self.collect_job)
        schedule.every().monday.at("15:30").do(self.collect_job)
        schedule.every().monday.at("16:00").do(self.collect_job)
        
        schedule.every().tuesday.at("09:30").do(self.collect_job)
        schedule.every().tuesday.at("10:30").do(self.collect_job)
        schedule.every().tuesday.at("11:30").do(self.collect_job)
        schedule.every().tuesday.at("12:30").do(self.collect_job)
        schedule.every().tuesday.at("13:30").do(self.collect_job)
        schedule.every().tuesday.at("14:30").do(self.collect_job)
        schedule.every().tuesday.at("15:30").do(self.collect_job)
        schedule.every().tuesday.at("16:00").do(self.collect_job)
        
        schedule.every().wednesday.at("09:30").do(self.collect_job)
        schedule.every().wednesday.at("10:30").do(self.collect_job)
        schedule.every().wednesday.at("11:30").do(self.collect_job)
        schedule.every().wednesday.at("12:30").do(self.collect_job)
        schedule.every().wednesday.at("13:30").do(self.collect_job)
        schedule.every().wednesday.at("14:30").do(self.collect_job)
        schedule.every().wednesday.at("15:30").do(self.collect_job)
        schedule.every().wednesday.at("16:00").do(self.collect_job)
        
        schedule.every().thursday.at("09:30").do(self.collect_job)
        schedule.every().thursday.at("10:30").do(self.collect_job)
        schedule.every().thursday.at("11:30").do(self.collect_job)
        schedule.every().thursday.at("12:30").do(self.collect_job)
        schedule.every().thursday.at("13:30").do(self.collect_job)
        schedule.every().thursday.at("14:30").do(self.collect_job)
        schedule.every().thursday.at("15:30").do(self.collect_job)
        schedule.every().thursday.at("16:00").do(self.collect_job)
        
        schedule.every().friday.at("09:30").do(self.collect_job)
        schedule.every().friday.at("10:30").do(self.collect_job)
        schedule.every().friday.at("11:30").do(self.collect_job)
        schedule.every().friday.at("12:30").do(self.collect_job)
        schedule.every().friday.at("13:30").do(self.collect_job)
        schedule.every().friday.at("14:30").do(self.collect_job)
        schedule.every().friday.at("15:30").do(self.collect_job)
        schedule.every().friday.at("16:00").do(self.collect_job)
        
        # Update SPX prices once daily at market close
        schedule.every().monday.at("16:30").do(self.collector.update_spx_prices)
        schedule.every().tuesday.at("16:30").do(self.collector.update_spx_prices)
        schedule.every().wednesday.at("16:30").do(self.collector.update_spx_prices)
        schedule.every().thursday.at("16:30").do(self.collector.update_spx_prices)
        schedule.every().friday.at("16:30").do(self.collector.update_spx_prices)
        
        self.logger.logger.info("Scheduled jobs configured for trading hours (9:30 AM - 4:00 PM ET)")
    
    def run(self):
        """Run the scheduler"""
        self.logger.logger.info("GEX Data Collection Scheduler starting...")
        self.setup_schedule()
        
        # Run initial collection if we're in trading hours
        if self.config.is_trading_day() and self.config.is_trading_hours():
            self.logger.logger.info("Running initial data collection...")
            self.collect_job()
        
        # Main scheduler loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.log_error("scheduler main loop", e)
                time.sleep(60)  # Continue after error
        
        self.logger.logger.info("GEX Data Collection Scheduler stopped")


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