"""
Application configuration using Pydantic settings.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # External API Configuration
    external_api_base_url: str = Field(
        default="https://api.example.com",
        description="Base URL for the external API"
    )
    external_api_key: str = Field(
        default="",
        description="API key for authentication"
    )
    
    # Retry Configuration
    max_retry_attempts: int = Field(
        default=3,
        description="Maximum number of retry attempts for API calls"
    )
    retry_backoff_multiplier: int = Field(
        default=1,
        description="Multiplier for exponential backoff"
    )
    retry_min_wait: int = Field(
        default=4,
        description="Minimum wait time in seconds between retries"
    )
    retry_max_wait: int = Field(
        default=10,
        description="Maximum wait time in seconds between retries"
    )
    
    # Missing Tree Detection Parameters
    missing_tree_threshold_multiplier: float = Field(
        default=1.5,
        description="Multiplier for expected tree spacing to detect gaps"
    )
    missing_tree_sigma_multiplier: float = Field(
        default=2.0,
        description="Number of standard deviations for unhealthy tree filtering"
    )
    missing_tree_min_distance_ratio: float = Field(
        default=0.5,
        description="Minimum distance from existing trees as ratio of expected spacing"
    )
    missing_tree_boundary_buffer_ratio: float = Field(
        default=0.3,
        description="Buffer from polygon boundary as ratio of expected spacing"
    )
    missing_tree_use_row_detection: bool = Field(
        default=True,
        description="Whether to attempt row/column pattern detection"
    )
    missing_tree_min_candidate_score: float = Field(
        default=0.3,
        description="Minimum score for a candidate to be considered valid"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    # CORS Configuration
    cors_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins (use specific origins in production)"
    )
    
    # Rate Limiting
    rate_limit_requests: int = Field(
        default=100,
        description="Maximum requests per minute per client"
    )
    
    # Application Settings
    app_name: str = Field(
        default="Mwazvita Mutowo Aerobotics Tech Assessment",
        description="Application name"
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version"
    )
    debug: bool = Field(
        default=False,
        description="Debug mode"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
