"""
Spatial analysis helper functions.

Provides utilities for:
- KD-Tree spatial indexing
- Gap detection and interpolation
- Row/column pattern detection
- Polygon operations
"""
from typing import Optional
import numpy as np
from scipy.spatial import KDTree
from shapely.geometry import Point, Polygon
import logging

logger = logging.getLogger(__name__)


def build_kdtree(coordinates: list[tuple[float, float]]) -> KDTree:
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
    coordinates: list[tuple[float, float]]
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
    coordinates: list[tuple[float, float]]
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
    spacing = float(np.median(distances))
    logger.debug(f"Estimated tree spacing: {spacing:.2f}m (median of {len(distances)} distances)")
    return spacing


def point_in_polygon(
    point: tuple[float, float],
    polygon_coords: list[tuple[float, float]]
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


def point_in_polygon_with_buffer(
    point: tuple[float, float],
    polygon_coords: list[tuple[float, float]],
    buffer_distance: float = 0.0
) -> bool:
    """
    Check if a point is inside a polygon with optional inward buffer.
    
    Args:
        point: (x, y) coordinate tuple
        polygon_coords: List of (x, y) coordinates defining the polygon
        buffer_distance: Inward buffer distance in meters (negative buffer)
        
    Returns:
        True if point is inside buffered polygon, False otherwise
    """
    point_geom = Point(point)
    polygon_geom = Polygon(polygon_coords)
    
    if buffer_distance > 0:
        # Negative buffer shrinks the polygon inward
        buffered_polygon = polygon_geom.buffer(-buffer_distance)
        if buffered_polygon.is_empty:
            return False
        return buffered_polygon.contains(point_geom)
    
    return polygon_geom.contains(point_geom)


def distance_to_nearest_tree(
    point: tuple[float, float],
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


def find_tree_pairs_with_gaps_optimized(
    coordinates: list[tuple[float, float]],
    threshold_distance: float,
    max_search_radius: Optional[float] = None
) -> list[tuple[int, int, float]]:
    """
    Find pairs of trees with gaps larger than the threshold.
    
    Optimized version using scipy's query_pairs for better performance
    on large datasets.
    
    Args:
        coordinates: List of (x, y) coordinate tuples
        threshold_distance: Minimum distance to consider as a gap
        max_search_radius: Maximum distance to search (default: 3x threshold)
        
    Returns:
        List of (index1, index2, distance) tuples for tree pairs with gaps
    """
    points = np.array(coordinates)
    kdtree = KDTree(points)
    
    # Use query_pairs for O(n log n) performance
    search_radius = max_search_radius or (threshold_distance * 3)
    
    # Get all pairs within search radius
    pairs = kdtree.query_pairs(r=search_radius, output_type='ndarray')
    
    if len(pairs) == 0:
        return []
    
    # Calculate distances for all pairs at once (vectorized)
    distances = np.linalg.norm(points[pairs[:, 0]] - points[pairs[:, 1]], axis=1)
    
    # Filter to gaps only
    gap_mask = distances > threshold_distance
    gap_pairs = pairs[gap_mask]
    gap_distances = distances[gap_mask]
    
    # Convert to list of tuples
    gaps = [
        (int(gap_pairs[i, 0]), int(gap_pairs[i, 1]), float(gap_distances[i]))
        for i in range(len(gap_pairs))
    ]
    
    logger.debug(f"Found {len(gaps)} gaps from {len(pairs)} pairs (threshold: {threshold_distance:.2f}m)")
    return gaps


def find_tree_pairs_with_gaps(
    kdtree: KDTree,
    coordinates: list[tuple[float, float]],
    threshold_distance: float
) -> list[tuple[int, int, float]]:
    """
    Find pairs of trees with gaps larger than the threshold.
    
    Legacy interface - calls optimized version internally.
    
    Args:
        kdtree: KDTree built from coordinates (unused, kept for compatibility)
        coordinates: List of (x, y) coordinate tuples
        threshold_distance: Minimum distance to consider as a gap
        
    Returns:
        List of (index1, index2, distance) tuples for tree pairs with gaps
    """
    return find_tree_pairs_with_gaps_optimized(coordinates, threshold_distance)


def calculate_midpoint(
    point1: tuple[float, float],
    point2: tuple[float, float]
) -> tuple[float, float]:
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


def interpolate_points_in_gap(
    point1: tuple[float, float],
    point2: tuple[float, float],
    expected_spacing: float,
    gap_distance: float
) -> list[tuple[float, float]]:
    """
    Generate evenly-spaced interpolated points within a gap.
    
    If the gap is large enough for multiple trees, generates
    multiple interpolated points.
    
    Args:
        point1: First endpoint (x, y)
        point2: Second endpoint (x, y)
        expected_spacing: Expected distance between trees
        gap_distance: Actual distance between the two points
        
    Returns:
        List of interpolated (x, y) coordinates for missing trees
    """
    # Calculate how many trees could fit in the gap
    # Gap of 2x spacing = 1 missing tree
    # Gap of 3x spacing = 2 missing trees, etc.
    num_missing = max(1, int(round(gap_distance / expected_spacing)) - 1)
    
    if num_missing == 0:
        return []
    
    interpolated = []
    p1 = np.array(point1)
    p2 = np.array(point2)
    
    for i in range(1, num_missing + 1):
        # Evenly distribute points along the line
        fraction = i / (num_missing + 1)
        point = p1 + fraction * (p2 - p1)
        interpolated.append((float(point[0]), float(point[1])))
    
    logger.debug(f"Gap of {gap_distance:.2f}m → {num_missing} interpolated points")
    return interpolated


def detect_row_orientation(
    coordinates: list[tuple[float, float]],
    num_samples: int = 100
) -> tuple[float, float]:
    """
    Detect the primary row orientation of an orchard using nearest-neighbor analysis.
    
    Args:
        coordinates: List of (x, y) coordinate tuples
        num_samples: Number of trees to sample for analysis
        
    Returns:
        Tuple of (row_angle_radians, confidence_score)
        - row_angle_radians: Angle of primary row direction (0 to π)
        - confidence_score: 0 to 1, how confident we are in the detection
    """
    points = np.array(coordinates)
    n = len(points)
    
    if n < 10:
        logger.warning("Too few trees for row detection, using default")
        return (0.0, 0.0)
    
    # Sample trees if there are many
    sample_size = min(num_samples, n)
    sample_indices = np.random.choice(n, sample_size, replace=False)
    
    kdtree = KDTree(points)
    
    # Collect angles to nearest neighbors
    angles = []
    for idx in sample_indices:
        # Get 4 nearest neighbors (excluding self)
        distances, neighbors = kdtree.query(points[idx], k=5)
        
        for i in range(1, len(neighbors)):  # Skip self (index 0)
            neighbor_idx = neighbors[i]
            dx = points[neighbor_idx, 0] - points[idx, 0]
            dy = points[neighbor_idx, 1] - points[idx, 1]
            angle = np.arctan2(dy, dx)
            
            # Normalize to [0, π) since direction doesn't matter
            if angle < 0:
                angle += np.pi
            if angle >= np.pi:
                angle -= np.pi
            angles.append(angle)
    
    angles = np.array(angles)
    
    # Use histogram to find dominant angle
    hist, bin_edges = np.histogram(angles, bins=36, range=(0, np.pi))
    
    # Find peak
    peak_idx = np.argmax(hist)
    primary_angle = (bin_edges[peak_idx] + bin_edges[peak_idx + 1]) / 2
    
    # Confidence based on how peaked the histogram is
    confidence = hist[peak_idx] / np.sum(hist) * 2  # Scale to [0, 1]
    confidence = min(1.0, confidence)
    
    logger.info(f"Detected row orientation: {np.degrees(primary_angle):.1f}° (confidence: {confidence:.2f})")
    return (float(primary_angle), float(confidence))


def estimate_row_and_column_spacing(
    coordinates: list[tuple[float, float]],
    row_angle: float
) -> tuple[float, float]:
    """
    Estimate spacing in row and cross-row (column) directions.
    
    Args:
        coordinates: List of (x, y) coordinate tuples
        row_angle: Row orientation angle in radians
        
    Returns:
        Tuple of (row_spacing, column_spacing) in meters
    """
    points = np.array(coordinates)
    n = len(points)
    
    if n < 10:
        # Fall back to simple median spacing
        kdtree = KDTree(points)
        distances, _ = kdtree.query(points, k=2)
        spacing = float(np.median(distances[:, 1]))
        return (spacing, spacing)
    
    kdtree = KDTree(points)
    
    # Rotation matrix to align with row direction
    cos_a, sin_a = np.cos(row_angle), np.sin(row_angle)
    rotation = np.array([[cos_a, sin_a], [-sin_a, cos_a]])
    
    # Rotate all points
    rotated = points @ rotation.T
    
    # For each point, find nearest neighbor distances in row and column directions
    row_distances = []
    col_distances = []
    
    sample_size = min(100, n)
    sample_indices = np.random.choice(n, sample_size, replace=False)
    
    for idx in sample_indices:
        distances, neighbors = kdtree.query(points[idx], k=9)
        
        for i in range(1, len(neighbors)):
            neighbor_idx = neighbors[i]
            
            # Get distance in rotated coordinates
            dx = rotated[neighbor_idx, 0] - rotated[idx, 0]
            dy = rotated[neighbor_idx, 1] - rotated[idx, 1]
            
            # If mostly in x direction, it's row spacing
            # If mostly in y direction, it's column spacing
            if abs(dx) > abs(dy) * 2:
                row_distances.append(abs(dx))
            elif abs(dy) > abs(dx) * 2:
                col_distances.append(abs(dy))
    
    row_spacing = float(np.median(row_distances)) if row_distances else estimate_tree_spacing(kdtree, coordinates)
    col_spacing = float(np.median(col_distances)) if col_distances else row_spacing
    
    logger.info(f"Estimated spacing - row: {row_spacing:.2f}m, column: {col_spacing:.2f}m")
    return (row_spacing, col_spacing)


def calculate_local_density(
    point: tuple[float, float],
    kdtree: KDTree,
    radius: float
) -> float:
    """
    Calculate local tree density around a point.
    
    Args:
        point: (x, y) coordinate tuple
        kdtree: KDTree of tree coordinates
        radius: Radius to search within
        
    Returns:
        Density score (trees per unit area)
    """
    neighbors = kdtree.query_ball_point(point, radius)
    area = np.pi * radius ** 2
    return len(neighbors) / area


def score_candidate_location(
    candidate: tuple[float, float],
    kdtree: KDTree,
    expected_spacing: float,
    polygon_coords: list[tuple[float, float]],
    row_spacing: Optional[float] = None,
    col_spacing: Optional[float] = None,
    row_angle: Optional[float] = None
) -> float:
    """
    Score a candidate missing tree location.
    
    Higher score = more likely to be a real missing tree.
    
    Args:
        candidate: (x, y) candidate location
        kdtree: KDTree of existing trees
        expected_spacing: Expected tree spacing
        polygon_coords: Orchard boundary
        row_spacing: Optional row spacing (if row pattern detected)
        col_spacing: Optional column spacing
        row_angle: Optional row angle
        
    Returns:
        Score from 0 to 1
    """
    score = 0.0
    
    # 1. Distance to nearest tree (30% weight)
    # Ideal: close to expected_spacing
    nearest_dist = distance_to_nearest_tree(candidate, kdtree)
    if nearest_dist > 0:
        dist_ratio = min(nearest_dist / expected_spacing, expected_spacing / nearest_dist)
        score += 0.3 * dist_ratio
    
    # 2. Local density consistency (30% weight)
    # Check if adding a tree here would create consistent spacing
    neighbors = kdtree.query_ball_point(candidate, expected_spacing * 2)
    if len(neighbors) >= 2:
        # Good - has neighbors but not too crowded
        score += 0.3 * min(1.0, len(neighbors) / 4)
    
    # 3. Distance from polygon boundary (20% weight)
    # Trees too close to boundary are suspicious
    polygon = Polygon(polygon_coords)
    point = Point(candidate)
    boundary_dist = polygon.exterior.distance(point)
    if boundary_dist > expected_spacing * 0.3:
        score += 0.2
    elif boundary_dist > 0:
        score += 0.2 * (boundary_dist / (expected_spacing * 0.3))
    
    # 4. Row pattern alignment (20% weight)
    if row_angle is not None and row_spacing is not None:
        # Check if candidate aligns with row pattern
        # Find nearest tree and check alignment
        _, nearest_idx = kdtree.query(candidate)
        if nearest_idx is not None:
            nearest_point = kdtree.data[nearest_idx]
            dx = candidate[0] - nearest_point[0]
            dy = candidate[1] - nearest_point[1]
            angle_to_nearest = np.arctan2(dy, dx)
            
            # Normalize angle
            if angle_to_nearest < 0:
                angle_to_nearest += np.pi
            if angle_to_nearest >= np.pi:
                angle_to_nearest -= np.pi
            
            # Check alignment with row or perpendicular (column)
            row_diff = abs(angle_to_nearest - row_angle)
            col_diff = abs(angle_to_nearest - (row_angle + np.pi/2) % np.pi)
            
            alignment = min(row_diff, col_diff)
            alignment_score = max(0, 1 - alignment / (np.pi / 4))
            score += 0.2 * alignment_score
    else:
        score += 0.1  # Partial score if no row info
    
    return min(1.0, score)
