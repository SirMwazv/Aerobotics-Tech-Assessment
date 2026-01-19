"""
Spatial analysis helper functions.
"""
from typing import List, Tuple
import numpy as np
from scipy.spatial import KDTree
from shapely.geometry import Point, Polygon


def build_kdtree(coordinates: List[Tuple[float, float]]) -> KDTree:
    """
    Build a KD-Tree for efficient spatial queries.
    
    Args:
        coordinates: List of (x, y) coordinate tuples
        
    Returns:
        KDTree instance
    """
    points = np.array(coordinates)
    return KDTree(points)


def calculate_nearest_neighbor_distances(
    kdtree: KDTree,
    coordinates: List[Tuple[float, float]]
) -> np.ndarray:
    """
    Calculate the distance to the nearest neighbor for each point.
    
    Args:
        kdtree: KDTree built from coordinates
        coordinates: List of (x, y) coordinate tuples
        
    Returns:
        Array of distances to nearest neighbors
    """
    points = np.array(coordinates)
    # Query for 2 nearest neighbors (first is the point itself, second is nearest)
    distances, _ = kdtree.query(points, k=2)
    # Return distances to the second nearest (index 1)
    return distances[:, 1]


def estimate_tree_spacing(
    kdtree: KDTree,
    coordinates: List[Tuple[float, float]]
) -> float:
    """
    Estimate expected tree spacing using median nearest-neighbor distance.
    
    Args:
        kdtree: KDTree built from coordinates
        coordinates: List of (x, y) coordinate tuples
        
    Returns:
        Estimated tree spacing in meters
    """
    distances = calculate_nearest_neighbor_distances(kdtree, coordinates)
    return float(np.median(distances))


def point_in_polygon(
    point: Tuple[float, float],
    polygon_coords: List[Tuple[float, float]]
) -> bool:
    """
    Check if a point is inside a polygon.
    
    Args:
        point: (x, y) coordinate tuple
        polygon_coords: List of (x, y) coordinates defining the polygon
        
    Returns:
        True if point is inside polygon, False otherwise
    """
    point_geom = Point(point)
    polygon_geom = Polygon(polygon_coords)
    return polygon_geom.contains(point_geom)


def distance_to_nearest_tree(
    point: Tuple[float, float],
    kdtree: KDTree
) -> float:
    """
    Calculate the distance from a point to the nearest tree.
    
    Args:
        point: (x, y) coordinate tuple
        kdtree: KDTree built from tree coordinates
        
    Returns:
        Distance to nearest tree in meters
    """
    distance, _ = kdtree.query(point)
    return float(distance)


def find_tree_pairs_with_gaps(
    kdtree: KDTree,
    coordinates: List[Tuple[float, float]],
    threshold_distance: float
) -> List[Tuple[int, int, float]]:
    """
    Find pairs of trees with gaps larger than the threshold.
    
    Args:
        kdtree: KDTree built from coordinates
        coordinates: List of (x, y) coordinate tuples
        threshold_distance: Minimum distance to consider as a gap
        
    Returns:
        List of (index1, index2, distance) tuples for tree pairs with gaps
    """
    points = np.array(coordinates)
    gaps = []
    
    # Query for neighbors within a reasonable search radius
    # Use 3x threshold to catch potential gaps
    search_radius = threshold_distance * 3
    
    for i, point in enumerate(points):
        # Find all neighbors within search radius
        indices = kdtree.query_ball_point(point, search_radius)
        
        for j in indices:
            # Avoid duplicates (only consider i < j) and self-pairs
            if i < j:
                distance = np.linalg.norm(points[i] - points[j])
                if distance > threshold_distance:
                    gaps.append((i, j, float(distance)))
    
    return gaps


def calculate_midpoint(
    point1: Tuple[float, float],
    point2: Tuple[float, float]
) -> Tuple[float, float]:
    """
    Calculate the midpoint between two points.
    
    Args:
        point1: First (x, y) coordinate tuple
        point2: Second (x, y) coordinate tuple
        
    Returns:
        Midpoint (x, y) coordinate tuple
    """
    x = (point1[0] + point2[0]) / 2
    y = (point1[1] + point2[1]) / 2
    return (x, y)
