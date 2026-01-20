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

The missing tree detection works in 11 steps:

### Step 1: Filter Unhealthy Trees
Before analyzing patterns, we filter out sick or dying trees that might skew our results. We use the 2-sigma rule: if a tree's size or health is significantly below average (more than 2 standard deviations), we exclude it from pattern analysis.

**Why?** Dead or dying trees have abnormal sizes that would confuse our spacing calculations.

### Step 2: Project Coordinates to Meters
GPS coordinates (latitude/longitude) are in degrees, which aren't useful for measuring distances. We convert them to meters using a standard map projection (UTM).

**Why?** Now we can actually measure "this tree is 10 meters from that tree."

### Step 3: Build KD-Tree for Spatial Indexing
We organize all tree locations into a special data structure called a KD-Tree that makes finding nearby trees very fast.

**Why?** With 10,000 trees, checking every pair would be slow. The KD-Tree makes searches almost instant.

### Step 4: Estimate Expected Tree Spacing
We look at how far each tree is from its nearest neighbor and find the typical (median) distance. This tells us the expected spacing in the orchard.

**Example:** If most trees are about 10 meters apart, expected spacing = 10m.

### Step 5: Detect Row Orientation (Optional)
We analyze the angles between neighboring trees to detect if the orchard has a regular row pattern. If confident enough, we estimate separate row and column spacing.

**Why?** Orchards with regular rows have predictable patterns we can use.

### Step 6: Detect Spatial Gaps
We look for pairs of trees that are unusually far apart (more than 1.5× the expected spacing).

**For large gaps:** If a gap is big enough for multiple trees, we calculate how many could fit.

### Step 7: Generate Candidate Locations
For each detected gap, we interpolate where missing trees should be. Large gaps get multiple evenly-spaced candidate points.

### Step 8: Score and Rank Candidates
Not all gaps are equally likely to be missing trees. We score each candidate based on:
- How well it fits the expected spacing pattern (30%)
- Local density - has neighbors but isn't crowded (30%)
- Distance from orchard boundary (20%)
- Alignment with detected row pattern (20%)

### Step 9: Validate Candidates
We filter out candidates that:
- Score below the minimum threshold
- Are outside the orchard polygon (with buffer)
- Are too close to existing trees

### Step 10: Sort and Limit Results
We sort candidates by score and return only the top N, where N is the known missing tree count from the survey.

### Step 11: Convert Back to GPS
Finally, we convert the validated candidate locations back from meters to latitude/longitude coordinates.

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