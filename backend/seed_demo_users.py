"""Create the documented fictional demo accounts."""
from sqlalchemy.orm import Session

from app.database import Base, engine, SessionLocal
from app.models.tables import User, Candidate
from app.auth import hash_password


DEMO_ACCOUNTS = [
    ("admin@demo.com", "Demo Admin", "Admin@12345", "admin"),
    ("interviewer1@demo.com", "Interviewer One", "Interview@123", "interviewer"),
    ("interviewer2@demo.com", "Interviewer Two", "Interview@123", "interviewer"),
    ("candidate@demo.com", "Demo Candidate", "Candidate@123", "candidate"),
]


def ensure_demo_users(db: Session) -> int:
    """Create missing fictional demo accounts and return the number added."""
    created = 0
    for email, full_name, password, role in DEMO_ACCOUNTS:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                role=role,
            )
            db.add(user)
            db.flush()
            created += 1
        if role == "candidate":
            candidate = db.query(Candidate).filter(Candidate.email == email).first()
            if candidate is None:
                db.add(Candidate(user_id=user.id, name=full_name, email=email))
    return created


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        created = ensure_demo_users(db)
        db.commit()
    print(f"Demo users ready ({created} created).")


if __name__ == "__main__":
    main()
