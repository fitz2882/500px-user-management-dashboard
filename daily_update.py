import requests
import time
import os
from dotenv import load_dotenv
import json
from datetime import datetime
from merge_utils import join_csv_files 
import pandas as pd
import shutil 

def execute_query(base_url, query_id, api_key):
    url = f"{base_url}/api/queries/{query_id}/refresh"
    headers = {'Authorization': f'Key {api_key}'}
    response = requests.post(url, headers=headers)
    response.raise_for_status()

    job = response.json()['job']

    # Poll for the job status
    while job['status'] not in (3, 4):
        time.sleep(5)
        job_response = requests.get(f"{base_url}/api/jobs/{job['id']}", headers=headers)
        job_response.raise_for_status()
        job = job_response.json()['job']

    if job['status'] == 3:
        # Job completed
        query_result_id = job['query_result_id']
        return query_result_id
    else:
        # Job failed
        raise Exception("Query execution failed")

def download_query_result(base_url, query_result_id, api_key, output_csv_file):
    url = f"{base_url}/api/query_results/{query_result_id}.csv"
    headers = {'Authorization': f'Key {api_key}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    with open(output_csv_file, 'wb') as f:
        f.write(response.content)

def main():
    load_dotenv()

    # Load configurations from config.json
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)

    # Update config with API key from environment variable
    config['api_key'] = os.getenv('REDASH_API_KEY')

    base_url = config['redash_base_url']
    api_key = config['api_key']
    query_ids = config['query_ids']
    output_folder = config['output_folder']

    csv_files = {}
    for key, query_id in query_ids.items():
        print(f"Executing {key} (Query ID: {query_id})")
        query_result_id = execute_query(base_url, query_id, api_key)
        output_csv_file = os.path.join(output_folder, f"{key}.csv")
        print(f"Downloading result to {output_csv_file}")
        download_query_result(base_url, query_result_id, api_key, output_csv_file)
        csv_files[key] = output_csv_file

    # Merge the CSV files
    join_file = os.path.join(output_folder, 'join_result.csv')
    print(f"Merging CSV files into {join_file}")
    
    join_csv_files(
        csv_files['query_1'],
        csv_files['query_2'],
        csv_files['query_3'],
        join_file
    )

    # Convert the merged CSV to Parquet format
    join_parquet_file = os.path.join(output_folder, 'join_result.parquet')
    print(f"Converting {join_file} to Parquet format at {join_parquet_file}")
    
    # Load the merged CSV into a DataFrame
    df = pd.read_csv(
        join_file,
        dtype={
            'user_id': 'Int64',
            'activity_week': 'string',
            'full_name': 'string',
            'username': 'string',
            'country': 'string',
            'profile_url': 'string',
            'user_type': 'category',
            'registration_date': 'string',
            'social_links': 'string',
            'membership': 'category',
            'avg_lai_score': 'float64',
            'exclusivity_rate': 'float64',
            'acceptance_rate': 'float64',
            'num_of_photos_featured': 'Int64',
            'num_of_galleries_featured': 'Int64',
            'num_of_stories_featured': 'Int64',
            'df2_total_uploads': 'Int64',
            'df2_total_licensing_submissions': 'Int64',
            'df2_total_sales_revenue': 'float64',
            'df2_total_num_of_sales': 'Int64',
            'df3_photo_likes': 'Int64',
            'df3_comments': 'Int64',
            'df3_avg_visit_days_monthly': 'float64',
            'df3_avg_aesthetic_score': 'float64'
        }
    )
    
    # Save as Parquet
    df.to_parquet(join_parquet_file, index=False, engine='pyarrow')

    # Optionally copy the Parquet file to a fixed location for the app to read from
    fixed_output_parquet = config.get('fixed_output_parquet', 'join_result.parquet')
    shutil.copyfile(join_parquet_file, fixed_output_parquet)
    
    print(f"Parquet file saved to {fixed_output_parquet}")
    print("Process completed successfully.")

if __name__ == '__main__':
    main()
