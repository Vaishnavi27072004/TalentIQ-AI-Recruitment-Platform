"""Shortlisting (human-controlled), interview approval, CSV/Excel export and secure sharing."""
import io
from datetime import timedelta, datetime
from typing import Optional
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.config import settings
from app.database import get_db
from app.models.tables import (Job, Candidate, Application, MatchResult, APP_APPLIED, APP_SHORTLISTED, APP_APPROVED,
                               ROLE_ADMIN)
from app.routes.job_routes import application_to_dict
from app.schemas.schemas import ShortlistRequest
from app.services.notification_service import notify

router = APIRouter(prefix="/api/shortlist", tags=["Shortlisting"])
public_router = APIRouter(prefix="/api/shared", tags=["Shared shortlist"])

SHARE_LINK_HOURS = 48
admin_only = [Depends(require_roles(ROLE_ADMIN))]


@router.post("", dependencies=admin_only)
def shortlist_candidates(data: ShortlistRequest, db: Session = Depends(get_db)):
    """Scenario 8: single or bulk shortlist for ONE job. Creates the application if the admin
    shortlists someone who has not applied (e.g. found through search)."""
    job = db.get(Job, data.job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    done = []
    for candidate_id in data.candidate_ids:
        candidate = db.get(Candidate, candidate_id)
        if candidate is None:
            continue
        application = db.query(Application).filter_by(job_id=job.id, candidate_id=candidate_id).first()
        if application is None:
            application = Application(job_id=job.id, candidate_id=candidate_id)
            db.add(application)
        if application.shortlisted:
            continue  # already shortlisted, do not send a second email
        application.shortlisted, application.status = True, APP_SHORTLISTED
        notify(db, candidate.user_id, candidate.email, f"You have been shortlisted: {job.title}",
               f"Hi {candidate.name}, you have been shortlisted for {job.title}. We will contact you about next steps.")
        db.flush()
        done.append(candidate_id)
    db.commit()
    return {"shortlisted_candidate_ids": done}


@router.delete("/{application_id}", dependencies=admin_only)
def remove_from_shortlist(application_id: int, db: Session = Depends(get_db)):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(404, "Application not found")
    application.shortlisted, application.status = False, APP_APPLIED
    db.commit()
    return application_to_dict(application)


@router.get("", dependencies=admin_only)
def get_shortlist(job_id: Optional[int] = None, db: Session = Depends(get_db)):
    return shortlist_rows(db, job_id)


@router.post("/{application_id}/approve", dependencies=admin_only)
def approve_for_interview(application_id: int, db: Session = Depends(get_db)):
    """Scenario 9: approving sends the candidate an interview notification."""
    application = db.get(Application, application_id)
    if application is None or not application.shortlisted:
        raise HTTPException(400, "Only shortlisted candidates can be approved for interview")
    application.status = APP_APPROVED
    candidate = application.candidate
    result = notify(db, candidate.user_id, candidate.email, f"Approved for interview: {application.job.title}",
                    f"Hi {candidate.name}, you are approved for an interview for {application.job.title}. Scheduling details will follow.")
    db.commit()
    return {**application_to_dict(application), "email_status": result}


def shortlist_rows(db: Session, job_id: Optional[int]) -> list[dict]:
    query = db.query(Application).filter(Application.shortlisted.is_(True))
    if job_id:
        query = query.filter(Application.job_id == job_id)
    rows = []
    for application in query.all():
        candidate = application.candidate
        match = db.query(MatchResult).filter_by(job_id=application.job_id, candidate_id=candidate.id).first()
        rows.append({
            **application_to_dict(application), "phone": candidate.phone, "location": candidate.location,
            "experience_years": candidate.total_experience_years,
            "skills": ", ".join(candidate.technical_skills or []),
            "match_score": match.final_score if match else None,
            "recommendation": (match.admin_override or match.ai_recommendation) if match else None,
        })
    return rows


@router.get("/export", dependencies=admin_only)
def export_shortlist(job_id: Optional[int] = None, format: str = "csv", db: Session = Depends(get_db)):
    if format not in ("csv", "xlsx"):
        raise HTTPException(400, "format must be csv or xlsx")
    columns = ["job_title", "candidate_name", "candidate_email", "phone", "location", "experience_years",
               "skills", "match_score", "recommendation", "status"]
    frame = pd.DataFrame(shortlist_rows(db, job_id), columns=columns)
    buffer = io.BytesIO()
    if format == "csv":
        buffer.write(frame.to_csv(index=False).encode("utf-8"))
        media_type = "text/csv"
    else:
        frame.to_excel(buffer, index=False, sheet_name="Shortlist")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    buffer.seek(0)
    return StreamingResponse(buffer, media_type=media_type,
                             headers={"Content-Disposition": f"attachment; filename=shortlist.{format}"})


@router.post("/share/{job_id}", dependencies=admin_only)
def create_share_link(job_id: int, db: Session = Depends(get_db)):
    """Secure sharing: a signed token that expires after SHARE_LINK_HOURS and only opens THIS job's list."""
    if db.get(Job, job_id) is None:
        raise HTTPException(404, "Job not found")
    expires = datetime.utcnow() + timedelta(hours=SHARE_LINK_HOURS)
    token = jwt.encode({"share_job_id": job_id, "exp": expires}, settings.secret_key, algorithm=settings.jwt_algorithm)
    return {"token": token, "expires_in_hours": SHARE_LINK_HOURS, "path": f"/api/shared/shortlist?token={token}"}


@public_router.get("/shortlist")
def view_shared_shortlist(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        job_id = int(payload["share_job_id"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid or expired share link")
    # Share only what a hiring manager needs - no internal notes, no email addresses.
    return [{"candidate_name": r["candidate_name"], "experience_years": r["experience_years"],
             "skills": r["skills"], "match_score": r["match_score"], "recommendation": r["recommendation"]}
            for r in shortlist_rows(db, job_id)]
