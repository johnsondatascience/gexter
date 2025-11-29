#!/usr/bin/env python3
"""Simple test to verify matplotlib works"""
import sys
from pathlib import Path

# Write all output to a log file
log_file = Path(__file__).parent.parent / 'docs' / 'chart_generation.log'

with open(log_file, 'w') as log:
    try:
        log.write("Starting chart generation test...\n")
        
        # Test imports
        log.write("Importing matplotlib...\n")
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        import matplotlib.pyplot as plt
        log.write(f"Matplotlib version: {matplotlib.__version__}\n")
        
        log.write("Importing numpy...\n")
        import numpy as np
        log.write(f"Numpy version: {np.__version__}\n")
        
        # Create output directory
        output_dir = Path(__file__).parent.parent / 'docs' / 'charts'
        output_dir.mkdir(parents=True, exist_ok=True)
        log.write(f"Output directory: {output_dir}\n")
        log.write(f"Directory exists: {output_dir.exists()}\n")
        
        # Create a simple test chart
        log.write("Creating test chart...\n")
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.bar(['Win', 'Loss'], [81, 19], color=['green', 'red'])
        ax.set_title('GEX Alpha Win Rate: 81%')
        ax.set_ylabel('Percentage')
        
        # Save
        output_path = output_dir / 'test_chart.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        log.write(f"Chart saved to: {output_path}\n")
        log.write(f"File exists: {output_path.exists()}\n")
        log.write(f"File size: {output_path.stat().st_size if output_path.exists() else 0} bytes\n")
        
        log.write("\n✅ Test completed successfully!\n")
        
    except Exception as e:
        import traceback
        log.write(f"\n❌ Error: {e}\n")
        traceback.print_exc(file=log)
        sys.exit(1)
