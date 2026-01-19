# Deployment Guide

This guide covers deploying the Agrotech Geospatial Analytics API to Render using Docker.

## Prerequisites

- Git repository with your code
- Render account (https://render.com)
- Aerobotics API credentials

## Deployment Options

### Option 1: Automated Deployment with render.yaml (Recommended)

The repository includes a `render.yaml` blueprint for automated deployment.

#### Steps:

1. **Push your code to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: FastAPI geospatial analytics API"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Connect to Render**:
   - Go to https://dashboard.render.com
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect `render.yaml`

3. **Configure Environment Variables**:
   - In the Render dashboard, go to your service
   - Navigate to "Environment" tab
   - Add the secret variable:
     - `EXTERNAL_API_KEY`: Your Aerobotics API key
   - All other variables are pre-configured in `render.yaml`

4. **Deploy**:
   - Render will automatically build and deploy your Docker container
   - Monitor the deployment logs in the dashboard
   - Once deployed, your API will be available at: `https://mwazvita-mutowo-aerobotics-tech.onrender.com`

### Option 2: Manual Deployment

1. **Create a New Web Service**:
   - Go to https://dashboard.render.com
   - Click "New" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**:
   - **Name**: `agrotech-geospatial-api`
   - **Environment**: Docker
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Dockerfile Path**: `./Dockerfile` (default)

3. **Set Environment Variables**:
   ```
   EXTERNAL_API_BASE_URL=https://api.aerobotics.com
   EXTERNAL_API_KEY=<your-api-key>
   MAX_RETRY_ATTEMPTS=3
   RETRY_BACKOFF_MULTIPLIER=1
   RETRY_MIN_WAIT=4
   RETRY_MAX_WAIT=10
   MISSING_TREE_THRESHOLD_MULTIPLIER=1.5
   APP_NAME=Agrotech Geospatial Analytics API
   APP_VERSION=1.0.0
   DEBUG=False
   ```

4. **Configure Health Check**:
   - **Health Check Path**: `/health`

5. **Deploy**:
   - Click "Create Web Service"
   - Render will build and deploy your container

## Local Docker Testing

Before deploying to Render, test locally with Docker:

### Build the Docker Image

```bash
docker build -t agrotech-geospatial-api .
```

### Run with Docker

```bash
docker run -p 8000:8000 \
  -e EXTERNAL_API_BASE_URL=https://api.aerobotics.com \
  -e EXTERNAL_API_KEY=your_api_key_here \
  agrotech-geospatial-api
```

### Run with Docker Compose

```bash
# Make sure .env file exists with your credentials
docker-compose up
```

Access the API at: http://localhost:8000

## Dockerfile Explanation

The Dockerfile includes:

1. **Base Image**: Python 3.13 slim for smaller image size
2. **System Dependencies**: 
   - `libproj-dev`: PROJ library for coordinate transformations
   - `proj-data`: Projection data files
   - `libgeos-dev`: GEOS library for geometric operations
3. **Security**: Non-root user for running the application
4. **Health Check**: Automated health monitoring
5. **Optimization**: Multi-stage caching for faster builds

## Render-Specific Configuration

### render.yaml

The blueprint configures:
- **Service Type**: Web service with Docker
- **Plan**: Starter (can be upgraded)
- **Region**: Oregon (can be changed)
- **Health Check**: Automatic monitoring at `/health`
- **Environment Variables**: Pre-configured with defaults

### Auto-Deploy

Render automatically deploys when you push to the `main` branch.

## Monitoring and Logs

### View Logs

In Render dashboard:
1. Go to your service
2. Click "Logs" tab
3. View real-time application logs

### Health Checks

Render automatically monitors the `/health` endpoint:
- **Interval**: Every 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3 attempts before marking unhealthy

### Metrics

Monitor in Render dashboard:
- CPU usage
- Memory usage
- Request count
- Response times

## Scaling

### Vertical Scaling

Upgrade your Render plan:
- **Starter**: 512 MB RAM, 0.5 CPU
- **Standard**: 2 GB RAM, 1 CPU
- **Pro**: 4 GB RAM, 2 CPU

### Horizontal Scaling

Render Pro plans support:
- Multiple instances
- Auto-scaling based on load
- Load balancing

## Troubleshooting

### Build Failures

**Issue**: Docker build fails with dependency errors

**Solution**: 
- Check that all system dependencies are in Dockerfile
- Verify requirements.txt is up to date
- Review build logs in Render dashboard

### Health Check Failures

**Issue**: Service marked as unhealthy

**Solution**:
- Check `/health` endpoint is accessible
- Verify application is listening on port 8000
- Review application logs for errors

### API Errors

**Issue**: External API calls failing

**Solution**:
- Verify `EXTERNAL_API_KEY` is set correctly
- Check API rate limits
- Review retry configuration

### Memory Issues

**Issue**: Container running out of memory

**Solution**:
- Upgrade to a larger Render plan
- Optimize spatial analysis for large datasets
- Implement pagination for tree data

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EXTERNAL_API_BASE_URL` | Yes | - | Aerobotics API base URL |
| `EXTERNAL_API_KEY` | Yes | - | API authentication key |
| `MAX_RETRY_ATTEMPTS` | No | 3 | Maximum retry attempts for API calls |
| `RETRY_BACKOFF_MULTIPLIER` | No | 1 | Exponential backoff multiplier |
| `RETRY_MIN_WAIT` | No | 4 | Minimum wait time between retries (seconds) |
| `RETRY_MAX_WAIT` | No | 10 | Maximum wait time between retries (seconds) |
| `MISSING_TREE_THRESHOLD_MULTIPLIER` | No | 1.5 | Gap detection threshold multiplier |
| `APP_NAME` | No | Agrotech Geospatial Analytics API | Application name |
| `APP_VERSION` | No | 1.0.0 | Application version |
| `DEBUG` | No | False | Debug mode |

## API Endpoints

Once deployed, your API will be available at:

- **Base URL**: `https://mwazvita-mutowo-aerobotics-tech.onrender.com`
- **Health Check**: `GET /health`
- **API Docs**: `GET /docs`
- **Missing Trees**: `GET /api/v1/orchards/{orchard_id}/missing-trees`

## Security Best Practices

1. **Never commit `.env` file** - It's in `.gitignore`
2. **Use Render's secret management** - For `EXTERNAL_API_KEY`
3. **Enable HTTPS** - Render provides free SSL certificates
4. **Monitor access logs** - Review for suspicious activity
5. **Keep dependencies updated** - Regularly update `requirements.txt`

## Cost Optimization

### Free Tier

Render offers a free tier with limitations:
- Service spins down after 15 minutes of inactivity
- 750 hours/month free
- Slower cold starts

### Paid Plans

For production use:
- **Starter**: $7/month - Always on, faster performance
- **Standard**: $25/month - More resources, better for production
- **Pro**: Custom pricing - Auto-scaling, dedicated support

## Continuous Deployment

Render automatically deploys when you push to GitHub:

1. Make changes to your code
2. Commit and push to `main` branch
3. Render detects changes and triggers build
4. New version deployed automatically
5. Health checks verify deployment success

## Support

For issues:
- **Render Support**: https://render.com/docs
- **Application Logs**: Check Render dashboard
- **GitHub Issues**: Create issues in your repository
