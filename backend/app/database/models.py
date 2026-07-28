from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, BigInteger, Index, func
from sqlalchemy.orm import relationship
from datetime import datetime
from .connection import Base

class Route(Base):
    __tablename__ = "routes"
    
    route_id = Column(String(50), primary_key=True, index=True)
    name = Column(String(255))
    type = Column(String(50))
    route_short_name = Column(String(50))
    route_long_name = Column(String(255))
    
    # Relationships
    features = relationship("RouteFeature", back_populates="route", cascade="all, delete-orphan")
    observations = relationship("TransitObservation", back_populates="route", cascade="all, delete-orphan")
    predictions = relationship("PredictionRecord", back_populates="route", cascade="all, delete-orphan")
    optimizations = relationship("OptimizationResult", back_populates="route", cascade="all, delete-orphan")
    recommendations = relationship("DRLRecommendation", back_populates="route", cascade="all, delete-orphan")

class RouteFeature(Base):
    __tablename__ = "route_features"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(String(50), ForeignKey("routes.route_id"), index=True)
    stop_count = Column(Integer)
    total_distance_km = Column(Float)
    average_duration_mins = Column(Float)
    
    route = relationship("Route", back_populates="features")

class TransitObservation(Base):
    __tablename__ = "transit_observations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    trip_id = Column(String(100), index=True)
    route_id = Column(String(50), ForeignKey("routes.route_id"), index=True)
    stop_id = Column(String(50))
    stop_sequence = Column(Integer)
    scheduled_time = Column(String(50))
    hour = Column(Integer, index=True)
    weekday = Column(String(20))
    weather = Column(String(50))
    temperature = Column(Float)
    rainfall = Column(Float)
    delay_minutes = Column(Float)
    congestion_score = Column(Float)
    passenger_count = Column(Integer)
    
    route = relationship("Route", back_populates="observations")

class PredictionRecord(Base):
    __tablename__ = "prediction_records"
    __table_args__ = {'comment': 'SAFE_TO_DELETE: Replaced by ForecastHistory'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True) # Forecast Generated Timestamp
    target_timestamp = Column(DateTime, default=datetime.utcnow, index=True) # Forecast Target Timestamp
    route_id = Column(String(50), ForeignKey("routes.route_id"), index=True)
    predicted_passengers = Column(Integer)
    confidence_score = Column(Float)
    model_version = Column(String(50))
    
    route = relationship("Route", back_populates="predictions")

    @property
    def route_predicted_passengers(self):
        return self.predicted_passengers

    @route_predicted_passengers.setter
    def route_predicted_passengers(self, value):
        self.predicted_passengers = value


class ForecastHistory(Base):
    """
    Immutable record of generated forecasts (model output).

    NOTE: `PredictionRecord` is the legacy table used by older endpoints.
    New admin dashboard analytics and insights should prefer `ForecastHistory`
    so KPIs are explicitly traceable to forecast pipeline output history.
    """
    __tablename__ = "forecast_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    target_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    route_id = Column(String(50), ForeignKey("routes.route_id"), index=True)
    predicted_passengers = Column(Integer, nullable=False)
    confidence_score = Column(Float, nullable=True)
    model_version = Column(String(80), nullable=True)

    route = relationship("Route")

    @property
    def route_predicted_passengers(self):
        return self.predicted_passengers

    @route_predicted_passengers.setter
    def route_predicted_passengers(self, value):
        self.predicted_passengers = value

class OptimizationResult(Base):
    __tablename__ = "optimization_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    route_id = Column(String(50), ForeignKey("routes.route_id"), index=True)
    route_name = Column(String(255))
    allocated_buses = Column(Integer)
    utilization = Column(Float)
    objective_score = Column(Float)
    predicted_demand = Column(Integer, default=0)
    unserved_demand = Column(Integer, default=0)
    priority_level = Column(String(50), default='MEDIUM')
    recommended_frequency = Column(String(100), default='')
    model_version = Column(String(50), default='catboost-v2')
    
    route = relationship("Route", back_populates="optimizations")

class DRLRecommendation(Base):
    __tablename__ = "drl_recommendations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    route_id = Column(String(50), ForeignKey("routes.route_id"), index=True)
    action = Column(String(255))
    confidence = Column(Float)
    expected_reward = Column(Float)
    
    route = relationship("Route", back_populates="recommendations")

class SystemMetric(Base):
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    metric_name = Column(String(100), index=True)
    metric_value = Column(Float)

class ModelMetadata(Base):
    __tablename__ = "model_metadata"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(100))
    version = Column(String(50))
    trained_at = Column(DateTime, default=datetime.utcnow)
    r2_score = Column(Float)
    rmse = Column(Float)
    mae = Column(Float)
    dataset_size = Column(Integer)
    is_active = Column(Boolean, default=True)

class GTFSStop(Base):
    __tablename__ = "gtfs_stops"
    stop_id = Column(String(50), primary_key=True, index=True)
    stop_name = Column(String(255))
    stop_lat = Column(Float)
    stop_lon = Column(Float)

