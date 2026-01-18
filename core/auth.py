"""
API Key Authentication Middleware

If API_SECRET_KEY is set in .env, all requests (except health check) 
must include the X-API-Key header.
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from core.config import settings

# Paths that don't require authentication
PUBLIC_PATHS = [
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/debug/location",
]

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth if no API key is configured
        if not settings.API_SECRET_KEY:
            return await call_next(request)
        
        # Allow public paths without auth
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith("/api/debug/location/"):
            return await call_next(request)
        
        # Check for API key in header
        api_key = request.headers.get("X-API-Key")
        
        # Fallback: Check query param (useful for OTA/legacy devices)
        if not api_key:
            api_key = request.query_params.get("api_key")
        
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing API key. Include X-API-Key header."}
            )
        
        if api_key != settings.API_SECRET_KEY:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid API key"}
            )
        
        return await call_next(request)
