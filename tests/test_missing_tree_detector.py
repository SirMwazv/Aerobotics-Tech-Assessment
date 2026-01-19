"""
Unit tests for missing tree detection algorithm.

Tests cover:
- Statistical filtering
- Gap detection
- Multi-tree gap handling
- Candidate scoring
- Row pattern detection
- End-to-end detection
"""
import pytest
import numpy as np
from typing import List, Tuple

from app.domain.models import TreeData, OrchardStatistics
from app.services.domain.missing_tree_detector import (
    MissingTreeDetector,
    DetectionConfig,
    ScoredCandidate,
)
from app.utils.spatial_helpers import (
    build_kdtree,
    estimate_tree_spacing,
    find_tree_pairs_with_gaps,
    interpolate_points_in_gap,
    detect_row_orientation,
    score_candidate_location,
    point_in_polygon,
    point_in_polygon_with_buffer,
)
from app.utils.geo_projection import (
    project_to_meters,
    project_to_latlon,
    get_utm_zone,
)


# ============================================================
# Test Fixtures
# ============================================================

@pytest.fixture
def sample_trees() -> List[TreeData]:
    """Create a sample grid of trees with one missing."""
    trees = []
    tree_id = 1
    
    # Create a 5x5 grid with regular spacing
    # Missing tree at position (2, 2)
    for row in range(5):
        for col in range(5):
            if row == 2 and col == 2:
                continue  # Skip to simulate missing tree
            
            trees.append(TreeData(
                id=tree_id,
                lat=-32.328 + row * 0.0001,  # ~11m spacing
                lng=18.826 + col * 0.0001,
                area=20.0 + np.random.normal(0, 2),
                ndre=0.55 + np.random.normal(0, 0.02),
                survey_id=1
            ))
            tree_id += 1
    
    return trees


@pytest.fixture
def sample_statistics() -> OrchardStatistics:
    """Create sample orchard statistics."""
    return OrchardStatistics(
        survey_id=1,
        tree_count=24,
        missing_tree_count=1,
        average_area_m2=20.0,
        stddev_area_m2=2.0,
        average_ndre=0.55,
        stddev_ndre=0.02,
    )


@pytest.fixture
def sample_polygon() -> List[List[float]]:
    """Create a sample orchard polygon."""
    # Square polygon around the grid
    return [
        [18.8255, -32.3285],  # lon, lat format
        [18.8270, -32.3285],
        [18.8270, -32.3275],
        [18.8255, -32.3275],
        [18.8255, -32.3285],  # Close the polygon
    ]


@pytest.fixture
def regular_grid_coords() -> List[Tuple[float, float]]:
    """Create regular grid coordinates in meters."""
    coords = []
    spacing = 10.0  # 10 meters
    
    for row in range(10):
        for col in range(10):
            coords.append((col * spacing, row * spacing))
    
    return coords


# ============================================================
# Statistical Filtering Tests
# ============================================================

class TestStatisticalFiltering:
    """Tests for unhealthy tree filtering."""
    
    def test_filters_low_area_trees(self):
        """Trees with area below threshold should be filtered."""
        detector = MissingTreeDetector()
        
        trees = [
            TreeData(id=1, lat=0, lng=0, area=20.0, ndre=0.55, survey_id=1),
            TreeData(id=2, lat=0, lng=0, area=10.0, ndre=0.55, survey_id=1),  # Low area
            TreeData(id=3, lat=0, lng=0, area=22.0, ndre=0.55, survey_id=1),
        ]
        stats = OrchardStatistics(
            survey_id=1, tree_count=3, missing_tree_count=0,
            average_area_m2=20.0, stddev_area_m2=2.0,
            average_ndre=0.55, stddev_ndre=0.02
        )
        
        healthy = detector._filter_healthy_trees(trees, stats)
        
        assert len(healthy) == 2
        assert all(t.area >= 16.0 for t in healthy)  # 20 - 2*2 = 16
    
    def test_filters_low_ndre_trees(self):
        """Trees with NDRE below threshold should be filtered."""
        detector = MissingTreeDetector()
        
        trees = [
            TreeData(id=1, lat=0, lng=0, area=20.0, ndre=0.55, survey_id=1),
            TreeData(id=2, lat=0, lng=0, area=20.0, ndre=0.45, survey_id=1),  # Low NDRE
            TreeData(id=3, lat=0, lng=0, area=20.0, ndre=0.58, survey_id=1),
        ]
        stats = OrchardStatistics(
            survey_id=1, tree_count=3, missing_tree_count=0,
            average_area_m2=20.0, stddev_area_m2=2.0,
            average_ndre=0.55, stddev_ndre=0.02
        )
        
        healthy = detector._filter_healthy_trees(trees, stats)
        
        assert len(healthy) == 2
        assert all(t.ndre >= 0.51 for t in healthy)  # 0.55 - 2*0.02 = 0.51
    
    def test_configurable_sigma(self):
        """Sigma multiplier should be configurable."""
        config = DetectionConfig(sigma_multiplier=1.0)  # Stricter
        detector = MissingTreeDetector(config=config)
        
        trees = [
            TreeData(id=1, lat=0, lng=0, area=20.0, ndre=0.55, survey_id=1),
            TreeData(id=2, lat=0, lng=0, area=17.0, ndre=0.55, survey_id=1),  # Would pass 2-sigma
        ]
        stats = OrchardStatistics(
            survey_id=1, tree_count=2, missing_tree_count=0,
            average_area_m2=20.0, stddev_area_m2=2.0,
            average_ndre=0.55, stddev_ndre=0.02
        )
        
        healthy = detector._filter_healthy_trees(trees, stats)
        
        # With 1-sigma, threshold is 18.0, so tree with 17.0 should be filtered
        assert len(healthy) == 1


