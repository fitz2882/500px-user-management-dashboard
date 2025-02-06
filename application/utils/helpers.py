import pandas as pd
from flask_caching import Cache
from dash import Dash, dcc, html
import dash_bootstrap_components as dbc
import re
from sqlalchemy import create_engine
from layout.layout_setup import app
from .data_loading import load_data

    
# Create an empty DataFrame with all required columns
def create_empty_dataframe():
    """
    Create an empty DataFrame with all required columns.
    """
    return pd.DataFrame({
        'user_id': [],
        'activity_week': [],
        'df2_full_name': [],
        'df2_username': [],
        'df2_user_type': [],
        'df2_registration_date': [],
        'df2_membership': [],
        'df2_country': [],
        'region': [],
        'df2_profile_url': [],
        'df2_social_links': [],
        'df3_med_aesthetic_score': [],
        'df3_med_lai_score': [],
        'df3_quality_score': [],
        'df2_exclusivity_rate': [],
        'df2_acceptance_rate': [],
        'num_of_photos_featured': [],
        'num_of_galleries_featured': [],
        'num_of_stories_featured': [],
        'total_uploads': [],
        'total_licensing_submissions': [],
        'total_accepted_licensing': [],
        'total_sales_revenue': [],
        'total_num_of_sales': [],
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

def create_table_row(row, row_number, is_selected=False):
    """Create a table row from a DataFrame row."""
    # Format registration date - handle both string and datetime inputs safely
    reg_date = '-'
    if pd.notnull(row['df2_registration_date']):
        try:
            if isinstance(row['df2_registration_date'], str):
                reg_date = row['df2_registration_date'].split(' ')[0]
            else:
                reg_date = str(row['df2_registration_date']).split(' ')[0]
        except Exception as e:
            print(f"Error formatting date: {e}")
            reg_date = '-'
    
    # Create checkbox with consistent value format
    checkbox = dcc.Checklist(
        id={'type': 'row-checkbox', 'index': str(row['user_id'])},
        options=[{'label': '', 'value': str(row['user_id'])}],
        value=[str(row['user_id'])] if is_selected else [],
        style={'margin': '0', 'padding': '0'}
    )
    
    # Create profile link cell
    profile_cell = html.Td(
        html.A('Profile', href=row['df2_profile_url'], target='_blank', className='profile-link')
        if pd.notnull(row['df2_profile_url']) else '-',
        style={'textAlign': 'center'}
    )
    
    # Create social links cell
    social_cell = html.Td(
        row['df2_social_links'] if pd.notnull(row['df2_social_links']) else '-',
        style={'textAlign': 'left'}
    )
    
    return html.Tr([
        html.Td(row_number, style={'textAlign': 'center'}),
        html.Td(checkbox, style={'textAlign': 'center'}),
        html.Td(row['user_id'], style={'textAlign': 'center'}),
        html.Td(row['df2_username'] or '-', style={'textAlign': 'left'}),
        html.Td(row['df2_full_name'] or '-', style={'textAlign': 'left'}),
        html.Td(row['df2_user_type'] or '-', style={'textAlign': 'center'}),
        html.Td(reg_date, style={'textAlign': 'center'}),
        html.Td(row['df2_membership'] or '-', style={'textAlign': 'center'}),
        html.Td(row['df2_country'] or '-', style={'textAlign': 'center'}),
        html.Td(row['region'] or '-', style={'textAlign': 'center'}),
        profile_cell,
        social_cell,
        html.Td(f"{row['total_uploads']:,.0f}" if pd.notnull(row['total_uploads']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['total_licensing_submissions']:,.0f}" if pd.notnull(row['total_licensing_submissions']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['total_accepted_licensing']:,.0f}" if pd.notnull(row['total_accepted_licensing']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['df3_med_aesthetic_score']:.2f}" if pd.notnull(row['df3_med_aesthetic_score']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['df3_med_lai_score']:.2f}" if pd.notnull(row['df3_med_lai_score']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['df3_quality_score']:.2f}" if pd.notnull(row['df3_quality_score']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['df2_exclusivity_rate']:.2f}%" if pd.notnull(row['df2_exclusivity_rate']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['df2_acceptance_rate']:.2f}%" if pd.notnull(row['df2_acceptance_rate']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['total_num_of_sales']:,.0f}" if pd.notnull(row['total_num_of_sales']) else '-', style={'textAlign': 'center'}),
        html.Td(f"${row['total_sales_revenue']:,.2f}" if pd.notnull(row['total_sales_revenue']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['df3_photo_likes']:,.0f}" if pd.notnull(row['df3_photo_likes']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['df3_comments']:,.0f}" if pd.notnull(row['df3_comments']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['df3_avg_visit_days_monthly']:.0f}" if pd.notnull(row['df3_avg_visit_days_monthly']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['num_of_photos_featured']:,.0f}" if pd.notnull(row['num_of_photos_featured']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['num_of_galleries_featured']:,.0f}" if pd.notnull(row['num_of_galleries_featured']) else '-', style={'textAlign': 'center'}),
        html.Td(f"{row['num_of_stories_featured']:,.0f}" if pd.notnull(row['num_of_stories_featured']) else '-', style={'textAlign': 'center'})
    ])