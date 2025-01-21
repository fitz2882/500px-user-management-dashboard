from flask import Flask
from layout.layout_setup import app
from layout.main_layout import layout
import json
import dash_bootstrap_components as dbc
from dotenv import load_dotenv
import os
from flask_caching import Cache
import logging
from utils.data_loading import init_data_loading
from dash import Dash

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv('REDASH_API_KEY')

try:
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
    config['api_key'] = api_key
except Exception as e:
    config = {}

# Initialize the Flask server
server = Flask(__name__)

# Configure cache
cache_config = {
    'CACHE_TYPE': 'SimpleCache',  # Choose appropriate cache type
    'CACHE_DEFAULT_TIMEOUT': 3600  # 1 hour
}
cache = Cache()
cache.init_app(server, config=cache_config)

# Initialize the Dash app
app = Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Initialize data loading with cache
init_data_loading(cache)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up layout
app.layout = layout

# Register callbacks
from callbacks.callbacks import (
    initialize_and_reset_data,
    reload_data,
    update_selected_users,
    update_page_number,
    update_table,
    reset_filters,
    update_total_records_display,
    export_selected_rows
)

# Initialize each callback
initialize_and_reset_data(app)
reload_data(app)
update_selected_users(app)
update_page_number(app)
update_table(app)
reset_filters(app)
update_total_records_display(app)
export_selected_rows(app)

# Run the app
if __name__ == '__main__':
    app.run_server(debug=False)