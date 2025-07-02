"""
Structured logging configuration for gitagent.

This module sets up comprehensive structured logging using structlog with
JSON output, performance metrics, security logging, and flexible configuration.
"""

import logging
import logging.handlers
import sys
from typing import Any, Dict, Optional

import structlog
from structlog.types import EventDict, Processor

from .config import Settings


def add_log_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add log level to the event dictionary."""
    event_dict["level"] = method_name.upper()
    return event_dict


def add_timestamp(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add timestamp to the event dictionary."""
    import time
    event_dict["timestamp"] = time.time()
    return event_dict


def add_process_info(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add process information to the event dictionary."""
    import os
    event_dict["process_id"] = os.getpid()
    return event_dict


def add_app_info(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application information to the event dictionary."""
    event_dict["app_name"] = "github-action-handler"
    event_dict["app_version"] = "1.0.0"
    return event_dict


def add_github_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add GitHub-specific context to logs."""
    # Extract GitHub-specific information if present
    if "event_type" in event_dict:
        event_dict["github_event_type"] = event_dict["event_type"]
    
    if "delivery_id" in event_dict:
        event_dict["github_delivery_id"] = event_dict["delivery_id"]
    
    if "repository" in event_dict:
        event_dict["github_repository"] = event_dict["repository"]
    
    if "sender" in event_dict:
        event_dict["github_sender"] = event_dict["sender"]
    
    return event_dict


def filter_sensitive_data(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Filter out sensitive data from logs."""
    sensitive_keys = {
        "token", "secret", "password", "key", "authorization", 
        "x-hub-signature", "x-hub-signature-256", "webhook_secret"
    }
    
    def filter_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively filter sensitive data from dictionary."""
        filtered = {}
        for key, value in d.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                filtered[key] = "[REDACTED]"
            elif isinstance(value, dict):
                filtered[key] = filter_dict(value)
            elif isinstance(value, list):
                filtered[key] = [
                    filter_dict(item) if isinstance(item, dict) else item 
                    for item in value
                ]
            else:
                filtered[key] = value
        return filtered
    
    return filter_dict(event_dict)


def add_performance_metrics(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add performance metrics to logs."""
    if "processing_time_ms" in event_dict:
        # Categorize processing time
        time_ms = event_dict["processing_time_ms"]
        if time_ms < 100:
            event_dict["performance_category"] = "fast"
        elif time_ms < 1000:
            event_dict["performance_category"] = "normal"
        elif time_ms < 5000:
            event_dict["performance_category"] = "slow"
        else:
            event_dict["performance_category"] = "very_slow"
    
    return event_dict


def add_security_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add security context for security-related events."""
    security_events = {
        "security_advisory", "vulnerability_alert", "dependabot_alert",
        "code_scanning_alert", "secret_scanning_alert"
    }
    
    if event_dict.get("event_type") in security_events:
        event_dict["security_event"] = True
        event_dict["alert_severity"] = event_dict.get("severity", "unknown")
    
    return event_dict


def setup_logging(settings: Settings) -> None:
    """Set up structured logging configuration."""
    
    # Configure structlog processors
    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        add_log_level,
        add_timestamp,
        add_process_info,
        add_app_info,
    ]
    
    # Add GitHub-specific processors if structured logging is enabled
    if settings.structured_logging:
        processors.extend([
            add_github_context,
            filter_sensitive_data,
            add_performance_metrics,
            add_security_context,
        ])
    
    # Add final processors based on format
    if settings.log_format == "json":
        processors.extend([
            structlog.processors.JSONRenderer()
        ])
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True)
        ])
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=get_log_stream(settings),
        level=getattr(logging, settings.log_level),
    )
    
    # Set up file logging if specified
    if settings.log_file:
        setup_file_logging(settings)


def get_log_stream(settings: Settings):
    """Get the appropriate log stream."""
    if settings.log_file:
        try:
            return open(settings.log_file, 'a', encoding='utf-8')
        except Exception as e:
            print(f"Failed to open log file {settings.log_file}: {e}", file=sys.stderr)
            return sys.stdout
    return sys.stdout


def setup_file_logging(settings: Settings) -> None:
    """Set up file-based logging with rotation."""
    if not settings.log_file:
        return
    
    try:
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            settings.log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # Set formatter
        if settings.log_format == "json":
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, settings.log_level))
        
        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        
    except Exception as e:
        print(f"Failed to set up file logging: {e}", file=sys.stderr)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)


def log_event_processing_start(logger: structlog.BoundLogger, event_type: str, delivery_id: str) -> None:
    """Log the start of event processing."""
    logger.info(
        "Event processing started",
        event_type=event_type,
        delivery_id=delivery_id,
        stage="start"
    )


def log_event_processing_success(
    logger: structlog.BoundLogger, 
    event_type: str, 
    delivery_id: str, 
    processing_time_ms: float,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Log successful event processing."""
    log_data = {
        "event_type": event_type,
        "delivery_id": delivery_id,
        "processing_time_ms": processing_time_ms,
        "stage": "success",
        "status": "completed"
    }
    
    if metadata:
        log_data.update(metadata)
    
    logger.info("Event processing completed successfully", **log_data)


def log_event_processing_error(
    logger: structlog.BoundLogger, 
    event_type: str, 
    delivery_id: str, 
    error: Exception,
    processing_time_ms: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Log event processing error."""
    log_data = {
        "event_type": event_type,
        "delivery_id": delivery_id,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "stage": "error",
        "status": "failed"
    }
    
    if processing_time_ms is not None:
        log_data["processing_time_ms"] = processing_time_ms
    
    if metadata:
        log_data.update(metadata)
    
    logger.error("Event processing failed", **log_data)


def log_webhook_received(
    logger: structlog.BoundLogger,
    event_type: str,
    delivery_id: str,
    repository: Optional[str] = None,
    sender: Optional[str] = None
) -> None:
    """Log webhook reception."""
    logger.info(
        "Webhook received",
        event_type=event_type,
        delivery_id=delivery_id,
        repository=repository,
        sender=sender,
        stage="webhook_received"
    )


def log_security_event(
    logger: structlog.BoundLogger,
    event_type: str,
    severity: str,
    repository: str,
    details: Dict[str, Any]
) -> None:
    """Log security-related events."""
    logger.warning(
        "Security event detected",
        event_type=event_type,
        severity=severity,
        repository=repository,
        security_event=True,
        **details
    )


def log_performance_metrics(
    logger: structlog.BoundLogger,
    metrics: Dict[str, Any]
) -> None:
    """Log performance metrics."""
    logger.info(
        "Performance metrics",
        **metrics,
        metric_type="performance"
    )


def log_health_check(
    logger: structlog.BoundLogger,
    status: str,
    checks: Dict[str, Any]
) -> None:
    """Log health check results."""
    logger.info(
        "Health check performed",
        status=status,
        **checks,
        metric_type="health_check"
    )


def log_rate_limit_exceeded(
    logger: structlog.BoundLogger,
    client_ip: str,
    requests_count: int
) -> None:
    """Log rate limit exceeded events."""
    logger.warning(
        "Rate limit exceeded",
        client_ip=client_ip,
        requests_count=requests_count,
        security_event=True
    )


def log_signature_verification_failed(
    logger: structlog.BoundLogger,
    delivery_id: str,
    client_ip: str
) -> None:
    """Log webhook signature verification failures."""
    logger.error(
        "Webhook signature verification failed",
        delivery_id=delivery_id,
        client_ip=client_ip,
        security_event=True,
        security_issue="signature_verification_failed"
    )


def log_application_startup(
    logger: structlog.BoundLogger,
    host: str,
    port: int,
    debug: bool
) -> None:
    """Log application startup."""
    logger.info(
        "gitagent started",
        host=host,
        port=port,
        debug_mode=debug,
        stage="startup"
    )


def log_application_shutdown(logger: structlog.BoundLogger) -> None:
    """Log application shutdown."""
    logger.info(
        "gitagent shutting down",
        stage="shutdown"
    ) 