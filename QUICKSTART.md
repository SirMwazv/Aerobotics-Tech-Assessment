# Quick Start Guide

## Local Development

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Aerobotics-Tech-Assessment
   ```

2. **Set up environment**:
   ```bash
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Configure environment variables
   cp .env.example .env
   # Edit .env with your API credentials
   ```

3. **Run the application**:
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Access the API**:
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Test: `curl http://localhost:8000/api/v1/orchards/216269/missing-trees`

## Docker Development

1. **Build and run with Docker**:
   ```bash
   docker-compose up
   ```

2. **Access the API**:
   - Same URLs as above

## Production Deployment (Render)

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Deploy to Render**:
   - Go to https://dashboard.render.com
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Set `EXTERNAL_API_KEY` in environment variables
   - Deploy!

3. **Your API will be live at**:
   ```
   https://agrotech-geospatial-api.onrender.com
   ```

## Testing the API

```bash
# Health check
curl https://your-service.onrender.com/health

# Get missing trees
curl https://your-service.onrender.com/api/v1/orchards/216269/missing-trees
```

For detailed instructions, see:
- [README.md](README.md) - Full documentation
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
