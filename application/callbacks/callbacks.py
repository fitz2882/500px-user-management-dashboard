import dash
import pandas as pd
import math
from dash import Output, Input, State, ALL, dcc
import dash_bootstrap_components as dbc
from utils.data_loading import load_data, load_paginated_data
import re
from utils.helpers import create_table_row
import logging

def get_cached_data(force_reload=False):
    return load_data(force_reload=force_reload)

def reload_cached_data():
    return get_cached_data(force_reload=True)

def initialize_and_reset_data(app):
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
         Input('user-id-search', 'n_submit'),
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
         Input('num-stories-featured-max', 'value')],
        [State('user-id-search', 'value')],
        prevent_initial_call='initial_duplicate'
    )
    def _initialize_and_reset_data(pathname, reset_clicks, clear_reg_clicks, clear_act_clicks,
                                user_id_search_submit, reg_start, reg_end, act_start, act_end,
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
                                user_id_search):
        try:
            ctx = dash.callback_context
            if not ctx.triggered:
                # On initial load, set default dates
                df = load_data()
                if df.empty:
                    return dash.no_update
                
                min_reg_date = pd.to_datetime(df['df2_registration_date'].min()).strftime('%Y-%m-%d')
                max_reg_date = pd.to_datetime(df['df2_registration_date'].max()).strftime('%Y-%m-%d')
                min_act_date = pd.to_datetime(df['activity_week'].min()).strftime('%Y-%m-%d')
                max_act_date = pd.to_datetime(df['activity_week'].max()).strftime('%Y-%m-%d')
                
                user_type_options = [{'label': ut, 'value': ut} for ut in sorted(df['df2_user_type'].dropna().unique())]
                region_options = [{'label': region, 'value': region} for region in sorted(df['region'].dropna().unique())]
                membership_options = [{'label': m, 'value': m} for m in sorted(df['df2_membership'].dropna().unique())]
                
                return (df['user_id'].astype(str).tolist(), df['user_id'].astype(str).tolist(),
                       user_type_options, region_options, membership_options,
                       min_reg_date, max_reg_date, min_act_date, max_act_date)
            
            trigger = ctx.triggered[0]['prop_id'].split('.')[0]
            
            df = load_data()
            if df.empty:
                raise ValueError("No data loaded")
            
            # Get min/max dates from data
            min_reg_date = pd.to_datetime(df['df2_registration_date'].min()).strftime('%Y-%m-%d')
            max_reg_date = pd.to_datetime(df['df2_registration_date'].max()).strftime('%Y-%m-%d')
            min_act_date = pd.to_datetime(df['activity_week'].min()).strftime('%Y-%m-%d')
            max_act_date = pd.to_datetime(df['activity_week'].max()).strftime('%Y-%m-%d')
            
            # Handle registration date range
            if trigger == 'registration-date-range':
                reg_start = pd.to_datetime(reg_start).strftime('%Y-%m-%d') if reg_start else min_reg_date
                reg_end = pd.to_datetime(reg_end).strftime('%Y-%m-%d') if reg_end else max_reg_date
            elif trigger == 'clear-registration-date':
                reg_start = min_reg_date
                reg_end = max_reg_date
            elif reg_start is None or reg_end is None:  # Set defaults if not set
                reg_start = min_reg_date
                reg_end = max_reg_date
            
            # Handle activity week range
            if trigger == 'activity-week-range':
                act_start = pd.to_datetime(act_start).strftime('%Y-%m-%d') if act_start else min_act_date
                act_end = pd.to_datetime(act_end).strftime('%Y-%m-%d') if act_end else max_act_date
            elif trigger == 'clear-activity-week':
                act_start = min_act_date
                act_end = max_act_date
            elif act_start is None or act_end is None:  # Set defaults if not set
                act_start = min_act_date
                act_end = max_act_date

            # Create the mask for filtering
            mask = pd.Series(True, index=df.index)
            
            # Apply registration date filter
            if reg_start and reg_end:
                mask &= (df['df2_registration_date'] >= pd.to_datetime(reg_start)) & (df['df2_registration_date'] <= pd.to_datetime(reg_end))
            
            # Apply activity week filter first
            if act_start and act_end:
                mask &= (df['activity_week'] >= pd.to_datetime(act_start)) & (df['activity_week'] <= pd.to_datetime(act_end))
            
            # Apply all other filters
            if user_types:
                mask &= df['df2_user_type'].isin(user_types if isinstance(user_types, list) else [user_types])
            
            # Apply region filter
            if regions:
                mask &= df['region'].isin(regions if isinstance(regions, list) else [regions])
            
            # Apply membership filter
            if membership_types:
                mask &= df['df2_membership'].isin(membership_types if isinstance(membership_types, list) else [membership_types])
            
            # Apply range filters
            if avg_aesthetic_score_range:
                mask &= (df['df3_avg_aesthetic_score'] >= avg_aesthetic_score_range[0]) & (df['df3_avg_aesthetic_score'] <= avg_aesthetic_score_range[1])
            if avg_lai_score_range:
                mask &= (df['df2_avg_lai_score'] >= avg_lai_score_range[0]) & (df['df2_avg_lai_score'] <= avg_lai_score_range[1])
            if exclusivity_rate_range:
                mask &= (df['df2_exclusivity_rate'] >= exclusivity_rate_range[0]) & (df['df2_exclusivity_rate'] <= exclusivity_rate_range[1])
            if acceptance_rate_range:
                mask &= (df['df2_acceptance_rate'] >= acceptance_rate_range[0]) & (df['df2_acceptance_rate'] <= acceptance_rate_range[1])
            if avg_visit_days_range:
                mask &= (df['df3_avg_visit_days_monthly'] >= avg_visit_days_range[0]) & (df['df3_avg_visit_days_monthly'] <= avg_visit_days_range[1])
            
            # Apply min/max filters
            if uploads_min is not None:
                mask &= df['total_uploads'] >= uploads_min
            if uploads_max is not None:
                mask &= df['total_uploads'] <= uploads_max
            
            if licensing_min is not None:
                mask &= df['total_licensing_submissions'] >= licensing_min
            if licensing_max is not None:
                mask &= df['total_licensing_submissions'] <= licensing_max
            
            if sales_min is not None:
                mask &= df['total_num_of_sales'] >= sales_min
            if sales_max is not None:
                mask &= df['total_num_of_sales'] <= sales_max
            
            if revenue_min is not None:
                mask &= df['total_sales_revenue'] >= revenue_min
            if revenue_max is not None:
                mask &= df['total_sales_revenue'] <= revenue_max
            
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
            
            # Apply user ID search filter
            if user_id_search:
                search_ids = [id.strip() for id in user_id_search.split(',')]
                mask &= df['user_id'].astype(str).isin(search_ids)
            
            # Apply the mask to get filtered data
            df_filtered = df.loc[mask].copy()
            
            # Now aggregate by user_id with the filtered data
            df_agg = df_filtered.groupby('user_id').agg({
                # Profile info - use first since these don't change
                'df2_username': 'first',
                'df2_full_name': 'first',
                'df2_user_type': 'first',
                'df2_registration_date': 'first',
                'df2_membership': 'first',
                'df2_country': 'first',
                'region': 'first',
                'df2_profile_url': 'first',
                'df2_social_links': 'first',
                # Metrics that are already averaged - use first
                'df3_avg_aesthetic_score': 'first',
                'df2_avg_lai_score': 'first',
                'df2_exclusivity_rate': 'first',
                'df2_acceptance_rate': 'first',
                'df3_avg_visit_days_monthly': 'first',
                # Activity metrics - sum for the filtered period
                'total_uploads': 'sum',
                'total_licensing_submissions': 'sum',
                'total_sales_revenue': 'sum',
                'total_num_of_sales': 'sum',
                'df3_photo_likes': 'sum',
                'df3_comments': 'sum',
                'num_of_photos_featured': 'sum',
                'num_of_galleries_featured': 'sum',
                'num_of_stories_featured': 'sum'
            }).reset_index()
            
            # Now apply all other filters on the aggregated data
            mask = pd.Series(True, index=df_agg.index)
            
            if user_types:
                mask &= df_agg['df2_user_type'].isin(user_types if isinstance(user_types, list) else [user_types])
            if regions:
                mask &= df_agg['region'].isin(regions if isinstance(regions, list) else [regions])
            if membership_types:
                mask &= df_agg['df2_membership'].isin(membership_types if isinstance(membership_types, list) else [membership_types])
            
            # Apply numeric range filters on aggregated data
            if avg_aesthetic_score_range:
                mask &= (df_agg['df3_avg_aesthetic_score'] >= avg_aesthetic_score_range[0]) & (df_agg['df3_avg_aesthetic_score'] <= avg_aesthetic_score_range[1])
            if avg_lai_score_range:
                mask &= (df_agg['df2_avg_lai_score'] >= avg_lai_score_range[0]) & (df_agg['df2_avg_lai_score'] <= avg_lai_score_range[1])
            if exclusivity_rate_range:
                mask &= (df_agg['df2_exclusivity_rate'] >= exclusivity_rate_range[0]) & (df_agg['df2_exclusivity_rate'] <= exclusivity_rate_range[1])
            if acceptance_rate_range:
                mask &= (df_agg['df2_acceptance_rate'] >= acceptance_rate_range[0]) & (df_agg['df2_acceptance_rate'] <= acceptance_rate_range[1])
            if avg_visit_days_range:
                mask &= (df_agg['df3_avg_visit_days_monthly'] >= avg_visit_days_range[0]) & (df_agg['df3_avg_visit_days_monthly'] <= avg_visit_days_range[1])
            
            # Apply min/max filters on aggregated metrics
            if uploads_min is not None:
                mask &= df_agg['total_uploads'] >= uploads_min
            if uploads_max is not None:
                mask &= df_agg['total_uploads'] <= uploads_max
            if licensing_min is not None:
                mask &= df_agg['total_licensing_submissions'] >= licensing_min
            if licensing_max is not None:
                mask &= df_agg['total_licensing_submissions'] <= licensing_max
            if sales_min is not None:
                mask &= df_agg['total_num_of_sales'] >= sales_min
            if sales_max is not None:
                mask &= df_agg['total_num_of_sales'] <= sales_max
            if revenue_min is not None:
                mask &= df_agg['total_sales_revenue'] >= revenue_min
            if revenue_max is not None:
                mask &= df_agg['total_sales_revenue'] <= revenue_max
            if likes_min is not None:
                mask &= df_agg['df3_photo_likes'] >= likes_min
            if likes_max is not None:
                mask &= df_agg['df3_photo_likes'] <= likes_max
            if comments_min is not None:
                mask &= df_agg['df3_comments'] >= comments_min
            if comments_max is not None:
                mask &= df_agg['df3_comments'] <= comments_max
            if photos_featured_min is not None:
                mask &= df_agg['num_of_photos_featured'] >= photos_featured_min
            if photos_featured_max is not None:
                mask &= df_agg['num_of_photos_featured'] <= photos_featured_max
            if galleries_featured_min is not None:
                mask &= df_agg['num_of_galleries_featured'] >= galleries_featured_min
            if galleries_featured_max is not None:
                mask &= df_agg['num_of_galleries_featured'] <= galleries_featured_max
            if stories_featured_min is not None:
                mask &= df_agg['num_of_stories_featured'] >= stories_featured_min
            if stories_featured_max is not None:
                mask &= df_agg['num_of_stories_featured'] <= stories_featured_max
            
            # Get filtered user IDs from the final masked data
            filtered_user_ids = df_agg.loc[mask, 'user_id'].astype(str).tolist()
            
            # Get dropdown options from original data
            df_original = load_data()
            user_type_options = [{'label': ut, 'value': ut} for ut in sorted(df_original['df2_user_type'].dropna().unique())]
            region_options = [{'label': region, 'value': region} for region in sorted(df_original['region'].dropna().unique())]
            membership_options = [{'label': m, 'value': m} for m in sorted(df_original['df2_membership'].dropna().unique())]
            
            return (filtered_user_ids, filtered_user_ids, user_type_options, region_options, membership_options,
                   reg_start, reg_end, act_start, act_end)
            
        except Exception as e:
            print(f"Error in initialize_and_reset_data: {str(e)}")
            return dash.no_update