class GTFSTrip(Base):
    __tablename__ = "gtfs_trips"
    trip_id = Column(String(100), primary_key=True, index=True)
    route_id = Column(String(50), ForeignKey("routes.route_id"), index=True)
    service_id = Column(String(50))
    trip_headsign = Column(String(255))

class GTFSStopTime(Base):
    __tablename__ = "gtfs_stop_times"
    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(String(100), ForeignKey("gtfs_trips.trip_id"), index=True)
    stop_id = Column(String(50), ForeignKey("gtfs_stops.stop_id"), index=True)
    arrival_time = Column(String(20))
    departure_time = Column(String(20))
    stop_sequence = Column(Integer, index=True)

class WeatherRecord(Base):
    __tablename__ = "weather_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, unique=True)
    temperature = Column(Float)
    condition = Column(String(50))
    precipitation = Column(Float, default=0.0)

class DemandHistory(Base):
    __tablename__ = "demand_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(String(50), ForeignKey("routes.route_id"), index=True)
    passenger_count = Column(Integer)
    occupancy_percent = Column(Float)
    weather = Column(String(50))
    traffic = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class FleetAllocation(Base):
    __tablename__ = "fleet_allocations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(String(50), ForeignKey("routes.route_id"), index=True)
    predicted_demand = Column(Integer)
    required_buses = Column(Integer)
    allocated_buses = Column(Integer)
    fleet_gap = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class PeakEvent(Base):
    __tablename__ = "peak_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(String(50), ForeignKey("routes.route_id"), index=True)
    event_type = Column(String(50))
    demand_spike = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_username", "username"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(Text, nullable=False, default="User")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime, default=None, nullable=True)

    # Transit administration fields (kept simple for MVP)
    # - region / depot: used for operational scope assignment in admin UX
    # - mfa_enabled: surfaced in User Administration
    # - is_locked: separate from is_active (lock/unlock is a security control)
    region = Column(Text, nullable=True)
    depot = Column(Text, nullable=True)
    mfa_enabled = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    # When mfa_enabled is true, we require a valid TOTP code during login.
    # Stored as base32 (compatible with authenticator apps).
    mfa_secret = Column(Text, nullable=True)

    # Relationships
    journey_history = relationship("JourneyHistory", back_populates="user", cascade="all, delete-orphan")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_username = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    target_user = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    module = Column(Text, nullable=False, server_default="User Administration")
    status = Column(Text, nullable=False, server_default="success")
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    ip_address = Column(Text, nullable=True)
    detail = Column(Text, nullable=True)


class JourneyHistory(Base):
    """Stores a record every time an authenticated passenger successfully plans a trip."""
    __tablename__ = "journey_history"
    __table_args__ = (
        Index("idx_journey_history_user_id", "user_id"),
        Index("idx_journey_history_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    source_stop_id = Column(String(100), nullable=True)
    source_stop_name = Column(String(255), nullable=True)
    destination_stop_id = Column(String(100), nullable=True)
    destination_stop_name = Column(String(255), nullable=True)
    route_summary = Column(String(500), nullable=True)   # e.g. "Route 401 → Route 500"
    transfer_count = Column(Integer, default=0)
    estimated_duration = Column(Integer, nullable=True)  # in minutes

    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    user = relationship("User", back_populates="journey_history")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(50), nullable=False) # 'aggregation', 'forecasting', 'optimization'
    status = Column(String(50), nullable=False) # 'success', 'failed', 'running'
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    records_processed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)


class PipelineExecutionLog(Base):
    """
    Canonical execution log for batch pipelines (aggregation/forecasting/optimization/etc).
    This replaces placeholder pipeline durations + failure counts in admin dashboards.
    """
    __tablename__ = "pipeline_execution_logs"
    __table_args__ = (
        Index("idx_pipeline_execution_logs_name_started", "pipeline_name", "started_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_name = Column(String(80), nullable=False, index=True)
    status = Column(String(30), nullable=False)  # running | success | failed
    duration_ms = Column(BigInteger, nullable=True)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)


class RouteScope(Base):
    """
    Operational scoping metadata: assigns a route to a region and depot.

    Dashboard filters (region/depot) are enforced by joining through this table.
    """
    __tablename__ = "route_scopes"
    __table_args__ = (
        Index("idx_route_scopes_region_depot", "region", "depot"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(String(50), ForeignKey("routes.route_id"), nullable=False, index=True)
    region = Column(Text, nullable=True, index=True)
    depot = Column(Text, nullable=True, index=True)
    assigned_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    route = relationship("Route")


class RoutePlanLog(Base):
    """
    Records route planning outcomes so route efficiency KPIs are traceable to
    actual routing computations (not mocked values).
    """
    __tablename__ = "route_plan_logs"
    __table_args__ = (
        Index("idx_route_plan_logs_route_ts", "route_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    route_id = Column(String(50), nullable=True, index=True)
    source_stop_id = Column(String(100), nullable=True)
    destination_stop_id = Column(String(100), nullable=True)

    route_efficiency = Column(Integer, nullable=False)  # 0-100
    transfers_count = Column(Integer, nullable=True)
    eta_minutes = Column(Float, nullable=True)
    traffic = Column(String(30), nullable=True)
    weather = Column(String(30), nullable=True)
