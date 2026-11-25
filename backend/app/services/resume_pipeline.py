"""Glue code: one function that runs the whole resume pipeline for ONE file.

process_resume() never raises for a bad resume. It records status on the Resume row
(completed / failed / duplicate) so a bulk upload keeps going when one file is broken.
"""
import uuid
import os
from pathlib import Path
from sqlalchemy.orm import Session

from app.config import settings
from app.models.tables import Candidate, Resume
from app.services import embedding_service
from app.services.resume_parser import (ResumeError, validate_resume_file, extract_resume_text,
                                        parse_resume, normalize_email)


def save_upload(filename: str, file_bytes: bytes) -> str:
    """Store the file under a random name so user-supplied names can never overwrite or traverse paths."""
    extension = Path(filename).suffix.lower()
    stored_path = Path(settings.upload_dir) / f"{uuid.uuid4().hex}{extension}"
    stored_path.write_bytes(file_bytes)
    return str(stored_path)


def apply_parsed_data(candidate: Candidate, parsed, keep_identity: bool) -> None:
    """Copy parsed fields onto the candidate row. keep_identity=True keeps account name/email."""
    if not keep_identity or not candidate.name:
        candidate.name = parsed.name or candidate.name
    candidate.phone = parsed.phone or candidate.phone
    candidate.location = parsed.location or candidate.location
    candidate.summary = parsed.summary or candidate.summary
    candidate.education = ([item.model_dump() for item in parsed.education]
                           or candidate.education or [])
    candidate.technical_skills = parsed.technical_skills or candidate.technical_skills or []
    candidate.soft_skills = parsed.soft_skills or candidate.soft_skills or []
    if parsed.total_experience_years is not None:
        candidate.total_experience_years = parsed.total_experience_years
    candidate.employment_history = ([item.model_dump() for item in parsed.employment_history]
                                    or candidate.employment_history or [])
    candidate.projects = ([item.model_dump() for item in parsed.projects]
                          or candidate.projects or [])
    candidate.certifications = parsed.certifications or candidate.certifications or []


def process_resume(db: Session, filename: str, file_bytes: bytes, uploaded_by: int,
                   existing_candidate: Candidate | None = None) -> Resume:
    resume = Resume(original_filename=filename, stored_path="", status="processing", uploaded_by=uploaded_by)
    db.add(resume)
    try:
        validate_resume_file(filename, file_bytes)  # type + size + empty check
        resume.stored_path = save_upload(filename, file_bytes)
        text = extract_resume_text(resume.stored_path)
        parsed = parse_resume(text)

        if existing_candidate is not None:  # candidate uploading their OWN resume
            candidate = existing_candidate
            apply_parsed_data(candidate, parsed, keep_identity=True)
        else:  # admin bulk upload: identify the person by normalised email
            email = normalize_email(parsed.email)
            if not email:
                raise ResumeError("No email address found in the resume, cannot identify the candidate.")
            if db.query(Candidate).filter(Candidate.email == email).first():
                resume.status = "duplicate"
                resume.error_message = f"A candidate with email {email} already exists."
                if resume.stored_path and os.path.exists(resume.stored_path):
                    os.remove(resume.stored_path)
                db.commit()
                return resume
            candidate = Candidate(email=email)
            apply_parsed_data(candidate, parsed, keep_identity=False)
            db.add(candidate)

        db.flush()  # gives candidate an id
        resume.candidate_id = candidate.id
        embedding_service.sync_candidate(candidate)  # keep Chroma in step with SQLite
        resume.status = "completed"
    except ResumeError as error:
        resume.status, resume.error_message = "failed", str(error)
        if resume.stored_path and os.path.exists(resume.stored_path):
            os.remove(resume.stored_path)
    except Exception as error:  # unexpected problem: record it, do not crash the batch
        resume.status, resume.error_message = "failed", f"Unexpected error: {error}"
        if resume.stored_path and os.path.exists(resume.stored_path):
            os.remove(resume.stored_path)
    db.commit()
    return resume
