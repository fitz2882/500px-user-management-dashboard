# 500px User Management Dashboard

A Flask-based web dashboard for managing and viewing 500px user data. The application fetches data from Redash queries, merges it into a unified dataset, and provides an interactive interface for filtering, viewing, and exporting user information.

## Features

- **Automated Data Updates**: Scheduled daily updates from Redash API queries
- **Interactive Dashboard**: Filter and search through user data with a responsive web interface
- **Data Export**: Export selected user records to CSV
- **Caching**: Built-in caching for improved performance
- **Docker Support**: Containerized deployment with Nginx
- **SQLite Database**: Local database storage for efficient data access

## Architecture

The application consists of several key components:

- **Flask/Dash Application**: Main web interface for user interaction
- **Data Pipeline**: Fetches data from Redash, merges multiple query results, and updates the database
- **Scheduler**: Runs daily updates at 05:00 to keep data fresh
- **SQLite Database**: Stores processed user data for quick access

## Prerequisites

- Python 3.11+
- Redash API access with valid API key
- Docker (optional, for containerized deployment)

## Installation

### Local Setup

1. Clone the repository:
```bash
git clone https://github.com/fitz2882/500px-user-management-dashboard.git
cd 500px-user-management-dashboard
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
Create a `.env` file in the root directory:
```
REDASH_API_KEY=your_redash_api_key_here
```

5. Configure application settings:
Edit `application/config.json` to specify:
- Redash base URL
- Query IDs for data sources
- Output folder paths

### Docker Setup

Build and run the application using Docker:

```bash
docker build -t 500px-user-dashboard .
docker run -p 8050:8050 500px-user-dashboard
```

## Usage

### Running the Application

Start the web dashboard:
```bash
cd application
python app.py
```

The dashboard will be available at `http://localhost:8050`

### Manual Data Update

To manually update user data from Redash:
```bash
cd application
python update_user_data.py
```

### Scheduled Updates

Run the scheduler for automatic daily updates:
```bash
cd application
python scheduler.py
```

The scheduler runs updates daily at 05:00 AM.

## Configuration

### config.json

The `application/config.json` file contains:

```json
{
  "redash_base_url": "https://your-redash-instance.com",
  "query_ids": {
    "query_1": 123,
    "query_2": 456,
    "query_3": 789
  },
  "output_folder": "./query_results",
  "fixed_output_csv": "./join_result.csv"
}
```

### Environment Variables

- `REDASH_API_KEY`: Your Redash API authentication key

## Project Structure

```
.
├── application/
│   ├── app.py                 # Main application entry point
│   ├── update_user_data.py    # Data fetching and update logic
│   ├── scheduler.py           # Scheduled task runner
│   ├── initialize_db.py       # Database initialization
│   ├── merge_utils.py         # CSV merging utilities
│   ├── callbacks/             # Dash callback functions
│   ├── layout/                # UI layout components
│   ├── utils/                 # Utility functions
│   ├── assets/                # Static assets (CSS, images)
│   └── config.json            # Application configuration
├── requirements.txt           # Python dependencies
├── Dockerfile                # Docker configuration
├── nginx.conf                # Nginx configuration
├── .env                      # Environment variables (not in repo)
└── README.md                 # This file
```

## Key Dependencies

- **Dash**: Interactive web application framework
- **Flask**: Web server framework
- **Pandas**: Data manipulation and analysis
- **SQLAlchemy**: Database ORM
- **Plotly**: Interactive visualizations
- **Schedule**: Task scheduling
- **Requests**: HTTP library for API calls

## Data Flow

1. **Fetch**: `update_user_data.py` queries the Redash API for latest data
2. **Merge**: Multiple query results are joined using `merge_utils.py`
3. **Process**: Data is processed and loaded into SQLite database
4. **Serve**: Flask/Dash application serves the data through the web interface
5. **Schedule**: Daily updates keep the data current

## Features in Detail

### Dashboard Interface

- Filter users by various criteria
- Pagination for large datasets
- Export selected rows to CSV
- Real-time data refresh
- Quality score tracking
- Licensing photo analysis

### Data Management

- Automatic merging of multiple data sources
- Country and region mapping
- Database caching for performance
- Error handling and retry logic for API calls

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is for internal 500px use.

## Support

For issues or questions, please open an issue in the GitHub repository.
