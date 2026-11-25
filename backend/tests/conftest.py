"""Test setup. Uses a throw-away SQLite DB and replaces the two things that need internet / big
downloads (the LLM call and the embedding model) with small fakes, so tests run offline in seconds.
The matching maths, auth, ownership checks and workflow are tested for real."""
import io
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["CHROMA_DIR"] = f"{_tmp}/chroma"
os.environ["SECRET_KEY"] = "test-secret"

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models.tables import User
from app.auth import hash_password
from app.schemas.schemas import ParsedResume
from app.services import embedding_service, resume_pipeline


def make_docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def fresh_database_and_fakes(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add_all([
        User(email="admin@test.com", full_name="Admin", password_hash=hash_password("Admin@12345"), role="admin"),
        User(email="int@test.com", full_name="Interviewer One", password_hash=hash_password("Interview@1"), role="interviewer"),
        User(email="int2@test.com", full_name="Interviewer Two", password_hash=hash_password("Interview@2"), role="interviewer"),
    ])
    db.commit()
    db.close()

    # --- fake LLM: reads the resume text and returns a parsed object (no network) ---
    def fake_parse_resume(text: str) -> ParsedResume:
        lines = dict(line.split(":", 1) for line in text.splitlines() if ":" in line)
        return ParsedResume(
            name=lines.get("Name", "").strip() or None, email=lines.get("Email", "").strip() or None,
            technical_skills=[s.strip() for s in lines.get("Skills", "").split(",") if s.strip()],
            total_experience_years=float(lines.get("Years", "0") or 0),
            education=[{"degree": lines.get("Degree", "").strip(), "institution": "Test University"}],
            summary="Test summary")
    monkeypatch.setattr(resume_pipeline, "parse_resume", fake_parse_resume)

    # --- fake embeddings: no model download ---
    monkeypatch.setattr(embedding_service, "sync_candidate", lambda c: None)
    monkeypatch.setattr(embedding_service, "remove_candidate", lambda cid: None)
    monkeypatch.setattr(embedding_service, "sync_job", lambda j: None)
    monkeypatch.setattr(embedding_service, "remove_job", lambda jid: None)
    monkeypatch.setattr(embedding_service, "cosine_similarity_candidate_job", lambda cid, jid: 0.5)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def login(client, email, password):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers(client):
    return login(client, "admin@test.com", "Admin@12345")


@pytest.fixture
def interviewer_headers(client):
    return login(client, "int@test.com", "Interview@1")


def register_candidate(client, name, email):
    response = client.post("/api/auth/register", json={"full_name": name, "email": email, "password": "Password@123"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


RESUME_TEXT = ("Name: {name}\nEmail: {email}\nSkills: Python, SQL, Machine Learning\nYears: {years}\n"
               "Degree: B.Sc Computer Science\nThis is a fictional test resume with enough text to pass validation.")


def resume_file(name="Test Person", email="test.person@example.com", years=3):
    return ("resume.docx", make_docx_bytes(RESUME_TEXT.format(name=name, email=email, years=years)),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


JOB_PAYLOAD = {
    "title": "Data Analyst", "description": "Analyse data and build dashboards for the business team.",
    "required_skills": ["Python", "SQL", "Power BI"], "preferred_skills": ["Machine Learning"],
    "min_experience": 2, "max_experience": 5, "education_requirement": "Bachelor's degree",
    "location": "Pune", "employment_type": "Full-time", "status": "active",
}
