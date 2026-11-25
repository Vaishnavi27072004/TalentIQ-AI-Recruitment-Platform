"""Candidate profile + resume endpoints, with ownership checks (scenario 12)."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_roles, get_candidate_for_user
from app.database import get_db
from app.models.tables import (User, Candidate, Resume, Application, Interview, MatchResult,
                               ROLE_ADMIN, ROLE_CANDIDATE, ROLE_INTERVIEWER)
from app.schemas.schemas import CandidateUpdate, NotesUpdate
from app.services import embedding_service
from app.services.resume_pipeline import process_resume

router = APIRouter(prefix="/api/candidates", tags=["Candidates"])


def candidate_to_dict(candidate: Candidate, include_private: bool = True) -> dict:
    data = {
        "id": candidate.id, "name": candidate.name, "email": candidate.email, "phone": candidate.phone,
        "location": candidate.location, "summary": candidate.summary, "education": candidate.education,
        "technical_skills": candidate.technical_skills, "soft_skills": candidate.soft_skills,
        "total_experience_years": candidate.total_experience_years,
        "employment_history": candidate.employment_history, "projects": candidate.projects,
        "certifications": candidate.certifications, "created_at": candidate.created_at,
        "resumes": [{"id": r.id, "filename": r.original_filename, "status": r.status} for r in candidate.resumes],
    }
    if include_private:  # internal notes are only for admins
        data["admin_notes"] = candidate.admin_notes
    return data


def check_can_view_candidate(db: Session, user: User, candidate_id: int) -> Candidate:
    """OWNERSHIP RULES
    admin       -> any candidate
    candidate   -> only their own profile (otherwise 403)
    interviewer -> only candidates they are assigned to interview"""
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(404, "Candidate not found")
    if user.role == ROLE_ADMIN:
        return candidate
    if user.role == ROLE_CANDIDATE:
        if candidate.user_id != user.id:
            raise HTTPException(403, "You can only access your own profile")
        return candidate
    assigned = (db.query(Interview).join(Application, Interview.application_id == Application.id)
                .filter(Interview.interviewer_id == user.id, Application.candidate_id == candidate_id).first())
    if assigned is None:
        raise HTTPException(403, "You are not assigned to interview this candidate")
    return candidate


# ---------- candidate self-service (declared BEFORE /{candidate_id} so 'me' is not read as an id) ----------
@router.get("/me")
def my_profile(user: User = Depends(require_roles(ROLE_CANDIDATE)), db: Session = Depends(get_db)):
    return candidate_to_dict(get_candidate_for_user(db, user), include_private=False)


@router.put("/me")
def update_my_profile(data: CandidateUpdate, user: User = Depends(require_roles(ROLE_CANDIDATE)),
                      db: Session = Depends(get_db)):
    candidate = get_candidate_for_user(db, user)
    apply_profile_update(candidate, data)
    db.commit()
    embedding_service.sync_candidate(candidate)
    return candidate_to_dict(candidate, include_private=False)


@router.post("/me/resume")
async def upload_my_resume(file: UploadFile = File(...), user: User = Depends(require_roles(ROLE_CANDIDATE)),
                           db: Session = Depends(get_db)):
    """Scenario 1: candidate uploads a resume -> profile filled with extracted info."""
    candidate = get_candidate_for_user(db, user)
    resume = process_resume(db, file.filename or "resume", await file.read(), user.id, existing_candidate=candidate)
    if resume.status == "failed":
        raise HTTPException(422, resume.error_message)
    db.refresh(candidate)
    return {"resume_status": resume.status, "profile": candidate_to_dict(candidate, include_private=False)}


# ---------- admin endpoints ----------
@router.post("/bulk-upload", dependencies=[Depends(require_roles(ROLE_ADMIN))])
async def bulk_upload(files: List[UploadFile] = File(...), user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """Scenarios 2 and 3: every file is processed on its own; one bad file never stops the rest."""
    results = []
    for upload in files:
        resume = process_resume(db, upload.filename or "resume", await upload.read(), user.id)
        results.append({"filename": resume.original_filename, "status": resume.status,
                        "error": resume.error_message, "candidate_id": resume.candidate_id})
    return results


@router.get("", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def list_candidates(search: Optional[str] = None, skill: Optional[str] = None, location: Optional[str] = None,
                    min_experience: Optional[float] = None, max_experience: Optional[float] = None,
                    job_id: Optional[int] = None, sort_by_score: bool = False, db: Session = Depends(get_db)):
    """Plain SQL-style filtering (this is NOT semantic search). Optional sort by cached match score for a job."""
    query = db.query(Candidate)
    if search:
        like = f"%{search.lower()}%"
        query = query.filter((Candidate.name.ilike(like)) | (Candidate.email.ilike(like)))
    if location:
        query = query.filter(Candidate.location.ilike(f"%{location}%"))
    if min_experience is not None:
        query = query.filter(Candidate.total_experience_years >= min_experience)
    if max_experience is not None:
        query = query.filter(Candidate.total_experience_years <= max_experience)
    candidates = query.order_by(Candidate.created_at.desc()).all()
    if skill:  # skills live in a JSON column, so filter in Python
        wanted = skill.strip().lower()
        candidates = [c for c in candidates if any(wanted in s.lower() for s in c.technical_skills or [])]

    scores = {}
    if job_id:
        rows = db.query(MatchResult).filter(MatchResult.job_id == job_id).all()
        scores = {row.candidate_id: row.final_score for row in rows}
        if sort_by_score:
            candidates.sort(key=lambda c: scores.get(c.id, -1), reverse=True)
    return [{**candidate_to_dict(c), "match_score": scores.get(c.id)} for c in candidates]


@router.get("/{candidate_id}")
def get_candidate(candidate_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    candidate = check_can_view_candidate(db, user, candidate_id)
    return candidate_to_dict(candidate, include_private=(user.role == ROLE_ADMIN))


@router.put("/{candidate_id}", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def admin_update_candidate(candidate_id: int, data: CandidateUpdate, db: Session = Depends(get_db)):
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(404, "Candidate not found")
    apply_profile_update(candidate, data)
    db.commit()
    embedding_service.sync_candidate(candidate)
    return candidate_to_dict(candidate)


@router.put("/{candidate_id}/notes", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def update_notes(candidate_id: int, data: NotesUpdate, db: Session = Depends(get_db)):
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(404, "Candidate not found")
    candidate.admin_notes = data.admin_notes
    db.commit()
    return {"admin_notes": candidate.admin_notes}


@router.delete("/{candidate_id}", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(404, "Candidate not found")
    db.query(MatchResult).filter(MatchResult.candidate_id == candidate_id).delete()
    db.delete(candidate)
    db.commit()
    embedding_service.remove_candidate(candidate_id)
    return {"deleted": candidate_id}


@router.get("/resumes/{resume_id}/download")
def download_resume(resume_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = db.get(Resume, resume_id)
    if resume is None or resume.candidate_id is None:
        raise HTTPException(404, "Resume not found")
    check_can_view_candidate(db, user, resume.candidate_id)  # same ownership rules as the profile
    return FileResponse(resume.stored_path, filename=resume.original_filename)


def apply_profile_update(candidate: Candidate, data: CandidateUpdate) -> None:
    """Only fields the user actually sent are changed."""
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(candidate, field, value)
