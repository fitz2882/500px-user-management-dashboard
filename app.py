from dash import Dash, dcc, html, Input, Output, State, ALL, callback_context, no_update
import dash
import pandas as pd
import json
import dash_bootstrap_components as dbc
from math import ceil
from io import StringIO
import re
from dotenv import load_dotenv
import os
from threading import Lock

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv('REDASH_API_KEY')

# Load the config.json file
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Update the API key in the configuration
config['api_key'] = api_key

# URL for the Bootstrap theme
external_stylesheets = [
    dbc.themes.BOOTSTRAP,
    "https://cdnjs.cloudflare.com/ajax/libs/bootstrap-icons/1.8.1/font/bootstrap-icons.min.css"
]

# Create the Dash app with the external stylesheet
app = Dash(__name__, title='User Management Dashboard', external_stylesheets=external_stylesheets)

data_lock = Lock()

# Global variables to store the DataFrame and the last modification time
df = None
df_last_modified = None
start_date_reg = None
end_date_reg = None
start_date_act = None
end_date_act = None
user_type_options = None
region_options = None
membership_options = None

select_all_checkbox = dcc.Checklist(
    id='select-all-checkbox',
    options=[{'label': '', 'value': 'all'}],
    value=['all'],
    style={'display': 'inline-block'}
)

def load_data():
    """
    Load data from the Parquet file if it has changed since the last read.
    Uses a lock to ensure thread-safe access.
    """
    global df, df_last_modified
    global start_date_reg, end_date_reg, start_date_act, end_date_act
    global user_type_options, region_options, membership_options
    
    file_path = '/Users/dave/Documents/SQL Query Project/User Management Dashboard/Auto Updates/join_result.parquet'
    
    try:
        last_modified = os.path.getmtime(file_path)
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return pd.DataFrame()
    
    # Use the lock to prevent multiple threads from reading the file simultaneously
    with data_lock:
        if df is None or df_last_modified != last_modified:
            # Load the data
            df = pd.read_parquet(file_path)
            df_last_modified = last_modified

            # Clean date columns
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

    return df

# Load data initially to set up variables for the layout
df = load_data()
all_user_ids = df['user_id'].tolist()

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

