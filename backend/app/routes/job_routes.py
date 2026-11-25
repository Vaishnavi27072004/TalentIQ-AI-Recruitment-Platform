"""Job CRUD (admin) + browsing (candidates) + applications."""
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.auth import get_current_user, require_roles, get_candidate_for_user
from app.database import get_db
from app.models.tables import (User, Job, Application, MatchResult, APPLICATION_STATUSES, APP_APPLIED,
                               ROLE_ADMIN, ROLE_CANDIDATE)
from app.schemas.schemas import JobCreate, JobUpdate, StatusUpdate
from app.services import embedding_service
from app.services.notification_service import notify

router = APIRouter(prefix="/api", tags=["Jobs & Applications"])


def job_to_dict(job: Job, db: Session | None = None) -> dict:
    data = {c: getattr(job, c) for c in (
        "id", "title", "description", "required_skills", "preferred_skills", "min_experience", "max_experience",
        "education_requirement", "location", "employment_type", "deadline", "status", "created_at")}
    if db is not None:
        data["application_count"] = db.query(Application).filter(Application.job_id == job.id).count()
    return data


# ------------------------------------------------------------------ jobs
@router.post("/jobs", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def create_job(data: JobCreate, db: Session = Depends(get_db)):
    """Scenario 4: job saved with all details; its embedding is stored for matching."""
    job = Job(**data.model_dump())
    db.add(job)
    db.commit()
    embedding_service.sync_job(job)
    return job_to_dict(job, db)


@router.get("/jobs")
def list_jobs(status: Optional[str] = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Job)
    if user.role == ROLE_CANDIDATE:  # candidates only see open jobs whose deadline has not passed
        query = query.filter(Job.status == "active")
        jobs = [j for j in query.all() if j.deadline is None or j.deadline >= date.today()]
    else:
        if status:
            query = query.filter(Job.status == status)
        jobs = query.order_by(Job.created_at.desc()).all()
    return [job_to_dict(j, db) for j in jobs]


@router.get("/jobs/{job_id}")
def get_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None or (user.role == ROLE_CANDIDATE and job.status != "active"):
        raise HTTPException(404, "Job not found")
    return job_to_dict(job, db)


@router.get("/jobs/{job_id}/interview-questions", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def generate_interview_questions(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")

    skills = []
    seen_skills = set()
    for skill in (job.required_skills or []) + (job.preferred_skills or []):
        skill = skill.strip()
        if skill and skill.casefold() not in seen_skills:
            skills.append(skill)
            seen_skills.add(skill.casefold())

    questions = [{
        "category": "Role fit",
        "question": f"What interests you about the {job.title} role, and which experience best prepares you for it?",
    }]
    for skill in skills[:5]:
        questions.append({
            "category": "Job skills",
            "question": f"Tell me about a project where you used {skill}. What challenge did you solve, and what was the result?",
        })
    if not skills:
        questions.append({
            "category": "Job skills",
            "question": f"What tools or methods would you bring to the {job.title} role, and why?",
        })
    questions.append({
        "category": "Situational",
        "question": f"If you joined as a {job.title} and received an unclear assignment, how would you clarify it and plan your first steps?",
    })
    return {"job_id": job.id, "job_title": job.title, "questions": questions}


@router.put("/jobs/{job_id}", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def update_job(job_id: int, data: JobUpdate, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    for field, value in data.model_dump().items():
        setattr(job, field, value)
    db.query(MatchResult).filter(MatchResult.job_id == job_id).delete()  # old scores are stale now
    db.commit()
    embedding_service.sync_job(job)
    return job_to_dict(job, db)


@router.delete("/jobs/{job_id}", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    db.query(MatchResult).filter(MatchResult.job_id == job_id).delete()
    db.delete(job)
    db.commit()
    embedding_service.remove_job(job_id)
    return {"deleted": job_id}


# ------------------------------------------------------------------ applications
def application_to_dict(app_row: Application) -> dict:
    return {
        "id": app_row.id, "status": app_row.status, "shortlisted": app_row.shortlisted,
        "applied_at": app_row.applied_at, "job_id": app_row.job_id, "job_title": app_row.job.title,
        "candidate_id": app_row.candidate_id, "candidate_name": app_row.candidate.name,
        "candidate_email": app_row.candidate.email,
    }


@router.post("/jobs/{job_id}/apply")
def apply_to_job(job_id: int, user: User = Depends(require_roles(ROLE_CANDIDATE)), db: Session = Depends(get_db)):
    candidate = get_candidate_for_user(db, user)
    job = db.get(Job, job_id)
    if job is None or job.status != "active" or (job.deadline and job.deadline < date.today()):
        raise HTTPException(400, "This job is not open for applications")
    if not (candidate.technical_skills or candidate.summary or candidate.employment_history):
        raise HTTPException(400, "Please upload your resume and complete your profile before applying")
    if db.query(Application).filter_by(candidate_id=candidate.id, job_id=job_id).first():
        raise HTTPException(409, "You have already applied to this job")  # duplicate protection
    application = Application(candidate_id=candidate.id, job_id=job_id, status=APP_APPLIED)
    db.add(application)
    try:
        db.flush()
    except IntegrityError:  # two clicks at the same moment: DB unique constraint is the last guard
        db.rollback()
        raise HTTPException(409, "You have already applied to this job")
    notify(db, user.id, user.email, f"Application received: {job.title}",
           f"Hi {candidate.name}, we received your application for {job.title}.")
    db.commit()
    return application_to_dict(application)


@router.get("/applications/me")
def my_applications(user: User = Depends(require_roles(ROLE_CANDIDATE)), db: Session = Depends(get_db)):
    candidate = get_candidate_for_user(db, user)
    return [application_to_dict(a) for a in candidate.applications]


@router.get("/applications", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def list_applications(job_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Application)
    if job_id:
        query = query.filter(Application.job_id == job_id)
    return [application_to_dict(a) for a in query.order_by(Application.applied_at.desc()).all()]


@router.put("/applications/{application_id}/status", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def update_application_status(application_id: int, data: StatusUpdate, db: Session = Depends(get_db)):
    """Admin makes the final call (e.g. selected / rejected)."""
    if data.status not in APPLICATION_STATUSES:
        raise HTTPException(400, f"Status must be one of {APPLICATION_STATUSES}")
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(404, "Application not found")
    application.status = data.status
    if data.status == APP_APPLIED:  # moving back to "applied" removes the shortlist flag
        application.shortlisted = False
    candidate = application.candidate
    notify(db, candidate.user_id, candidate.email, f"Application update: {application.job.title}",
           f"Your application status is now: {data.status.replace('_', ' ')}.")
    db.commit()
    return application_to_dict(application)
