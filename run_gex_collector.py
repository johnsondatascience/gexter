#!/usr/bin/env python3
"""
GEX Collector Entry Point

Simple entry point script for running the GEX collector with the new folder structure.
"""

import sys
import os
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.config import Config
from src.gex_collector import GEXCollector

def main():
    """Main entry point for GEX data collection"""
    # Load environment variables (override any existing env vars)
    load_dotenv(override=True)
    
    # Initialize configuration and collector
    config = Config()
    collector = GEXCollector(config)
    
    # Run the data collection
    success = collector.collect_data()
    
    if success:
        print("GEX data collection completed successfully")
        return 0
    else:
        print("GEX data collection failed")
        return 1

if __name__ == "__main__":
    exit(main())