@app.callback(
    [Output('table-body', 'children'),
     Output('page-display', 'children'),
     Output('page-number', 'data'),
     Output('total_records', 'data')],
    [Input('registration-date-range', 'start_date'),
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
     Input('previous-page', 'n_clicks'),
     Input('next-page', 'n_clicks'),
     Input('page-size', 'value'),
     Input('select-all-checkbox', 'value')],
    [State('page-number', 'data'),
     State('total_records', 'data'),
     State('selected_user_ids', 'data'),
     State('filtered_user_ids', 'data')]
)
def update_table(*args):
    
    # Split args into inputs and states
    inputs = args[:-4]
    page_number, total_records, selected_user_ids, filtered_user_ids = args[-4:]

     # Get all input parameters
    (reg_start_date, reg_end_date, act_start_date, act_end_date, 
     user_types, regions, avg_aesthetic_score_range, avg_lai_score_range, 
     exclusivity_rate_range, acceptance_rate_range, avg_visit_days_range, 
     num_uploads_min, num_uploads_max, num_licensing_submissions_min, 
     num_licensing_submissions_max, num_sales_min, num_sales_max, 
     num_revenue_min, num_revenue_max, num_likes_min, num_likes_max, 
     num_comments_min, num_comments_max, num_photos_featured_min, 
     num_photos_featured_max, num_galleries_featured_min, 
     num_galleries_featured_max, num_stories_featured_min, 
     num_stories_featured_max, membership_types, sort_by, order, 
     prev_clicks, next_clicks, page_size, select_all_checkbox) = inputs
    
    # print("Count of selected_user_ids:", len(selected_user_ids))
    # print("Count of filtered_user_ids:", len(filtered_user_ids))

   # Load data
    df = load_data()
    
    # Initialize variables
    page_number = 0 if page_number is None else page_number
    page_size = int(page_size) if page_size else 20
    selected_user_ids = set(selected_user_ids or [])

    # Determine which input was triggered
    ctx = dash.callback_context
    if not ctx.triggered:
        triggered_id = None
    else:
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Apply filters
    mask = pd.Series(True, index=df.index)

    # Filter by registration date range
    if reg_start_date and reg_end_date:
        reg_start_date_dt = pd.to_datetime(reg_start_date).normalize()
        reg_end_date_dt = pd.to_datetime(reg_end_date).normalize()
        mask &= (df['registration_date'] >= reg_start_date_dt) & (df['registration_date'] <= reg_end_date_dt)

    # Filter by activity week range
    if act_start_date and act_end_date:
        act_start_date_dt = pd.to_datetime(act_start_date).normalize()
        act_end_date_dt = pd.to_datetime(act_end_date).normalize()
        mask &= (df['activity_week'] >= act_start_date_dt) & (df['activity_week'] <= act_end_date_dt)

    # Filter by user type
    if user_types and user_types is not None:
        if isinstance(user_types, list):
            mask &= df['user_type'].isin(user_types)
        else:
            mask &= df['user_type'] == user_types

    # Filter by region
    if regions and regions is not None:
        if isinstance(regions, list):
            mask &= df['region'].isin(regions)
        else:
            mask &= df['region'] == regions

    # Apply the mask to filter data
    filtered_df = df[mask].reset_index(drop=True)

    # Proceed with grouping by 'user_id'
    aggregated_df = filtered_df.groupby('user_id').agg({
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

    # Apply filters on aggregated columns
    aggregated_mask = pd.Series(True, index=aggregated_df.index)

    # Filter by avg aesthetic score range on aggregated data
    if isinstance(avg_aesthetic_score_range, list) and len(avg_aesthetic_score_range) == 2:
        aggregated_mask &= (aggregated_df['df3_avg_aesthetic_score'] >= avg_aesthetic_score_range[0]) & (aggregated_df['df3_avg_aesthetic_score'] <= avg_aesthetic_score_range[1])

    # Filter by avg lai score range on aggregated data
    if isinstance(avg_lai_score_range, list) and len(avg_lai_score_range) == 2:
        aggregated_mask &= (aggregated_df['avg_lai_score'] >= avg_lai_score_range[0]) & (aggregated_df['avg_lai_score'] <= avg_lai_score_range[1])

    # Filter by exclusivity rate range on aggregated data
    if isinstance(exclusivity_rate_range, list) and len(exclusivity_rate_range) == 2:
        aggregated_mask &= (aggregated_df['exclusivity_rate'] >= exclusivity_rate_range[0]) & (aggregated_df['exclusivity_rate'] <= exclusivity_rate_range[1])

    # Filter by acceptance rate range on aggregated data
    if isinstance(acceptance_rate_range, list) and len(acceptance_rate_range) == 2:
        aggregated_mask &= (aggregated_df['acceptance_rate'] >= acceptance_rate_range[0]) & (aggregated_df['acceptance_rate'] <= acceptance_rate_range[1])

    # Filter by avg visit days range on aggregated data
    if isinstance(avg_visit_days_range, list) and len(avg_visit_days_range) == 2:
        aggregated_mask &= (aggregated_df['df3_avg_visit_days_monthly'] >= avg_visit_days_range[0]) & (aggregated_df['df3_avg_visit_days_monthly'] <= avg_visit_days_range[1])

    # Filter by number of uploads range on aggregated data
    if num_uploads_min is not None:
        aggregated_mask &= aggregated_df['df2_total_uploads'] >= num_uploads_min
    if num_uploads_max is not None:
        aggregated_mask &= aggregated_df['df2_total_uploads'] <= num_uploads_max

    # Filter by number of licensing submissions range on aggregated data
    if num_licensing_submissions_min is not None:
        aggregated_mask &= aggregated_df['df2_total_licensing_submissions'] >= num_licensing_submissions_min
    if num_licensing_submissions_max is not None:
        aggregated_mask &= aggregated_df['df2_total_licensing_submissions'] <= num_licensing_submissions_max

    # Filter by number of sales range on aggregated data
    if num_sales_min is not None:
        aggregated_mask &= aggregated_df['df2_total_num_of_sales'] >= num_sales_min
    if num_sales_max is not None:
        aggregated_mask &= aggregated_df['df2_total_num_of_sales'] <= num_sales_max

    # Filter by revenue range on aggregated data
    if num_revenue_min is not None:
        aggregated_mask &= aggregated_df['df2_total_sales_revenue'] >= num_revenue_min
    if num_revenue_max is not None:
        aggregated_mask &= aggregated_df['df2_total_sales_revenue'] <= num_revenue_max

    # Filter by number of likes range on aggregated data
    if num_likes_min is not None:
        aggregated_mask &= aggregated_df['df3_photo_likes'] >= num_likes_min
    if num_likes_max is not None:
        aggregated_mask &= aggregated_df['df3_photo_likes'] <= num_likes_max

    # Filter by number of comments range on aggregated data
    if num_comments_min is not None:
        aggregated_mask &= aggregated_df['df3_comments'] >= num_comments_min
    if num_comments_max is not None:
        aggregated_mask &= aggregated_df['df3_comments'] <= num_comments_max

    # Filter by number of photos featured range on aggregated data
    if num_photos_featured_min is not None:
        aggregated_mask &= aggregated_df['num_of_photos_featured'] >= num_photos_featured_min
    if num_photos_featured_max is not None:
        aggregated_mask &= aggregated_df['num_of_photos_featured'] <= num_photos_featured_max

    # Filter by number of galleries featured range on aggregated data
    if num_galleries_featured_min is not None:
        aggregated_mask &= aggregated_df['num_of_galleries_featured'] >= num_galleries_featured_min
    if num_galleries_featured_max is not None:
        aggregated_mask &= aggregated_df['num_of_galleries_featured'] <= num_galleries_featured_max

    # Filter by number of stories featured range on aggregated data
    if num_stories_featured_min is not None:
        aggregated_mask &= aggregated_df['num_of_stories_featured'] >= num_stories_featured_min
    if num_stories_featured_max is not None:
        aggregated_mask &= aggregated_df['num_of_stories_featured'] <= num_stories_featured_max

    # Filter by membership type on aggregated data
    if membership_types and membership_types is not None:
        if isinstance(membership_types, list):
            aggregated_mask &= aggregated_df['membership'].isin(membership_types)
        else:
            aggregated_mask &= aggregated_df['membership'] == membership_types

    # Apply the aggregated mask to the aggregated data
    aggregated_df = aggregated_df[aggregated_mask].reset_index(drop=True)

    # Check if aggregated_df is empty after aggregated filters
    if aggregated_df.empty:
        empty_message = html.Tr([
            html.Td(
                "No results found for the current filters",
                colSpan=26,
                style={'text-align': 'left', 'padding': '20px'}
            )
        ])
        return [empty_message], "Page 0 of 0", 0, 0

    # Sort the data if specified
    if sort_by and sort_by in aggregated_df.columns:
        ascending = order == 'asc'
        aggregated_df = aggregated_df.sort_values(by=sort_by, ascending=ascending)

    # Calculate total pages
    total_records = len(aggregated_df)
    total_pages = max(1, ceil(total_records / page_size))

    # Reset page number if:
    # 1. Page size changed
    # 2. Filters changed
    # 3. Sort changed
    if (triggered_id in ['page-size', 'sort-by-dropdown', 'order-dropdown'] or 
        triggered_id in ['registration-date-range', 'activity-week-range', 'user-type-dropdown',
                        'region-dropdown', 'membership-dropdown'] or
        triggered_id is None):
        page_number = 0
    # Handle pagination based on triggered input
    elif triggered_id == 'previous-page' and page_number > 0:
        page_number -= 1
    elif triggered_id == 'next-page' and page_number < total_pages - 1:
        page_number += 1

    # Ensure current page number is valid for new page size
    max_page = max(0, total_pages - 1)
    page_number = min(page_number, max_page)
    
    # Calculate start and end indices
    start_idx = page_number * page_size
    end_idx = min(start_idx + page_size, total_records)

    # Get current page data
    page_data = aggregated_df.iloc[start_idx:end_idx].copy()
    page_data.insert(0, 'Row', range(start_idx + 1, end_idx + 1))

    # Convert filtered data to table rows
    rows = []
    for _, row in page_data.iterrows():
        user_id = int(row['user_id'])
        
        # Modified checkbox creation
        checkbox = dcc.Checklist(
            options=[{'label': '', 'value': user_id}],
            value=[user_id] if user_id in selected_user_ids else [],
            id={'type': 'row-checkbox', 'index': user_id},
            style={'display': 'inline-block'}
        )

        # Format dates and other values
        registration_date_display = row['registration_date'].strftime('%Y-%m-%d') if not pd.isnull(row['registration_date']) else 'N/A'

        # Format social links
        social_links = row['social_links'].split(',')
        social_links_components = []
        for link in social_links:
            formatted_link = validate_and_format_url(link)
            if formatted_link:
                social_links_components.append(html.A(href=formatted_link, children=formatted_link, target="_blank"))
                social_links_components.append(html.Br())
        if social_links_components:
            social_links_components.pop()

        rows.append(html.Tr([
            html.Td(row['Row'], id='row-number'),
            html.Td(checkbox),
            html.Td(row['user_id']),
            html.Td(row['username']),
            html.Td(row['full_name']),
            html.Td(row['user_type']),
            html.Td(registration_date_display),
            html.Td(row['membership']),
            html.Td(row['country']),
            html.Td(row['region']),
            html.Td(html.A(href=row['profile_url'], children=row['profile_url'], target="_blank")),
            html.Td(html.Div(social_links_components)),
            html.Td(f"{row['df2_total_uploads']:,d}"),
            html.Td(f"{row['df2_total_licensing_submissions']:,d}"),
            html.Td(f"{row['df3_avg_aesthetic_score']:.2f}"),
            html.Td(f"{row['avg_lai_score']:.1f}"),
            html.Td(f"{row['exclusivity_rate']:.2f}%"),
            html.Td(f"{row['acceptance_rate']:.2f}%"),
            html.Td(f"{row['df2_total_num_of_sales']:,d}"),
            html.Td(f"${row['df2_total_sales_revenue']:,.2f}"),
            html.Td(f"{row['df3_photo_likes']:,d}"),
            html.Td(f"{row['df3_comments']:,d}"),
            html.Td(f"{row['df3_avg_visit_days_monthly']:.1f}"),
            html.Td(f"{row['num_of_photos_featured']:,d}"),
            html.Td(f"{row['num_of_galleries_featured']:,d}"),
            html.Td(f"{row['num_of_stories_featured']:,d}")
        ]))

     # Update page display
    page_display = f"Page {page_number + 1:,} of {total_pages:,}"

    return rows, page_display, page_number, total_records


@app.callback(
    Output('selected_user_ids', 'data', allow_duplicate=True),
    Input('url', 'pathname'), 
    State('selected_user_ids', 'data'),
    prevent_initial_call='initial_duplicate'
)
def initialize_selected_user_ids(pathname, current_selected):
    if current_selected is None:
        df = load_data()
        return df['user_id'].astype(int).tolist()
    return current_selected


# Define the layout
app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='page-number', data=0),
    dcc.Store(id='total_records', data=0),
    dcc.Store(id='selected_user_ids', data=load_data()['user_id'].astype(int).tolist()),  # Initialize with all users
    dcc.Store(id='filtered_user_ids', data=load_data()['user_id'].astype(int).tolist()),  # Initialize with all users
    dbc.Row([
        # Left column - Table
        dbc.Col([
            html.Div([
                html.Div([
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
                        html.I(className="bi-x-circle", id="clear-activity-week", n_clicks=0)
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
                    html.I(className="bi-x-circle", id="clear-registration-date", n_clicks=0)
                ], className='bi-x-circle-container'),
            ], className='mb-4'),
                
            # Dropdown Filters
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Label('User Type', className='label'),
                        dcc.Dropdown(
                            id='user-type-dropdown',
                            options=user_type_options,
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
                                options=membership_options,
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
                                options=region_options,
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
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-uploads-max',
                                type='number',
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
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-licensing-submissions-max',
                                type='number',
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
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-sales-max',
                                type='number',
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
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-revenue-max',
                                type='number',
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
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-likes-max',
                                type='number',
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
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-comments-max',
                                type='number',
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
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-photos-featured-max',
                                type='number',
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
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-galleries-featured-max',
                                type='number',
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
                                placeholder='Min',
                                style={'width': '100%'},
                                className='dash-input'
                            )
                        ], width=6),
                        dbc.Col([
                            dcc.Input(
                                id='num-stories-featured-max',
                                type='number',
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
                    dbc.Alert("CSV exported successfully!", id="alert-fade", dismissable=True, is_open=False, color="success"),
                    dbc.Button("Export to CSV", id="export-button", n_clicks=0, className='btn btn-primary w-100'),
                    dcc.Download(id="download-dataframe-csv"),
                    dcc.Store(id='filtered-data-store')
                ], className='mt-4'),

            ], style={'height': '100vh', 'overflowY': 'auto', 'padding': '20px', 'paddingBottom': '30px'})
        ], width=3)
    ], className='g-0', style={'marginBottom': '0px', 'paddingBottom': '0px'}),  # g-0 removes gutters between columns
], fluid=True, style={'padding': '0'})

