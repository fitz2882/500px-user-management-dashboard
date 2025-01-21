import pandas as pd
import sqlite3
import json
import os

def create_region_column(df, region_mappings):
    """Create a region column based on country mappings."""
    def get_region(country):
        if not isinstance(country, str):
            return 'Unknown'
        for region, countries in region_mappings.items():
            if country in countries:
                return region
        return 'Unknown'
    
    df['region'] = df['df2_country'].apply(get_region)
    return df

def load_and_process_data(csv_path, config_path, db_path='user_data.db'):
    # Load configuration
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    
    country_mappings_path = config.get('country_mappings_path', 'country_mappings.json')
    region_mappings_path = config.get('region_mappings_path', 'region_mappings.json')
    
    # Load country mappings
    if not os.path.exists(country_mappings_path):
        print(f"Country mappings file not found at {country_mappings_path}. Skipping country mapping.")
        country_mappings = {}
    else:
        with open(country_mappings_path, 'r') as f:
            country_mappings = json.load(f)
    
    # Load region mappings
    if not os.path.exists(region_mappings_path):
        print(f"Region mappings file not found at {region_mappings_path}. Skipping region mapping.")
        region_mappings = {}
    else:
        with open(region_mappings_path, 'r') as f:
            region_mappings = json.load(f)
    
    # Define the expected date format (modify as per your data)
    DATE_FORMAT = '%Y-%m-%d'  # Example: '2023-10-15'
    
    # Load raw data with explicit date parsing
    try:
        df = pd.read_csv(
            csv_path,
            encoding='utf-8',
            parse_dates=['df2_registration_date', 'activity_week'],
            dtype={'df2_registration_date': 'object', 'activity_week': 'object'}
        )
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    print(f"Initial columns: {df.columns.tolist()}")

    # Debug prints
    print("Initial data load:")
    print(f"Total rows: {len(df)}")

    # Convert to datetime without altering the dtype to datetime.date
    df['df2_registration_date'] = pd.to_datetime(df['df2_registration_date'], format=DATE_FORMAT, errors='coerce')
    df['activity_week'] = pd.to_datetime(df['activity_week'], format=DATE_FORMAT, errors='coerce')

    # Drop rows with invalid dates if needed
    df.dropna(subset=['df2_registration_date', 'activity_week'], inplace=True)

    # Fill NaN in 'df2_country' with 'Unknown' and ensure all entries are strings
    df['df2_country'] = df['df2_country'].fillna('Unknown').astype(str)

    # Clean country names
    df['df2_country'] = df['df2_country'].str.strip()
    df['df2_country'] = df['df2_country'].str.split(',').str[0]
    df['df2_country'] = df['df2_country'].str.title()
    
    # Map country names to English if mappings are provided
    if country_mappings:
        df['df2_country'] = df['df2_country'].apply(lambda x: country_mappings.get(x, x))
    
    # Create region column
    df = create_region_column(df, region_mappings)
    
    # Convert categorical columns if they exist
    if 'df2_user_type' in df.columns:
        df['df2_user_type'] = df['df2_user_type'].astype('category')
    else:
        print("df2_user_type column not found in CSV. Skipping conversion.")
    
    if 'df2_membership' in df.columns:
        df['df2_membership'] = df['df2_membership'].astype('category')
    else:
        print("df2_membership column not found in CSV. Skipping conversion.")
    
    if 'region' in df.columns:
        df['region'] = df['region'].astype('category')
    else:
        print("region column not found after mapping. Skipping conversion.")
    
    # Ensure consistent data types for numeric columns
    numeric_columns = [
        'total_uploads', 'total_licensing_submissions', 'total_num_of_sales',
        'total_sales_revenue', 'df3_photo_likes', 'df3_comments',
        'df3_avg_aesthetic_score', 'df2_avg_lai_score',
        'df2_exclusivity_rate', 'df2_acceptance_rate',
        'df3_avg_visit_days_monthly', 'num_of_photos_featured',
        'num_of_galleries_featured', 'num_of_stories_featured'
    ]
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            print(f"Numeric column '{col}' not found in CSV. Skipping conversion.")
    
    # Save to SQLite and create indexes
    try:
        conn = sqlite3.connect(db_path)
        df.to_sql('user_data', conn, if_exists='replace', index=False)
        
        # Create indexes for faster querying
        cursor = conn.cursor()
        index_columns = ['user_id', 'df2_user_type', 'region', 'df2_registration_date', 'activity_week']
        for col in index_columns:
            if col in df.columns:
                try:
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{col} ON user_data ({col})")
                except sqlite3.OperationalError as e:
                    print(f"Error creating index for '{col}': {e}")
            else:
                print(f"Cannot create index on '{col}' as it does not exist in the data.")
        conn.commit()
        conn.close()
        print(f"Data successfully loaded into {db_path} with indexes")
    except Exception as e:
        print(f"Error saving to SQLite: {e}")
        conn.close()

def create_empty_dataframe():
    """Create an empty DataFrame with the expected schema."""
    columns = [
        'user_id', 'df2_full_name', 'df2_username', 'df2_user_type',
        'df2_registration_date', 'df2_membership', 'df2_country',
        'region', 'df2_profile_url', 'df2_social_links',
        'total_uploads', 'total_licensing_submissions', 'df3_avg_aesthetic_score',
        'df2_avg_lai_score', 'df2_exclusivity_rate', 'df2_acceptance_rate',
        'df3_avg_visit_days_monthly', 'num_of_photos_featured',
        'num_of_galleries_featured', 'num_of_stories_featured',
        'total_num_of_sales', 'total_sales_revenue', 'df3_photo_likes',
        'df3_comments'
    ]
    return pd.DataFrame(columns=columns)

if __name__ == '__main__':
    CONFIG_PATH = './config.json'      # Update with your config path if different
    CSV_PATH = './join_result.csv'     # Update with your CSV path
    DB_PATH = './user_data.db'         # SQLite database file
    
    # Ensure the CSV path exists
    if not os.path.exists(CSV_PATH):
        print(f"CSV file not found at {CSV_PATH}. Please check the path in config.json.")
    else:
        load_and_process_data(CSV_PATH, CONFIG_PATH, DB_PATH)
