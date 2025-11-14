@echo off
REM Windows batch script to run GEX data collector
REM This script can be scheduled in Windows Task Scheduler

REM Change to the script directory
cd /d "C:\Users\johnsnmi\gextr"

REM Activate virtual environment if you're using one
REM call venv\Scripts\activate

REM Run the GEX collector
python gex_collector.py

REM Log the completion
echo %date% %time% - GEX collection completed >> gex_scheduler.log