# Define the callback to store filtered user IDs
@app.callback(
    Output('filtered_user_ids', 'data'),
    [Input('registration-date-range', 'start_date'),
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
     Input('membership-dropdown', 'value')],
)
def update_filtered_user_ids(*args):
    # Check if no filters are applied
    if all(arg is None for arg in args):
        df = load_data()
        return df['user_id'].astype(int).tolist()
    
    (reg_start_date, reg_end_date, act_start_date, act_end_date, user_types, regions, 
    avg_aesthetic_score_range, avg_lai_score_range, exclusivity_rate_range, acceptance_rate_range,
    avg_visit_days_range, num_uploads_min, num_uploads_max, num_licensing_submissions_min, num_licensing_submissions_max,
    num_sales_min, num_sales_max, num_revenue_min, num_revenue_max, num_likes_min, num_likes_max, num_comments_min, num_comments_max,
    num_photos_featured_min, num_photos_featured_max, num_galleries_featured_min, num_galleries_featured_max, 
    num_stories_featured_min, num_stories_featured_max, membership_types) = args

    # Load data
    df = load_data()

    # Apply filters one by one
    mask = pd.Series(True, index=df.index)

    # Apply date filters
    if reg_start_date and reg_end_date:
        reg_start_date_dt = pd.to_datetime(reg_start_date).normalize()
        reg_end_date_dt = pd.to_datetime(reg_end_date).normalize()
        mask &= (df['registration_date'] >= reg_start_date_dt) & (df['registration_date'] <= reg_end_date_dt)

    if act_start_date and act_end_date:
        act_start_date_dt = pd.to_datetime(act_start_date).normalize()
        act_end_date_dt = pd.to_datetime(act_end_date).normalize()
        mask &= (df['activity_week'] >= act_start_date_dt) & (df['activity_week'] <= act_end_date_dt)

    # Apply other filters
    if user_types and user_types != 'All':
        if isinstance(user_types, list):
            mask &= df['user_type'].isin(user_types)
        else:
            mask &= df['user_type'] == user_types

    if regions and regions != 'All':
        if isinstance(regions, list):
            mask &= df['region'].isin(regions)
        else:
            mask &= df['region'] == regions

    # Apply additional filters (sliders, min/max values, and membership types) similar to above
    if isinstance(avg_aesthetic_score_range, list) and len(avg_aesthetic_score_range) == 2:
        mask &= (df['df3_avg_aesthetic_score'] >= avg_aesthetic_score_range[0]) & (df['df3_avg_aesthetic_score'] <= avg_aesthetic_score_range[1])

    if isinstance(avg_lai_score_range, list) and len(avg_lai_score_range) == 2:
        mask &= (df['avg_lai_score'] >= avg_lai_score_range[0]) & (df['avg_lai_score'] <= avg_lai_score_range[1])

    if isinstance(exclusivity_rate_range, list) and len(exclusivity_rate_range) == 2:
        mask &= (df['exclusivity_rate'] >= exclusivity_rate_range[0]) & (df['exclusivity_rate'] <= exclusivity_rate_range[1])

    if isinstance(acceptance_rate_range, list) and len(acceptance_rate_range) == 2:
        mask &= (df['acceptance_rate'] >= acceptance_rate_range[0]) & (df['acceptance_rate'] <= acceptance_rate_range[1])

    if isinstance(avg_visit_days_range, list) and len(avg_visit_days_range) == 2:
        mask &= (df['df3_avg_visit_days_monthly'] >= avg_visit_days_range[0]) & (df['df3_avg_visit_days_monthly'] <= avg_visit_days_range[1])

    if num_uploads_min is not None:
        mask &= df['df2_total_uploads'] >= num_uploads_min
    if num_uploads_max is not None:
        mask &= df['df2_total_uploads'] <= num_uploads_max

    if num_licensing_submissions_min is not None:
        mask &= df['df2_total_licensing_submissions'] >= num_licensing_submissions_min
    if num_licensing_submissions_max is not None:
        mask &= df['df2_total_licensing_submissions'] <= num_licensing_submissions_max

    if num_sales_min is not None:
        mask &= df['df2_total_num_of_sales'] >= num_sales_min
    if num_sales_max is not None:
        mask &= df['df2_total_num_of_sales'] <= num_sales_max

    if num_revenue_min is not None:
        mask &= df['df2_total_sales_revenue'] >= num_revenue_min
    if num_revenue_max is not None:
        mask &= df['df2_total_sales_revenue'] <= num_revenue_max

    if num_likes_min is not None:
        mask &= df['df3_photo_likes'] >= num_likes_min
    if num_likes_max is not None:
        mask &= df['df3_photo_likes'] <= num_likes_max

    if num_comments_min is not None:
        mask &= df['df3_comments'] >= num_comments_min
    if num_comments_max is not None:
        mask &= df['df3_comments'] <= num_comments_max

    if num_photos_featured_min is not None:
        mask &= df['num_of_photos_featured'] >= num_photos_featured_min
    if num_photos_featured_max is not None:
        mask &= df['num_of_photos_featured'] <= num_photos_featured_max

    if num_galleries_featured_min is not None:
        mask &= df['num_of_galleries_featured'] >= num_galleries_featured_min
    if num_galleries_featured_max is not None:
        mask &= df['num_of_galleries_featured'] <= num_galleries_featured_max

    if num_stories_featured_min is not None:
        mask &= df['num_of_stories_featured'] >= num_stories_featured_min
    if num_stories_featured_max is not None:
        mask &= df['num_of_stories_featured'] <= num_stories_featured_max

    if membership_types and membership_types != 'All':
        if isinstance(membership_types, list):
            mask &= df['membership'].isin(membership_types)
        else:
            mask &= df['membership'] == membership_types

    # Apply the mask to the DataFrame
    filtered_df = df[mask]
    return filtered_df['user_id'].astype(int).tolist()


