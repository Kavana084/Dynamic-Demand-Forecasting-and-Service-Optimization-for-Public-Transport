import os
import pandas as pd
import asyncio
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .api_routes import router, init_dataset
from .api.navigation import router as navigation_router
from .service import init_service
from .task_scheduler import start_scheduler, stop_scheduler, set_app_state
from .logger import app_logger
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
from .websocket_manager import manager
from .services.realtime_simulator import generate_realtime_updates
from .exceptions import setup_exception_handlers
from .services.demand_prediction_service import demand_prediction_service as _demand_svc
from .services.raptor_service import warm_raptor_cache
from .database.connection import (
    SessionLocal,
    engine,
    Base,
    get_pool_status,
    get_query_count,
    reset_query_count,
    check_db_connectivity,
)
from .services.user_service import ensure_users_table_and_seed, seed_existing_users
from .services.model_metadata_service import model_metadata_service

app = FastAPI(
    title="AI-Driven Smart Transit Optimization API (Production Upgrade)",
    description="Real-time backend serving ML predictions, MILP optimization, and dashboard analytics for BMTC GTFS data.",
    version="2.0.0"
)

@app.middleware("http")
async def structured_request_logging(request: Request, call_next):
    reset_query_count()
    started = time.perf_counter()
    path = str(request.url.path)
    method = request.method
    app_logger.info(
        "Request started",
        extra={
            "extra_data": {
                "method": method,
                "path": path,
                "query": str(request.url.query),
            }
        },
    )
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        app_logger.exception(
            "Request failed",
            extra={
                "extra_data": {
                    "method": method,
                    "path": path,
                    "duration_ms": duration_ms,
                    "db_query_count": get_query_count(),
                    "db_pool": get_pool_status(),
                }
            },
        )
        raise

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response_size = response.headers.get("content-length")
    memory_usage = None
    try:
        import psutil

        memory_usage = psutil.Process().memory_info().rss
    except Exception:
        memory_usage = None

    log_method = app_logger.warning if duration_ms > 500 else app_logger.info
    log_method(
        "Slow request completed" if duration_ms > 500 else "Request completed",
        extra={
            "extra_data": {
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "response_size_bytes": int(response_size) if response_size else None,
                "db_query_count": get_query_count(),
                "db_pool": get_pool_status(),
                "memory_rss_bytes": memory_usage,
            }
        },
    )
    response.headers["X-DB-Query-Count"] = str(get_query_count())
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    return response

# Global exception logging middleware so unexpected backend errors are visible in console logs.
@app.middleware("http")
async def log_unhandled_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except asyncio.CancelledError:
        # Client disconnected or server reload/shutdown cancelled the request.
        # Don't log as an "error" and don't convert to 500.
        raise
    except Exception:
        app_logger.exception(
            "Unhandled exception while processing request",
            extra={
                "extra_data": {
                    "method": request.method,
                    "path": str(request.url.path),
                    "query": str(request.url.query),
                }
            },
        )
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(navigation_router)