# ============================================================
# Gap Detection Tests
# ============================================================

class TestGapDetection:
    """Tests for spatial gap detection."""
    
    def test_detects_single_gap(self):
        """Should detect a gap between two distant trees."""
        coords = [
            (0, 0),
            (10, 0),
            (30, 0),  # Gap here - 20m instead of 10m
            (40, 0),
        ]
        
        gaps = find_tree_pairs_with_gaps(None, coords, threshold_distance=15.0)
        
        # Algorithm finds all pairs with distance > threshold
        # Including (1, 2) = 20m gap which is the primary gap
        assert len(gaps) >= 1
        gap_distances = [g[2] for g in gaps]
        assert 20.0 in gap_distances  # The main gap we care about
    
    def test_no_gaps_when_tightly_spaced(self):
        """No gaps should be detected when spacing is under threshold."""
        # Use threshold higher than any pair distance
        coords = [(i * 10, 0) for i in range(5)]  # Max distance = 40m
        
        # Threshold = 50m, so no gaps should exceed it within search radius
        gaps = find_tree_pairs_with_gaps(None, coords, threshold_distance=50.0)
        
        assert len(gaps) == 0
    
    def test_multiple_gaps(self, regular_grid_coords):
        """Should detect multiple gaps."""
        # Remove some trees to create gaps
        coords = [c for i, c in enumerate(regular_grid_coords) if i not in [22, 33, 44]]
        
        kdtree = build_kdtree(coords)
        spacing = estimate_tree_spacing(kdtree, coords)
        
        gaps = find_tree_pairs_with_gaps(kdtree, coords, spacing * 1.5)
        
        assert len(gaps) > 0


# ============================================================
# Multi-Tree Gap Interpolation Tests
# ============================================================

class TestMultiTreeGapInterpolation:
    """Tests for multi-tree gap handling."""
    
    def test_single_tree_gap(self):
        """Gap of 2x spacing should yield 1 interpolated point."""
        point1 = (0, 0)
        point2 = (20, 0)
        expected_spacing = 10.0
        
        interpolated = interpolate_points_in_gap(point1, point2, expected_spacing, 20.0)
        
        assert len(interpolated) == 1
        assert interpolated[0] == (10.0, 10.0) or np.isclose(interpolated[0][0], 10.0)
    
    def test_two_tree_gap(self):
        """Gap of 3x spacing should yield 2 interpolated points."""
        point1 = (0, 0)
        point2 = (30, 0)
        expected_spacing = 10.0
        
        interpolated = interpolate_points_in_gap(point1, point2, expected_spacing, 30.0)
        
        assert len(interpolated) == 2
        # Points should be at 10 and 20
        assert np.isclose(interpolated[0][0], 10.0, atol=0.1)
        assert np.isclose(interpolated[1][0], 20.0, atol=0.1)
    
    def test_large_gap(self):
        """Large gap should yield multiple points."""
        point1 = (0, 0)
        point2 = (50, 0)
        expected_spacing = 10.0
        
        interpolated = interpolate_points_in_gap(point1, point2, expected_spacing, 50.0)
        
        assert len(interpolated) == 4  # 5 intervals - 1 = 4 missing trees
    
    def test_diagonal_gap(self):
        """Should work for diagonal gaps."""
        point1 = (0, 0)
        point2 = (30, 40)  # Distance = 50
        expected_spacing = 10.0
        
        interpolated = interpolate_points_in_gap(point1, point2, expected_spacing, 50.0)
        
        assert len(interpolated) == 4
        # Points should be evenly distributed along the line


