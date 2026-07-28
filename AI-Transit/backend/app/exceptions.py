from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import asyncio
import logging

app_logger = logging.getLogger(__name__)

# Common CORS headers for exception responses
cors_headers = {"Access-Control-Allow-Origin": "*"}

class ServiceException(Exception):
    def __init__(self, message: str, error_code: str = "SERVICE_ERROR", status_code: int = 500):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    app_logger.warning(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation error",
            "error_code": "VALIDATION_ERROR",
            "details": exc.errors()
        },
        headers=cors_headers
    )

async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    app_logger.error(f"Database Error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "A database error occurred.",
            "error_code": "DATABASE_ERROR"
        },
        headers=cors_headers
    )

async def service_exception_handler(request: Request, exc: ServiceException):
    app_logger.error(f"Service Error [{exc.error_code}]: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "error_code": exc.error_code
        },
        headers=cors_headers
    )

async def unexpected_exception_handler(request: Request, exc: Exception):
    # Request cancellation (client disconnected, dev reload, server shutdown) should not be surfaced as 500.
    if isinstance(exc, asyncio.CancelledError):
        return JSONResponse(
            status_code=499,
            content={
                "success": False,
                "message": "Request cancelled",
                "error_code": "REQUEST_CANCELLED",
            },
            headers=cors_headers,
        )
    app_logger.error(f"Unexpected Error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An unexpected error occurred.",
            "error_code": "INTERNAL_SERVER_ERROR"
        },
        headers=cors_headers
    )

def setup_exception_handlers(app):
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(ServiceException, service_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)
