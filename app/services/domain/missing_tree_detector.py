"""
Domain service: Missing tree detection using spatial analysis and agronomic signals.

This module provides a comprehensive algorithm for detecting missing trees
in orchards using:
- Statistical filtering (2-sigma rule)
- KD-Tree spatial indexing
- Multi-tree gap interpolation
- Row/column pattern detection
- Candidate scoring and ranking
"""
from typing import Optional
from dataclasses import dataclass
import numpy as np
import logging
from scipy.spatial import KDTree

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
    interpolate_points_in_gap,
    point_in_polygon_with_buffer,
    distance_to_nearest_tree,
    detect_row_orientation,
    estimate_row_and_column_spacing,
    score_candidate_location,
)
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DetectionConfig:
    """Configuration for missing tree detection algorithm."""
    
    # Gap detection
    threshold_multiplier: float = 1.5
    """Multiplier for expected spacing to detect gaps (e.g., 1.5 = 150% of spacing)"""
    
    # Statistical filtering
    sigma_multiplier: float = 2.0
    """Number of standard deviations for unhealthy tree filtering"""
    
    # Validation
    min_distance_ratio: float = 0.5
    """Minimum distance from existing trees as ratio of expected spacing"""
    
    boundary_buffer_ratio: float = 0.3
    """Buffer from polygon boundary as ratio of expected spacing"""
    
    # Row pattern detection
    use_row_detection: bool = True
    """Whether to attempt row/column pattern detection"""
    
    row_confidence_threshold: float = 0.3
    """Minimum confidence to use detected row orientation"""
    
    # Scoring
    min_candidate_score: float = 0.3
    """Minimum score for a candidate to be considered valid"""


@dataclass
class ScoredCandidate:
    """A candidate missing tree location with its score."""
    x: float
    y: float
    score: float
    
    @property
    def coordinates(self) -> tuple[float, float]:
        return (self.x, self.y)


