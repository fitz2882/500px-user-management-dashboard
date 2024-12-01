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
    url = f"{base_url}/api/query_results/{query_result_id}"
    headers = {
        'Authorization': f'Key {api_key}',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Parse JSON response
    data = response.json()
    
    # Convert to DataFrame and save as CSV
    if 'query_result' in data and 'data' in data['query_result']:
        df = pd.DataFrame(data['query_result']['data']['rows'])
        df.to_csv(output_csv_file, index=False)
    else:
        raise ValueError("Unexpected response format from API")

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

    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    csv_files = {}
    for key, query_id in query_ids.items():
        print(f"Executing {key} (Query ID: {query_id})")
        query_result_id = execute_query(base_url, query_id, api_key)
        output_csv_file = os.path.join(output_folder, f"{key}.csv")
        print(f"Downloading result to {output_csv_file}")
        download_query_result(base_url, query_result_id, api_key, output_csv_file)
        csv_files[key] = output_csv_file

    # Add file existence checks before merge
    for file_path in csv_files.values():
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Required CSV file not found: {file_path}")
    
    # Get fixed_output_csv path from config
    fixed_output_csv = config.get('fixed_output_csv', './join_result.csv')
    print(f"Merging CSV files into {fixed_output_csv}")
    
    try:
        # Merge the CSV files
        join_csv_files(
            csv_files['query_1'],
            csv_files['query_2'],
            csv_files['query_3'],
            fixed_output_csv
        )
        print(f"CSV file saved to {fixed_output_csv}")
        print("Process completed successfully.")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Cleaning up...")
        # Optionally clean up incomplete output file
        if os.path.exists(fixed_output_csv):
            os.remove(fixed_output_csv)
        raise
    except Exception as e:
        print(f"Error during file merge: {str(e)}")
        raise

if __name__ == '__main__':
    main()
