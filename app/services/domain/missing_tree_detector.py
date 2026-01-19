"""
Domain service: Missing tree detection using spatial analysis and agronomic signals.
"""
from typing import List, Tuple, Optional
import numpy as np

from app.domain.models import TreeData, OrchardStatistics
from app.utils.geo_projection import (
    project_to_meters,
    project_to_latlon,
    project_polygon_to_meters,
)
from app.utils.spatial_helpers import (
    build_kdtree,
    estimate_tree_spacing,
    find_tree_pairs_with_gaps,
    calculate_midpoint,
    point_in_polygon,
    distance_to_nearest_tree,
)
from app.config import settings


class MissingTreeDetector:
    """
    Domain service for detecting missing trees in orchards.
    
    Uses statistical filtering and spatial analysis to identify
    locations where trees are likely missing.
    """
    
    def __init__(self, threshold_multiplier: Optional[float] = None):
        """
        Initialize the detector.
        
        Args:
            threshold_multiplier: Multiplier for expected tree spacing
                                 to detect gaps (default from settings)
        """
        self.threshold_multiplier = (
            threshold_multiplier or settings.missing_tree_threshold_multiplier
        )
    
    def detect_missing_trees(
        self,
        trees: List[TreeData],
        statistics: OrchardStatistics,
        polygon_coords: List[List[float]],
    ) -> List[Tuple[float, float]]:
        """
        Detect missing tree locations in an orchard.
        
        Args:
            trees: List of tree data from survey
            statistics: Survey statistics including mean/std and missing count
            polygon_coords: Orchard boundary as list of [lon, lat] pairs
            
        Returns:
            List of (latitude, longitude) tuples for missing tree locations
        """
        # Step 1: Filter unhealthy trees using statistical analysis
        healthy_trees = self._filter_healthy_trees(trees, statistics)
        
        if len(healthy_trees) < 3:
            # Not enough trees for spatial analysis
            return []
        
        # Step 2: Project coordinates to planar system (meters)
        # Convert TreeData to (lat, lon) tuples
        tree_coords = [(t.lat, t.lng) for t in healthy_trees]
        projected_coords, reverse_transformer = project_to_meters(tree_coords)
        
        # Project orchard polygon
        polygon_projected, _ = project_polygon_to_meters(polygon_coords)
        
        # Step 3: Build KD-Tree for spatial indexing
        kdtree = build_kdtree(projected_coords)
        
        # Step 4: Estimate expected tree spacing
        expected_spacing = estimate_tree_spacing(kdtree, projected_coords)
        threshold_distance = expected_spacing * self.threshold_multiplier
        
        # Step 5: Detect spatial gaps
        gaps = find_tree_pairs_with_gaps(
            kdtree, projected_coords, threshold_distance
        )
        
        # Step 6: Generate candidate missing tree locations
        candidates = []
        for idx1, idx2, distance in gaps:
            midpoint = calculate_midpoint(
                projected_coords[idx1],
                projected_coords[idx2]
            )
            candidates.append(midpoint)
        
        # Step 7: Validate candidates
        valid_candidates = self._validate_candidates(
            candidates,
            polygon_projected,
            kdtree,
            expected_spacing,
        )
        
        # Step 8: Limit to known missing tree count
        missing_count = statistics.missing_tree_count
        limited_candidates = valid_candidates[:missing_count]
        
        # Step 9: Convert back to lat/lon
        missing_tree_locations = project_to_latlon(
            limited_candidates,
            reverse_transformer
        )
        
        return missing_tree_locations
    
    def _filter_healthy_trees(
        self,
        trees: List[TreeData],
        statistics: OrchardStatistics,
    ) -> List[TreeData]:
        """
        Filter out unhealthy trees using survey-level statistics.
        
        Excludes trees where:
        - area < (average_area_m2 - 2 * stddev_area_m2)
        - OR ndre < (average_ndre - 2 * stddev_ndre)
        
        Args:
            trees: List of tree data
            statistics: Survey statistics
            
        Returns:
            List of healthy trees
        """
        # Calculate thresholds (2-sigma rule)
        area_threshold = statistics.average_area_m2 - (2 * statistics.stddev_area_m2)
        ndre_threshold = statistics.average_ndre - (2 * statistics.stddev_ndre)
        
        healthy_trees = []
        for tree in trees:
            # Check if tree is healthy
            is_healthy = (
                tree.area >= area_threshold and
                tree.ndre >= ndre_threshold
            )
            
            if is_healthy:
                healthy_trees.append(tree)
        
        return healthy_trees
    
    def _validate_candidates(
        self,
        candidates: List[Tuple[float, float]],
        polygon_coords: List[Tuple[float, float]],
        kdtree,
        expected_spacing: float,
    ) -> List[Tuple[float, float]]:
        """
        Validate candidate missing tree locations.
        
        Candidates must:
        - Be inside the orchard polygon
        - Be sufficiently far from existing trees (>= 0.5 * expected_spacing)
        
        Args:
            candidates: List of candidate (x, y) coordinates
            polygon_coords: Orchard boundary coordinates
            kdtree: KD-Tree of existing tree locations
            expected_spacing: Expected tree spacing in meters
            
        Returns:
            List of valid candidate coordinates
        """
        min_distance = expected_spacing * 0.5  # Minimum distance from existing trees
        valid = []
        
        for candidate in candidates:
            # Check if inside polygon
            if not point_in_polygon(candidate, polygon_coords):
                continue
            
            # Check distance to nearest existing tree
            distance = distance_to_nearest_tree(candidate, kdtree)
            if distance >= min_distance:
                valid.append(candidate)
        
        return valid
