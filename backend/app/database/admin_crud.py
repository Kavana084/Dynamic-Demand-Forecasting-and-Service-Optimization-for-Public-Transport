from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from passlib.context import CryptContext
import secrets

from . import models

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

# --- User Management ---
def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).filter(models.User.deleted_at == None).offset(skip).limit(limit).all()

def create_user(db: Session, username: str, role: str, admin_username: str, ip_address: str):
    temp_password = secrets.token_urlsafe(12)
    db_user = models.User(
        username=username,
        password_hash=get_password_hash(temp_password),
        role=role,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Audit log
    audit = models.AuditLog(
        admin_username=admin_username,
        action="CREATE_USER",
        target_user=username,
        new_value=role,
        ip_address=ip_address
    )
    db.add(audit)
    db.commit()
    
    return db_user, temp_password

def update_user_status(db: Session, username: str, is_active: bool, admin_username: str, ip_address: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if user:
        prev_status = str(user.is_active)
        user.is_active = is_active
        
        audit = models.AuditLog(
            admin_username=admin_username,
            action="ENABLE_USER" if is_active else "DISABLE_USER",
            target_user=username,
            previous_value=prev_status,
            new_value=str(is_active),
            ip_address=ip_address
        )
        db.add(audit)
        db.commit()
    return user

def change_user_role(db: Session, username: str, new_role: str, admin_username: str, ip_address: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if user:
        prev_role = user.role
        user.role = new_role
        
        audit = models.AuditLog(
            admin_username=admin_username,
            action="CHANGE_ROLE",
            target_user=username,
            previous_value=prev_role,
            new_value=new_role,
            ip_address=ip_address
        )
        db.add(audit)
        db.commit()
    return user

def reset_user_password(db: Session, username: str, admin_username: str, ip_address: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if user:
        temp_password = secrets.token_urlsafe(12)
        user.password_hash = get_password_hash(temp_password)
        
        audit = models.AuditLog(
            admin_username=admin_username,
            action="RESET_PASSWORD",
            target_user=username,
            ip_address=ip_address
        )
        db.add(audit)
        db.commit()
        return temp_password
    return None

def soft_delete_user(db: Session, username: str, admin_username: str, ip_address: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if user:
        user.deleted_at = datetime.utcnow()
        user.is_active = False
        
        audit = models.AuditLog(
            admin_username=admin_username,
            action="SOFT_DELETE",
            target_user=username,
            ip_address=ip_address
        )
        db.add(audit)
        db.commit()
    return user

def get_audit_logs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()

# --- AI & Analytics ---
def get_ai_performance(db: Session):
    model_meta = db.query(models.ModelMetadata).order_by(models.ModelMetadata.trained_at.desc()).first()
    if model_meta:
        return {
            "rmse": model_meta.rmse,
            "mae": model_meta.mae,
            "version": model_meta.version,
            "featureImportance": "Feature Importance Unavailable" # As CatBoost importances aren't stored in DB directly
        }
    return None

def get_optimization_insights(db: Session, limit: int = 20):
    # Retrieve the latest optimization results
    results = db.query(models.OptimizationResult).order_by(models.OptimizationResult.timestamp.desc()).limit(limit).all()
    out = []
    for r in results:
        reasoning = "Optimization reasoning unavailable."
        # If there's reasoning in future fields, it can be mapped here. Currently none exists in the model schema.
        out.append({
            "route_id": r.route_id,
            "route_name": r.route_name,
            "predicted_demand": r.predicted_demand,
            "allocated_buses": r.allocated_buses,
            "fleet_gap": r.unserved_demand, # or calculated gap
            "utilization": r.utilization,
            "explainability": reasoning
        })
    return out

def get_historical_monitoring(db: Session):
    # Forecast Accuracy Trend, RMSE Trend, Prediction Volume Trend, Optimization Run Trend
    return {
        "forecastAccuracyTrend": [], # Compute from prediction_records vs demand_history if aligned
        "rmseTrend": [], # from model_metadata history
        "predictionVolumeTrend": [],
        "optimizationRunTrend": []
    }