def update_selected_users(app):
    @app.callback(
        [Output('selected_user_ids', 'data', allow_duplicate=True),
         Output('select-all-checkbox', 'value', allow_duplicate=True),
         Output({'type': 'row-checkbox', 'index': ALL}, 'value')],
        [Input('select-all-checkbox', 'value'),
         Input({'type': 'row-checkbox', 'index': ALL}, 'value'),
         Input('filtered_user_ids', 'data'),
         Input('page-number', 'data')],
        [State({'type': 'row-checkbox', 'index': ALL}, 'id'),
         State('selected_user_ids', 'data')],
        prevent_initial_call='initial_duplicate'
    )
    def _manage_selections(select_all_checked, checkbox_values, filtered_user_ids, 
                         page_number, checkbox_ids, current_selections):
        ctx = dash.callback_context
        trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        # Initialize empty states
        if not filtered_user_ids:
            return [], [], [[] for _ in checkbox_ids] if checkbox_ids else []
        
        current_selections = current_selections or []
        
        # Handle true initial load (first time only)
        if not trigger and page_number is None:
            checkbox_values = [[id_dict['index']] for id_dict in checkbox_ids] if checkbox_ids else []
            return filtered_user_ids, ['all'], checkbox_values
        
        # Handle page navigation or filtered_user_ids update
        if trigger in ['page-number', 'filtered_user_ids', None]:
            new_checkbox_values = []
            for id_dict in checkbox_ids:
                if id_dict['index'] in current_selections:
                    new_checkbox_values.append([id_dict['index']])
                else:
                    new_checkbox_values.append([])
            all_selected = ['all'] if len(current_selections) == len(filtered_user_ids) else []
            return current_selections, all_selected, new_checkbox_values
        
        # Handle select-all checkbox
        if trigger == 'select-all-checkbox':
            if select_all_checked and 'all' in select_all_checked:
                checkbox_values = [[id_dict['index']] for id_dict in checkbox_ids]
                return filtered_user_ids, ['all'], checkbox_values
            return [], [], [[] for _ in checkbox_ids]
        
        # Handle individual row checkboxes
        if trigger.startswith('{'):
            try:
                selected_ids = current_selections.copy()
                new_checkbox_values = []
                
                for values, id_dict in zip(checkbox_values, checkbox_ids):
                    user_id = id_dict['index']
                    if values:  # Checkbox is checked
                        if user_id not in selected_ids:
                            selected_ids.append(user_id)
                        new_checkbox_values.append([user_id])
                    else:  # Checkbox is unchecked
                        if user_id in selected_ids:
                            selected_ids.remove(user_id)
                        new_checkbox_values.append([])
                
                # Update select-all checkbox based on whether all filtered users are selected
                all_selected = ['all'] if len(selected_ids) == len(filtered_user_ids) else []
                return selected_ids, all_selected, new_checkbox_values
                
            except Exception as e:
                return dash.no_update, dash.no_update, dash.no_update
        
        return dash.no_update, dash.no_update, dash.no_update

