from dash import html, dcc
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify
from .layout_setup import app

start_date_reg = None
end_date_reg = None
start_date_act = None
end_date_act = None

select_all_checkbox = dcc.Checklist(
    id='select-all-checkbox',
    options=[{'label': '', 'value': 'all'}],
    value=[],
    style={'display': 'inline-block'}
)

layout = app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='page-number', data=0),
    dcc.Store(id='total_records', data=0),
    dcc.Store(id='selected_user_ids', data=[]),
    dcc.Store(id='filtered_user_ids', data=[]),
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
                                    {'label': 'User Type', 'value': 'df2_user_type'},
                                    {'label': 'Registration Date', 'value': 'df2_registration_date'},
                                    {'label': 'Membership', 'value': 'df2_membership'},
                                    {'label': 'Country', 'value': 'df2_country'},
                                    {'label': 'Region', 'value': 'region'},
                                    {'label': 'Uploads', 'value': 'total_uploads'},
                                    {'label': 'Licensing Submissions', 'value': 'total_licensing_submissions'},
                                    {'label': 'Avg Aesthetic Score', 'value': 'df3_avg_aesthetic_score'},
                                    {'label': 'Avg LAI Score', 'value': 'df2_avg_lai_score'},
                                    {'label': 'Exclusivity Rate', 'value': 'df2_exclusivity_rate'},
                                    {'label': 'Acceptance Rate', 'value': 'df2_acceptance_rate'},
                                    {'label': 'Sales', 'value': 'total_num_of_sales'},
                                    {'label': 'Revenue', 'value': 'total_sales_revenue'},
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