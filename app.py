from dash import Dash, dcc, html, Input, Output, State, ALL, callback_context, no_update
from dash.exceptions import PreventUpdate
import dash
import pandas as pd
import json
import math
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify
from math import ceil
from io import StringIO
import re
from dotenv import load_dotenv
import os
from threading import Lock
from flask_caching import Cache

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv('REDASH_API_KEY')

try:
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
    config['api_key'] = api_key
except Exception as e:
    print(f"Error loading config: {e}")
    config = {}

app = Dash(
    __name__, 
    title='User Management Dashboard', 
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/bootstrap-icons/1.8.1/font/bootstrap-icons.min.css"
    ],
    prevent_initial_callbacks='initial_duplicate'
)

cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache',
    'CACHE_DEFAULT_TIMEOUT': 300
})

cache.clear()

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

os.makedirs(os.path.dirname(config.get('data_path', './data/join_result.parquet')), exist_ok=True)

# Helper functions
@cache.memoize(timeout=300)
def load_data(force_reload=False):
    """
    Load data from the Parquet file if it has changed since the last read.
    Uses caching and thread-safe access.
    """
    global df, df_last_modified, user_type_options, region_options, membership_options, all_user_ids, start_date_reg, end_date_reg, start_date_act, end_date_act
    print("\n=== Debug: load_data called ===")
    
    file_path = config.get('data_path')
    if not file_path:
        print("Error: data_path not found in config")
        return create_empty_dataframe()
    
    try:
        # Force reload by clearing the cache if requested
        if force_reload:
            cache.delete_memoized(load_data)
            print("Cache cleared for force reload")
        
        last_modified = os.path.getmtime(file_path)
        with data_lock:
            if df is None or df_last_modified != last_modified or force_reload:
                print("Loading data from parquet file...")
                df = pd.read_parquet(file_path)
                df_last_modified = last_modified
                
                # Process data 
                df['activity_week'] = df['activity_week'].replace(['0', '', pd.NA, 'NaT'], pd.NaT)
                df['registration_date'] = df['registration_date'].replace(['0', '', pd.NA, 'NaT'], pd.NaT)

                # Specify the date format explicitly
                date_format = '%Y-%m-%d'

                # Parse date columns with the specified format
                df['registration_date'] = pd.to_datetime(df['registration_date'], format=date_format, errors='coerce')
                df['activity_week'] = pd.to_datetime(df['activity_week'], format=date_format, errors='coerce')

                # Normalize the timestamps to remove the time component
                df['registration_date'] = df['registration_date'].dt.normalize()
                df['activity_week'] = df['activity_week'].dt.normalize()

                # Exclude NaT values when calculating min and max dates
                registration_dates = df['registration_date'].dropna()
                activity_week_dates = df['activity_week'].dropna()

                # Use these dates for DatePickerRange
                start_date_reg = registration_dates.min()
                end_date_reg = registration_dates.max()
                start_date_act = activity_week_dates.min()
                end_date_act = activity_week_dates.max()

                # Clean country names
                df['country'] = df['country'].str.strip()
                df['country'] = df['country'].str.split(',').str[0]
                df['country'] = df['country'].str.title()
                
                # Load country mappings from JSON file
                with open('country_mappings.json', 'r') as f:
                    country_mappings = json.load(f)
                country_to_english = country_mappings

                # Map other languages to English country names only if they exist in the dictionary
                df['country'] = df['country'].apply(lambda x: country_to_english.get(x, x))

                # Load region mappings from JSON file
                with open('region_mappings.json', 'r') as f:
                    region_mappings = json.load(f)
                country_to_region = region_mappings

                # Map countries to regions
                df['region'] = df['country'].map(country_to_region).fillna('Other')
                df['region'] = df['region'].astype('category')

                # Replace specific values with custom labels
                df['country'] = df['country'].replace({'0': 'Unknown',
                                                    '': 'Unknown'})
                df['profile_url'] = df['profile_url'].replace({'0': ''})
                df['social_links'] = df['social_links'].replace({'0': ''})
                df['user_type'] = df['user_type'].replace({'0': 'Basic'})

                # Replace specific values with custom labels before converting to categorical
                df['membership'] = df['membership'].replace({
                    '0': 'No membership',
                    'Trial - Awesome Monthly - 30 Days': 'Trial - Awesome - M',
                    'Trial - Awesome Yearly - 30 Days': 'Trial - Awesome - Y',
                    'Trial - Pro Monthly - 30 Days': 'Trial - Pro - M',
                    'Trial - Pro Yearly - 30 Days': 'Trial - Pro - Y'
                })

                # Get unique user records by grouping by user_id
                df = df.groupby('user_id').agg({
                    'activity_week': 'first',
                    'full_name': 'first',
                    'username': 'first',
                    'user_type': 'first',
                    'registration_date': 'first',
                    'membership': 'first',
                    'country': 'first',
                    'region': 'first',
                    'profile_url': 'first',
                    'social_links': 'first',
                    'df3_avg_aesthetic_score': 'mean',
                    'avg_lai_score': 'mean',
                    'exclusivity_rate': 'mean',
                    'acceptance_rate': 'mean',
                    'num_of_photos_featured': 'sum',
                    'num_of_galleries_featured': 'sum',
                    'num_of_stories_featured': 'sum',
                    'df2_total_uploads': 'sum',
                    'df2_total_licensing_submissions': 'sum',
                    'df2_total_sales_revenue': 'sum',
                    'df2_total_num_of_sales': 'sum',
                    'df3_photo_likes': 'sum',
                    'df3_comments': 'sum',
                    'df3_avg_visit_days_monthly': 'mean'
                }).reset_index()

                # Convert 'membership' column to categorical after replacement
                df['membership'] = df['membership'].astype('category')

                # Define custom sort order
                custom_membership_order = ['No membership', 'Awesome - Monthly', 'Awesome - Yearly', 'Pro - Monthly', 'Pro - Yearly',
                                        'Android - Monthly', 'Android - Yearly', 'iOS - Monthly', 'iOS - Yearly', 'Free Pro CX',
                                        'Free Awesome CX', 'Trial - Awesome - M', 'Trial - Awesome - Y',
                                        'Trial - Pro - M', 'Trial - Pro - Y']

                custom_region_order = ['North America', 'South America', 'Northern Europe', 'Southern Europe', 'Western Europe', 
                                        'Eastern Europe', 'Africa', 'Asia Pacific (excl. China & Indonesia)', 'Rest of Asia', 'China',
                                            'Indonesia', 'Other']

                # Precompute options for dropdowns
                user_type_options = [
                    {'label': user_type, 'value': user_type} 
                    for user_type in sorted(df['user_type'].unique())
                ]

                region_options = [
                    {'label': region, 'value': region}
                    for region in sorted(df['region'].unique(), key=lambda x: custom_region_order.index(x) if x in custom_region_order else len(custom_region_order))
                ]

                membership_options = [
                    {'label': membership, 'value': membership}
                    for membership in sorted(df['membership'].unique(), key=lambda x: custom_membership_order.index(x) if x in custom_membership_order else len(custom_membership_order))
                ]
                
                print(f"Loaded and processed {len(df)} rows")
            return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return create_empty_dataframe()
    
    
