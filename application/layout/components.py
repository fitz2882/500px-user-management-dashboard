from dash import html, dcc
import dash_bootstrap_components as dbc

# Filters Layout
filters_layout = html.Div([
    html.H3("Filters", className="filter-header"),
    html.Div([
        dcc.DatePickerRange(
            id='registration-date-range',
            min_date_allowed='2020-01-01',
            max_date_allowed='today',
            start_date_placeholder_text='Start Date',
            end_date_placeholder_text='End Date',
            className="date-picker"
        ),
        dcc.DatePickerRange(
            id='activity-week-range',
            min_date_allowed='2020-01-01',
            max_date_allowed='today',
            start_date_placeholder_text='Start Date',
            end_date_placeholder_text='End Date',
            className="date-picker"
        ),
        dcc.Dropdown(
            id='user-type-dropdown',
            options=[],
            multi=True,
            placeholder="Select User Types",
            className="dropdown"
        ),
        dcc.Dropdown(
            id='region-dropdown',
            options=[],
            multi=True,
            placeholder="Select Regions",
            className="dropdown"
        ),
        dcc.RangeSlider(
            id='avg-aesthetic-score-slider',
            min=0,
            max=10,
            step=0.1,
            marks={i: str(i) for i in range(11)},
            value=[0, 10],
            className="range-slider"
        ),
        dcc.RangeSlider(
            id='avg-lai-score-slider',
            min=0,
            max=10,
            step=0.1,
            marks={i: str(i) for i in range(11)},
            value=[0, 10],
            className="range-slider"
        ),
        dcc.RangeSlider(
            id='exclusivity-rate-slider',
            min=0,
            max=1,
            step=0.05,
            marks={i/10: str(i/10) for i in range(11)},
            value=[0, 1],
            className="range-slider"
        ),
        dcc.RangeSlider(
            id='acceptance-rate-slider',
            min=0,
            max=1,
            step=0.05,
            marks={i/10: str(i/10) for i in range(11)},
            value=[0, 1],
            className="range-slider"
        ),
        dcc.RangeSlider(
            id='avg-visit-days-slider',
            min=0,
            max=31,
            step=1,
            marks={i: str(i) for i in range(0, 32, 5)},
            value=[0, 31],
            className="range-slider"
        ),
        dcc.Input(id='num-uploads-min', type='number', placeholder='Min Uploads', className="input-field"),
        dcc.Input(id='num-uploads-max', type='number', placeholder='Max Uploads', className="input-field"),
        dcc.Input(id='num-licensing-submissions-min', type='number', placeholder='Min Licensing', className="input-field"),
        dcc.Input(id='num-licensing-submissions-max', type='number', placeholder='Max Licensing', className="input-field"),
        dcc.Input(id='num-sales-min', type='number', placeholder='Min Sales', className="input-field"),
        dcc.Input(id='num-sales-max', type='number', placeholder='Max Sales', className="input-field"),
        dcc.Input(id='num-revenue-min', type='number', placeholder='Min Revenue', className="input-field"),
        dcc.Input(id='num-revenue-max', type='number', placeholder='Max Revenue', className="input-field"),
        dcc.Input(id='num-likes-min', type='number', placeholder='Min Likes', className="input-field"),
        dcc.Input(id='num-likes-max', type='number', placeholder='Max Likes', className="input-field"),
        dcc.Input(id='num-comments-min', type='number', placeholder='Min Comments', className="input-field"),
        dcc.Input(id='num-comments-max', type='number', placeholder='Max Comments', className="input-field"),
        dcc.Input(id='num-photos-featured-min', type='number', placeholder='Min Photos Featured', className="input-field"),
        dcc.Input(id='num-photos-featured-max', type='number', placeholder='Max Photos Featured', className="input-field"),
        dcc.Input(id='num-galleries-featured-min', type='number', placeholder='Min Galleries Featured', className="input-field"),
        dcc.Input(id='num-galleries-featured-max', type='number', placeholder='Max Galleries Featured', className="input-field"),
        dcc.Input(id='num-stories-featured-min', type='number', placeholder='Min Stories Featured', className="input-field"),
        dcc.Input(id='num-stories-featured-max', type='number', placeholder='Max Stories Featured', className="input-field"),
        dcc.Dropdown(
            id='membership-dropdown',
            options=[],
            multi=True,
            placeholder="Select Membership Types",
            className="dropdown"
        ),
        dcc.Dropdown(
            id='sort-by-dropdown',
            options=[],
            placeholder="Sort By",
            className="dropdown"
        ),
        dcc.Dropdown(
            id='order-dropdown',
            options=[
                {'label': 'Ascending', 'value': 'asc'},
                {'label': 'Descending', 'value': 'desc'}
            ],
            value='asc',
            placeholder="Sort Order",
            className="dropdown"
        ),
        dcc.Input(id='user-id-search', type='text', placeholder='Search User IDs', className="input-field"),
        dcc.Input(id='page-size', type='number', value=20, placeholder='Rows per page', className="input-field"),
    ], className="filters-content")
])

# Table Layout
table_layout = html.Div([
    html.Table([
        html.Thead([
            html.Tr([
                html.Th("User ID", className="table-header-row"),
                html.Th("Full Name", className="table-header-row"),
                html.Th("Username", className="table-header-row"),
                html.Th("User Type", className="table-header-row"),
                html.Th("Registration Date", className="table-header-row"),
                html.Th("Membership", className="table-header-row"),
                html.Th("Country", className="table-header-row"),
                html.Th("Region", className="table-header-row"),
                html.Th("Profile URL", className="table-header-row"),
                html.Th("Social Links", className="table-header-row"),
                html.Th("Avg Aesthetic Score", className="table-header-row"),
                html.Th("Avg LAI Score", className="table-header-row"),
                html.Th("Exclusivity Rate", className="table-header-row"),
                html.Th("Acceptance Rate", className="table-header-row"),
                html.Th("Photos Featured", className="table-header-row"),
                html.Th("Galleries Featured", className="table-header-row"),
                html.Th("Stories Featured", className="table-header-row"),
                html.Th("Total Uploads", className="table-header-row"),
                html.Th("Licensing Submissions", className="table-header-row"),
                html.Th("Sales Revenue", className="table-header-row"),
                html.Th("Number of Sales", className="table-header-row"),
                html.Th("Photo Likes", className="table-header-row"),
                html.Th("Comments", className="table-header-row"),
                html.Th("Avg Visit Days Monthly", className="table-header-row")
            ], className="table-header")
        ]),
        html.Tbody(id='table-body')
    ], className="table table-striped table-bordered")
], className="table-responsive")

# Pagination Layout
pagination_layout = html.Div([
    html.Div(id='page-display', className="pagination-info"),
    dbc.ButtonGroup([
        dbc.Button("Previous", id='previous-page', n_clicks=0, color="primary", outline=True),
        dbc.Button("Next", id='next-page', n_clicks=0, color="primary", outline=True)
    ], className="pagination-buttons")
], className="pagination-container mt-3") 