from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from collections import defaultdict
from jose import jwt, JWTError

from app.auth import (hash_password, verify_password, create_access_token, get_current_user, require_roles)
from app.database import get_db
from app.models.tables import User, Candidate, ROLE_CANDIDATE, ROLE_ADMIN, ROLE_INTERVIEWER
from app.config import settings
from app.schemas.schemas import (RegisterRequest, LoginRequest, TokenResponse, UserCreateByAdmin,
                                 PasswordResetRequest, PasswordResetConfirm)
from app.services.resume_parser import normalize_email
from app.services.notification_service import notify

router = APIRouter(prefix="/api/auth", tags=["Auth"])

_login_attempts: dict[str, list[datetime]] = defaultdict(list)


def check_login_attempts(email: str) -> None:
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=settings.login_attempt_window_seconds)
    attempts = [attempted_at for attempted_at in _login_attempts[email] if attempted_at > cutoff]
    _login_attempts[email] = attempts
    if len(attempts) >= settings.login_max_attempts:
        raise HTTPException(429, "Too many login attempts. Try again later.")


def token_for(user: User) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(user), role=user.role, full_name=user.full_name)


@router.post("/register", response_model=TokenResponse)
def register_candidate(data: RegisterRequest, db: Session = Depends(get_db)):
    """Public registration is for CANDIDATES only. Admin/interviewer accounts are created by an admin."""
    email = normalize_email(data.email)
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=email, full_name=data.full_name, password_hash=hash_password(data.password), role=ROLE_CANDIDATE)
    db.add(user)
    db.flush()
    # If an admin already uploaded this person's resume, link the account to that profile.
    candidate = db.query(Candidate).filter(Candidate.email == email).first()
    if candidate and candidate.user_id is None:
        candidate.user_id = user.id
    elif candidate is None:
        db.add(Candidate(user_id=user.id, name=data.full_name, email=email))
    db.commit()
    return token_for(user)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    email = normalize_email(data.email)
    check_login_attempts(email)
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(data.password, user.password_hash):
        _login_attempts[email].append(datetime.utcnow())
        raise HTTPException(401, "Incorrect email or password")
    _login_attempts.pop(email, None)
    return token_for(user)


@router.post("/login-form", include_in_schema=False)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Lets the Swagger 'Authorize' button work."""
    email = normalize_email(form.username)
    check_login_attempts(email)
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(form.password, user.password_hash):
        _login_attempts[email].append(datetime.utcnow())
        raise HTTPException(401, "Incorrect email or password")
    _login_attempts.pop(email, None)
    return {"access_token": create_access_token(user), "token_type": "bearer"}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}


@router.post("/password-reset/request")
def request_password_reset(data: PasswordResetRequest, db: Session = Depends(get_db)):
    """Issue a short-lived reset token and deliver it through the configured notification channel."""
    user = db.query(User).filter(User.email == normalize_email(data.email)).first()
    if user:
        expires = datetime.utcnow() + timedelta(minutes=30)
        token = jwt.encode(
            {"sub": str(user.id), "purpose": "password-reset", "exp": expires},
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )
        notify(db, user.id, user.email, "Password reset request",
              f"Your password reset token is: {token}\nIt expires in 30 minutes.")
        db.commit()
    # Do not reveal whether an account exists.
    return {"message": "If the email exists, password reset instructions have been sent."}


@router.post("/password-reset/confirm")
def confirm_password_reset(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(data.token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("purpose") != "password-reset":
            raise JWTError("Wrong token purpose")
        user_id = int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError):
        raise HTTPException(400, "Invalid or expired reset token")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(400, "Invalid or expired reset token")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "Password updated successfully"}


@router.post("/users", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def create_staff_user(data: UserCreateByAdmin, db: Session = Depends(get_db)):
    if data.role not in (ROLE_ADMIN, ROLE_INTERVIEWER):
        raise HTTPException(400, "Role must be admin or interviewer")
    email = normalize_email(data.email)
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=email, full_name=data.full_name, password_hash=hash_password(data.password), role=data.role)
    db.add(user)
    db.commit()
    return {"id": user.id, "email": user.email, "role": user.role}


@router.get("/interviewers", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def list_interviewers(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role == ROLE_INTERVIEWER).all()
    return [{"id": u.id, "full_name": u.full_name, "email": u.email} for u in users]