# Store components in layout
dcc.Store(id='selected-rows', data=[]),
dcc.Store(id='filtered-rows', data=[]),

# Combined callback to manage selections
@app.callback(
    [Output('selected_user_ids', 'data'),
     Output('select-all-checkbox', 'value')],
    [Input('select-all-checkbox', 'value'),
     Input({'type': 'row-checkbox', 'index': ALL}, 'value'),
     Input('filtered_user_ids', 'data')],
    [State({'type': 'row-checkbox', 'index': ALL}, 'id'),
     State('selected_user_ids', 'data')]
)
def manage_selections(select_all_checked, checkbox_values, filtered_user_ids, checkbox_ids, selected_user_ids):
    ctx = dash.callback_context

    # On initial load, select all filtered users
    if not ctx.triggered:
        return filtered_user_ids, ['all']
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # print("\n=== Debug Info ===")
    # print(f"Triggered by: {ctx.triggered[0]['prop_id']}")
    # print(f"Select all checked: {select_all_checked}")
    # print(f"Number of checkbox values: {len(checkbox_values)}")
    # print(f"Number of checkbox IDs: {len(checkbox_ids)}")
    # print(f"Current selected_user_ids count: {len(selected_user_ids or [])}")
    # print(f"Filtered user IDs count: {len(filtered_user_ids or [])}")
    
    # Initialize selected set
    selected = set(selected_user_ids or [])
    filtered = set(filtered_user_ids or [])

    # If filters changed, intersect selected with filtered
    if triggered_id == 'filtered_user_ids':
        return filtered_user_ids, ['all']
    
    # Handle select all checkbox
    if triggered_id == 'select-all-checkbox':
        if select_all_checked and 'all' in select_all_checked:
            return list(filtered), ['all']
        else:
            return [], []

    # Handle individual checkboxes
    if triggered_id.startswith('{'):
        # Parse the JSON-like string without using eval
        import json
        checkbox_id = json.loads(triggered_id.replace("'", '"'))
        user_id = int(checkbox_id['index'])
        value = ctx.triggered[0]['value']
        
        # Start with current selection state, but only keep filtered users
        selected = selected.intersection(filtered)
        
        if value:
            selected.add(user_id)
        else:
            selected.discard(user_id)
        
        is_all_selected = len(selected) == len(filtered)
        return list(selected), ['all'] if is_all_selected else []

    # Default case: ensure selections are valid
    selected = selected.intersection(filtered)
    print(f"Selected set size after change: {len(selected)}")

    is_all_selected = len(selected) == len(filtered)
    return list(selected), ['all'] if is_all_selected else []


