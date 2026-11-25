"""Load the fictional jobs and valid sample resumes into the local demo database."""

import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models.tables import Candidate, Job, Resume, User
from app.services import embedding_service
from app.services.resume_parser import (
    extract_resume_text,
    normalize_email,
    parse_resume_locally,
)
from app.services.resume_pipeline import apply_parsed_data, save_upload
from seed_demo_users import ensure_demo_users


SAMPLE_DATA_DIR = Path(__file__).resolve().parents[1] / "sample_data"
SAMPLE_JOB_PATTERN = re.compile(
    r"^## \d+\.\s*(.+?)\s*\n(.*?)(?=^## \d+\.|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _field(section: str, label: str) -> str:
    match = re.search(rf"^- \*\*{re.escape(label)}:\*\*\s*(.+)$", section, re.MULTILINE)
    if match is None:
        raise ValueError(f"Sample job is missing the '{label}' field.")
    return match.group(1).strip()


def _parse_sample_jobs(jobs_file: Path) -> list[dict[str, Any]]:
    content = jobs_file.read_text(encoding="utf-8")
    jobs = []
    for match in SAMPLE_JOB_PATTERN.finditer(content):
        title, section = match.groups()
        experience = re.search(r"(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)\s*years", _field(section, "Experience"), re.I)
        location = re.search(r"\*\*Location:\*\*\s*([^|]+)", section)
        employment_type = re.search(r"\*\*Type:\*\*\s*([^|]+)", section)
        status = re.search(r"\*\*Status:\*\*\s*([^\s|]+)", section)
        if experience is None or location is None or employment_type is None or status is None:
            raise ValueError(f"Sample job '{title}' has invalid experience or location details.")
        jobs.append(
            {
                "title": title.strip(),
                "description": _field(section, "Description"),
                "required_skills": [skill.strip() for skill in _field(section, "Required skills").split(",")],
                "preferred_skills": [skill.strip() for skill in _field(section, "Preferred skills").split(",")],
                "min_experience": float(experience.group(1)),
                "max_experience": float(experience.group(2)),
                "education_requirement": _field(section, "Education"),
                "location": location.group(1).strip(),
                "employment_type": employment_type.group(1).strip(),
                "status": status.group(1).strip(),
            }
        )
    if not jobs:
        raise ValueError(f"No sample jobs found in {jobs_file}.")
    return jobs


def _upsert_jobs(db: Session, data_dir: Path) -> int:
    created = 0
    for values in _parse_sample_jobs(data_dir / "sample_jobs.md"):
        job = db.query(Job).filter(Job.title == values["title"]).first()
        if job is None:
            job = Job(**values)
            db.add(job)
            db.flush()
            created += 1
        else:
            for field, value in values.items():
                setattr(job, field, value)
        embedding_service.sync_job(job)
    return created


def _load_sample_resumes(
    db: Session,
    data_dir: Path,
    admin: User,
    stored_files: list[Path],
) -> tuple[int, int]:
    candidates_created = 0
    resumes_created = 0
    for resume_file in sorted((data_dir / "resumes").glob("*.docx")):
        parsed = parse_resume_locally(extract_resume_text(str(resume_file)))
        email = normalize_email(parsed.email)
        if not email:
            raise ValueError(f"No email found in sample resume {resume_file.name}.")

        candidate = db.query(Candidate).filter(Candidate.email == email).first()
        if candidate is None:
            candidate = Candidate(email=email)
            apply_parsed_data(candidate, parsed, keep_identity=False)
            db.add(candidate)
            db.flush()
            candidates_created += 1

        existing_resume = db.query(Resume).filter(Resume.candidate_id == candidate.id).first()
        if existing_resume is not None:
            embedding_service.sync_candidate(candidate)
            continue

        stored_path = Path(save_upload(resume_file.name, resume_file.read_bytes()))
        stored_files.append(stored_path)
        db.add(
            Resume(
                candidate_id=candidate.id,
                original_filename=resume_file.name,
                stored_path=str(stored_path),
                status="completed",
                uploaded_by=admin.id,
            )
        )
        db.flush()
        embedding_service.sync_candidate(candidate)
        resumes_created += 1
    return candidates_created, resumes_created


def load_demo_data(db: Session, data_dir: Path = SAMPLE_DATA_DIR) -> dict[str, int]:
    """Seed missing users, sample jobs, and valid resumes; safe to run repeatedly."""
    stored_files: list[Path] = []
    try:
        accounts_created = ensure_demo_users(db)
        admin = db.query(User).filter(User.email == "admin@demo.com").one()
        jobs_created = _upsert_jobs(db, data_dir)
        candidates_created, resumes_created = _load_sample_resumes(db, data_dir, admin, stored_files)
        db.commit()
    except Exception:
        db.rollback()
        for stored_file in stored_files:
            stored_file.unlink(missing_ok=True)
        raise
    return {
        "accounts_created": accounts_created,
        "jobs_created": jobs_created,
        "candidates_created": candidates_created,
        "resumes_created": resumes_created,
    }


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        counts = load_demo_data(db)
    summary = ", ".join(f"{key.replace('_created', '')} {value}" for key, value in counts.items())
    print(f"Demo data ready: {summary}.")


if __name__ == "__main__":
    main()
