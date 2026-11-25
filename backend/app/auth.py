"""Password hashing, JWT tokens and role/ownership dependencies.

Interview explanation:
- Passwords are hashed with bcrypt (one-way, salted) - we never store plain text.
- On login we issue a JWT containing the user id; the frontend sends it in the
  Authorization header; get_current_user decodes it on every protected request.
- require_roles(...) is a small guard that returns 403 for the wrong role.
"""
from datetime import datetime, timedelta
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.tables import User, Candidate

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login-form")


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), password_hash.encode())


def create_access_token(user: User) -> str:
    expires = datetime.utcnow() + timedelta(minutes=settings.token_expire_minutes)
    payload = {"sub": str(user.id), "role": user.role, "exp": expires}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise credentials_error
    user = db.get(User, user_id)
    if user is None:
        raise credentials_error
    return user


def require_roles(*allowed_roles: str):
    """Usage: Depends(require_roles("admin")) on a route."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission for this action")
        return user
    return checker


def get_candidate_for_user(db: Session, user: User) -> Candidate:
    """The candidate profile that belongs to a logged-in candidate user."""
    candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
    if candidate is None:
        raise HTTPException(404, "Candidate profile not found")
    return candidate
