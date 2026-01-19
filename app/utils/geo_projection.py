"""
Geospatial projection utilities for coordinate transformations.
"""
from typing import Tuple, List
import pyproj
from pyproj import Transformer


def get_utm_zone(longitude: float) -> int:
    """
    Calculate the UTM zone number from longitude.
    
    Args:
        longitude: Longitude in degrees
        
    Returns:
        UTM zone number (1-60)
    """
    return int((longitude + 180) / 6) + 1


def get_utm_crs(longitude: float, latitude: float) -> str:
    """
    Get the appropriate UTM CRS (Coordinate Reference System) for a location.
    
    Args:
        longitude: Longitude in degrees
        latitude: Latitude in degrees
        
    Returns:
        EPSG code for the UTM zone
    """
    zone = get_utm_zone(longitude)
    # Northern hemisphere: EPSG:326XX, Southern hemisphere: EPSG:327XX
    hemisphere = "6" if latitude >= 0 else "7"
    return f"EPSG:32{hemisphere}{zone:02d}"


def project_to_meters(
    coordinates: List[Tuple[float, float]]
) -> Tuple[List[Tuple[float, float]], Transformer]:
    """
    Project lat/lon coordinates to a planar coordinate system (UTM) in meters.
    
    Args:
        coordinates: List of (latitude, longitude) tuples in degrees
        
    Returns:
        Tuple of:
            - List of (x, y) coordinates in meters
            - Transformer object for reverse transformation
    """
    if not coordinates:
        raise ValueError("Coordinates list cannot be empty")
    
    # Use the first coordinate to determine the UTM zone
    lat, lon = coordinates[0]
    utm_crs = get_utm_crs(lon, lat)
    
    # Create transformer from WGS84 (EPSG:4326) to UTM
    transformer = Transformer.from_crs(
        "EPSG:4326",  # WGS84 (lat/lon)
        utm_crs,      # UTM zone
        always_xy=True  # Ensure (lon, lat) -> (x, y) order
    )
    
    # Transform all coordinates
    projected = []
    for lat, lon in coordinates:
        x, y = transformer.transform(lon, lat)
        projected.append((x, y))
    
    # Create reverse transformer for later use
    reverse_transformer = Transformer.from_crs(
        utm_crs,
        "EPSG:4326",
        always_xy=True
    )
    
    return projected, reverse_transformer


def project_to_latlon(
    coordinates: List[Tuple[float, float]],
    transformer: Transformer
) -> List[Tuple[float, float]]:
    """
    Project planar coordinates (meters) back to lat/lon.
    
    Args:
        coordinates: List of (x, y) coordinates in meters
        transformer: Transformer object from project_to_meters
        
    Returns:
        List of (latitude, longitude) tuples in degrees
    """
    latlon = []
    for x, y in coordinates:
        lon, lat = transformer.transform(x, y)
        latlon.append((lat, lon))
    
    return latlon


def project_polygon_to_meters(
    polygon_coords: List[List[float]]
) -> Tuple[List[Tuple[float, float]], Transformer]:
    """
    Project polygon coordinates from [lon, lat] format to meters.
    
    Args:
        polygon_coords: List of [longitude, latitude] pairs
        
    Returns:
        Tuple of:
            - List of (x, y) coordinates in meters
            - Transformer object for reverse transformation
    """
    # Convert [lon, lat] to (lat, lon) tuples
    lat_lon_coords = [(coord[1], coord[0]) for coord in polygon_coords]
    return project_to_meters(lat_lon_coords)
