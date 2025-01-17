import pandas as pd
import sqlite3
import logging
from sqlalchemy import create_engine, text
import json
from pathlib import Path

# Database configuration
DB_PATH = './user_data.db'
ENGINE = create_engine(f'sqlite:///{DB_PATH}')

# Initialize cache as None
cache = None

def init_data_loading(cache_instance):
    """Initialize the data loading with the cache instance"""
    global cache
    cache = cache_instance

def load_region_mappings():
    """Load region mappings from JSON file"""
    try:
        mappings_path = Path(__file__).parent.parent / "region_mappings.json"
        with open(mappings_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading region mappings: {e}")
        return {}

def load_data(force_reload=False):
    """
    Load data from the SQLite database.
    """
    global cache
    
    # If cache is initialized and force_reload is True, clear the cache
    if cache and force_reload:
        cache.delete('data')
    
    # If cache is initialized and data is cached, return cached data
    if cache and not force_reload:
        cached_data = cache.get('data')
        if cached_data is not None:
            return cached_data
    
    # Load fresh data
    df = load_data_from_db()
    
    # Cache the new data if cache is initialized
    if cache:
        cache.set('data', df, timeout=3600)
    
    return df

def load_data_from_db():
    """Load data directly from the database"""
    try:
        # Create table if it doesn't exist
        with ENGINE.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_data (
                    user_id TEXT PRIMARY KEY,
                    df2_full_name TEXT,
                    df2_username TEXT,
                    df2_user_type TEXT,
                    df2_registration_date DATE,
                    df2_membership TEXT,
                    df2_country TEXT,
                    region TEXT,
                    df2_profile_url TEXT,
                    df2_social_links TEXT,
                    df3_avg_aesthetic_score FLOAT,
                    df2_avg_lai_score FLOAT,
                    df2_exclusivity_rate FLOAT,
                    df2_acceptance_rate FLOAT,
                    num_of_photos_featured INTEGER,
                    num_of_galleries_featured INTEGER,
                    num_of_stories_featured INTEGER,
                    total_uploads INTEGER,
                    total_licensing_submissions INTEGER,
                    total_sales_revenue FLOAT,
                    total_num_of_sales INTEGER,
                    df3_photo_likes INTEGER,
                    df3_comments INTEGER,
                    df3_avg_visit_days_monthly FLOAT,
                    activity_week DATE
                )
            """))
            
            query = text("SELECT * FROM user_data")
            df = pd.read_sql(query, conn)
            
            if not df.empty:
                # Load and apply region mappings
                region_mappings = load_region_mappings()
                df['region'] = df['df2_country'].map(region_mappings).fillna('Other')
                
                # Convert date columns
                df['df2_registration_date'] = pd.to_datetime(df['df2_registration_date'])
                df['activity_week'] = pd.to_datetime(df['activity_week'])
            
            return df
            
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

def load_filtered_data(user_ids=None, columns=None):
    """
    Load data with optional filtering by user_ids and column selection
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Build query dynamically
        select_cols = ', '.join(columns) if columns else '*'
        query = f"SELECT {select_cols} FROM user_data"
        
        # Add WHERE clause only if filtering by user_ids
        if user_ids:
            placeholders = ','.join('?' * len(user_ids))
            query += f" WHERE user_id IN ({placeholders})"
            df = pd.read_sql_query(query, conn, params=user_ids)
        else:
            df = pd.read_sql_query(query, conn)
            
        return df
    except Exception as e:
        logging.error(f"Error loading data: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def load_paginated_data(page_number, rows_per_page, filtered_user_ids):
    """
    Load paginated data from SQLite using a temporary table approach
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create temporary table for filtered IDs
        cursor.execute("CREATE TEMP TABLE IF NOT EXISTS temp_filtered_ids (user_id TEXT)")
        cursor.execute("DELETE FROM temp_filtered_ids")  # Clear existing data
        
        # Insert filtered IDs in chunks to avoid variable limit
        chunk_size = 500
        for i in range(0, len(filtered_user_ids), chunk_size):
            chunk = filtered_user_ids[i:i + chunk_size]
            cursor.executemany("INSERT INTO temp_filtered_ids VALUES (?)", 
                             [(id,) for id in chunk])
        
        # Calculate offset
        offset = (page_number - 1) * rows_per_page if page_number else 0
        
        # Query using JOIN with temp table
        query = """
            SELECT * FROM user_data 
            WHERE user_id IN (SELECT user_id FROM temp_filtered_ids)
            LIMIT ? OFFSET ?
        """
        
        df = pd.read_sql_query(query, conn, params=(rows_per_page, offset))
        
        return df
    except Exception as e:
        logging.error(f"Error in load_paginated_data: {e}")
        return pd.DataFrame()
    finally:
        if cursor:
            cursor.execute("DROP TABLE IF EXISTS temp_filtered_ids")
            conn.commit()
        if conn:
            conn.close() 