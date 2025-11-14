#!/usr/bin/env python3
"""
GEX Scheduler Entry Point

Entry point script for running the GEX scheduler with the new folder structure.
"""

import sys
import os
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.config import Config
from src.utils.scheduler import GEXScheduler

def main():
    """Main entry point for GEX scheduler"""
    # Load environment variables
    load_dotenv()
    
    # Initialize configuration and scheduler
    config = Config()
    scheduler = GEXScheduler(config)
    
    # Run the scheduler
    scheduler.run()

if __name__ == "__main__":
    main()