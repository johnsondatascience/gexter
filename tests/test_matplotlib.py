#!/usr/bin/env python3
"""Simple test to verify matplotlib works - uses absolute paths"""
import sys

# Use absolute path for log file
log_path = r'c:\Users\johnsnmi\gexter\docs\chart_log.txt'

with open(log_path, 'w') as log:
    try:
        log.write("Starting chart generation test...\n")
        log.flush()
        
        # Test imports
        log.write("Importing matplotlib...\n")
        log.flush()
        
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        import matplotlib.pyplot as plt
        log.write(f"Matplotlib version: {matplotlib.__version__}\n")
        log.flush()
        
        import numpy as np
        log.write(f"Numpy version: {np.__version__}\n")
        log.flush()
        
        # Create output directory
        import os
        output_dir = r'c:\Users\johnsnmi\gexter\docs\charts'
        os.makedirs(output_dir, exist_ok=True)
        log.write(f"Output directory created: {output_dir}\n")
        log.flush()
        
        # Create a simple test chart
        log.write("Creating test chart...\n")
        log.flush()
        
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.bar(['Win', 'Loss'], [81, 19], color=['#22c55e', '#ef4444'])
        ax.set_title('GEX Alpha Win Rate: 81%', fontsize=14, fontweight='bold')
        ax.set_ylabel('Percentage')
        
        # Save
        output_path = os.path.join(output_dir, 'test_chart.png')
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        log.write(f"Chart saved to: {output_path}\n")
        log.write(f"File exists: {os.path.exists(output_path)}\n")
        if os.path.exists(output_path):
            log.write(f"File size: {os.path.getsize(output_path)} bytes\n")
        
        log.write("\nSUCCESS!\n")
        
    except Exception as e:
        import traceback
        log.write(f"\nERROR: {e}\n")
        traceback.print_exc(file=log)

print("Done - check docs/chart_log.txt")