class MissingTreeDetector:
    """
    Domain service for detecting missing trees in orchards.
    
    Uses statistical filtering and spatial analysis to identify
    locations where trees are likely missing.
    
    Features:
    - Multi-tree gap handling (gaps with 2+ missing trees)
    - Row/column pattern detection for regular orchards
    - Candidate scoring and ranking
    - Configurable parameters
    - Comprehensive logging
    """
    
    def __init__(
        self,
        config: Optional[DetectionConfig] = None,
        threshold_multiplier: Optional[float] = None,
    ):
        """
        Initialize the detector.
        
        Args:
            config: Full configuration object (preferred)
            threshold_multiplier: Legacy param for backward compatibility
        """
        if config:
            self.config = config
        else:
            self.config = DetectionConfig(
                threshold_multiplier=threshold_multiplier or settings.missing_tree_threshold_multiplier
            )
        
        logger.info(f"Initialized MissingTreeDetector with config: "
                   f"threshold={self.config.threshold_multiplier}, "
                   f"sigma={self.config.sigma_multiplier}")
    
    # Backward compatibility
    @property
    def threshold_multiplier(self) -> float:
        return self.config.threshold_multiplier
    
    def detect_missing_trees(
        self,
        trees: list[TreeData],
        statistics: OrchardStatistics,
        polygon_coords: list[list[float]],
    ) -> list[tuple[float, float]]:
        """
        Detect missing tree locations in an orchard.
        
        Args:
            trees: List of tree data from survey
            statistics: Survey statistics including mean/std and missing count
            polygon_coords: Orchard boundary as list of [lon, lat] pairs
            
        Returns:
            List of (latitude, longitude) tuples for missing tree locations
        """
        logger.info(f"Starting missing tree detection for {len(trees)} trees")
        logger.info(f"Expected missing trees: {statistics.missing_tree_count}")
        
        # Step 1: Filter unhealthy trees using statistical analysis
        healthy_trees = self._filter_healthy_trees(trees, statistics)
        logger.info(f"Healthy trees after filtering: {len(healthy_trees)}/{len(trees)}")
        
        if len(healthy_trees) < 3:
            logger.warning("Not enough healthy trees for spatial analysis (need >= 3)")
            return []
        
        # Step 2: Project coordinates to planar system (meters)
        tree_coords = [(t.lat, t.lng) for t in healthy_trees]
        projected_coords, reverse_transformer = project_to_meters(tree_coords)
        polygon_projected, _ = project_polygon_to_meters(polygon_coords)
        
        logger.debug(f"Projected {len(projected_coords)} tree coordinates to UTM")
        
        # Step 3: Build KD-Tree for spatial indexing
        kdtree = build_kdtree(projected_coords)
        
        # Step 4: Estimate expected tree spacing
        expected_spacing = estimate_tree_spacing(kdtree, projected_coords)
        threshold_distance = expected_spacing * self.config.threshold_multiplier
        logger.info(f"Expected spacing: {expected_spacing:.2f}m, gap threshold: {threshold_distance:.2f}m")
        
        # Step 5: Detect row orientation (optional)
        row_angle = None
        row_spacing = None
        col_spacing = None
        
        if self.config.use_row_detection and len(projected_coords) >= 20:
            row_angle, confidence = detect_row_orientation(projected_coords)
            
            if confidence >= self.config.row_confidence_threshold:
                row_spacing, col_spacing = estimate_row_and_column_spacing(
                    projected_coords, row_angle
                )
                logger.info(f"Row pattern detected with confidence {confidence:.2f}")
            else:
                logger.info(f"Row pattern not confident enough ({confidence:.2f})")
                row_angle = None
        
        # Step 6: Detect spatial gaps
        gaps = find_tree_pairs_with_gaps(kdtree, projected_coords, threshold_distance)
        logger.info(f"Found {len(gaps)} gaps exceeding threshold")
        
        # Step 7: Generate candidate missing tree locations (with multi-tree support)
        candidates = self._generate_candidates(
            projected_coords, gaps, expected_spacing
        )
        logger.info(f"Generated {len(candidates)} candidate locations")
        
        # Step 8: Score and rank candidates
        scored_candidates = self._score_candidates(
            candidates=candidates,
            kdtree=kdtree,
            expected_spacing=expected_spacing,
            polygon_coords=polygon_projected,
            row_angle=row_angle,
            row_spacing=row_spacing,
            col_spacing=col_spacing,
        )
        
        # Step 9: Validate candidates
        valid_candidates = self._validate_candidates(
            scored_candidates=scored_candidates,
            polygon_coords=polygon_projected,
            kdtree=kdtree,
            expected_spacing=expected_spacing,
        )
        logger.info(f"Valid candidates after filtering: {len(valid_candidates)}")
        
        # Step 10: Sort by score and limit to known count
        valid_candidates.sort(key=lambda c: c.score, reverse=True)
        missing_count = statistics.missing_tree_count
        limited_candidates = valid_candidates[:missing_count]
        
        logger.info(f"Returning top {len(limited_candidates)} candidates (limit: {missing_count})")
        
        # Log top candidates
        for i, candidate in enumerate(limited_candidates[:5]):
            logger.debug(f"  #{i+1}: ({candidate.x:.2f}, {candidate.y:.2f}) score={candidate.score:.3f}")
        
        # Step 11: Convert back to lat/lon
        candidate_coords = [c.coordinates for c in limited_candidates]
        missing_tree_locations = project_to_latlon(candidate_coords, reverse_transformer)
        
        return missing_tree_locations
    
    def _filter_healthy_trees(
        self,
        trees: list[TreeData],
        statistics: OrchardStatistics,
    ) -> list[TreeData]:
        """
        Filter out unhealthy trees using survey-level statistics.
        
        Excludes trees where:
        - area < (average_area_m2 - sigma * stddev_area_m2)
        - OR ndre < (average_ndre - sigma * stddev_ndre)
        
        Args:
            trees: List of tree data
            statistics: Survey statistics
            
        Returns:
            List of healthy trees
        """
        sigma = self.config.sigma_multiplier
        
        # Calculate thresholds
        area_threshold = statistics.average_area_m2 - (sigma * statistics.stddev_area_m2)
        ndre_threshold = statistics.average_ndre - (sigma * statistics.stddev_ndre)
        
        logger.debug(f"Health thresholds: area >= {area_threshold:.2f}m², ndre >= {ndre_threshold:.3f}")
        
        healthy_trees = []
        unhealthy_count = 0
        
        for tree in trees:
            is_healthy = (
                tree.area >= area_threshold and
                tree.ndre >= ndre_threshold
            )
            
            if is_healthy:
                healthy_trees.append(tree)
            else:
                unhealthy_count += 1
        
        logger.debug(f"Filtered out {unhealthy_count} unhealthy trees")
        return healthy_trees
    
    def _generate_candidates(
        self,
        projected_coords: list[tuple[float, float]],
        gaps: list[tuple[int, int, float]],
        expected_spacing: float,
    ) -> list[tuple[float, float]]:
        """
        Generate candidate missing tree locations from detected gaps.
        
        Handles gaps large enough for multiple missing trees by
        interpolating evenly-spaced points.
        
        Args:
            projected_coords: Projected tree coordinates
            gaps: List of (idx1, idx2, distance) gap tuples
            expected_spacing: Expected tree spacing
            
        Returns:
            List of candidate (x, y) coordinates
        """
        candidates = []
        single_tree_gaps = 0
        multi_tree_gaps = 0
        
        for idx1, idx2, distance in gaps:
            point1 = projected_coords[idx1]
            point2 = projected_coords[idx2]
            
            # Calculate how many trees could fit
            interpolated = interpolate_points_in_gap(
                point1, point2, expected_spacing, distance
            )
            
            if len(interpolated) == 1:
                single_tree_gaps += 1
            else:
                multi_tree_gaps += 1
            
            candidates.extend(interpolated)
        
        logger.debug(f"Gap breakdown: {single_tree_gaps} single-tree, {multi_tree_gaps} multi-tree")
        
        # Remove duplicate candidates (within 1m of each other)
        candidates = self._deduplicate_candidates(candidates, min_distance=1.0)
        
        return candidates
    
    def _deduplicate_candidates(
        self,
        candidates: list[tuple[float, float]],
        min_distance: float,
    ) -> list[tuple[float, float]]:
        """
        Remove duplicate candidates that are too close together.
        
        Args:
            candidates: List of candidate coordinates
            min_distance: Minimum distance between candidates
            
        Returns:
            Deduplicated list of candidates
        """
        if not candidates:
            return []
        
        points = np.array(candidates)
        kdtree = build_kdtree(candidates)
        
        # Mark duplicates
        keep = np.ones(len(candidates), dtype=bool)
        
        for i in range(len(candidates)):
            if not keep[i]:
                continue
            
            # Find nearby candidates
            nearby = kdtree.query_ball_point(candidates[i], min_distance)
            
            for j in nearby:
                if j > i:  # Only remove later ones
                    keep[j] = False
        
        result = [candidates[i] for i in range(len(candidates)) if keep[i]]
        
        if len(result) < len(candidates):
            logger.debug(f"Removed {len(candidates) - len(result)} duplicate candidates")
        
        return result
    
    def _score_candidates(
        self,
        candidates: list[tuple[float, float]],
        kdtree: KDTree,
        expected_spacing: float,
        polygon_coords: list[tuple[float, float]],
        row_angle: Optional[float] = None,
        row_spacing: Optional[float] = None,
        col_spacing: Optional[float] = None,
    ) -> list[ScoredCandidate]:
        """
        Score all candidates and return ranked list.
        
        Args:
            candidates: List of candidate coordinates
            kdtree: KD-Tree of existing trees
            expected_spacing: Expected tree spacing
            polygon_coords: Orchard boundary
            row_angle: Optional detected row angle
            row_spacing: Optional row spacing
            col_spacing: Optional column spacing
            
        Returns:
            List of ScoredCandidate objects
        """
        scored = []
        
        for x, y in candidates:
            score = score_candidate_location(
                candidate=(x, y),
                kdtree=kdtree,
                expected_spacing=expected_spacing,
                polygon_coords=polygon_coords,
                row_spacing=row_spacing,
                col_spacing=col_spacing,
                row_angle=row_angle,
            )
            scored.append(ScoredCandidate(x=x, y=y, score=score))
        
        # Log score distribution
        if scored:
            scores = [c.score for c in scored]
            logger.debug(f"Score distribution: min={min(scores):.3f}, max={max(scores):.3f}, "
                        f"mean={np.mean(scores):.3f}")
        
        return scored
    
    def _validate_candidates(
        self,
        scored_candidates: list[ScoredCandidate],
        polygon_coords: list[tuple[float, float]],
        kdtree: KDTree,
        expected_spacing: float,
    ) -> list[ScoredCandidate]:
        """
        Validate candidate missing tree locations.
        
        Candidates must:
        - Have score >= min_candidate_score
        - Be inside the orchard polygon (with buffer)
        - Be sufficiently far from existing trees
        
        Args:
            scored_candidates: List of scored candidates
            polygon_coords: Orchard boundary coordinates
            kdtree: KD-Tree of existing tree locations
            expected_spacing: Expected tree spacing in meters
            
        Returns:
            List of valid candidates
        """
        min_distance = expected_spacing * self.config.min_distance_ratio
        buffer_distance = expected_spacing * self.config.boundary_buffer_ratio
        min_score = self.config.min_candidate_score
        
        valid = []
        rejected_score = 0
        rejected_polygon = 0
        rejected_distance = 0
        
        for candidate in scored_candidates:
            # Check score threshold
            if candidate.score < min_score:
                rejected_score += 1
                continue
            
            # Check if inside polygon (with buffer)
            if not point_in_polygon_with_buffer(
                candidate.coordinates, polygon_coords, buffer_distance
            ):
                rejected_polygon += 1
                continue
            
            # Check distance to nearest existing tree
            distance = distance_to_nearest_tree(candidate.coordinates, kdtree)
            if distance < min_distance:
                rejected_distance += 1
                continue
            
            valid.append(candidate)
        
        logger.debug(f"Validation rejections: score={rejected_score}, "
                    f"polygon={rejected_polygon}, distance={rejected_distance}")
        
        return valid
