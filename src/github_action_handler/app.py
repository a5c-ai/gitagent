"""
FastAPI application for GitHub Action Handler.

This application provides REST endpoints for processing GitHub Action events
and retrieving handler information, without webhook functionality.
"""

import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import structlog

from .config import Settings
from .event_handler import GitHubActionEventProcessor
from .models import (
    GitHubEvent,
    EventProcessingResult,
    HealthCheck,
    DetailedHealthCheck,
    EventStatistics,
    ConfigurationInfo,
)

# Initialize structured logging
logger = structlog.get_logger(__name__)

# Global settings and processor
settings = Settings()
event_processor = GitHubActionEventProcessor(settings)

# Application start time for uptime calculation
app_start_time = datetime.now(timezone.utc)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="GitHub Action Handler",
        description="Comprehensive GitHub Action event handler with commit history context",
        version="1.0.0",
        docs_url="/docs" if settings.development_mode else None,
        redoc_url="/redoc" if settings.development_mode else None,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.development_mode else [],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    
    return app


app = create_app()


@app.get("/health", response_model=HealthCheck, tags=["Health"])
async def health_check() -> HealthCheck:
    """Basic health check endpoint."""
    uptime = datetime.now(timezone.utc) - app_start_time
    uptime_str = str(uptime).split('.')[0]  # Remove microseconds
    
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        uptime=uptime_str
    )


@app.get("/health/detailed", response_model=DetailedHealthCheck, tags=["Health"])
async def detailed_health_check() -> DetailedHealthCheck:
    """Detailed health check with system information."""
    import psutil
    
    uptime = datetime.now(timezone.utc) - app_start_time
    uptime_str = str(uptime).split('.')[0]  # Remove microseconds
    
    # Get system metrics
    system_info = {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "memory_used": psutil.virtual_memory().used,
        "disk_percent": psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:\\').percent,
        "process_count": len(psutil.pids())
    }
    
    # Get application metrics
    stats = event_processor.get_statistics()
    application_info = {
        "events_processed": stats["total_events"],
        "events_successful": stats["successful_events"],
        "events_failed": stats["failed_events"],
        "success_rate": stats["success_rate"],
        "events_per_second": stats["events_per_second"]
    }
    
    # Check GitHub API status (stub)
    github_api_info = {
        "status": "available",
        "last_check": datetime.now(timezone.utc).isoformat(),
        "token_configured": bool(settings.github_token)
    }
    
    return DetailedHealthCheck(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        uptime=uptime_str,
        system=system_info,
        application=application_info,
        github_api=github_api_info
    )


@app.post("/events/process", response_model=EventProcessingResult, tags=["Events"])
async def process_github_event(
    event: GitHubEvent,
    background_tasks: BackgroundTasks
) -> EventProcessingResult:
    """Process a GitHub event directly."""
    try:
        logger.info("Processing GitHub event", event_type=event.__class__.__name__)
        
        # Process the event
        if settings.background_tasks:
            # Process in background
            background_tasks.add_task(event_processor.process_event, event)
            
            return EventProcessingResult(
                event_type="background_task",
                processing_time=0.0,
                success=True,
                message="Event queued for background processing",
                metadata={"queued": True}
            )
        else:
            # Process immediately
            result = await event_processor.process_event(event)
            return result
            
    except Exception as e:
        logger.error("Failed to process event", error=str(e))
        raise HTTPException(status_code=500, detail=f"Event processing failed: {str(e)}")


@app.get("/events/supported", tags=["Events"])
async def get_supported_events() -> Dict[str, Any]:
    """Get list of all supported GitHub event types."""
    events = event_processor.get_supported_events()
    
    return {
        "events": events,
        "total_count": len(events),
        "categories": list(set(event["category"] for event in events))
    }


@app.get("/events/structure/{event_type}", tags=["Events"])
async def get_event_structure(event_type: str) -> Dict[str, Any]:
    """Get the expected structure for a specific event type."""
    # This is a stub implementation - in practice, you might want to provide
    # detailed schema information for each event type
    
    supported_events = [event["name"] for event in event_processor.get_supported_events()]
    
    if event_type not in supported_events:
        raise HTTPException(status_code=404, detail=f"Event type '{event_type}' is not supported")
    
    return {
        "event_type": event_type,
        "description": f"Structure for {event_type} events",
        "documentation_url": f"https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#{event_type}",
        "note": "This is a stub implementation - refer to GitHub documentation for complete event structure"
    }


@app.get("/stats", response_model=EventStatistics, tags=["Statistics"])
async def get_statistics() -> EventStatistics:
    """Get event processing statistics."""
    stats = event_processor.get_statistics()
    uptime = datetime.now(timezone.utc) - app_start_time
    uptime_str = str(uptime).split('.')[0]  # Remove microseconds
    
    return EventStatistics(
        total_events=stats["total_events"],
        successful_events=stats["successful_events"],
        failed_events=stats["failed_events"],
        events_per_second=stats["events_per_second"],
        processing_times={
            "average": 0.0,  # Stub - implement actual timing statistics
            "min": 0.0,
            "max": 0.0
        },
        event_types=stats["events_by_type"],
        last_processed=None,  # Stub - implement last processed tracking
        uptime=uptime_str
    )


@app.get("/config", response_model=ConfigurationInfo, tags=["Configuration"])
async def get_configuration() -> ConfigurationInfo:
    """Get current configuration (sanitized for security)."""
    
    return ConfigurationInfo(
        log_level=settings.log_level,
        log_format=settings.log_format,
        max_concurrent_events=settings.max_concurrent_events,
        event_timeout_seconds=settings.event_timeout_seconds,
        background_tasks=settings.background_tasks,
        metrics_enabled=settings.metrics_enabled,
        health_check_enabled=settings.health_check_enabled,
        event_storage_enabled=settings.event_storage_enabled,
        enabled_events=settings.enabled_events,
        disabled_events=settings.disabled_events
    )


@app.get("/metrics", tags=["Monitoring"])
async def get_metrics() -> Dict[str, Any]:
    """Get Prometheus-style metrics."""
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Metrics are disabled")
    
    stats = event_processor.get_statistics()
    uptime_seconds = (datetime.now(timezone.utc) - app_start_time).total_seconds()
    
    # Return metrics in a simple format (not full Prometheus format for now)
    return {
        "github_events_total": stats["total_events"],
        "github_events_successful_total": stats["successful_events"],
        "github_events_failed_total": stats["failed_events"],
        "github_events_per_second": stats["events_per_second"],
        "github_handler_uptime_seconds": uptime_seconds,
        "github_events_by_type": stats["events_by_type"]
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error(
        "Unhandled exception",
        path=str(request.url),
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.development_mode else "An error occurred"
        }
    )


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(
        "GitHub Action Handler starting up",
        version="1.0.0",
        log_level=settings.log_level,
        max_concurrent_events=settings.max_concurrent_events
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("GitHub Action Handler shutting down")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
        access_log=True
    ) 