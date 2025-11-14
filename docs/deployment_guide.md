# GEX Data Collector - Production Deployment Guide

## Overview

This production-ready GEX (Gamma Exposure) data collector fetches SPX option chain data from the Tradier API and calculates gamma exposure for each strike and expiration date. It's designed for reliable, automated deployment with comprehensive error handling, logging, and monitoring.

## Features

- ✅ Secure API credential management via environment variables
- ✅ Comprehensive error handling and logging
- ✅ Trading hours awareness (only runs during market hours)
- ✅ Rate limit handling and retry logic
- ✅ Data validation and duplicate prevention
- ✅ Slack and email notifications
- ✅ SQLite database storage with CSV export
- ✅ Scheduling support (hourly during trading sessions)

## Quick Start

### 1. Environment Setup

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   ```bash
   # Tradier API Configuration
   TRADIER_API_KEY=your_actual_api_key_here
   TRADIER_ACCOUNT_ID=your_actual_account_id_here
   
   # Optional: Notification settings
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   EMAIL_SMTP_SERVER=smtp.gmail.com
   EMAIL_USERNAME=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password
   EMAIL_TO=alerts@yourcompany.com
   ```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Test the Setup

```bash
# Test data collection (will run even outside trading hours)
python gex_collector.py --force

# Test notifications
python -c "from config import Config; from notifications import NotificationManager; config = Config(); nm = NotificationManager(config); print(nm.test_notifications())"
```

## Deployment Options

### Option 1: Windows Task Scheduler (Recommended for Windows)

1. **Create the scheduled task:**
   - Open Task Scheduler
   - Create Basic Task
   - Name: "GEX Data Collector"
   - Trigger: Daily, repeat every 1 hour for 8 hours
   - Start time: 9:30 AM
   - Action: Start a program
   - Program: `C:\Users\johnsnmi\gextr\windows_task_scheduler.bat`

2. **Configure advanced settings:**
   - Run whether user is logged on or not
   - Run with highest privileges
   - Configure for Windows 10/11

### Option 2: Python Scheduler (Cross-platform)

Run the built-in scheduler that handles trading hours automatically:

```bash
python scheduler.py
```

For background operation:
```bash
python scheduler.py --daemon
```

### Option 3: Cron (Linux/macOS)

Add to crontab for hourly execution during trading hours:

```bash
# Run every hour from 9:30 AM to 4:00 PM, Monday through Friday (EST)
30 9-16 * * 1-5 cd /path/to/gextr && python gex_collector.py
```

## Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TRADIER_API_KEY` | ✅ | - | Your Tradier API key |
| `TRADIER_ACCOUNT_ID` | ✅ | - | Your Tradier account ID |
| `DATABASE_PATH` | ❌ | `gex_data.db` | SQLite database file path |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | ❌ | `gex_collector.log` | Log file path |
| `TRADING_HOURS_START` | ❌ | `09:30` | Market open time (HH:MM) |
| `TRADING_HOURS_END` | ❌ | `16:00` | Market close time (HH:MM) |
| `TIMEZONE` | ❌ | `America/New_York` | Timezone for trading hours |

### Command Line Options

```bash
python gex_collector.py [options]

Options:
  --force              Force data collection outside trading hours
  --prices-only        Only update SPX prices
  --env-file PATH      Path to environment file (default: .env)
```

## Monitoring and Alerting

### Logs

All operations are logged to:
- Console (INFO level and above)
- Log file (all levels, configurable via `LOG_FILE`)

### Notifications

Configure Slack and/or email notifications for:
- ✅ Successful data collection
- ❌ Failed data collection
- ⚠️ Warnings (e.g., no new data available)
- ⏱️ API rate limits

### Health Checks

Monitor these files for system health:
- `gex_collector.log` - Application logs
- `gex.csv` - Most recent data export
- `gex_data.db` - Database file

## Data Storage

### Database Schema

The SQLite database (`gex_data.db`) contains a `gex_table` with the following key columns:
- `greeks.updated_at` - Timestamp of the data
- `expiration_date` - Option expiration date
- `option_type` - 'call' or 'put'
- `strike` - Strike price
- `gex` - Calculated gamma exposure
- Plus all other option chain fields from Tradier API

### CSV Export

The system automatically exports data to `gex.csv` for dashboard consumption.

## Security Best Practices

1. **Never commit `.env` file** - It contains sensitive API credentials
2. **Use environment variables** - API keys are loaded from environment, not hardcoded
3. **Restrict file permissions** - Ensure only authorized users can read config files
4. **Regular credential rotation** - Update API keys periodically
5. **Monitor API usage** - Watch for unusual activity in your Tradier account

## Troubleshooting

### Common Issues

1. **API Key Errors**
   ```
   ValueError: TRADIER_API_KEY environment variable is required
   ```
   - Ensure `.env` file exists and contains valid API key
   - Check that environment variable is loaded correctly

2. **Rate Limiting**
   ```
   WARNING: API rate limit - Available: 0, Resets in: 60s
   ```
   - Normal behavior, system will retry automatically
   - Consider reducing collection frequency if persistent

3. **Database Issues**
   ```
   Error in saving data to database: database is locked
   ```
   - Ensure no other processes are accessing the database
   - Check file permissions

4. **Trading Hours Detection**
   ```
   Market status: CLOSED (Trading day: True, Trading hours: False)
   ```
   - System correctly detects market hours
   - Use `--force` flag to override if needed

### Debug Mode

Enable debug logging by setting:
```
LOG_LEVEL=DEBUG
```

This provides detailed information about:
- API requests and responses
- Data processing steps
- Database operations
- Market hours calculations

## Performance Optimization

1. **Database Maintenance**: Periodically optimize the SQLite database:
   ```bash
   sqlite3 gex_data.db "VACUUM;"
   ```

2. **Log Rotation**: Set up log rotation to prevent large log files:
   ```python
   # Add to your system's log rotation configuration
   /path/to/gex_collector.log {
       daily
       rotate 7
       compress
       missingok
       notifempty
   }
   ```

3. **Resource Monitoring**: Monitor CPU and memory usage during peak trading hours

## API Rate Limits

Tradier API limits:
- Production: 120 requests per minute
- Sandbox: 60 requests per minute

The system automatically handles rate limits with:
- Exponential backoff retry logic
- Rate limit detection and waiting
- Graceful error handling

## Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly**: Review logs for errors or warnings
2. **Monthly**: Check database size and performance
3. **Quarterly**: Update dependencies and review configuration
4. **As needed**: Rotate API credentials

### Backup Strategy

Recommended backup approach:
1. **Database**: Daily backup of `gex_data.db`
2. **Configuration**: Version control for all scripts and config
3. **Logs**: Archive old logs for troubleshooting

### Updates and Upgrades

To update the system:
1. Test changes in a development environment
2. Backup current database and configuration
3. Update code and dependencies
4. Test with `--force` flag before production deployment

## Contact and Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs for specific error messages
3. Consult Tradier API documentation for API-related issues
4. Consider posting in relevant financial/trading development forums

---

*Last updated: 2025-10-31*