# Create an empty DataFrame with all required columns
def create_empty_dataframe():
    """
    Create an empty DataFrame with all required columns.
    """
    return pd.DataFrame({
        'user_id': [],
        'activity_week': [],
        'full_name': [],
        'username': [],
        'user_type': [],
        'registration_date': [],
        'membership': [],
        'country': [],
        'region': [],
        'profile_url': [],
        'social_links': [],
        'df3_avg_aesthetic_score': [],
        'avg_lai_score': [],
        'exclusivity_rate': [],
        'acceptance_rate': [],
        'num_of_photos_featured': [],
        'num_of_galleries_featured': [],
        'num_of_stories_featured': [],
        'df2_total_uploads': [],
        'df2_total_licensing_submissions': [],
        'df2_total_sales_revenue': [],
        'df2_total_num_of_sales': [],
        'df3_photo_likes': [],
        'df3_comments': [],
        'df3_avg_visit_days_monthly': []
    })

# Define the validate_and_format_url function
def validate_and_format_url(link):
        link = link.strip()  # Remove any leading/trailing whitespace
        if not link:
            return None
        # Check if the link is a valid URL
        if not re.match(r'^(http://|https://)?[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+([/?].*)?$', link):
            return None
        # Ensure the link starts with http:// or https://
        if not link.startswith(('http://', 'https://')):
            link = 'https://' + link
        return link

def create_table_row(row, is_selected, row_number):
    """Create a table row with proper formatting and alignment."""
    user_id_str = str(row['user_id'])
    print(f"Creating row for user {user_id_str}, selected: {is_selected}")
    
    # Format profile URLs - split by comma and create multiple links
    profile_links = []
    if row['profile_url']:
        urls = str(row['profile_url']).split(',')
        profile_links = [
            html.A(url.strip(), href=validate_and_format_url(url.strip()), target='_blank')
            for url in urls if url.strip()
        ]
        profile_links = [html.Div(link) for link in profile_links]
    profile_cell = html.Td(profile_links if profile_links else '-', style={'textAlign': 'left'})
    
    # Format social links - split by comma and create multiple links
    social_links = []
    if row['social_links']:
        urls = str(row['social_links']).split(',')
        social_links = [
            html.A(url.strip(), href=validate_and_format_url(url.strip()), target='_blank')
            for url in urls if url.strip()
        ]
        social_links = [html.Div(link) for link in social_links]
    social_cell = html.Td(social_links if social_links else '-', style={'textAlign': 'left'})
    
    # Format dates
    reg_date = row['registration_date'].strftime('%Y-%m-%d') if pd.notnull(row['registration_date']) else '-'
    
    return html.Tr([
        html.Td(row_number, style={'textAlign': 'center'}),
        html.Td(dcc.Checklist(
            options=[{'label': '', 'value': str(row['user_id'])}],
            value=[str(row['user_id'])] if is_selected else [],
            id={'type': 'row-checkbox', 'index': str(row['user_id'])},
            style={'margin': '0', 'padding': '0'}
        ), style={'textAlign': 'center'}),
        html.Td(row['user_id'], style={'textAlign': 'center'}),
        html.Td(row['username'] or '-', style={'textAlign': 'left'}),
        html.Td(row['full_name'] or '-', style={'textAlign': 'left'}),
        html.Td(row['user_type'] or '-', style={'textAlign': 'center'}),
        html.Td(reg_date, style={'textAlign': 'center'}),
        html.Td(row['membership'] or '-', style={'textAlign': 'center'}),
        html.Td(row['country'] or '-', style={'textAlign': 'center'}),
        html.Td(row['region'] or '-', style={'textAlign': 'center'}),
        profile_cell,
        social_cell,
        html.Td(f"{row['df2_total_uploads']:,.0f}" if pd.notnull(row['df2_total_uploads']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['df2_total_licensing_submissions']:,.0f}" if pd.notnull(row['df2_total_licensing_submissions']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['df3_avg_aesthetic_score']:.2f}" if pd.notnull(row['df3_avg_aesthetic_score']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['avg_lai_score']:.2f}" if pd.notnull(row['avg_lai_score']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['exclusivity_rate']:.2f}%" if pd.notnull(row['exclusivity_rate']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['acceptance_rate']:.2f}%" if pd.notnull(row['acceptance_rate']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['df2_total_num_of_sales']:,.0f}" if pd.notnull(row['df2_total_num_of_sales']) else '-', style={'textAlign': 'center'}),
        html.Td(f"${row['df2_total_sales_revenue']:,.2f}" if pd.notnull(row['df2_total_sales_revenue']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['df3_photo_likes']:,.0f}" if pd.notnull(row['df3_photo_likes']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['df3_comments']:,.0f}" if pd.notnull(row['df3_comments']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['df3_avg_visit_days_monthly']:.0f}" if pd.notnull(row['df3_avg_visit_days_monthly']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['num_of_photos_featured']:,.0f}" if pd.notnull(row['num_of_photos_featured']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['num_of_galleries_featured']:,.0f}" if pd.notnull(row['num_of_galleries_featured']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['num_of_stories_featured']:,.0f}" if pd.notnull(row['num_of_stories_featured']) else '-', style={'textAlign': 'center'})
    ])

# Layout
select_all_checkbox = dcc.Checklist(
    id='select-all-checkbox',
    options=[{'label': '', 'value': 'all'}],
    value=['all'],  
    style={'display': 'inline-block'}
)

