import logging
import sys
from datetime import datetime
from typing import Optional

def setup_logger(name: str, log_file: str, log_level: str = 'INFO') -> logging.Logger:
    """Set up logger with both file and console handlers"""
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    return logger

class GEXLogger:
    """Custom logger for GEX data collection operations"""
    
    def __init__(self, config):
        self.logger = setup_logger('gex_collector', config.log_file, config.log_level)
        self.start_time = None
    
    def log_start(self, operation: str):
        """Log the start of an operation"""
        self.start_time = datetime.now()
        self.logger.info(f"Starting {operation}")
    
    def log_completion(self, operation: str, records_processed: Optional[int] = None):
        """Log the completion of an operation"""
        duration = datetime.now() - self.start_time if self.start_time else None
        duration_str = f" in {duration.total_seconds():.2f}s" if duration else ""
        
        if records_processed is not None:
            self.logger.info(f"Completed {operation} - {records_processed} records processed{duration_str}")
        else:
            self.logger.info(f"Completed {operation}{duration_str}")
    
    def log_error(self, operation: str, error: Exception):
        """Log an error during an operation"""
        self.logger.error(f"Error in {operation}: {str(error)}", exc_info=True)
    
    def log_api_rate_limit(self, available: str, reset_time: str):
        """Log API rate limit information"""
        self.logger.warning(f"API rate limit - Available: {available}, Resets in: {reset_time}s")
    
    def log_data_validation_error(self, message: str):
        """Log data validation errors"""
        self.logger.error(f"Data validation error: {message}")
    
    def log_market_status(self, is_trading_hours: bool, is_trading_day: bool):
        """Log market status information"""
        status = "OPEN" if (is_trading_hours and is_trading_day) else "CLOSED"
        self.logger.info(f"Market status: {status} (Trading day: {is_trading_day}, Trading hours: {is_trading_hours})")
    
    def log_spx_price(self, price_data: dict):
        """Log SPX price information"""
        if price_data:
            self.logger.info(f"SPX: ${price_data['last']:.2f} "
                           f"(O: ${price_data.get('open', 'N/A')}, "
                           f"H: ${price_data.get('high', 'N/A')}, "
                           f"L: ${price_data.get('low', 'N/A')}) "
                           f"Change: {price_data.get('change', 0):+.2f} "
                           f"({price_data.get('change_percentage', 0):+.2f}%)")
    
    def log_spx_price_summary(self, price_data: dict, options_count: int):
        """Log SPX price context with options summary"""
        if price_data:
            self.logger.info(f"Market Context: SPX ${price_data['last']:.2f} | "
                           f"Options collected: {options_count:,} | "
                           f"Session change: {price_data.get('change_percentage', 0):+.2f}%")