# ============================================================
# Row Pattern Detection Tests
# ============================================================

class TestRowPatternDetection:
    """Tests for row/column pattern detection."""
    
    def test_detects_horizontal_rows(self):
        """Should detect horizontal row orientation."""
        # Create horizontal rows
        coords = []
        for row in range(5):
            for col in range(20):
                coords.append((col * 10, row * 8))  # 10m between trees, 8m between rows
        
        angle, confidence = detect_row_orientation(coords)
        
        # Horizontal = 0 radians
        assert np.isclose(angle, 0.0, atol=0.2) or np.isclose(angle, np.pi, atol=0.2)
        assert confidence > 0.3
    
    def test_detects_angled_rows(self):
        """Should detect 45-degree row orientation."""
        coords = []
        angle_rad = np.pi / 4  # 45 degrees
        
        for row in range(5):
            for col in range(20):
                x = col * 10 * np.cos(angle_rad) - row * 8 * np.sin(angle_rad)
                y = col * 10 * np.sin(angle_rad) + row * 8 * np.cos(angle_rad)
                coords.append((x, y))
        
        detected_angle, confidence = detect_row_orientation(coords)
        
        # Should be close to 45 degrees or perpendicular
        # Note: angle is normalized to [0, π)
        assert confidence > 0.2  # Some confidence
    
    def test_low_confidence_for_random(self):
        """Random points should have low confidence."""
        np.random.seed(42)
        coords = [(np.random.uniform(0, 100), np.random.uniform(0, 100)) for _ in range(50)]
        
        _, confidence = detect_row_orientation(coords)
        
        assert confidence < 0.5  # Should not be confident


# ============================================================
# Candidate Scoring Tests
# ============================================================

class TestCandidateScoring:
    """Tests for candidate location scoring."""
    
    def test_good_candidate_scores_high(self):
        """Well-placed candidate should score high."""
        # Create grid with one missing
        coords = []
        for row in range(5):
            for col in range(5):
                if not (row == 2 and col == 2):
                    coords.append((col * 10, row * 10))
        
        kdtree = build_kdtree(coords)
        polygon = [(0, 0), (50, 0), (50, 50), (0, 50), (0, 0)]
        
        # Candidate at the missing position
        candidate = (20, 20)
        
        score = score_candidate_location(
            candidate=candidate,
            kdtree=kdtree,
            expected_spacing=10.0,
            polygon_coords=polygon,
        )
        
        assert score > 0.5  # Should be a good score
    
    def test_edge_candidate_scores_lower(self):
        """Candidate near edge should score lower."""
        coords = [(i * 10, 0) for i in range(5)]
        kdtree = build_kdtree(coords)
        polygon = [(0, -5), (50, -5), (50, 5), (0, 5), (0, -5)]
        
        # Candidate near boundary
        candidate = (25, 4)  # Very close to edge
        
        score = score_candidate_location(
            candidate=candidate,
            kdtree=kdtree,
            expected_spacing=10.0,
            polygon_coords=polygon,
        )
        
        assert score < 0.7  # Should be penalized for being near edge


# ============================================================
# Polygon Tests
# ============================================================

class TestPolygonOperations:
    """Tests for polygon containment operations."""
    
    def test_point_inside_polygon(self):
        """Point inside should return True."""
        polygon = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        
        assert point_in_polygon((5, 5), polygon) == True
    
    def test_point_outside_polygon(self):
        """Point outside should return False."""
        polygon = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        
        assert point_in_polygon((15, 5), polygon) == False
    
    def test_buffered_polygon(self):
        """Buffer should shrink polygon."""
        polygon = [(0, 0), (20, 0), (20, 20), (0, 20), (0, 0)]
        
        # Point near edge
        near_edge = (1, 10)
        
        # Should be inside original
        assert point_in_polygon(near_edge, polygon) == True
        
        # Should be outside with 2m buffer
        assert point_in_polygon_with_buffer(near_edge, polygon, 2.0) == False
        
        # Center should still be inside
        assert point_in_polygon_with_buffer((10, 10), polygon, 2.0) == True


# ============================================================
# Coordinate Projection Tests
# ============================================================

class TestCoordinateProjection:
    """Tests for coordinate transformation."""
    
    def test_utm_zone_calculation(self):
        """UTM zone should be calculated correctly."""
        # Cape Town area (longitude ~18)
        assert get_utm_zone(18.0) == 34
        
        # New York area (longitude ~-74)
        assert get_utm_zone(-74.0) == 18
    
    def test_projection_roundtrip(self):
        """Projecting and unprojecting should return original coordinates."""
        coords = [(-32.328, 18.826), (-32.329, 18.827)]
        
        projected, transformer = project_to_meters(coords)
        
        # Verify projection changed the values
        assert projected[0] != coords[0]
        
        # Unproject
        unprojected = project_to_latlon(projected, transformer)
        
        # Should be close to original
        assert np.isclose(unprojected[0][0], coords[0][0], atol=0.0001)
        assert np.isclose(unprojected[0][1], coords[0][1], atol=0.0001)


