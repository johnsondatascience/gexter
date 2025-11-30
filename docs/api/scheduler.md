# Scheduler API Reference

The Scheduler module manages automated data collection during market hours.

## Module: `scheduler`

::: src.scheduler

## Overview

The scheduler ensures data is collected:

- Only during trading hours (9:30 AM - 4:00 PM ET)
- Only on trading days (Monday-Friday)
- At configurable intervals (default: 5 minutes)
- With timezone awareness (US/Eastern)

## Scheduler Class

```python
class Scheduler:
    """
    Manages scheduled execution of GEX data collection.

    The scheduler:
    - Runs only during market hours
    - Skips weekends and holidays
    - Handles timezone conversions
    - Provides logging and monitoring
    """

    def __init__(self):
        """Initialize scheduler with configuration from environment."""
        self.interval = int(os.getenv('COLLECTION_INTERVAL_MINUTES', 5))
        self.start_time = os.getenv('TRADING_HOURS_START', '09:30')
        self.end_time = os.getenv('TRADING_HOURS_END', '16:00')
        self.timezone = pytz.timezone(os.getenv('TIMEZONE', 'America/New_York'))
```

## Key Methods

### Schedule Collection

```python
def schedule_collection(self):
    """
    Set up the collection schedule.

    Creates a schedule that runs the GEX collector:
    - Every N minutes (configured)
    - Only during market hours
    - Only on trading days
    """
    schedule.every(self.interval).minutes.do(
        self._run_if_market_hours,
        job_func=collect_gex_data
    )
```

### Check Market Hours

```python
def is_market_hours(self) -> bool:
    """
    Check if current time is within trading hours.

    Returns:
        bool: True if market is currently open

    Example:
        >>> scheduler = Scheduler()
        >>> if scheduler.is_market_hours():
        ...     collect_data()
    """
    now = datetime.now(self.timezone)

    # Check if trading day (Mon-Fri)
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False

    # Check if within trading hours
    market_open = now.replace(
        hour=int(self.start_time.split(':')[0]),
        minute=int(self.start_time.split(':')[1]),
        second=0
    )
    market_close = now.replace(
        hour=int(self.end_time.split(':')[0]),
        minute=int(self.end_time.split(':')[1]),
        second=0
    )

    return market_open <= now <= market_close
```

### Run Scheduler

```python
def run(self):
    """
    Start the scheduler and run indefinitely.

    This method:
    - Logs startup information
    - Runs scheduled jobs
    - Handles interruptions gracefully
    - Logs shutdown
    """
    logger.info(f"Scheduler started - collecting every {self.interval} minutes")
    logger.info(f"Trading hours: {self.start_time} - {self.end_time} ET")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        raise
```

## Configuration

Configure the scheduler via environment variables:

```bash
# Collection frequency
COLLECTION_INTERVAL_MINUTES=5

# Trading hours (ET)
TRADING_HOURS_START=09:30
TRADING_HOURS_END=16:00

# Timezone
TIMEZONE=America/New_York
```

## Usage Examples

### Basic Usage

```python
from src.scheduler import Scheduler

# Create and run scheduler
scheduler = Scheduler()
scheduler.schedule_collection()
scheduler.run()
```

### Custom Schedule

```python
from src.scheduler import Scheduler
from src.gex_collector import collect_gex_data

scheduler = Scheduler()

# Run at specific times
schedule.every().day.at("09:35").do(collect_gex_data)  # Market open
schedule.every().day.at("12:00").do(collect_gex_data)  # Midday
schedule.every().day.at("15:55").do(collect_gex_data)  # Before close

scheduler.run()
```

### One-Time Collection

```python
from src.scheduler import Scheduler
from src.gex_collector import collect_gex_data

scheduler = Scheduler()

# Only run if market is open
if scheduler.is_market_hours():
    collect_gex_data()
else:
    print("Market is closed")
```

## Schedule Patterns

The scheduler supports various patterns via the `schedule` library:

```python
# Every N minutes
schedule.every(5).minutes.do(job)

# Every hour
schedule.every().hour.do(job)

# At specific time
schedule.every().day.at("10:30").do(job)

# Multiple times per day
schedule.every().day.at("09:30").do(job)
schedule.every().day.at("15:00").do(job)

# Every Monday
schedule.every().monday.at("09:30").do(job)
```

## Logging

The scheduler provides detailed logging:

```
2024-11-29 09:28:00 - INFO - Scheduler started - collecting every 5 minutes
2024-11-29 09:28:00 - INFO - Trading hours: 09:30 - 16:00 ET
2024-11-29 09:30:00 - INFO - Market hours - running collection
2024-11-29 09:30:10 - INFO - Collection completed successfully
2024-11-29 09:35:00 - INFO - Market hours - running collection
...
2024-11-29 16:01:00 - INFO - Outside market hours - skipping collection
```

## Error Handling

```python
def _run_if_market_hours(self, job_func):
    """
    Run job only if market is open, with error handling.
    """
    if not self.is_market_hours():
        logger.debug("Outside market hours - skipping")
        return

    try:
        logger.info("Market hours - running collection")
        job_func()
    except Exception as e:
        logger.error(f"Collection failed: {e}")
        # Send alert (optional)
        self._send_alert(f"Collection error: {e}")
```

## Holiday Handling

For market holidays, you can extend the scheduler:

```python
from pandas.tseries.holiday import USFederalHolidayCalendar

class TradingScheduler(Scheduler):
    """Scheduler with holiday awareness."""

    def __init__(self):
        super().__init__()
        self.calendar = USFederalHolidayCalendar()

    def is_market_hours(self) -> bool:
        """Check market hours including holidays."""
        # First check standard market hours
        if not super().is_market_hours():
            return False

        # Then check if it's a holiday
        now = datetime.now(self.timezone)
        holidays = self.calendar.holidays(
            start=now.date(),
            end=now.date()
        )
        return now.date() not in holidays.date
```

## Docker Integration

In Docker, the scheduler runs as the main process:

```dockerfile
# Dockerfile
CMD ["python", "run_scheduler.py"]
```

```python
# run_scheduler.py
from src.scheduler import Scheduler

if __name__ == "__main__":
    scheduler = Scheduler()
    scheduler.schedule_collection()
    scheduler.run()
```

## Monitoring

Monitor the scheduler health:

```python
import time
from datetime import datetime

def health_check():
    """Check if scheduler is running properly."""
    last_run = get_last_collection_time()
    now = datetime.now()
    minutes_since_last_run = (now - last_run).total_seconds() / 60

    if minutes_since_last_run > 15:  # Alert if no collection in 15 min
        send_alert(f"No collection in {minutes_since_last_run} minutes")

# Run health check every 5 minutes
schedule.every(5).minutes.do(health_check)
```

## See Also

- [GEX Collector](gex_collector.md) - Collection module
- [Python schedule library](https://schedule.readthedocs.io/) - Underlying scheduler
- [Deployment Guide](../deployment_guide.md) - Production deployment
