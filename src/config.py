import os
from datetime import datetime, time
import pytz
from typing import Optional

class Config:
    """Configuration management for GEX data collector"""
    
    def __init__(self):
        # Load environment variables
        self.tradier_api_key = os.getenv('TRADIER_API_KEY')
        self.tradier_account_id = os.getenv('TRADIER_ACCOUNT_ID')

        # Database configuration
        self.database_type = os.getenv('DATABASE_TYPE', 'sqlite').lower()
        self.database_path = os.getenv('DATABASE_PATH', 'data/gex_data.db')

        # PostgreSQL configuration (only used if database_type is 'postgresql')
        self.postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
        self.postgres_port = int(os.getenv('POSTGRES_PORT', '5432'))
        self.postgres_db = os.getenv('POSTGRES_DB', 'gexdb')
        self.postgres_user = os.getenv('POSTGRES_USER', 'gexuser')
        self.postgres_password = os.getenv('POSTGRES_PASSWORD', '')
        self.postgres_pool_size = int(os.getenv('POSTGRES_POOL_SIZE', '5'))
        self.postgres_max_overflow = int(os.getenv('POSTGRES_MAX_OVERFLOW', '10'))

        # Underlying symbols configuration
        self.collect_spx = os.getenv('COLLECT_SPX', 'true').lower() == 'true'
        self.collect_xsp = os.getenv('COLLECT_XSP', 'false').lower() == 'true'

        # Build list of symbols to collect
        self.underlying_symbols = []
        if self.collect_spx:
            self.underlying_symbols.append('SPX')
        if self.collect_xsp:
            self.underlying_symbols.append('XSP')

        # Logging configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('LOG_FILE', 'logs/gex_collector.log')

        # Trading hours configuration
        self.trading_hours_start = self._parse_time(os.getenv('TRADING_HOURS_START', '09:30'))
        self.trading_hours_end = self._parse_time(os.getenv('TRADING_HOURS_END', '16:00'))
        self.timezone = pytz.timezone(os.getenv('TIMEZONE', 'America/New_York'))
        
        # Notification configuration
        self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        self.email_smtp_server = os.getenv('EMAIL_SMTP_SERVER')
        self.email_smtp_port = int(os.getenv('EMAIL_SMTP_PORT', '587'))
        self.email_username = os.getenv('EMAIL_USERNAME')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.email_to = os.getenv('EMAIL_TO')
        
        # Validate required configuration
        self._validate_config()
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string in HH:MM format"""
        try:
            hour, minute = map(int, time_str.split(':'))
            return time(hour, minute)
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid time format: {time_str}. Use HH:MM format.")
    
    def _validate_config(self):
        """Validate required configuration values"""
        if not self.tradier_api_key:
            raise ValueError("TRADIER_API_KEY environment variable is required")
        
        if not self.tradier_account_id:
            raise ValueError("TRADIER_ACCOUNT_ID environment variable is required")
    
    def is_trading_hours(self, dt: Optional[datetime] = None) -> bool:
        """Check if current time is within trading hours"""
        if dt is None:
            dt = datetime.now(self.timezone)
        
        current_time = dt.time()
        return self.trading_hours_start <= current_time <= self.trading_hours_end
    
    def is_trading_day(self, dt: Optional[datetime] = None) -> bool:
        """Check if current day is a trading day (Monday-Friday)"""
        if dt is None:
            dt = datetime.now(self.timezone)
        
        return dt.weekday() < 5  # Monday=0, Sunday=6