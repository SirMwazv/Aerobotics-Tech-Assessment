# Agrotech Geospatial Analytics API

A production-ready FastAPI application for detecting missing trees in orchards using geospatial analysis and agronomic signals.

## Features

- **Missing Tree Detection**: Identifies locations of missing trees using statistical filtering and spatial gap analysis
- **Geospatial Analysis**: Projects coordinates to planar systems, builds KD-Trees for spatial indexing
- **Robust Error Handling**: Automatic retries with exponential backoff for external API calls
- **SOLID Architecture**: Clean separation of concerns with dependency injection
- **OpenAPI Documentation**: Auto-generated interactive API documentation

## Architecture

The application follows a layered architecture:

```
├── API Layer (routers/controllers)
│   └── FastAPI endpoints with no business logic
├── Application Layer (services/application)
│   └── Orchestration and coordination
├── Domain Layer (services/domain)
│   └── Core business logic and algorithms
├── Infrastructure Layer (infrastructure)
│   └── External API client with retry logic
└── Utilities (utils)
    └── Geospatial projections and spatial helpers
```

## Installation

### Prerequisites

- Python 3.9 or higher
- pip

### Setup

1. Clone the repository:
```bash
cd /Users/mwazvitamutowo/Aerobotics-Tech-Assessment
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

Edit the `.env` file to configure the application:

```env
# External API Configuration
EXTERNAL_API_BASE_URL=https://api.example.com
EXTERNAL_API_KEY=your_api_key_here

# Retry Configuration
MAX_RETRY_ATTEMPTS=3
RETRY_BACKOFF_MULTIPLIER=1
RETRY_MIN_WAIT=4
RETRY_MAX_WAIT=10

# Missing Tree Detection Parameters
MISSING_TREE_THRESHOLD_MULTIPLIER=1.5
```

## Running the Application

### Development Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Production Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### Get Missing Tree Locations

```
GET /api/v1/orchards/{orchard_id}/missing-trees
```

**Description**: Detects and returns the locations of missing trees in an orchard.

**Parameters**:
- `orchard_id` (path): Unique identifier for the orchard

**Response**:
```json
{
  "orchard_id": "orchard_123",
  "missing_tree_count": 3,
  "locations": [
    {"latitude": 34.0522, "longitude": -118.2437},
    {"latitude": 34.0523, "longitude": -118.2438},
    {"latitude": 34.0524, "longitude": -118.2439}
  ]
}
```

**Example**:
```bash
curl http://localhost:8000/api/v1/orchards/orchard_123/missing-trees
```

### Health Check

```
GET /health
```

Returns the health status of the API.

## Missing Tree Detection Algorithm

The algorithm follows these steps:

1. **Statistical Filtering**: Filters out unhealthy trees using 2-sigma rule:
   - Excludes trees where `canopy_area < (mean - 2 * std)`
   - Excludes trees where `ndre < (mean - 2 * std)`

2. **Coordinate Projection**: Projects lat/lon to planar coordinates (UTM) for accurate distance calculations

3. **Spatial Indexing**: Builds a KD-Tree for efficient spatial queries

4. **Spacing Estimation**: Calculates expected tree spacing using median nearest-neighbor distance

5. **Gap Detection**: Identifies tree pairs with distance > `expected_spacing * threshold_multiplier`

6. **Location Estimation**: Generates candidate locations at midpoints of gaps

7. **Validation**: Ensures candidates are:
   - Inside the orchard polygon
   - Sufficiently far from existing trees (>= 0.5 * expected_spacing)

8. **Limiting**: Returns up to `missing_tree_count` locations

## Technology Stack

- **FastAPI**: Modern web framework for building APIs
- **Pydantic**: Data validation and settings management
- **Shapely**: Geometric operations and polygon handling
- **PyProj**: Coordinate transformations and projections
- **SciPy**: KD-Tree implementation for spatial indexing
- **Tenacity**: Retry logic with exponential backoff
- **httpx**: Async HTTP client for external API calls

## Project Structure

```
app/
├── __init__.py
├── main.py                          # FastAPI application
├── config.py                        # Configuration management
├── api/
│   ├── dependencies.py              # Dependency injection
│   └── v1/
│       ├── routers/
│       │   └── orchards.py          # Orchard endpoints
│       └── models/
│           └── responses.py         # Response models
├── services/
│   ├── application/
│   │   └── orchard_service.py       # Orchestration layer
│   └── domain/
│       └── missing_tree_detector.py # Detection algorithm
├── infrastructure/
│   └── external_api_client.py       # External API integration
├── utils/
│   ├── geo_projection.py            # Coordinate transformations
│   └── spatial_helpers.py           # Spatial utilities
└── middleware/
    └── error_handler.py             # Global error handling
```

## Error Handling

The application implements comprehensive error handling:

- **Retry Logic**: Automatic retries with exponential backoff for transient failures
- **Global Middleware**: Catches unhandled exceptions and returns consistent error responses
- **Custom Exceptions**: Domain-specific exceptions for better error tracking
- **Logging**: Structured logging for debugging and monitoring

## SOLID Principles

The codebase follows SOLID principles:

- **Single Responsibility**: Each class has one reason to change
- **Open/Closed**: Open for extension, closed for modification
- **Liskov Substitution**: Subtypes are substitutable for their base types
- **Interface Segregation**: Clients depend only on methods they use
- **Dependency Inversion**: Depend on abstractions, not concretions

## Development

### Code Style

The project follows PEP 8 style guidelines. Use type hints for better code quality.

### Testing

(To be implemented)

```bash
pytest tests/
```

## License

This project is part of the Aerobotics Technical Assessment.

## Contact

For questions or support, please contact the development team.