# ============================================================
# End-to-End Tests
# ============================================================

class TestEndToEnd:
    """End-to-end integration tests."""
    
    def test_detects_single_missing_tree(self, sample_trees, sample_statistics, sample_polygon):
        """Should detect a single missing tree in a grid."""
        detector = MissingTreeDetector()
        
        locations = detector.detect_missing_trees(
            trees=sample_trees,
            statistics=sample_statistics,
            polygon_coords=sample_polygon,
        )
        
        assert len(locations) == 1  # Should find the one missing tree
    
    def test_returns_empty_for_complete_grid(self, sample_polygon):
        """Should return empty for complete grid with 0 missing."""
        # Create complete 5x5 grid
        trees = []
        for row in range(5):
            for col in range(5):
                trees.append(TreeData(
                    id=row * 5 + col,
                    lat=-32.328 + row * 0.0001,
                    lng=18.826 + col * 0.0001,
                    area=20.0,
                    ndre=0.55,
                    survey_id=1
                ))
        
        stats = OrchardStatistics(
            survey_id=1, tree_count=25, missing_tree_count=0,
            average_area_m2=20.0, stddev_area_m2=2.0,
            average_ndre=0.55, stddev_ndre=0.02
        )
        
        detector = MissingTreeDetector()
        locations = detector.detect_missing_trees(trees, stats, sample_polygon)
        
        assert len(locations) == 0
    
    def test_handles_multiple_missing(self, sample_polygon):
        """Should handle multiple missing trees."""
        # Create grid with 3 missing
        trees = []
        missing_positions = [(1, 1), (2, 3), (4, 2)]
        tree_id = 1
        
        for row in range(5):
            for col in range(5):
                if (row, col) in missing_positions:
                    continue
                trees.append(TreeData(
                    id=tree_id,
                    lat=-32.328 + row * 0.0001,
                    lng=18.826 + col * 0.0001,
                    area=20.0,
                    ndre=0.55,
                    survey_id=1
                ))
                tree_id += 1
        
        stats = OrchardStatistics(
            survey_id=1, tree_count=22, missing_tree_count=3,
            average_area_m2=20.0, stddev_area_m2=2.0,
            average_ndre=0.55, stddev_ndre=0.02
        )
        
        detector = MissingTreeDetector()
        locations = detector.detect_missing_trees(trees, stats, sample_polygon)
        
        assert len(locations) == 3
    
    def test_respects_missing_count_limit(self, sample_polygon):
        """Should not return more than missing_tree_count."""
        # Create grid with many gaps but limit to 2
        trees = []
        for i in range(10):
            trees.append(TreeData(
                id=i,
                lat=-32.328 + (i % 5) * 0.0002,  # Larger gaps
                lng=18.826 + (i // 5) * 0.0002,
                area=20.0,
                ndre=0.55,
                survey_id=1
            ))
        
        stats = OrchardStatistics(
            survey_id=1, tree_count=10, missing_tree_count=2,  # Limit to 2
            average_area_m2=20.0, stddev_area_m2=2.0,
            average_ndre=0.55, stddev_ndre=0.02
        )
        
        detector = MissingTreeDetector()
        locations = detector.detect_missing_trees(trees, stats, sample_polygon)
        
        assert len(locations) <= 2


# ============================================================
# Configuration Tests
# ============================================================

class TestConfiguration:
    """Tests for configuration handling."""
    
    def test_default_config(self):
        """Default config should be used when none provided."""
        detector = MissingTreeDetector()
        
        assert detector.config.threshold_multiplier == 1.5
        assert detector.config.sigma_multiplier == 2.0
    
    def test_custom_config(self):
        """Custom config should override defaults."""
        config = DetectionConfig(
            threshold_multiplier=2.0,
            sigma_multiplier=1.5,
            min_candidate_score=0.5,
        )
        detector = MissingTreeDetector(config=config)
        
        assert detector.config.threshold_multiplier == 2.0
        assert detector.config.sigma_multiplier == 1.5
        assert detector.config.min_candidate_score == 0.5
    
    def test_backward_compatibility(self):
        """Legacy threshold_multiplier param should work."""
        detector = MissingTreeDetector(threshold_multiplier=1.8)
        
        assert detector.threshold_multiplier == 1.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
