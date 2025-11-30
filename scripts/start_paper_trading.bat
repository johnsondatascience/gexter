@echo off
REM Quick Start Script for Paper Trading
REM Run this Monday morning to start paper trading

echo.
echo ================================================================================
echo PAPER TRADING - HEDGED STRANGLE STRATEGY
echo ================================================================================
echo.

REM Create logs directory
echo [1/5] Creating logs directory...
if not exist logs mkdir logs
echo       Done!
echo.

REM Check if Docker is running
echo [2/5] Checking GEX collector status...
docker-compose ps | findstr "gex-collector"
if errorlevel 1 (
    echo       WARNING: GEX collector not running!
    echo       Starting GEX collector...
    docker-compose up -d
) else (
    echo       GEX collector is running!
)
echo.

REM Check output directory
echo [3/5] Checking output directory...
if not exist output mkdir output
echo       Done!
echo.

REM Quick database test
echo [4/5] Testing database connection...
python -c "import psycopg2; from dotenv import load_dotenv; import os; load_dotenv(); conn = psycopg2.connect(host=os.getenv('POSTGRES_HOST', 'localhost'), port=5432, database=os.getenv('POSTGRES_DB', 'gexdb'), user=os.getenv('POSTGRES_USER', 'gexuser'), password=os.getenv('POSTGRES_PASSWORD')); print('      Database connected successfully!'); conn.close()" 2>nul
if errorlevel 1 (
    echo       ERROR: Database connection failed!
    echo       Check your .env file and Docker containers
    pause
    exit /b 1
)
echo.

echo [5/5] Starting paper trading engine...
echo.
echo ================================================================================
echo PAPER TRADING ENGINE STARTING
echo ================================================================================
echo.
echo Monitor this window for trading activity.
echo Press Ctrl+C to stop paper trading.
echo.
echo Strategy: Hedged Strangle (Independent Leg Timing)
echo Profit Target: 25%%
echo Stop Loss: 40%%
echo PDT Protected: No same-day round trips
echo.
echo ================================================================================
echo.

REM Start paper trading
python scripts\paper_trade_hedged.py

echo.
echo ================================================================================
echo PAPER TRADING STOPPED
echo ================================================================================
echo.
pause
