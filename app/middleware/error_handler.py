"""
Global error handling middleware.
"""
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

from app.infrastructure.external_api_client import ExternalAPIError


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.
    
    Catches unhandled exceptions and returns consistent error responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process the request and handle any exceptions.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            Response object
        """
        try:
            response = await call_next(request)
            return response
        
        except ExternalAPIError as e:
            # Log external API errors
            logger.error(
                f"External API error: {str(e)}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": e.status_code,
                }
            )
            # Pass through the original status code from the external API
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": "External API error",
                    "detail": e.message,
                }
            )
        
        except ValueError as e:
            # Log validation errors
            logger.warning(
                f"Validation error: {str(e)}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                }
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Invalid request",
                    "detail": str(e),
                }
            )
        
        except Exception as e:
            # Log unexpected errors
            logger.exception(
                f"Unhandled exception: {str(e)}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                }
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "detail": "An unexpected error occurred",
                }
            )
