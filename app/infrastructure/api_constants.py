"""
API endpoint constants and configuration.

This module contains all external API endpoint paths and related constants.
Centralizing these values makes it easy to swap out endpoints or update API versions.
"""

# Aerobotics API Endpoints
class AeroboticsAPIEndpoints:
    """Aerobotics API endpoint paths."""
    
    # Base paths
    FARMING_BASE = "/farming"
    
    # Survey endpoints
    SURVEYS = f"{FARMING_BASE}/surveys/"
    SURVEY_BY_ID = f"{FARMING_BASE}/surveys/{{survey_id}}"
    SURVEY_TREE_SUMMARIES = f"{FARMING_BASE}/surveys/{{survey_id}}/tree_survey_summaries/"
    TREE_SURVEYS = f"{FARMING_BASE}/surveys/{{survey_id}}/tree_surveys/"
    
    @classmethod
    def get_surveys(cls, orchard_id: int = None) -> str:
        """
        Get surveys endpoint with optional orchard_id filter.
        
        Args:
            orchard_id: Optional orchard ID to filter by
            
        Returns:
            Endpoint path with query parameter if provided
        """
        if orchard_id:
            return f"{cls.SURVEYS}?orchard_id={orchard_id}"
        return cls.SURVEYS
    
    @classmethod
    def get_survey_summaries(cls, survey_id: int) -> str:
        """
        Get survey summaries endpoint for a specific survey.
        
        Args:
            survey_id: Survey ID
            
        Returns:
            Formatted endpoint path
        """
        return cls.SURVEY_TREE_SUMMARIES.format(survey_id=survey_id)
    
    @classmethod
    def get_tree_surveys(cls, survey_id: int) -> str:
        """
        Get tree surveys endpoint for a specific survey.
        
        Args:
            survey_id: Survey ID
            
        Returns:
            Formatted endpoint path
        """
        return cls.TREE_SURVEYS.format(survey_id=survey_id)


# API Configuration Constants
class APIConstants:
    """General API configuration constants."""
    
    # HTTP Headers
    CONTENT_TYPE_JSON = "application/json"
    
    # Timeouts (in seconds)
    DEFAULT_TIMEOUT = 30.0
    LONG_TIMEOUT = 60.0
    
    # Pagination
    DEFAULT_PAGE_SIZE = 100
    MAX_PAGE_SIZE = 1000