def update_page_number(app):
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
    def _update_page_number(prev_clicks, next_clicks, current_page, total_records, page_size, 
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

def update_table(app):
    @app.callback(
        [Output('table-body', 'children'),
         Output('page-display', 'children'),
         Output('page-number', 'data'),
         Output('total_records', 'data')],
        [Input('filtered_user_ids', 'data'),
         Input('page-size', 'value'),
         Input('previous-page', 'n_clicks'),
         Input('next-page', 'n_clicks'),
         Input('sort-by-dropdown', 'value'),
         Input('order-dropdown', 'value'),
         Input('user-id-search', 'n_submit'),
         Input('activity-week-range', 'start_date'),  # Add these inputs
         Input('activity-week-range', 'end_date')],
        [State('page-number', 'data'),
         State('total_records', 'data'),
         State('user-id-search', 'value'),
         State('selected_user_ids', 'data')],
        prevent_initial_call='initial_duplicate'
    )
    def _update_table(filtered_user_ids, rows_per_page, prev_clicks, next_clicks, sort_by, order, 
                     search_submit, act_start, act_end, page_number, total_records, 
                     user_id_search, selected_user_ids):
        try:
            ctx = dash.callback_context
            if not ctx.triggered:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
            triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            # Initialize page number if None
            if page_number is None:
                page_number = 1
            
            # Set default rows_per_page if None or invalid
            if not rows_per_page or not str(rows_per_page).isdigit():
                rows_per_page = 20
            else:
                rows_per_page = int(rows_per_page)
            
            # Handle user ID search
            if triggered_id == 'user-id-search' and user_id_search:
                search_ids = [id.strip() for id in user_id_search.split(',')]
                filtered_user_ids = [id for id in filtered_user_ids if id in search_ids]
                page_number = 1
            
            # Create no results row
            no_results_row = dash.html.Tr([
                dash.html.Td("No results found", colSpan=26, style={
                    'backgroundColor': 'tomato', 
                    'textAlign': 'left',
                    'padding': '10px',
                    'color': '#222222',
                    'fontSize': '14px'
                })
            ])
            
            # Handle empty filtered_user_ids
            if not filtered_user_ids:
                print("No filtered user IDs")
                return [no_results_row], "Page 1 of 1", 1, 0
            
            # Use cached data
            df = load_data()
            if df is None or df.empty:
                print("No data loaded")
                return [no_results_row], "Page 1 of 1", 1, 0
            
            print(f"Loaded data shape: {df.shape}")
            
            # Filter for the current filtered_user_ids
            df = df.loc[df['user_id'].astype(str).isin(filtered_user_ids)].copy()
            
            # Apply activity week filter
            if act_start and act_end:
                df = df.loc[(df['activity_week'] >= pd.to_datetime(act_start)) & 
                           (df['activity_week'] <= pd.to_datetime(act_end))]
            
            # Handle empty dataframe
            if df.empty:
                return [no_results_row], "Page 1 of 1", 1, 0
            
            # Aggregate the filtered data
            df = df.groupby('user_id').agg({
                'df2_username': 'first',
                'df2_full_name': 'first',
                'df2_user_type': 'first',
                'df2_registration_date': 'first',
                'df2_membership': 'first',
                'df2_country': 'first',
                'region': 'first',
                'df2_profile_url': 'first',
                'df2_social_links': 'first',
                # Use first for pre-averaged metrics
                'df3_avg_aesthetic_score': 'first',
                'df2_avg_lai_score': 'first',
                'df2_exclusivity_rate': 'first',
                'df2_acceptance_rate': 'first',
                'df3_avg_visit_days_monthly': 'first',
                # Sum activity metrics for the filtered period
                'total_uploads': 'sum',
                'total_licensing_submissions': 'sum',
                'total_sales_revenue': 'sum',
                'total_num_of_sales': 'sum',
                'df3_photo_likes': 'sum',
                'df3_comments': 'sum',
                'num_of_photos_featured': 'sum',
                'num_of_galleries_featured': 'sum',
                'num_of_stories_featured': 'sum'
            }).reset_index()
            
            # Apply sorting if specified
            if sort_by and sort_by in df.columns:
                ascending = order != 'desc'
                df = df.sort_values(by=sort_by, ascending=ascending)
            
            # Handle page navigation after knowing total records
            total_records = len(df)
            total_pages = max(1, -(-total_records // rows_per_page))  # Ceiling division
            
            if triggered_id == 'next-page' and page_number < total_pages:
                page_number += 1
            elif triggered_id == 'previous-page' and page_number > 1:
                page_number -= 1
            
            # Ensure page_number is within bounds
            page_number = max(1, min(page_number, total_pages))
            
            # Calculate start and end indices
            start_idx = (page_number - 1) * rows_per_page
            end_idx = min(start_idx + rows_per_page, total_records)
            
            # Get page data using .iloc
            df_page = df.iloc[start_idx:end_idx]
            
            # Create table rows
            table_rows = [
                create_table_row(row, idx + start_idx + 1, is_selected=str(row['user_id']) in selected_user_ids) 
                for idx, (_, row) in enumerate(df_page.iterrows())
            ]
            
            page_display = f"Page {page_number:,} of {total_pages:,}"
            
            return table_rows, page_display, page_number, total_records
            
        except Exception as e:
            import traceback
            print(f"Error in update_table: {str(e)}")
            print(traceback.format_exc())
            no_results_row = dash.html.Tr([
                dash.html.Td("No results found", colSpan=26, style={
                    'backgroundColor': 'tomato', 
                    'textAlign': 'left',
                    'padding': '10px',
                    'color': '#222222',
                    'fontSize': '14px'
                })
            ])
            return [no_results_row], "Page 1 of 1", 1, 0

def reset_filters(app):
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
         State('activity-week-range', 'end_date')],
    )
    def _reset_filters(reset_clicks, clear_reg_clicks, clear_act_clicks, reg_start_date, reg_end_date, act_start_date, act_end_date):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update

        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # Load data to get min/max dates
        df = load_data()
        min_reg_date = pd.to_datetime(df['df2_registration_date'].min()).strftime('%Y-%m-%d')
        max_reg_date = pd.to_datetime(df['df2_registration_date'].max()).strftime('%Y-%m-%d')
        min_act_date = pd.to_datetime(df['activity_week'].min()).strftime('%Y-%m-%d')
        max_act_date = pd.to_datetime(df['activity_week'].max()).strftime('%Y-%m-%d')

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

def reload_data(app):
    @app.callback(
        [Output('filtered_user_ids', 'data', allow_duplicate=True),
         Output('selected_user_ids', 'data', allow_duplicate=True),
         Output('reload-alert', 'is_open'),
         Output('reset-filters-button', 'n_clicks')],  # Add this to trigger reset_filters
        [Input('reload-data-button', 'n_clicks')],
        prevent_initial_call='initial_duplicate'
    )
    def _reload_data(n_clicks):
        try:
            if n_clicks is None:
                return dash.no_update
            
            print("Reloading data...")
            # Load fresh data (caching is handled in load_data)
            df = load_data(force_reload=True)
            
            if df is None or df.empty:
                raise ValueError("No data loaded")
                
            user_ids = df['user_id'].astype(str).tolist()
            print(f"Reloaded {len(user_ids)} user IDs")
            
            # Return values and trigger reset_filters by incrementing n_clicks
            return user_ids, user_ids, True, n_clicks
            
        except Exception as e:
            import traceback
            print(f"Error reloading data: {str(e)}")
            print(traceback.format_exc())
            return dash.no_update, dash.no_update, False, dash.no_update

def update_total_records_display(app):
    @app.callback(
        Output('total-records-display', 'children'),
        Input('total_records', 'data')
    )
    def _update_total_records_display(total_records):
        return f"Total Records: {total_records:,}"

def export_selected_rows(app):
    # Define the column mapping and order
    EXPORT_COLUMNS = {
        'user_id': 'User ID',
        'df2_username': 'Username',
        'df2_full_name': 'Name',
        'df2_user_type': 'User Type',
        'df2_registration_date': 'Registration Date',
        'df2_membership': 'Membership',
        'df2_country': 'Country',
        'region': 'Region',
        'df2_profile_url': 'Profile URL',
        'df2_social_links': 'Social Links',
        'total_uploads': 'Uploads',
        'total_licensing_submissions': 'Licensing Submissions',
        'df3_avg_aesthetic_score': 'Avg Aesthetic Score',
        'df2_avg_lai_score': 'Avg LAI Score',
        'df2_exclusivity_rate': 'Exclusivity Rate',
        'df2_acceptance_rate': 'Acceptance Rate',
        'total_num_of_sales': 'Sales',
        'total_sales_revenue': 'Revenue',
        'df3_photo_likes': 'Likes',
        'df3_comments': 'Comments',
        'df3_avg_visit_days_monthly': 'Avg Visit Days Monthly',
        'num_of_photos_featured': 'Photos Featured',
        'num_of_galleries_featured': 'Galleries Featured',
        'num_of_stories_featured': 'Stories Featured'
    }

    @app.callback(
        [Output('download-dataframe-csv', 'data'),
         Output("export-alert", "is_open", allow_duplicate=True)],
        [Input('export-button', 'n_clicks')],
        [State('selected_user_ids', 'data'),
         State('filtered_user_ids', 'data')],
        prevent_initial_call=True
    )
    def _export_selected_rows(n_clicks, selected_user_ids, filtered_user_ids):
        if not n_clicks or not selected_user_ids or not filtered_user_ids:
            print("Export cancelled: No data to export")
            return None, False
        
        try:
            print("Starting export process...")
            # Load the full dataset
            df = load_data()
            print(f"Data loaded, shape: {df.shape}")
            
            # Convert IDs to strings and prepare export list
            print("Converting IDs to strings...")
            df['user_id'] = df['user_id'].astype(str)
            selected_user_ids = set(str(id) for id in selected_user_ids)
            filtered_user_ids = set(str(id) for id in filtered_user_ids)
            
            # Get intersection of selected and filtered IDs
            export_user_ids = selected_user_ids.intersection(filtered_user_ids)
            print(f"Number of users to export: {len(export_user_ids)}")
            
            if not export_user_ids:
                print("No users selected for export")
                return None, False
            
            # Filter the dataframe
            print("Filtering data...")
            mask = df['user_id'].isin(export_user_ids)
            df_selected = df.loc[mask].copy()
            print(f"Filtered data shape: {df_selected.shape}")
            
            if df_selected.empty:
                print("No data found for selected users")
                return None, False

            print("Starting aggregation...")
            # Pre-select only needed columns before aggregation
            needed_columns = ['user_id'] + [col for col in EXPORT_COLUMNS.keys() if col != 'user_id']
            df_selected = df_selected[needed_columns]
            
            # Perform aggregation
            agg_dict = {
                'df2_username': 'first',
                'df2_full_name': 'first',
                'df2_user_type': 'first',
                'df2_registration_date': 'first',
                'df2_membership': 'first',
                'df2_country': 'first',
                'region': 'first',
                'df2_profile_url': 'first',
                'df2_social_links': 'first',
                'df3_avg_aesthetic_score': 'mean',
                'df2_avg_lai_score': 'mean',
                'df2_exclusivity_rate': 'mean',
                'df2_acceptance_rate': 'mean',
                'num_of_photos_featured': 'sum',
                'num_of_galleries_featured': 'sum',
                'num_of_stories_featured': 'sum',
                'total_uploads': 'sum',
                'total_licensing_submissions': 'sum',
                'total_sales_revenue': 'sum',
                'total_num_of_sales': 'sum',
                'df3_photo_likes': 'sum',
                'df3_comments': 'sum',
                'df3_avg_visit_days_monthly': 'mean'
            }
            
            df_selected = df_selected.groupby('user_id', as_index=False).agg(agg_dict)
            print(f"Aggregated data shape: {df_selected.shape}")

            print("Formatting dates...")
            df_selected['df2_registration_date'] = pd.to_datetime(df_selected['df2_registration_date']).dt.strftime('%Y-%m-%d')
            
            print("Preparing export data...")
            df_export = df_selected.rename(columns=EXPORT_COLUMNS)
            print(f"Final export data shape: {df_export.shape}")
            
            print("Creating CSV file...")
            return dcc.send_data_frame(
                df_export.to_csv,
                filename='user_management_exported_data.csv',
                index=False,
                encoding='utf-8-sig'
            ), True
            
        except Exception as e:
            print(f"Error in export: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None, False

def safe_numeric_value(value, default=None):
    """Helper function to safely extract numeric values from inputs"""
    try:
        if value is None:
            return default
        if isinstance(value, (list, tuple)):
            # For range sliders that return [min, max]
            if len(value) == 2:
                # If we're looking for a min value, return the first element
                # If we're looking for a max value, return the second element
                return value[0]  # or value[1] for max
            # For single values wrapped in a list
            value = value[0]
        # Convert to float to handle both int and float inputs
        return float(value)
    except (TypeError, ValueError, IndexError):
        return default

def apply_range_filter(df, column, min_val, max_val, mask):
    """Helper function to apply range filters safely"""
    try:
        if isinstance(min_val, (list, tuple)) and len(min_val) == 2:
            # If it's a range slider value, use both values
            mask &= (df[column] >= min_val[0]) & (df[column] <= min_val[1])
        else:
            # Otherwise use separate min/max values
            if min_val is not None:
                min_val = safe_numeric_value(min_val)
                if min_val is not None:
                    mask &= df[column] >= min_val
            if max_val is not None:
                max_val = safe_numeric_value(max_val)
                if max_val is not None:
                    mask &= df[column] <= max_val
    except Exception as e:
        print(f"Error applying filter for {column}: {str(e)}")
    return mask
