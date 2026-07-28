from sqlalchemy.orm import Session
import secrets
import string
from app.database.models import User, AuditLog
from fastapi import HTTPException
from app.services.auth_service import get_password_hash

class AdminUserService:
    @staticmethod
    def _log_action(
        db: Session,
        admin_username: str,
        action: str,
        target_user: str,
        previous: str = None,
        new: str = None,
        ip_address: str = None,
        module: str = "User Administration",
        status: str = "success",
        detail: str = None,
    ):
        log = AuditLog(
            admin_username=admin_username,
            action=action,
            target_user=target_user,
            module=module,
            status=status,
            previous_value=previous,
            new_value=new,
            ip_address=ip_address,
            detail=detail,
        )
        db.add(log)
        db.commit()

    @staticmethod
    def get_all_users(db: Session):
        users = db.query(User).filter(User.deleted_at == None).all()
        return [{
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "is_active": u.is_active,
            "region": getattr(u, "region", None),
            "depot": getattr(u, "depot", None),
            "mfa_enabled": bool(getattr(u, "mfa_enabled", False)),
            "is_locked": bool(getattr(u, "is_locked", False)),
            "created_at": u.created_at,
        } for u in users]

    @staticmethod
    def create_user(db: Session, admin_username: str, username: str, role: str, ip_address: str = None):
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # generate random temp password
        temp_pwd = ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(12))
        
        user = User(
            username=username,
            password_hash=get_password_hash(temp_pwd),
            role=role,
            is_active=True
        )
        db.add(user)
        db.commit()
        
        AdminUserService._log_action(
            db,
            admin_username,
            "User Created",
            username,
            None,
            f"Role: {role}",
            ip_address,
            detail="Created a new user account and assigned an initial role.",
        )

        # Do not return secrets (no temporary password display in admin UI)
        return {"status": "success", "username": username}

    @staticmethod
    def toggle_user_status(db: Session, admin_username: str, user_id: int, is_active: bool, ip_address: str = None):
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        prev = "Enabled" if user.is_active else "Disabled"
        new_val = "Enabled" if is_active else "Disabled"
        
        user.is_active = is_active
        db.commit()
        
        action = "User Enabled" if is_active else "User Disabled"
        AdminUserService._log_action(
            db,
            admin_username,
            action,
            user.username,
            prev,
            new_val,
            ip_address,
            detail="Changed user activation status (affects ability to sign in).",
        )
        return {"status": "success"}

    @staticmethod
    def change_role(db: Session, admin_username: str, user_id: int, new_role: str, ip_address: str = None):
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        prev = user.role
        user.role = new_role
        db.commit()
        
        AdminUserService._log_action(
            db,
            admin_username,
            "Role Updated",
            user.username,
            prev,
            new_role,
            ip_address,
            detail="Updated the user's role for module-level permissions.",
        )
        return {"status": "success"}

    @staticmethod
    def send_reset_link(db: Session, admin_username: str, user_id: int, ip_address: str = None):
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # For MVP we don't integrate with an email provider. We still log the action
        # and return a safe success response for the UI workflow.
        AdminUserService._log_action(
            db,
            admin_username,
            "Reset Link Sent",
            user.username,
            None,
            None,
            ip_address,
            detail="Triggered a password reset link workflow (no password revealed).",
        )
        return {"status": "success"}

    @staticmethod
    def set_scope(db: Session, admin_username: str, user_id: int, region: str = None, depot: str = None, ip_address: str = None):
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        prev = f"Region: {getattr(user, 'region', None) or '—'} | Depot: {getattr(user, 'depot', None) or '—'}"
        setattr(user, "region", region)
        setattr(user, "depot", depot)
        db.commit()

        new_val = f"Region: {region or '—'} | Depot: {depot or '—'}"
        AdminUserService._log_action(
            db,
            admin_username,
            "Scope Updated",
            user.username,
            prev,
            new_val,
            ip_address,
            detail="Updated operational scope assignment (region/depot).",
        )
        return {"status": "success"}

    @staticmethod
    def set_mfa(db: Session, admin_username: str, user_id: int, mfa_enabled: bool, ip_address: str = None):
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        prev = "Enabled" if bool(getattr(user, "mfa_enabled", False)) else "Disabled"
        setattr(user, "mfa_enabled", bool(mfa_enabled))
        db.commit()

        new_val = "Enabled" if bool(mfa_enabled) else "Disabled"
        AdminUserService._log_action(
            db,
            admin_username,
            "MFA Updated",
            user.username,
            prev,
            new_val,
            ip_address,
            detail="Updated MFA status for the user account.",
        )
        return {"status": "success"}

    @staticmethod
    def set_lock(db: Session, admin_username: str, user_id: int, is_locked: bool, ip_address: str = None):
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        prev = "Locked" if bool(getattr(user, "is_locked", False)) else "Unlocked"
        setattr(user, "is_locked", bool(is_locked))
        db.commit()

        new_val = "Locked" if bool(is_locked) else "Unlocked"
        AdminUserService._log_action(
            db,
            admin_username,
            "Account Lock Updated",
            user.username,
            prev,
            new_val,
            ip_address,
            detail="Locked/unlocked the account (security control).",
        )
        return {"status": "success"}

    @staticmethod
    def soft_delete_user(db: Session, admin_username: str, user_id: int, ip_address: str = None):
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        from datetime import datetime
        user.deleted_at = datetime.utcnow()
        user.is_active = False # Ensures soft deleted users are also disabled
        db.commit()
        
        AdminUserService._log_action(
            db,
            admin_username,
            "User Deactivated",
            user.username,
            None,
            "Deleted",
            ip_address,
            detail="Soft-deleted the user and disabled sign-in.",
        )
        return {"status": "success"}

    @staticmethod
    def get_audit_logs(
        db: Session,
        q: str = None,
        user: str = None,
        module: str = None,
        status: str = None,
        date_from=None,
        date_to=None,
        limit: int = 500,
    ):
        query = db.query(AuditLog)

        if user:
            query = query.filter(AuditLog.admin_username == user)

        if module:
            query = query.filter(AuditLog.module == module)

        if status:
            query = query.filter(AuditLog.status == status)

        if date_from is not None:
            query = query.filter(AuditLog.timestamp >= date_from)

        if date_to is not None:
            query = query.filter(AuditLog.timestamp <= date_to)

        if q:
            # Simple cross-field search. Use ilike when supported; fall back to like.
            like = f"%{q}%"
            try:
                query = query.filter(
                    (AuditLog.action.ilike(like))
                    | (AuditLog.target_user.ilike(like))
                    | (AuditLog.module.ilike(like))
                    | (AuditLog.admin_username.ilike(like))
                )
            except Exception:
                query = query.filter(
                    (AuditLog.action.like(like))
                    | (AuditLog.target_user.like(like))
                    | (AuditLog.module.like(like))
                    | (AuditLog.admin_username.like(like))
                )

        logs = query.order_by(AuditLog.timestamp.desc()).limit(max(1, min(2000, limit))).all()
        return logs
