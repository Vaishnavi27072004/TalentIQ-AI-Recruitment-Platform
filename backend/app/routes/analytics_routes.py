"""Dashboard numbers + charts. Every figure is a database query (no hardcoded values)."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.auth import require_roles, get_current_user
from app.database import get_db
from app.models.tables import (User, Candidate, Resume, Job, Application, Interview, Notification,
                               APPLICATION_STATUSES, APP_SELECTED, INTERVIEW_COMPLETED, INTERVIEW_SCHEDULED,
                               ROLE_ADMIN)

router = APIRouter(prefix="/api", tags=["Analytics & Notifications"])


def _utc_naive(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _date_filters(column, start_at: datetime | None, end_at: datetime | None) -> list:
    filters = []
    if start_at is not None:
        filters.append(column >= start_at)
    if end_at is not None:
        filters.append(column < end_at)
    return filters


@router.get("/analytics/dashboard", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def dashboard(start_at: datetime | None = None, end_at: datetime | None = None,
              db: Session = Depends(get_db)):
    start_at, end_at = _utc_naive(start_at), _utc_naive(end_at)
    if start_at is not None and end_at is not None and start_at >= end_at:
        raise HTTPException(422, "Start date must be earlier than end date")

    candidate_filters = _date_filters(Candidate.created_at, start_at, end_at)
    resume_filters = _date_filters(Resume.uploaded_at, start_at, end_at)
    job_filters = _date_filters(Job.created_at, start_at, end_at)
    application_filters = _date_filters(Application.applied_at, start_at, end_at)
    interview_filters = _date_filters(Interview.scheduled_at, start_at, end_at)

    applications = db.query(Application).filter(*application_filters)
    total_applications = applications.count()
    shortlisted = applications.filter(Application.shortlisted.is_(True)).count()
    interviewed = applications.filter(
        Application.interviews.any(Interview.status == INTERVIEW_COMPLETED)).count()
    selected = applications.filter(Application.status == APP_SELECTED).count()

    kpis = {
        "total_candidates": db.query(Candidate).filter(*candidate_filters).count(),
        "total_resumes": db.query(Resume).filter(*resume_filters).count(),
        "active_jobs": db.query(Job).filter(Job.status == "active", *job_filters).count(),
        "total_applications": total_applications,
        "shortlisted_candidates": shortlisted,
        "scheduled_interviews": db.query(Interview).filter(
            Interview.status == INTERVIEW_SCHEDULED, *interview_filters).count(),
        "selected_candidates": selected,
    }

    application_join = and_(Application.job_id == Job.id, *application_filters)
    applications_by_job = [{"job": title, "applications": count} for title, count in
                           db.query(Job.title, func.count(Application.id)).outerjoin(Application, application_join)
                           .group_by(Job.id, Job.title).all()]
    status_counts = dict(db.query(Application.status, func.count(Application.id))
                         .filter(*application_filters).group_by(Application.status).all())
    statuses = [{"status": s, "count": status_counts.get(s, 0)} for s in APPLICATION_STATUSES]

    # Funnel counts are the current progress of applications created in the selected period.
    funnel = [
        {"stage": "Applied", "count": total_applications},
        {"stage": "Shortlisted", "count": shortlisted},
        {"stage": "Interviewed", "count": interviewed},
        {"stage": "Selected", "count": selected},
    ]
    conversion_rates = {
        "shortlisted": round(shortlisted * 100 / total_applications, 1) if total_applications else 0.0,
        "interviewed": round(interviewed * 100 / total_applications, 1) if total_applications else 0.0,
        "selected": round(selected * 100 / total_applications, 1) if total_applications else 0.0,
    }

    interview_counts = dict(db.query(Interview.status, func.count(Interview.id))
                            .filter(*interview_filters).group_by(Interview.status).all())
    interviews = [{"status": s, "count": interview_counts.get(s, 0)} for s in ("scheduled", "completed", "cancelled")]
    resume_counts = dict(db.query(Resume.status, func.count(Resume.id))
                         .filter(*resume_filters).group_by(Resume.status).all())
    return {"kpis": kpis, "applications_by_job": applications_by_job, "application_statuses": statuses,
            "funnel": funnel, "conversion_rates": conversion_rates, "interview_stats": interviews,
            "resume_processing": resume_counts}


@router.get("/notifications")
def my_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(50).all()
    return [{"id": n.id, "message": n.message, "is_read": n.is_read, "created_at": n.created_at} for n in rows]


@router.post("/notifications/read-all")
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.user_id == user.id).update({"is_read": True})
    db.commit()
    return {"ok": True}
