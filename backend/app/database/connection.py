import os
from contextvars import ContextVar
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import socket
import urllib.parse
from app.logger import app_logger
from app.config import settings

load_dotenv()

DATABASE_URL = settings.database_url

def check_db_connectivity() -> bool:
    """Verifies DB connectivity via DNS and TCP without exposing credentials."""
    if not DATABASE_URL:
        app_logger.error("check_db_connectivity: DATABASE_URL is not set.")
        return False
        
    try:
        parsed = urllib.parse.urlparse(DATABASE_URL)

        # ── SQLite: no network connection needed, just confirm the file path is usable ──
        if parsed.scheme.startswith("sqlite"):
            try:
                db_path = parsed.path.lstrip('/')
                if not db_path or db_path == ':memory:':
                    return True
                # Resolve relative paths against cwd
                if not os.path.isabs(db_path):
                    db_path = os.path.abspath(db_path)
                db_dir = os.path.dirname(db_path)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
                app_logger.info(f"check_db_connectivity: SQLite path resolved to {db_path}")
                return True
            except Exception as e:
                app_logger.error(f"check_db_connectivity: SQLite check failed: {e}")
                return False

        # ── PostgreSQL / other network databases ──
        host = parsed.hostname
        port = parsed.port or 5432
        
        if not host:
            app_logger.error("check_db_connectivity: Could not parse hostname from DATABASE_URL.")
            return False
            
        # 1. DNS Resolution
        try:
            ip = socket.gethostbyname(host)
            app_logger.info(f"check_db_connectivity: DNS resolution successful for {host} -> {ip}")
        except socket.gaierror as e:
            app_logger.error(f"check_db_connectivity: DNS resolution failed for {host}: {e}")
            return False
            
        # 2. TCP Connection
        try:
            with socket.create_connection((host, port), timeout=5):
                app_logger.info(f"check_db_connectivity: TCP connection successful to {host}:{port}")
        except socket.timeout:
            app_logger.error(f"check_db_connectivity: TCP connection timed out to {host}:{port}")
            return False
        except socket.error as e:
            app_logger.error(f"check_db_connectivity: TCP connection failed to {host}:{port}: {e}")
            return False
            
        return True
    except Exception as e:
        app_logger.error(f"check_db_connectivity: Unexpected error: {e}")
        return False

# Setup SQLAlchemy engine
if settings.database_type.lower() == "sqlite":
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    
    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,        # Number of connections to keep open
        max_overflow=20,     # Max extra connections if pool is exhausted
        pool_recycle=3600,   # Recycle connections after an hour
        pool_pre_ping=True   # Check connection health before using
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

_request_query_count: ContextVar[int] = ContextVar("request_query_count", default=0)


def reset_query_count():
    _request_query_count.set(0)


def get_query_count() -> int:
    return _request_query_count.get()


def get_pool_status():
    pool = getattr(engine, "pool", None)
    checked_out = getattr(pool, "checkedout", None)
    checked_in = getattr(pool, "checkedin", None)
    overflow = getattr(pool, "overflow", None)
    size = getattr(pool, "size", None)

    def _call(value):
        try:
            return value() if callable(value) else None
        except Exception:
            return None

    return {
        "pool_size": _call(size),
        "checked_in": _call(checked_in),
        "checked_out": _call(checked_out),
        "overflow": _call(overflow),
    }


@event.listens_for(engine, "before_cursor_execute")
def _count_sql_queries(conn, cursor, statement, parameters, context, executemany):
    _request_query_count.set(_request_query_count.get() + 1)


def get_db():
    """Dependency for FastAPI endpoints to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
