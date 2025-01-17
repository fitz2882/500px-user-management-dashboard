from dash import Dash
import dash_bootstrap_components as dbc
from pathlib import Path

# Get the absolute path to the assets directory
assets_path = Path(__file__).parent.parent / 'assets'

app = Dash(
    __name__, 
    title='User Management Dashboard', 
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/bootstrap-icons/1.8.1/font/bootstrap-icons.min.css"
    ],
    prevent_initial_callbacks='initial_duplicate',
    assets_folder=str(assets_path)
)
