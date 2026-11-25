"""Create the documented fictional demo accounts."""
from app.database import Base, engine, SessionLocal
from app.models.tables import User, Candidate
from app.auth import hash_password


Base.metadata.create_all(bind=engine)
db = SessionLocal()

accounts = [
    ("admin@demo.com", "Demo Admin", "Admin@12345", "admin"),
    ("interviewer1@demo.com", "Interviewer One", "Interview@123", "interviewer"),
    ("interviewer2@demo.com", "Interviewer Two", "Interview@123", "interviewer"),
    ("candidate@demo.com", "Demo Candidate", "Candidate@123", "candidate"),
]

for email, full_name, password, role in accounts:
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
    if role == "candidate":
        candidate = db.query(Candidate).filter(Candidate.email == email).first()
        if candidate is None:
            db.add(Candidate(user_id=user.id, name=full_name, email=email))

db.commit()
db.close()
print("Demo users ready.")