# Startup event to load model and dataset, and start scheduler
@app.on_event("startup")
def startup_event():
    app_logger.info("Starting up FastAPI application...")
    
    # 1. Check DB Connectivity
    app.state.db_connected = check_db_connectivity()
    
    if not app.state.db_connected:
        app_logger.warning("======================================================")
        app_logger.warning(" DEGRADED MODE: Database is offline or unreachable.")
        app_logger.warning(" APIs not requiring DB (like ML predictions) will work.")
        app_logger.warning(" DB-dependent APIs will return 503 Service Unavailable.")
        app_logger.warning("======================================================")
        
    # Log database URL for debugging
    app_logger.info(f"DEBUG_DATABASE: engine.url={engine.url}")
    from .config import settings
    if hasattr(settings, 'DATABASE_URL'):
        app_logger.info(f"DEBUG_DATABASE: settings.DATABASE_URL={settings.DATABASE_URL}")
    else:
        app_logger.info("DEBUG_DATABASE: settings.DATABASE_URL not found")
    
    # Log absolute database path for SQLite
    if settings.database_type.lower() == "sqlite":
        import os
        db_path = settings.sqlite_database_url.replace("sqlite:///", "")
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)
        app_logger.info(f"DEBUG_DATABASE: Absolute DB path={db_path}")
        app_logger.info(f"DEBUG_DATABASE: DB file exists={os.path.exists(db_path)}")
        if os.path.exists(db_path):
            app_logger.info(f"DEBUG_DATABASE: DB file size={os.path.getsize(db_path)} bytes")
    
    if app.state.db_connected:
        try:
            app_logger.info("Syncing database tables...")
            from .database import models  # Ensure all models are registered
            Base.metadata.create_all(bind=engine)
            
            # Schema Migration: Add missing target_timestamp column if the model is newer than the DB
            from sqlalchemy import text
            def _try_exec(conn, sql_if_exists: str, sql_plain: str, label: str):
                """
                Execute a migration statement in a best-effort way across common DBs.
                - Prefer `IF NOT EXISTS` when supported.
                - Fall back to plain ALTER TABLE for engines that don't support it.
                """
                try:
                    conn.execute(text(sql_if_exists))
                    app_logger.info(f"Executed schema migration: {label}")
                    return
                except Exception as e1:
                    # Fall back for engines without IF NOT EXISTS support (e.g. some SQLite builds)
                    try:
                        conn.execute(text(sql_plain))
                        app_logger.info(f"Executed schema migration (fallback): {label}")
                    except Exception as e2:
                        # If it already exists (duplicate column), ignore. Otherwise log.
                        msg = f"{e2}".lower()
                        if "duplicate" in msg or "exists" in msg:
                            app_logger.info(f"Schema migration skipped (already applied): {label}")
                        else:
                            app_logger.error(f"Schema migration failed: {label} ({e1} / {e2})")

            with engine.begin() as conn:
                if settings.database_type.lower() != "sqlite":
                    _try_exec(
                        conn,
                        "ALTER TABLE prediction_records ADD COLUMN IF NOT EXISTS target_timestamp TIMESTAMP;",
                        "ALTER TABLE prediction_records ADD COLUMN target_timestamp TIMESTAMP;",
                        "prediction_records.target_timestamp",
                    )

                    _try_exec(
                        conn,
                        "ALTER TABLE optimization_results ADD COLUMN IF NOT EXISTS model_version VARCHAR(50);",
                        "ALTER TABLE optimization_results ADD COLUMN model_version VARCHAR(50);",
                        "optimization_results.model_version",
                    )
                    try:
                        conn.execute(text("UPDATE optimization_results SET model_version = 'catboost-v2' WHERE model_version IS NULL;"))
                    except Exception:
                        pass

                    # User administration scope / security fields
                    _try_exec(
                        conn,
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS region TEXT;",
                        "ALTER TABLE users ADD COLUMN region TEXT;",
                        "users.region",
                    )
                    _try_exec(
                        conn,
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS depot TEXT;",
                        "ALTER TABLE users ADD COLUMN depot TEXT;",
                        "users.depot",
                    )
                    _try_exec(
                        conn,
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN DEFAULT 0;",
                        "ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN DEFAULT 0;",
                        "users.mfa_enabled",
                    )
                    _try_exec(
                        conn,
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT 0;",
                        "ALTER TABLE users ADD COLUMN is_locked BOOLEAN DEFAULT 0;",
                        "users.is_locked",
                    )
                    # mfa_secret: base32 TOTP seed required when mfa_enabled=true.
                    # This column was present in the SQLAlchemy model but was never
                    # included in the startup migration, causing every User query to
                    # fail with psycopg2.errors.UndefinedColumn and breaking login.
                    _try_exec(
                        conn,
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret TEXT;",
                        "ALTER TABLE users ADD COLUMN mfa_secret TEXT;",
                        "users.mfa_secret",
                    )

                    # Audit logs: module + status + detail (for enterprise audit UX)
                    _try_exec(
                        conn,
                        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS module TEXT DEFAULT 'User Administration';",
                        "ALTER TABLE audit_logs ADD COLUMN module TEXT DEFAULT 'User Administration';",
                        "audit_logs.module",
                    )
                    _try_exec(
                        conn,
                        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'success';",
                        "ALTER TABLE audit_logs ADD COLUMN status TEXT DEFAULT 'success';",
                        "audit_logs.status",
                    )
                    _try_exec(
                        conn,
                        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS detail TEXT;",
                        "ALTER TABLE audit_logs ADD COLUMN detail TEXT;",
                        "audit_logs.detail",
                    )
                    
        except Exception as e:
            app_logger.error(f"Error syncing database tables: {str(e)}", exc_info=True)
    else:
        app_logger.warning("Skipped syncing database tables (offline).")

    if app.state.db_connected:
        try:
            ensure_users_table_and_seed()
            db = SessionLocal()
            try:
                seed_existing_users(db)
            except Exception as seed_error:
                # If seeding fails due to existing users, log and continue
                app_logger.warning(f"User seeding skipped (users may already exist): {str(seed_error)}")
            finally:
                db.close()
            app_logger.info("User authentication store initialized successfully")
            
            # Log table row counts for verification
            from sqlalchemy import text
            app_logger.info("DATABASE TABLE ROW COUNTS:")
            key_tables = ['gtfs_stops', 'gtfs_stop_times', 'routes', 'forecast_history', 'optimization_results', 'users']
            for table in key_tables:
                try:
                    with engine.connect() as conn:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        app_logger.info(f"  {table}: {count} rows")
                except Exception as e:
                    app_logger.warning(f"  {table}: ERROR - {e}")
        except Exception as e:
            app_logger.error(f"Error initializing user authentication store: {str(e)}", exc_info=True)
    else:
        app_logger.warning("Skipped user authentication store initialization (offline).")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(base_dir, "DataSet", "syn_data", "synthetic_passenger_demand.csv")
    
    # Initialize ML service with new CatBoost model
    app_logger.info("Initializing ML Prediction Service with CatBoost model...")
    from .config import settings
    from .ml.model_loader import model_loader
    
    try:
        # Load CatBoost model using ModelLoader
        success = model_loader.load_model()
        if success:
            app_logger.info("CatBoost model loaded successfully")
            app.state.model_loader = model_loader
            
            # Initialize legacy PredictionService for backward compatibility
            svc = init_service()
            app.state.prediction_service = svc
            
            # Inject app.state into DemandPredictionService
            _demand_svc.set_app_state(app.state)
            app_logger.info("DemandPredictionService wired to CatBoost model.")
            
            # Populate model metadata with CatBoost metrics
            if app.state.db_connected:
                model_metadata_service.populate_catboost_metadata(model_loader)
            else:
                app_logger.warning("Skipped populating model metadata (offline).")
        else:
            app_logger.error("Failed to load CatBoost model")
            # Initialize legacy service as fallback
            svc = init_service()
            app.state.prediction_service = svc
    except Exception as e:
        app_logger.error(f"Error initializing ML Prediction Service: {str(e)}", exc_info=True)
    
    # Load dataset into memory
    app_logger.info("Loading processed dataset into memory...")
    try:
        if os.path.exists(dataset_path):
            df = pd.read_csv(dataset_path)
            init_dataset(df)
            app.state.dataset = df
            app_logger.info("Dataset loaded successfully")
        else:
            app_logger.error(f"Dataset not found at {dataset_path}")
    except Exception as e:
        app_logger.error(f"Error loading dataset: {str(e)}", exc_info=True)
        
    # Share app.state with the background scheduler (schedule engine needs ML model + dataset)
    set_app_state(app.state)

    # Start background scheduler
    start_scheduler()

    # Load RAPTOR's TransitData (routes/patterns/trips/walk-transfers) BEFORE
    # declaring startup complete, so uvicorn never accepts a request while
    # the cache is cold.
    #
    # This used to run in a background thread (start_raptor_warmup()) so
    # startup itself would return quickly. But the load takes ~50-55s on
    # this dataset (55k+ trips, 1.4M+ stop times) — not the "~10s" the old
    # comment assumed. Any request landing during that window called
    # get_transit_data(), which correctly blocked on TransitData's lock
    # rather than double-loading, but blocked for up to ~55s — which blew
    # straight through the AI Assistant's 15s per-request timeout
    # (_plan_trip's asyncio.wait_for(..., timeout=15.0)). The request
    # would then return a "took too long" error to the user while the
    # orphaned background thread kept running and completed successfully
    # 30-40s later, invisibly, after the user already saw a failure.
    #
    # Blocking startup on this call trades ~55s of extra startup time for
    # a guarantee that no request can ever race the cold cache again.
    if app.state.db_connected:
        db = SessionLocal()
        try:
            warm_raptor_cache(db)
        except Exception as e:
            app_logger.error(f"RAPTOR warmup failed during startup: {e}", exc_info=True)
        finally:
            db.close()
    else:
        app_logger.warning("Skipped routing warmup (offline).")

@app.on_event("startup")
async def start_realtime():
    app.state.simulator_task = asyncio.create_task(generate_realtime_updates())

@app.on_event("shutdown")
def shutdown_event():
    app_logger.info("Shutting down FastAPI application...")
    stop_scheduler()
    if hasattr(app.state, 'simulator_task'):
        app.state.simulator_task.cancel()

# Include routers
app.include_router(router)
from .api.fleet import router as fleet_router
app.include_router(fleet_router, prefix="/api/fleet", tags=["Fleet"])
from .api.admin import router as admin_router
app.include_router(admin_router, tags=["Admin"])
from .api.ai import router as ai_router
app.include_router(ai_router, tags=["AI"])
from .api.ai_assistant import router as ai_assistant_router
app.include_router(ai_assistant_router)

setup_exception_handlers(app)

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

@app.get("/")
def read_root():
    return {"message": "Welcome to the Production AI-Driven Smart Transit Optimization API"}

@app.websocket("/ws/transit")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)