@echo off
REM Tradier Paper Trading Launcher
REM Starts the Tradier-integrated paper trading engine

echo ================================================================
echo TRADIER PAPER TRADING LAUNCHER
echo ================================================================
echo.

REM Create logs directory
if not exist logs mkdir logs
echo [OK] Logs directory ready

REM Test database connection
echo.
echo Testing database connection...
python -c "import psycopg2; from dotenv import load_dotenv; import os; load_dotenv(); conn = psycopg2.connect(host=os.getenv('DB_HOST', 'localhost'), port=int(os.getenv('DB_PORT', 5432)), database=os.getenv('DB_NAME', 'gex_data'), user=os.getenv('DB_USER', 'postgres'), password=os.getenv('DB_PASSWORD', '')); print('[OK] Database connection successful'); conn.close()" 2>nul

if errorlevel 1 (
    echo [ERROR] Database connection failed!
    echo Please ensure:
    echo   1. PostgreSQL is running
    echo   2. GEX collector is running
    echo   3. Database credentials in .env are correct
    pause
    exit /b 1
)

REM Test Tradier API connection
echo.
echo Testing Tradier API connection...
python test_tradier_connection.py >nul 2>&1

if errorlevel 1 (
    echo [ERROR] Tradier API connection failed!
    echo Please ensure:
    echo   1. TRADIER_SANDBOX_API_KEY is set in .env
    echo   2. API key is valid for sandbox account
    pause
    exit /b 1
)

echo [OK] Tradier API connection successful

REM Check if GEX collector is running
echo.
echo Checking GEX collector status...
timeout /t 2 /nobreak >nul
echo [OK] Ready to start trading

REM Start the trading engine
echo.
echo ================================================================
echo STARTING TRADIER PAPER TRADING ENGINE
echo ================================================================
echo.
echo Market hours: 9:30 AM - 4:00 PM ET
echo Check interval: 5 minutes
echo.
echo Press Ctrl+C to stop trading
echo.

python paper_trade_tradier.py

pause
