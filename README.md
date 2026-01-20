# Mwazvita Mutowo - Aerobotics Tech Assessment

A FastAPI application for detecting missing trees in orchards using geospatial analysis.

**Live Demo:** https://mwazvita-mutowo-aerobotics-tech.onrender.com

**Swagger Documentation:** https://mwazvita-mutowo-aerobotics-tech.onrender.com/docs

---

## Quick Start

### Option 1: Run with Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/SirMwazv/Aerobotics-Tech-Assessment.git
cd Aerobotics-Tech-Assessment

# Create environment file
cp .env.example .env

# Build and run with Docker Compose
docker-compose up --build
```

The API will be available at `http://localhost:8000`

### Option 2: Run Locally

```bash
# Clone the repository
git clone https://github.com/SirMwazv/Aerobotics-Tech-Assessment.git
cd Aerobotics-Tech-Assessment

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Run the application
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

---

## API Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Endpoint

```
GET /api/v1/orchards/{orchard_id}/missing-trees
```

**Example Request:**
```bash
curl http://localhost:8000/api/v1/orchards/216269/missing-trees
```

**Example Response:**
```json
{
  "orchard_id": "216269",
  "locations": [
    {"latitude": -32.328023, "longitude": 18.826754},
    {"latitude": -32.327970, "longitude": 18.826769},
    {"latitude": -32.328037, "longitude": 18.826818}
  ]
}
```

---

## How the Algorithm Works

The missing tree detection works in simple steps:

### 1. Get the Data
We fetch tree survey data from Aerobotics API, which includes each tree's GPS location, size (canopy area), and health indicator (NDRE).

### 2. Remove Unhealthy Trees
Before analyzing patterns, we filter out sick or dying trees that might skew our results. We use a simple rule: if a tree's size or health is significantly below average (more than 2 standard deviations), we exclude it from the pattern analysis.

**Why?** Dead or dying trees have abnormal sizes that would confuse our spacing calculations.

### 3. Convert Coordinates
GPS coordinates (latitude/longitude) are in degrees, which aren't useful for measuring distances. We convert them to meters using a standard map projection (UTM).

**Why?** Now we can actually measure "this tree is 10 meters from that tree."

### 4. Build a Search Index
We organize all tree locations into a special data structure called a KD-Tree that makes finding nearby trees very fast.

**Why?** With 10,000 trees, checking every pair would be slow. The KD-Tree makes searches almost instant.

### 5. Figure Out Normal Spacing
We look at how far each tree is from its nearest neighbor and find the typical (median) distance. This tells us the expected spacing in the orchard.

**Example:** If most trees are about 10 meters apart, expected spacing = 10m.

### 6. Find the Gaps
We look for pairs of trees that are unusually far apart. If two trees are 25 meters apart when they should be 10 meters apart, there's probably one or more trees missing between them.

**For large gaps:** If a gap is big enough for multiple trees, we calculate how many could fit and mark each potential location.

### 7. Score and Rank Candidates
Not all gaps are equally likely to be missing trees. We score each candidate location based on:
- How well it fits the expected spacing pattern
- Whether it has neighbors (but isn't crowded)
- How far it is from the orchard edge
- Whether it aligns with the orchard's row pattern

### 8. Validate and Return
Finally, we check that each candidate is actually inside the orchard boundary, then return the best locations as GPS coordinates.

### Important Considerations

- **Edge cases:** Trees near orchard boundaries might appear as gaps but aren't actually missing
- **Planting patterns:** Most orchards have regular rows, which the algorithm tries to detect and use
- **Accuracy vs. completeness:** We prioritize accuracy (fewer false positives) over finding every possible gap
- **Data quality:** Results are only as good as the input data from surveys

---

## Project Structure

```
app/
├── api/                    # HTTP endpoints
│   └── v1/routers/         # API routes (controllers)
├── domain/                 # Core data models
├── services/
│   ├── application/        # Orchestration layer
│   └── domain/             # Business logic & algorithm
├── infrastructure/         # External API client
├── utils/                  # Helper functions
├── middleware/             # Error handling
├── config.py               # Configuration
└── main.py                 # Application entry point
```

---

## Configuration

All settings can be configured via environment variables in `.env`:

```env
# API Settings
EXTERNAL_API_BASE_URL=https://api.aerobotics.com
EXTERNAL_API_KEY=your_api_key

# Detection Parameters (optional - defaults shown)
MISSING_TREE_THRESHOLD_MULTIPLIER=1.5    # How big a gap triggers detection
MISSING_TREE_SIGMA_MULTIPLIER=2.0        # Sensitivity for filtering unhealthy trees
MISSING_TREE_USE_ROW_DETECTION=True      # Try to detect row patterns
```

---

## Running Tests

```bash
# Activate virtual environment if not already active
source venv/bin/activate

# Run all tests
pytest tests/ -v
```

---

## Technology Stack

| Technology | Purpose |
|------------|---------|
| FastAPI | Web framework |
| Pydantic | Data validation |
| SciPy | Spatial indexing (KD-Tree) |
| PyProj | Coordinate transformations |
| Shapely | Geometric operations |
| Docker | Containerization |

---

## Architecture

The application follows clean architecture principles:

- **API Layer:** Handles HTTP requests, no business logic
- **Service Layer:** Orchestrates workflows and coordinates components
- **Domain Layer:** Contains the core detection algorithm
- **Infrastructure Layer:** Manages external API communication

This separation makes the code easier to test, maintain, and extend.

---

## Contact

Mwazvita Mutowo