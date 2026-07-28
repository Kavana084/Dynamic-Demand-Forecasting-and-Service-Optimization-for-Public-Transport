from typing import Optional, List, Dict

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import engine
from app.database.models import User, JourneyHistory
from app.services.auth_service import get_password_hash, verify_password


SEED_USERS = [
    {"username": "admin", "password": "admin123", "role": "Admin"},
    {"username": "operator", "password": "operator123", "role": "Operator"},
    {"username": "viewer", "password": "viewer123", "role": "Viewer"},
]


def normalize_username(username: str) -> str:
    return username.strip().lower()


def user_to_dict(user: User) -> Dict:
    return {
        "id": user.id,
        "username": user.username,
        "hashed_password": user.password_hash,
        "role": user.role,
        "created_at": user.created_at,
    }


def get_user_by_username(db: Session, username: str) -> Optional[Dict]:
    normalized_username = normalize_username(username)
    user = db.query(User).filter(User.username == normalized_username).first()
    return user_to_dict(user) if user else None


def create_user(db: Session, username: str, password: str, role: str = "User") -> Dict:
    normalized_username = normalize_username(username)

    if not normalized_username:
        raise ValueError("Username is required")

    if not password:
        raise ValueError("Password is required")

    if get_user_by_username(db, normalized_username):
        raise ValueError("Username already exists")

    user = User(
        username=normalized_username,
        password_hash=get_password_hash(password),
        role=role,
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Username already exists") from exc

    db.refresh(user)
    return user_to_dict(user)


def authenticate_user(db: Session, username: str, password: str) -> Optional[Dict]:
    user = get_user_by_username(db, username)
    if not user:
        return None

    if not verify_password(password, user["hashed_password"]):
        return None

    return user


def list_users(db: Session) -> List[Dict]:
    users = db.query(User).order_by(User.created_at.asc(), User.id.asc()).all()
    return [user_to_dict(user) for user in users]


def ensure_users_table_and_seed() -> None:
    User.__table__.create(bind=engine, checkfirst=True)
    JourneyHistory.__table__.create(bind=engine, checkfirst=True)


def seed_existing_users(db: Session) -> None:
    for user in SEED_USERS:
        if get_user_by_username(db, user["username"]):
            continue
        create_user(db, user["username"], user["password"], user["role"])
