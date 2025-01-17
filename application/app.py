from layout.layout_setup import app
from layout.main_layout import layout
import json
import dash_bootstrap_components as dbc
from dotenv import load_dotenv
import os
from threading import Lock
from flask_caching import Cache
import logging
import dash
from utils.data_loading import init_data_loading

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

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.config.suppress_callback_exceptions = True

# Initialize cache
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache',
    'CACHE_DEFAULT_TIMEOUT': 3600
})

# Global variables
df = None
df_last_modified = None
all_user_ids = []
start_date_reg = None
end_date_reg = None
start_date_act = None
end_date_act = None
user_type_options = None
region_options = None
membership_options = None
data_lock = Lock()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import layout and callbacks
from layout.main_layout import layout
from callbacks import register_callbacks

app.layout = layout

# Register all callbacks
register_callbacks(app)

# After creating cache
init_data_loading(cache)

# Then import callbacks
from callbacks import register_callbacks

if __name__ == '__main__':
    app.run_server(debug=False)