# Define the layout
app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='page-number', data=0),
    dcc.Store(id='total_records', data=0),
    dcc.Store(id='selected_user_ids', data=[]),
    dcc.Store(id='filtered_user_ids', data=[]),
    dcc.Store(id='initialization-trigger', data=True),
    dbc.Row([
        # Left column - Table
        dbc.Col([
            html.Div([
                html.Div([
                    dcc.Loading(
                        id="loading-1",
                        type="default",
                        children=[  
                            dbc.Table(
                                id='table',
                                children=[
                                    html.Thead(
                                        html.Tr([
                                            html.Th('Row'),
                                            html.Th(select_all_checkbox),
                                            html.Th('User ID'),
                                            html.Th('Username'),
                                            html.Th('Name'),
                                            html.Th('User Type'),
                                            html.Th('Registration Date'),
                                            html.Th('Membership'),
                                            html.Th('Country'),
                                            html.Th('Region'),
                                            html.Th('Profile URL'),
                                            html.Th('Social Links'),
                                            html.Th('Uploads *'),
                                            html.Th('Licensing Submissions *'),
                                            html.Th('Avg Aesthetic Score'),
                                            html.Th('Avg LAI Score'),
                                            html.Th('Exclusivity Rate'),
                                            html.Th('Acceptance Rate'),
                                            html.Th('Sales *'),
                                            html.Th('Revenue *'),
                                            html.Th('Likes *'),
                                            html.Th('Comments *'),
                                            html.Th('AVG Visit Days (per Month)'),
                                            html.Th('Photos Featured *'),
                                            html.Th('Galleries Featured *'),
                                            html.Th('Stories Featured *')
                                        ], className='table-header')
                                    ),
                                    html.Tbody(id='table-body')
                                ],
                                bordered=True,
                                hover=True,
                                responsive=False,
                                striped=True,
                                className='table-sm',
                                style={'tableLayout': 'auto', 'width': '100%'}
                            )
                        ],
                        className="loading-wrapper",
                        parent_style={"position": "relative"},
                        style={"visibility": "visible"}
                    ),
                    ], style={'overflowX': 'auto', 'overflowY': 'auto', 'height': 'calc(100vh - 89px)'}),
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            html.Span(id='total-records-display', 
                                    className='d-flex justify-content-left align-items-center', 
                                    style={'margin': '0 10px'}),
                        ], width=3),
                        # Center the page navigation buttons
                        dbc.Col([
                            dbc.Button("Previous", id="previous-page", style={'width': '100px', 'textAlign': 'center'}),
                            html.Span(id='page-display', style={'margin': '0 10px'}),
                            dbc.Button("Next", id="next-page", style={'width': '100px', 'textAlign': 'center'})
                        ], width=6, className='d-flex justify-content-center align-items-center'),

                        # Right-align the rows per page dropdown
                        dbc.Col([
                            dbc.Label("Rows per page:", style={'marginRight': '10px', 'marginBottom': '0px'}),
                            dbc.Select(
                                id='page-size',
                                options=[
                                    {'label': '10', 'value': 10},
                                    {'label': '20', 'value': 20},
                                    {'label': '50', 'value': 50},
                                    {'label': '100', 'value': 100}
                                ],
                                value=20, 
                                style={'width': '100px'}
                            )
                        ], width=3, className='d-flex justify-content-end align-items-center', style={'paddingRight': '0px'})
                    ], className='align-items-center', style={'marginTop': '25px', 'marginBottom': '25px'})
                ], style={
                    'position': 'fixed',
                    'bottom': '0',
                    'width': '75%',
                    'backgroundColor': 'white',
                    'padding': '0 10px',
                    'borderTop': '1px solid #dee2e6'
                })
            ], style={'height': '100vh', 'overflowY': 'auto', 'marginBottom': '0px'})
        ], width=9, style={'borderRight': '1px solid #dee2e6', 'height': '100vh'}),

        # Right column - Filters
        dbc.Col([
            html.Div([
                # Reload Data Button
                dbc.Button(
                    "Reload Data", 
                    id="reload-data-button", 
                    n_clicks=0,
                    className='btn btn-secondary',
                    style={'marginRight': '10px'}
                ),
                dbc.Alert(
                    "Data reloaded successfully!",
                    id="reload-alert",
                    is_open=False,
                    duration=4000,  # Alert will disappear after 4 seconds
                    color="success"
                ),  
                # User ID Search Input
                html.Div([
                    dbc.Label('Search User IDs', className='label'),
                    dcc.Input(
                        id='user-id-search',
                        type='text',
                        debounce=True,
                        placeholder='Enter User IDs (comma-separated)',
                        className='dash-input',
                        style={'width': '100%'},
                        value='',
                        n_submit=0
                        )
                    ], className='mb-4'),
                # Sort By and Order Dropdowns
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            dbc.Label('Sort By', className='label'),
                            dcc.Dropdown(
                                id='sort-by-dropdown',
                                options=[
                                    {'label': 'User ID', 'value': 'user_id'},
                                    {'label': 'User Type', 'value': 'user_type'},
                                    {'label': 'Registration Date', 'value': 'registration_date'},
                                    {'label': 'Membership', 'value': 'membership'},
                                    {'label': 'Country', 'value': 'country'},
                                    {'label': 'Region', 'value': 'region'},
                                    {'label': 'Uploads', 'value': 'df2_total_uploads'},
                                    {'label': 'Licensing Submissions', 'value': 'df2_total_licensing_submissions'},
                                    {'label': 'Avg Aesthetic Score', 'value': 'df3_avg_aesthetic_score'},
                                    {'label': 'Avg LAI Score', 'value': 'avg_lai_score'},
                                    {'label': 'Exclusivity Rate', 'value': 'exclusivity_rate'},
                                    {'label': 'Acceptance Rate', 'value': 'acceptance_rate'},
                                    {'label': 'Sales', 'value': 'df2_total_num_of_sales'},
                                    {'label': 'Revenue', 'value': 'df2_total_sales_revenue'},
                                    {'label': 'Likes', 'value': 'df3_photo_likes'},
                                    {'label': 'Comments', 'value': 'df3_comments'},
                                    {'label': 'Avg Visit Days', 'value': 'df3_avg_visit_days_monthly'},
                                    {'label': 'Photos Featured', 'value': 'num_of_photos_featured'},
                                    {'label': 'Galleries Featured', 'value': 'num_of_galleries_featured'},
                                    {'label': 'Stories Featured', 'value': 'num_of_stories_featured'}
                                ],
                                placeholder='Select Column to Sort By',
                                value='user_id',
                                className='dropdown',
                                style={'width': '100%'}
                            )
                        ], className='mb-4'),
                    ], width=8),
                    dbc.Col([
                        html.Div([
                            dbc.Label('Order', className='label'),
                            dcc.Dropdown(
                                id='order-dropdown',
                                options=[
                                    {'label': 'ASC', 'value': 'asc'},
                                    {'label': 'DESC', 'value': 'desc'}
                                ],
                                placeholder='Order',
                                value='asc',
                                className='dropdown'
                            )
                        ], className='mb-4'),
                    ], width=4)
                ]),
        
                # Date Range Filters
                html.Div([
                    dbc.Label('Activity Week Range', className='label'),
                    dcc.DatePickerRange(
                        id='activity-week-range',
                        start_date=start_date_act,
                        end_date=end_date_act,
                        display_format='YYYY-MM-DD',
                        className='date-picker'
                    ),
                    html.Div([
                        html.Button(
                            DashIconify(icon="material-symbols:restart-alt", width=20),
                            id='clear-activity-week',
                            className='clear-date-button',
                            n_clicks=0
                        )
                    ], className='bi-x-circle-container'),
                ], className='mb-4', style={'width': '100%'}),
                
                html.Div([
                    dbc.Label('Registration Date Range', className='label'),
                    dcc.DatePickerRange(
                        id='registration-date-range',
                        start_date=start_date_reg,
                        end_date=end_date_reg,
                        display_format='YYYY-MM-DD',
                        className='date-picker'
                    ),
                    html.Div([
                        html.Button(
                            DashIconify(icon="material-symbols:restart-alt", width=20),
                            id='clear-registration-date',
                            className='clear-date-button',
                            n_clicks=0
                        )
                    ], className='bi-x-circle-container'),
                ], className='mb-4'),
                
                # Dropdown Filters
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            dbc.Label('User Type', className='label'),
                            dcc.Dropdown(
                                id='user-type-dropdown',
                                options=[],
                                multi=True,
                                placeholder='Select User Type',
                                className='dropdown',
                                style={'width': '100%'}
                            )
                        ], className='mb-4'),
                    ], width=6),
                    dbc.Col([
                        html.Div([
                            dbc.Label('Membership Type', className='label'),
                            dcc.Dropdown(
                                id='membership-dropdown',
                                options=[],
                                multi=True,
                                placeholder='Select Membership Type',
                                className='dropdown',
                                style={'width': '100%'}
                            )
                        ], className='mb-4'),
                    ], width=6)
                ]),

                dbc.Row([
                    dbc.Col([
                        html.Div([
                            dbc.Label('Region', className='label'),
                            dcc.Dropdown(
                                id='region-dropdown',
                                options=[],
                                multi=True,
                                placeholder='Select Region',
                                className='dropdown',
                                style={'width': '100%'}
                            )
                        ], className='mb-4'),
                    ], width=12)
                ]),

                    # Inputs for Number of Uploads
                html.Div([
                    dbc.Label('Number of Uploads', className='label'),
                    dbc.Row([
                        dbc.Col([
                            dcc.Input(
                                id='num-uploads-min',
                                type='number',
                                debounce=True,
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-uploads-max',
                                type='number',
                                debounce=True,
                                placeholder='Max',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6)
                    ])
                ], className='mb-4'),

                # Inputs for Number of Licensing Submissions
                html.Div([
                    dbc.Label('Number of Licensing Submissions', className='label'),
                    dbc.Row([
                        dbc.Col([
                            dcc.Input(
                                id='num-licensing-submissions-min',
                                type='number',
                                debounce=True,
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-licensing-submissions-max',
                                type='number',
                                debounce=True,
                                placeholder='Max',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6)
                    ])
                ], className='mb-4'),

                # Inputs for Sales
                html.Div([
                    dbc.Label('Number of Sales', className='label'),
                    dbc.Row([
                        dbc.Col([
                            dcc.Input(
                                id='num-sales-min',
                                type='number',
                                debounce=True,
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-sales-max',
                                type='number',
                                debounce=True,
                                placeholder='Max',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6)
                    ])
                ], className='mb-4'),

                # Inputs for Revenue
                html.Div([
                    dbc.Label('Revenue', className='label'),
                    dbc.Row([
                        dbc.Col([
                            dcc.Input(
                                id='num-revenue-min',
                                type='number',
                                debounce=True,
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-revenue-max',
                                type='number',
                                debounce=True,
                                placeholder='Max',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6)
                    ])
                ], className='mb-4'),

                # Inputs for Number of Likes
                html.Div([
                    dbc.Label('Number of Likes', className='label'),
                    dbc.Row([
                        dbc.Col([
                            dcc.Input(
                                id='num-likes-min',
                                type='number',
                                debounce=True,
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-likes-max',
                                type='number',
                                debounce=True,
                                placeholder='Max',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6)
                    ])
                ], className='mb-4'),

                # Inputs for Number of Comments
                html.Div([
                    dbc.Label('Number of Comments', className='label'),
                    dbc.Row([
                        dbc.Col([
                            dcc.Input(
                                id='num-comments-min',
                                type='number',
                                debounce=True,
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-comments-max',
                                type='number',
                                debounce=True,
                                placeholder='Max',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6)
                    ])
                ], className='mb-4'),

                # Inputs for Number of Featured Photos
                html.Div([
                    dbc.Label('Number of Photos Featured', className='label'),
                    dbc.Row([
                        dbc.Col([
                            dcc.Input(
                                id='num-photos-featured-min',
                                type='number',
                                debounce=True,
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-photos-featured-max',
                                type='number',
                                debounce=True,
                                placeholder='Max',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6)
                    ])
                ], className='mb-4'),

                # Inputs for Number of Galleries Featured
                html.Div([
                    dbc.Label('Number of Galleries Featured', className='label'),
                    dbc.Row([
                        dbc.Col([
                            dcc.Input(
                                id='num-galleries-featured-min',
                                type='number',
                                debounce=True,
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-galleries-featured-max',
                                type='number',
                                debounce=True,
                                placeholder='Max',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6)
                    ])
                ], className='mb-4'),

                # Inputs for Number of Stories Featured
                html.Div([
                    dbc.Label('Number of Stories Featured', className='label'),
                    dbc.Row([
                        dbc.Col([
                            dcc.Input(
                                id='num-stories-featured-min',
                                type='number',
                                debounce=True,
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-stories-featured-max',
                                type='number',
                                debounce=True,
                                placeholder='Max',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6)
                    ])
                ], className='mb-4'),

                # Slider for Avg Visit Days (per Month)
                html.Div([
                    dbc.Label('Avg Visit Days (per Month)', className='label'),
                    dcc.RangeSlider(
                        id='avg-visit-days-slider',
                        min=0,
                        max=31,
                        step=1,
                        value=[0, 31],
                        marks={i: f'{i}' for i in range(0, 32, 5)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], className='mb-4'),

                # Slider for Avg Aesthetic Score
                html.Div([
                    dbc.Label('Avg Aesthetic Score', className='label'),
                    dcc.RangeSlider(
                        id='avg-aesthetic-score-slider',
                        min=0.00,
                        max=1.00,
                        step=0.01,
                        value=[0.00, 1.00],  # Ensure this is a list
                        marks={i/10: f'{i/10:.1f}' for i in range(0, 11)},  # Generate marks with decimal values
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], className='mb-4'),

                # Slider for Avg LAI Score
                html.Div([
                    dbc.Label('Avg LAI Score', className='label'),
                    dcc.RangeSlider(
                        id='avg-lai-score-slider',
                        min=0.0,
                        max=10.0,
                        step=0.1,
                        value=[0.0, 10.0],  # Ensure this is a list
                        marks={i: f'{i}' for i in range(0, 11)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], className='mb-4'),

                # Slider for Exclusivity Rate
                html.Div([
                    dbc.Label('Exclusivity Rate', className='label'),
                    dcc.RangeSlider(
                        id='exclusivity-rate-slider',
                        min=0.0,
                        max=100.0,
                        step=1,
                        value=[0.0, 100.0],
                        marks={i: f'{i}%' for i in range(0, 101, 10)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], className='mb-4'),

                # Slider for Acceptance Rate
                html.Div([
                    dbc.Label('Acceptance Rate', className='label'),
                    dcc.RangeSlider(
                        id='acceptance-rate-slider',
                        min=0.0,
                        max=100.0,
                        step=1,
                        value=[0.0, 100.0],
                        marks={i: f'{i}%' for i in range(0, 101, 10)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], className='mb-4'),
                
                # Horizontal line
                dbc.Row([
                    html.Div(html.Hr(style={'borderWidth': "2px", "width": "100%", "borderColor": "#cfb14d", 'margin': '0px'}))
                ]),

                # Buttons for Clear Filters and Export to CSV
                html.Div([
                    dbc.Button("Clear Filters", id="reset-filters-button", n_clicks=0, className='btn btn-secondary w-100 mb-2 clear-filters'),
                    dbc.Alert("CSV exported successfully!", 
                        id="export-alert", 
                        dismissable=True, 
                        is_open=False,
                        duration=4000,
                        color="success"),
                    dbc.Button("Export to CSV", id="export-button", n_clicks=0, className='btn btn-primary w-100'),
                    dcc.Download(id="download-dataframe-csv"),
                    dcc.Store(id='filtered-data-store')
                ], className='mt-4'),

            ], style={'height': '100vh', 'overflowY': 'auto', 'padding': '20px', 'paddingBottom': '30px'})
        ], width=3)
    ], className='g-0', style={'marginBottom': '0px', 'paddingBottom': '0px'}),  # g-0 removes gutters between columns
], fluid=True, style={'padding': '0'})


# Callbacks

# Initialization callback
@app.callback(
    [Output('filtered_user_ids', 'data', allow_duplicate=True),
     Output('selected_user_ids', 'data', allow_duplicate=True),
     Output('user-type-dropdown', 'options'),
     Output('region-dropdown', 'options'),
     Output('membership-dropdown', 'options'),
     Output('registration-date-range', 'start_date', allow_duplicate=True),
     Output('registration-date-range', 'end_date', allow_duplicate=True),
     Output('activity-week-range', 'start_date', allow_duplicate=True),
     Output('activity-week-range', 'end_date', allow_duplicate=True)],
    [Input('url', 'pathname'),
     Input('reset-filters-button', 'n_clicks'),
     Input('clear-registration-date', 'n_clicks'),
     Input('clear-activity-week', 'n_clicks'),
     Input('registration-date-range', 'start_date'),
     Input('registration-date-range', 'end_date'),
     Input('activity-week-range', 'start_date'),
     Input('activity-week-range', 'end_date'),
     Input('user-type-dropdown', 'value'),
     Input('region-dropdown', 'value'),
     Input('membership-dropdown', 'value'),
     Input('avg-aesthetic-score-slider', 'value'),
     Input('avg-lai-score-slider', 'value'),
     Input('exclusivity-rate-slider', 'value'),
     Input('acceptance-rate-slider', 'value'),
     Input('avg-visit-days-slider', 'value'),
     Input('num-uploads-min', 'value'),
     Input('num-uploads-max', 'value'),
     Input('num-licensing-submissions-min', 'value'),
     Input('num-licensing-submissions-max', 'value'),
     Input('num-sales-min', 'value'),
     Input('num-sales-max', 'value'),
     Input('num-revenue-min', 'value'),
     Input('num-revenue-max', 'value'),
     Input('num-likes-min', 'value'),
     Input('num-likes-max', 'value'),
     Input('num-comments-min', 'value'),
     Input('num-comments-max', 'value'),
     Input('num-photos-featured-min', 'value'),
     Input('num-photos-featured-max', 'value'),
     Input('num-galleries-featured-min', 'value'),
     Input('num-galleries-featured-max', 'value'),
     Input('num-stories-featured-min', 'value'),
     Input('num-stories-featured-max', 'value'),
     Input('user-id-search', 'n_submit')],
    [State('user-id-search', 'value')],
    prevent_initial_call=False
)
def initialize_and_reset_data(pathname, reset_clicks, clear_reg_clicks, clear_act_clicks,
                            reg_start, reg_end, act_start, act_end,
                            user_types, regions, membership_types,
                            avg_aesthetic_score_range, avg_lai_score_range,
                            exclusivity_rate_range, acceptance_rate_range,
                            avg_visit_days_range,
                            uploads_min, uploads_max,
                            licensing_min, licensing_max,
                            sales_min, sales_max,
                            revenue_min, revenue_max,
                            likes_min, likes_max,
                            comments_min, comments_max,
                            photos_featured_min, photos_featured_max,
                            galleries_featured_min, galleries_featured_max,
                            stories_featured_min, stories_featured_max,
                            search_submit, user_id_search):
    try:
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        print(f"\n=== Debug: initialize_and_reset_data called by {triggered_id} ===")
        
        df = load_data()
        if df is None or df.empty:
            return [], [], [], [], [], None, None, None, None
            
        # Get min/max dates from the data
        min_reg_date = df['registration_date'].min().date().isoformat()
        max_reg_date = df['registration_date'].max().date().isoformat()
        min_act_date = df['activity_week'].min().date().isoformat()
        max_act_date = df['activity_week'].max().date().isoformat()
        
        # Prepare dropdown options
        user_type_options = [{'label': t, 'value': t} for t in sorted(df['user_type'].unique())]
        region_options = [{'label': r, 'value': r} for r in sorted(df['region'].unique())]
        membership_options = [{'label': m, 'value': m} for m in sorted(df['membership'].unique())]
        
        # Handle different trigger cases
        if triggered_id == 'clear-registration-date':
            return df['user_id'].astype(str).tolist(), df['user_id'].astype(str).tolist(), user_type_options, region_options, membership_options, min_reg_date, max_reg_date, dash.no_update, dash.no_update
            
        elif triggered_id == 'clear-activity-week':
            return df['user_id'].astype(str).tolist(), df['user_id'].astype(str).tolist(), user_type_options, region_options, membership_options, dash.no_update, dash.no_update, min_act_date, max_act_date
            
        elif triggered_id in ['url', 'reset-filters-button', None]:
            user_ids = df['user_id'].astype(str).tolist()
            print(f"Resetting filters, returning all {len(user_ids)} user IDs")
            return user_ids, user_ids, user_type_options, region_options, membership_options, min_reg_date, max_reg_date, min_act_date, max_act_date
        
        # Apply filters
        mask = pd.Series(True, index=df.index)
        
        if reg_start and reg_end:
            mask &= (df['registration_date'] >= reg_start) & (df['registration_date'] <= reg_end)
        if act_start and act_end:
            mask &= (df['activity_week'] >= act_start) & (df['activity_week'] <= act_end)
        if user_types:
            mask &= df['user_type'].isin(user_types)
        if regions:
            mask &= df['region'].isin(regions)
        if membership_types:
            mask &= df['membership'].isin(membership_types)
        if avg_aesthetic_score_range:
            mask &= (df['df3_avg_aesthetic_score'] >= avg_aesthetic_score_range[0]) & (df['df3_avg_aesthetic_score'] <= avg_aesthetic_score_range[1])
        if avg_lai_score_range:
            mask &= (df['avg_lai_score'] >= avg_lai_score_range[0]) & (df['avg_lai_score'] <= avg_lai_score_range[1])
        if exclusivity_rate_range:
            mask &= (df['exclusivity_rate'] >= exclusivity_rate_range[0]) & (df['exclusivity_rate'] <= exclusivity_rate_range[1])
        if acceptance_rate_range:
            mask &= (df['acceptance_rate'] >= acceptance_rate_range[0]) & (df['acceptance_rate'] <= acceptance_rate_range[1])
        if avg_visit_days_range:
            mask &= (df['df3_avg_visit_days_monthly'] >= avg_visit_days_range[0]) & (df['df3_avg_visit_days_monthly'] <= avg_visit_days_range[1])
            
        # Apply numeric filters
        if uploads_min is not None:
            mask &= df['df2_total_uploads'] >= uploads_min
        if uploads_max is not None:
            mask &= df['df2_total_uploads'] <= uploads_max
        if licensing_min is not None:
            mask &= df['df2_total_licensing_submissions'] >= licensing_min
        if licensing_max is not None:
            mask &= df['df2_total_licensing_submissions'] <= licensing_max
        if sales_min is not None:
            mask &= df['df2_total_num_of_sales'] >= sales_min
        if sales_max is not None:
            mask &= df['df2_total_num_of_sales'] <= sales_max
        if revenue_min is not None:
            mask &= df['df2_total_sales_revenue'] >= revenue_min
        if revenue_max is not None:
            mask &= df['df2_total_sales_revenue'] <= revenue_max
        if likes_min is not None:
            mask &= df['df3_photo_likes'] >= likes_min
        if likes_max is not None:
            mask &= df['df3_photo_likes'] <= likes_max
        if comments_min is not None:
            mask &= df['df3_comments'] >= comments_min
        if comments_max is not None:
            mask &= df['df3_comments'] <= comments_max
        if photos_featured_min is not None:
            mask &= df['num_of_photos_featured'] >= photos_featured_min
        if photos_featured_max is not None:
            mask &= df['num_of_photos_featured'] <= photos_featured_max
        if galleries_featured_min is not None:
            mask &= df['num_of_galleries_featured'] >= galleries_featured_min
        if galleries_featured_max is not None:
            mask &= df['num_of_galleries_featured'] <= galleries_featured_max
        if stories_featured_min is not None:
            mask &= df['num_of_stories_featured'] >= stories_featured_min
        if stories_featured_max is not None:
            mask &= df['num_of_stories_featured'] <= stories_featured_max

        # Apply search filter
        if triggered_id == 'user-id-search' and user_id_search:
            try:
                search_ids = [int(id_str) for id_str in re.findall(r'\d+', user_id_search)]
                if search_ids:
                    mask &= df['user_id'].isin(search_ids)
            except ValueError:
                pass

        filtered_user_ids = df[mask]['user_id'].astype(str).tolist()
        print(f"Applied filters, returning {len(filtered_user_ids)} user IDs")
        
        return filtered_user_ids, filtered_user_ids, user_type_options, region_options, membership_options, reg_start or min_reg_date, reg_end or max_reg_date, act_start or min_act_date, act_end or max_act_date
        
    except Exception as e:
        print(f"Error in initialize_and_reset_data: {str(e)}")
        raise


# Initialize selected_user_ids with all filtered users
@app.callback(
    [Output('selected_user_ids', 'data', allow_duplicate=True)],
    [Input('filtered_user_ids', 'data')],
    prevent_initial_call=False
)
def initialize_selected_users(filtered_user_ids):
    """Initialize selected_user_ids with all filtered users."""
    if filtered_user_ids:
        return [filtered_user_ids]
    return [[]]


# Manage selections
@app.callback(
    [Output('selected_user_ids', 'data'),
     Output('select-all-checkbox', 'value')],
    [Input('select-all-checkbox', 'value'),
     Input({'type': 'row-checkbox', 'index': ALL}, 'value'),
     Input('filtered_user_ids', 'data')],
    [State({'type': 'row-checkbox', 'index': ALL}, 'id'),
     State('selected_user_ids', 'data')],
    prevent_initial_call=True
)
def manage_selections(select_all_checked, checkbox_values, filtered_user_ids, checkbox_ids, current_selected):
    """Update selected users based on checkbox interactions"""
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    print(f"\n=== Debug: manage_selections called by {trigger} ===")
    
    # On initial load or when filtered_user_ids changes, select all users
    if not trigger or trigger == 'filtered_user_ids':
        print("Initializing selections with all filtered IDs")
        return filtered_user_ids, ['all']
    
    # Handle select-all checkbox
    if trigger == 'select-all-checkbox':
        if select_all_checked and 'all' in select_all_checked:
            return filtered_user_ids, ['all']
        return [], []
    
    # Handle individual row checkboxes
    if trigger.startswith('{'):
        # Get the currently selected IDs from the visible checkboxes
        visible_selected = []
        for values, id_dict in zip(checkbox_values, checkbox_ids):
            if values:
                visible_selected.append(id_dict['index'])
        
        # Get the IDs that were checked/unchecked
        changed_id = eval(trigger)['index']
        
        # Update the full selection list
        if current_selected is None:
            current_selected = []
            
        if changed_id in visible_selected:
            # Checkbox was checked - add to selections if not already there
            if changed_id not in current_selected:
                current_selected.append(changed_id)
        else:
            # Checkbox was unchecked - remove from selections
            if changed_id in current_selected:
                current_selected.remove(changed_id)
        
        # Update select-all checkbox based on whether all filtered users are selected
        all_selected = ['all'] if len(current_selected) == len(filtered_user_ids) else []
        print(f"Individual selection changed. Selected count: {len(current_selected)}, All selected: {len(current_selected) == len(filtered_user_ids)}")
        
        return current_selected, all_selected

    return current_selected or [], ['all'] if current_selected and len(current_selected) == len(filtered_user_ids) else []


# Update page number
@app.callback(
    [Output('page-number', 'data', allow_duplicate=True)],
    [Input('previous-page', 'n_clicks'),
     Input('next-page', 'n_clicks')],
    [State('page-number', 'data'),
     State('total_records', 'data'),
     State('page-size', 'value'),
     State('selected_user_ids', 'data'),  # Add this state
     State('filtered_user_ids', 'data')], # Add this state
    prevent_initial_call=True
)
def update_page_number(prev_clicks, next_clicks, current_page, total_records, page_size, 
                      selected_user_ids, filtered_user_ids):
    ctx = dash.callback_context
    if not ctx.triggered:
        return [1]
    
    # Convert page_size to integer
    page_size = int(page_size) if page_size else 20
        
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    total_pages = math.ceil(total_records / page_size) if total_records and page_size else 1
    
    if button_id == 'previous-page':
        new_page = max(1, (current_page or 1) - 1)
    else:  # next-page
        new_page = min((current_page or 1) + 1, total_pages)
        
    return [new_page]


# Update table
@app.callback(
    [Output('table-body', 'children', allow_duplicate=True),
     Output('page-display', 'children', allow_duplicate=True),
     Output('page-number', 'data', allow_duplicate=True),
     Output('total_records', 'data', allow_duplicate=True)],
    [Input('filtered_user_ids', 'data'),
     Input('registration-date-range', 'start_date'),
     Input('registration-date-range', 'end_date'),
     Input('activity-week-range', 'start_date'),
     Input('activity-week-range', 'end_date'),
     Input('user-type-dropdown', 'value'),
     Input('region-dropdown', 'value'),
     Input('avg-aesthetic-score-slider', 'value'),
     Input('avg-lai-score-slider', 'value'),
     Input('exclusivity-rate-slider', 'value'),
     Input('acceptance-rate-slider', 'value'),
     Input('avg-visit-days-slider', 'value'),
     Input('num-uploads-min', 'value'),
     Input('num-uploads-max', 'value'),
     Input('num-licensing-submissions-min', 'value'),
     Input('num-licensing-submissions-max', 'value'),
     Input('num-sales-min', 'value'),
     Input('num-sales-max', 'value'),
     Input('num-revenue-min', 'value'),
     Input('num-revenue-max', 'value'),
     Input('num-likes-min', 'value'),
     Input('num-likes-max', 'value'),
     Input('num-comments-min', 'value'),
     Input('num-comments-max', 'value'),
     Input('num-photos-featured-min', 'value'),
     Input('num-photos-featured-max', 'value'),
     Input('num-galleries-featured-min', 'value'),
     Input('num-galleries-featured-max', 'value'),
     Input('num-stories-featured-min', 'value'),
     Input('num-stories-featured-max', 'value'),
     Input('membership-dropdown', 'value'),
     Input('sort-by-dropdown', 'value'),
     Input('order-dropdown', 'value'),
     Input('user-id-search', 'n_submit'),
     Input('page-number', 'data'),
     Input('page-size', 'value'),
     Input('select-all-checkbox', 'value')],
    [State('user-id-search', 'value'),
     State('selected_user_ids', 'data')],
    prevent_initial_call=True
)
def update_table(filtered_user_ids, reg_start, reg_end, act_start, act_end, 
                user_types, regions, avg_aesthetic_score_range, avg_lai_score_range,
                exclusivity_rate_range, acceptance_rate_range, avg_visit_days_range,
                uploads_min, uploads_max, licensing_min, licensing_max,
                sales_min, sales_max, revenue_min, revenue_max,
                likes_min, likes_max, comments_min, comments_max,
                photos_featured_min, photos_featured_max,
                galleries_featured_min, galleries_featured_max,
                stories_featured_min, stories_featured_max,
                membership_types, sort_by, order, search_submit,
                page_number, rows_per_page, select_all_value, user_id_search, selected_user_ids):
                
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
        
    if not filtered_user_ids:
        # Return a single row with "No results found" message
        no_results_row = html.Tr([
            html.Td(
                "No results found", 
                colSpan=26,  # Span all columns
                className="no-results-row"
            )
        ])
        return [no_results_row], "Showing 0 records", 0, 0

    print("\n=== Debug: update_table called ===")
    print(f"Trigger: {ctx.triggered[0]['prop_id']}")
    print(f"Select all value: {select_all_value}")
    print(f"Selected user IDs: {len(selected_user_ids) if selected_user_ids else 0}")
    print(f"Filtered user IDs: {len(filtered_user_ids) if filtered_user_ids else 0}")
    
    # Convert rows_per_page to integer
    rows_per_page = int(rows_per_page) if rows_per_page else 20
    
    # Load data only once
    df = load_data()
    
    print("\n=== Debug: Initial Data Analysis ===")
    print(f"Initial df shape: {df.shape}")
    print(f"Initial unique user IDs: {len(df['user_id'].unique())}")
    
    # Convert user_id to string for consistent comparison
    df['user_id'] = df['user_id'].astype(str)
    
    # Filter dataframe based on filtered_user_ids first
    if filtered_user_ids:
        mask = df['user_id'].astype(str).isin(filtered_user_ids)
        print(f"\nFiltering Analysis:")
        print(f"Number of user IDs to filter by: {len(filtered_user_ids)}")
        print(f"Number of unique user IDs to filter by: {len(set(filtered_user_ids))}")
        print(f"Sample of filtered_user_ids: {filtered_user_ids[:5]}")
        print(f"Rows where mask is True: {mask.sum()}")
    else:
        mask = pd.Series(True, index=df.index)
    
    filtered_df = df[mask].copy()
    print(f"\nAfter initial filtering:")
    print(f"Filtered df shape: {filtered_df.shape}")
    print(f"Filtered unique user IDs: {len(filtered_df['user_id'].unique())}")
    
    # Convert user_id to numeric for proper sorting
    df['user_id'] = pd.to_numeric(df['user_id'])
    filtered_df = df[df['user_id'].isin([int(id) for id in filtered_user_ids])]

    # Apply all other filters
    if reg_start and reg_end:
        mask &= (df['registration_date'] >= reg_start) & (df['registration_date'] <= reg_end)
    if act_start and act_end:
        mask &= (df['activity_week'] >= act_start) & (df['activity_week'] <= act_end)
    
    # Apply dropdown filters
    if user_types:
        mask &= df['user_type'].isin(user_types)
    if regions:
        mask &= df['region'].isin(regions)
    if membership_types:
        mask &= df['membership'].isin(membership_types)
    
    # Apply slider filters
    if avg_aesthetic_score_range:
        mask &= (df['df3_avg_aesthetic_score'] >= avg_aesthetic_score_range[0]) & (df['df3_avg_aesthetic_score'] <= avg_aesthetic_score_range[1])
    if avg_lai_score_range:
        mask &= (df['avg_lai_score'] >= avg_lai_score_range[0]) & (df['avg_lai_score'] <= avg_lai_score_range[1])
    if exclusivity_rate_range:
        mask &= (df['exclusivity_rate'] >= exclusivity_rate_range[0]) & (df['exclusivity_rate'] <= exclusivity_rate_range[1])
    if acceptance_rate_range:
        mask &= (df['acceptance_rate'] >= acceptance_rate_range[0]) & (df['acceptance_rate'] <= acceptance_rate_range[1])
    if avg_visit_days_range:
        mask &= (df['df3_avg_visit_days_monthly'] >= avg_visit_days_range[0]) & (df['df3_avg_visit_days_monthly'] <= avg_visit_days_range[1])
    
    # Apply numeric filters
    if uploads_min is not None:
        mask &= df['df2_total_uploads'] >= uploads_min
    if uploads_max is not None:
        mask &= df['df2_total_uploads'] <= uploads_max
    if licensing_min is not None:
        mask &= df['df2_total_licensing_submissions'] >= licensing_min
    if licensing_max is not None:
        mask &= df['df2_total_licensing_submissions'] <= licensing_max
    if sales_min is not None:
        mask &= df['df2_total_num_of_sales'] >= sales_min
    if sales_max is not None:
        mask &= df['df2_total_num_of_sales'] <= sales_max
    if revenue_min is not None:
        mask &= df['df2_total_sales_revenue'] >= revenue_min
    if revenue_max is not None:
        mask &= df['df2_total_sales_revenue'] <= revenue_max
    if likes_min is not None:
        mask &= df['df3_photo_likes'] >= likes_min
    if likes_max is not None:
        mask &= df['df3_photo_likes'] <= likes_max
    if comments_min is not None:
        mask &= df['df3_comments'] >= comments_min
    if comments_max is not None:
        mask &= df['df3_comments'] <= comments_max
    if photos_featured_min is not None:
        mask &= df['num_of_photos_featured'] >= photos_featured_min
    if photos_featured_max is not None:
        mask &= df['num_of_photos_featured'] <= photos_featured_max
    if galleries_featured_min is not None:
        mask &= df['num_of_galleries_featured'] >= galleries_featured_min
    if galleries_featured_max is not None:
        mask &= df['num_of_galleries_featured'] <= galleries_featured_max
    if stories_featured_min is not None:
        mask &= df['num_of_stories_featured'] >= stories_featured_min
    if stories_featured_max is not None:
        mask &= df['num_of_stories_featured'] <= stories_featured_max

    # Apply search filter
    if user_id_search:
        try:
            search_ids = [int(id_str) for id_str in re.findall(r'\d+', user_id_search)]
            if search_ids:
                mask &= df['user_id'].isin(search_ids)
        except ValueError:
            pass
    
    # Apply the mask to get filtered dataframe
    filtered_df = df[mask].copy()

    # Sort the dataframe
    if sort_by and order:
        ascending = order == 'asc'
        filtered_df = filtered_df.sort_values(by=sort_by, ascending=ascending)
    
    # Calculate pagination
    total_records = len(filtered_df)
    print(f"Final length of filtered_df: {len(filtered_df)}")
    print(f"Total records: {total_records}")
    if total_records == 0:
        return [], "No records to display", 1, 0
        
    total_pages = math.ceil(total_records / rows_per_page)
    page_number = min(max(page_number or 1, 1), total_pages)
    
    start_idx = (page_number - 1) * rows_per_page
    end_idx = min(start_idx + rows_per_page, total_records)
    
    # Create table rows for the current page
    table_rows = []
    selected_user_ids = selected_user_ids or []
    
    for i, (_, row) in enumerate(filtered_df.iloc[start_idx:end_idx].iterrows(), start=start_idx + 1):
        is_selected = str(row['user_id']) in selected_user_ids if selected_user_ids else False
        table_rows.append(create_table_row(row=row, is_selected=is_selected, row_number=i))
    
    # Update page display
    page_display = f"Page {page_number:,} of {total_pages:,}"
    
    print(f"Returning {len(table_rows)} rows, total records: {total_records}")
    return table_rows, page_display, page_number, total_records


# Update total records display
@app.callback(
    Output('total-records-display', 'children'),
    Input('total_records', 'data')
)
def update_total_records_display(total_records):
    return f"Total Records: {total_records:,}"


# Define the column mapping and order
EXPORT_COLUMNS = {
    'user_id': 'User ID',
    'username': 'Username',
    'full_name': 'Name',
    'user_type': 'User Type',
    'registration_date': 'Registration Date',
    'membership': 'Membership',
    'country': 'Country',
    'region': 'Region',
    'profile_url': 'Profile URL',
    'social_links': 'Social Links',
    'df2_total_uploads': 'Uploads',
    'df2_total_licensing_submissions': 'Licensing Submissions',
    'df3_avg_aesthetic_score': 'Avg Aesthetic Score',
    'avg_lai_score': 'Avg LAI Score',
    'exclusivity_rate': 'Exclusivity Rate',
    'acceptance_rate': 'Acceptance Rate',
    'df2_total_num_of_sales': 'Sales',
    'df2_total_sales_revenue': 'Revenue',
    'df3_photo_likes': 'Likes',
    'df3_comments': 'Comments',
    'df3_avg_visit_days_monthly': 'Avg Visit Days Monthly',
    'num_of_photos_featured': 'Photos Featured',
    'num_of_galleries_featured': 'Galleries Featured',
    'num_of_stories_featured': 'Stories Featured'
}

# Export the filtered data to CSV
@app.callback(
    [Output('download-dataframe-csv', 'data'),
     Output("export-alert", "is_open", allow_duplicate=True)],
    [Input('export-button', 'n_clicks')],
    [State('selected_user_ids', 'data')],
    prevent_initial_call=True
)
def export_selected_rows(n_clicks, selected_user_ids):
    if not n_clicks or not selected_user_ids:
        return None, False

    print(f"Exporting data for {len(selected_user_ids)} selected users")
    
    try:
        # Load the full dataset
        df = load_data()
        
        # Convert IDs to strings for comparison
        df['user_id'] = df['user_id'].astype(str)
        selected_user_ids = [str(id) for id in selected_user_ids]
        
        # Filter for selected user IDs
        df_selected = df[df['user_id'].isin(selected_user_ids)]
        
        if df_selected.empty:
            print("No data to export")
            return None, False

        # Format dates
        df_selected['registration_date'] = pd.to_datetime(df_selected['registration_date']).dt.strftime('%Y-%m-%d')
        df_selected['activity_week'] = pd.to_datetime(df_selected['activity_week']).dt.strftime('%Y-%m-%d')
        
        # Select and rename columns
        df_export = df_selected[list(EXPORT_COLUMNS.keys())].rename(columns=EXPORT_COLUMNS)
        
        return dcc.send_data_frame(
            df_export.to_csv,
            filename='user_management_exported_data.csv',
            index=False,
            encoding='utf-8-sig'
        ), True
        
    except Exception as e:
        print(f"Error exporting data: {str(e)}")
        return None, False


# Reset filters
@app.callback(
    [Output('registration-date-range', 'start_date'),
     Output('registration-date-range', 'end_date'),
     Output('activity-week-range', 'start_date'),
     Output('activity-week-range', 'end_date'),
     Output('user-type-dropdown', 'value'),
     Output('membership-dropdown', 'value'),
     Output('region-dropdown', 'value'),
     Output('avg-aesthetic-score-slider', 'value'),
     Output('avg-lai-score-slider', 'value'),
     Output('exclusivity-rate-slider', 'value'),
     Output('acceptance-rate-slider', 'value'),
     Output('avg-visit-days-slider', 'value'),
     Output('num-uploads-min', 'value'),
     Output('num-uploads-max', 'value'),
     Output('num-licensing-submissions-min', 'value'),
     Output('num-licensing-submissions-max', 'value'),
     Output('num-sales-min', 'value'),
     Output('num-sales-max', 'value'),
     Output('num-revenue-min', 'value'),
     Output('num-revenue-max', 'value'),
     Output('num-likes-min', 'value'),
     Output('num-likes-max', 'value'),
     Output('num-comments-min', 'value'),
     Output('num-comments-max', 'value'),
     Output('num-photos-featured-min', 'value'),
     Output('num-photos-featured-max', 'value'),
     Output('num-galleries-featured-min', 'value'),
     Output('num-galleries-featured-max', 'value'),
     Output('num-stories-featured-min', 'value'),
     Output('num-stories-featured-max', 'value'),
     Output('user-id-search', 'value'),
     Output('sort-by-dropdown', 'value'),
     Output('order-dropdown', 'value')],
    [Input('reset-filters-button', 'n_clicks'),
     Input('clear-registration-date', 'n_clicks'),
     Input('clear-activity-week', 'n_clicks')],
    [State('registration-date-range', 'start_date'),
     State('registration-date-range', 'end_date'),
     State('activity-week-range', 'start_date'),
     State('activity-week-range', 'end_date')]
)
def reset_filters(reset_clicks, clear_reg_clicks, clear_act_clicks, reg_start_date, reg_end_date, act_start_date, act_end_date):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Load data to get min/max dates
    df = load_data()
    min_reg_date = df['registration_date'].min().date().isoformat()
    max_reg_date = df['registration_date'].max().date().isoformat()
    min_act_date = df['activity_week'].min().date().isoformat()
    max_act_date = df['activity_week'].max().date().isoformat()

    print(f"Min reg date: {min_reg_date}, Max reg date: {max_reg_date}")
    print(f"Min act date: {min_act_date}, Max act date: {max_act_date}")

    if button_id == 'reset-filters-button':
        return [
            min_reg_date, max_reg_date,  # registration date range
            min_act_date, max_act_date,  # activity week range
            None,  # user type
            None,  # membership
            None,  # region
            [0.00, 1.00],  # aesthetic score
            [0.0, 10.0],  # LAI score
            [0.0, 100.0],  # exclusivity rate
            [0.0, 100.0],  # acceptance rate
            [0, 31],  # visit days
            None, None,  # uploads
            None, None,  # licensing submissions
            None, None,  # sales
            None, None,  # revenue
            None, None,  # likes
            None, None,  # comments
            None, None,  # photos featured
            None, None,  # galleries featured
            None, None,  # stories featured
            '',  # user id search
            'user_id',  # sort by
            'asc'   # order by
        ]
    elif button_id == 'clear-activity-week':
        return [reg_start_date, reg_end_date, min_act_date, max_act_date] + [dash.no_update] * 29
    elif button_id == 'clear-registration-date':
        return [min_reg_date, max_reg_date, act_start_date, act_end_date] + [dash.no_update] * 29 

    return [dash.no_update] * 33


# Reload data
@app.callback(
    [Output('filtered_user_ids', 'data', allow_duplicate=True),
     Output('selected_user_ids', 'data', allow_duplicate=True),
     Output('reload-alert', 'is_open')],
    Input('reload-data-button', 'n_clicks'),
    prevent_initial_call=True
)
def reload_data(n_clicks):
    if n_clicks is None:
        return dash.no_update, dash.no_update, dash.no_update
        
    try:
        print("\n=== Reloading data ===")
        df = load_data(force_reload=True)  # Add force_reload parameter to load_data
        user_ids = df['user_id'].astype(str).tolist()
        return user_ids, user_ids, True
    except Exception as e:
        print(f"Error reloading data: {str(e)}")
        return dash.no_update, dash.no_update, False


if __name__ == '__main__':
    app.run_server(debug=False)