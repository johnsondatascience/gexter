"""
Database schema update script

Adds Greek difference columns to the existing gex_table
"""

import sqlite3
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database_schema(db_path: str = 'gex_data.db'):
    """Add Greek difference columns to the database"""
    
    # Greek columns that will have difference calculations
    greek_columns = [
        'greeks.delta', 'greeks.gamma', 'greeks.theta', 'greeks.vega', 
        'greeks.rho', 'greeks.phi', 'greeks.bid_iv', 'greeks.mid_iv', 
        'greeks.ask_iv', 'greeks.smv_vol', 'gex'
    ]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(gex_table)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        logger.info(f"Current table has {len(existing_columns)} columns")
        
        # Add difference columns
        columns_added = 0
        for greek_col in greek_columns:
            diff_col = f'{greek_col}_diff'
            pct_change_col = f'{greek_col}_pct_change'
            
            # Add absolute difference column
            if diff_col not in existing_columns:
                try:
                    cursor.execute(f'ALTER TABLE gex_table ADD COLUMN "{diff_col}" REAL')
                    logger.info(f"Added column: {diff_col}")
                    columns_added += 1
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        logger.error(f"Error adding {diff_col}: {e}")
            
            # Add percentage change column
            if pct_change_col not in existing_columns:
                try:
                    cursor.execute(f'ALTER TABLE gex_table ADD COLUMN "{pct_change_col}" REAL')
                    logger.info(f"Added column: {pct_change_col}")
                    columns_added += 1
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        logger.error(f"Error adding {pct_change_col}: {e}")
        
        # Add metadata columns
        metadata_columns = [
            ('prev_timestamp', 'TIMESTAMP'),
            ('has_previous_data', 'BOOLEAN')
        ]
        
        for col_name, col_type in metadata_columns:
            if col_name not in existing_columns:
                try:
                    cursor.execute(f'ALTER TABLE gex_table ADD COLUMN "{col_name}" {col_type}')
                    logger.info(f"Added metadata column: {col_name}")
                    columns_added += 1
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        logger.error(f"Error adding {col_name}: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Schema update completed. Added {columns_added} new columns.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating database schema: {e}")
        return False

def verify_schema_update(db_path: str = 'gex_data.db'):
    """Verify that the schema update was successful"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get updated schema
        cursor.execute("PRAGMA table_info(gex_table)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Check for difference columns
        diff_columns = [col for col in columns if col.endswith('_diff')]
        pct_change_columns = [col for col in columns if col.endswith('_pct_change')]
        metadata_columns = [col for col in columns if col in ['prev_timestamp', 'has_previous_data']]
        
        logger.info(f"Verification complete:")
        logger.info(f"  Total columns: {len(columns)}")
        logger.info(f"  Difference columns: {len(diff_columns)}")
        logger.info(f"  Percentage change columns: {len(pct_change_columns)}")
        logger.info(f"  Metadata columns: {len(metadata_columns)}")
        
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error verifying schema update: {e}")
        return False

if __name__ == "__main__":
    print("Updating database schema...")
    success = update_database_schema()
    
    if success:
        print("Verifying schema update...")
        verify_schema_update()
        print("Schema update completed successfully!")
    else:
        print("Schema update failed!")