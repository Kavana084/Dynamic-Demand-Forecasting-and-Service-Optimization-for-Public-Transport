import logging
import os
import time
import json
from functools import wraps

class StructuredJSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name
        }
        
        # Add any extra arguments passed via extra=...
        if hasattr(record, 'extra_data') and isinstance(record.extra_data, dict):
            log_obj.update(record.extra_data)
            
        return json.dumps(log_obj)

def setup_logger():
    # Store logs in backend/logs/
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger("transit_system")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        formatter = StructuredJSONFormatter()
        
        # File handler
        fh = logging.FileHandler(os.path.join(log_dir, 'app.log'))
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger

app_logger = setup_logger()

def log_execution_time(endpoint_name: str, category: str = "request"):
    """Decorator to log API request execution time with structured data."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                app_logger.info(
                    f"Completed {endpoint_name}", 
                    extra={'extra_data': {
                        "endpoint": endpoint_name,
                        "category": category,
                        "status": "Success",
                        "duration_ms": round(duration * 1000, 2)
                    }}
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                app_logger.error(
                    f"Error in {endpoint_name}", 
                    exc_info=True,
                    extra={'extra_data': {
                        "endpoint": endpoint_name,
                        "category": category,
                        "status": "Error",
                        "duration_ms": round(duration * 1000, 2),
                        "error_message": str(e)
                    }}
                )
                raise
        return wrapper
    return decorator