# Define the callback to export the filtered data to CSV
@app.callback(
    Output('download-dataframe-csv', 'data'),
    [Input('export-button', 'n_clicks')],
    [State('selected_user_ids', 'data'),
     State('filtered_user_ids', 'data')],
    prevent_initial_call=True
)
def export_selected_rows(n_clicks, selected_user_ids, filtered_user_ids):
    if not n_clicks or not selected_user_ids:
        return None

    print(f"Exporting data for {len(selected_user_ids)} selected users")
    
    # Load the full dataset
    df = load_data()
    
    # Filter for selected user IDs
    df_selected = df[df['user_id'].isin(selected_user_ids)]
    
    print(f"Found {len(df_selected)} rows to export")
    
    if df_selected.empty:
        print("No data to export")
        return None

    # Format the data for export
    df_selected['registration_date'] = df_selected['registration_date'].dt.strftime('%Y-%m-%d')
    df_selected['activity_week'] = df_selected['activity_week'].dt.strftime('%Y-%m-%d')
    
    # Ensure numeric formatting
    df_selected['df2_total_sales_revenue'] = df_selected['df2_total_sales_revenue'].apply(lambda x: f"${x:,.2f}")
    df_selected['exclusivity_rate'] = df_selected['exclusivity_rate'].apply(lambda x: f"{x:.2f}%")
    df_selected['acceptance_rate'] = df_selected['acceptance_rate'].apply(lambda x: f"{x:.2f}%")
    
    # Specify the column order
    columns_order = [
        'user_id',
        'full_name',
        'username',
        'user_type',
        'registration_date',
        'membership',
        'country',
        'region',
        'profile_url',
        'social_links',
        'df2_total_uploads',
        'df2_total_licensing_submissions',
        'df3_avg_aesthetic_score',
        'avg_lai_score',
        'exclusivity_rate',
        'acceptance_rate',
        'df2_total_num_of_sales',
        'df2_total_sales_revenue',
        'df3_photo_likes',
        'df3_comments',
        'df3_avg_visit_days_monthly',
        'num_of_photos_featured',
        'num_of_galleries_featured',
        'num_of_stories_featured'
    ]

    # Reorder the DataFrame based on selected user IDs
    df_selected = df_selected.reindex(columns=columns_order)

    # Return the formatted CSV
    return dcc.send_data_frame(
        df_selected.to_csv,
        filename='exported_data.csv',
        index=False,
        encoding='utf-8-sig'  # Use UTF-8 with BOM for Excel compatibility
    )


@app.callback(
    Output('total-records-display', 'children'),
    Input('total_records', 'data')
)
def update_total_records_display(total_records):
    return f"Total Records: {total_records:,}"

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
     Output('num-stories-featured-max', 'value')
     ],
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

    if button_id == 'reset-filters-button':
        return [None, None, None, None, None, None, None, [0.00, 1.00], [0, 10], [0, 100], [0, 100], [0, 31], None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]
    elif button_id == 'clear-registration-date':
        return [None, None, act_start_date, act_end_date, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update]
    elif button_id == 'clear-activity-week':
        return [reg_start_date, reg_end_date, None, None, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update]

    return dash.no_update

# Define the callback to toggle the alert message
@app.callback(
    Output("alert-fade", "is_open"),
    [Input("export-button", "n_clicks")],
    [State("alert-fade", "is_open")],
)
def toggle_alert(n, is_open):
    if n:
        return not is_open
    return is_open


if __name__ == '__main__':
    app.run_server(debug=False)