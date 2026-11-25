"""Interview scheduling (admin), assigned interviews + feedback (interviewer), own schedule (candidate)."""
from typing import Optional
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_roles, get_candidate_for_user
from app.database import get_db
from app.models.tables import (User, Application, Interview, Feedback, APP_APPROVED, APP_INTERVIEW,
                               INTERVIEW_SCHEDULED, INTERVIEW_CANCELLED, INTERVIEW_COMPLETED,
                               ROLE_ADMIN, ROLE_CANDIDATE, ROLE_INTERVIEWER)
from app.schemas.schemas import InterviewCreate, InterviewReschedule, FeedbackCreate
from app.services.notification_service import notify

router = APIRouter(prefix="/api/interviews", tags=["Interviews"])


def feedback_to_dict(feedback: Feedback | None) -> dict | None:
    if feedback is None:
        return None
    return {"technical_score": feedback.technical_score, "communication_score": feedback.communication_score,
            "problem_solving_score": feedback.problem_solving_score, "remarks": feedback.remarks,
            "recommendation": feedback.recommendation, "submitted_at": feedback.submitted_at}


def interview_to_dict(interview: Interview, include_feedback: bool) -> dict:
    application = interview.application
    data = {
        "id": interview.id, "application_id": application.id, "job_title": application.job.title,
        "candidate_id": application.candidate_id, "candidate_name": application.candidate.name,
        "interviewer_id": interview.interviewer_id, "interviewer_name": interview.interviewer.full_name,
        "scheduled_at": interview.scheduled_at.replace(tzinfo=timezone.utc), "duration_minutes": interview.duration_minutes,
        "interview_type": interview.interview_type, "meeting_link": interview.meeting_link,
        "status": interview.status, "has_feedback": interview.feedback is not None,
    }
    if include_feedback:
        data["feedback"] = feedback_to_dict(interview.feedback)
    return data


def interviewer_is_busy(db: Session, interviewer_id: int, start, minutes: int, ignore_id: int | None = None) -> bool:
    """True if the interviewer already has a scheduled interview overlapping [start, start+minutes)."""
    from datetime import timedelta
    if start.tzinfo is not None:
        start = start.astimezone(timezone.utc).replace(tzinfo=None)
    end = start + timedelta(minutes=minutes)
    others = db.query(Interview).filter(Interview.interviewer_id == interviewer_id,
                                        Interview.status == INTERVIEW_SCHEDULED).all()
    for other in others:
        if other.id == ignore_id:
            continue
        other_start = other.scheduled_at
        if other_start.tzinfo is not None:
            other_start = other_start.astimezone(timezone.utc).replace(tzinfo=None)
        other_end = other_start + timedelta(minutes=other.duration_minutes)
        if start < other_end and other_start < end:
            return True
    return False


@router.post("", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def schedule_interview(data: InterviewCreate, db: Session = Depends(get_db)):
    """Scenario 10: details saved, candidate + interviewer notified, candidate can see it."""
    application = db.get(Application, data.application_id)
    interviewer = db.get(User, data.interviewer_id)
    if application is None:
        raise HTTPException(404, "Application not found")
    if interviewer is None or interviewer.role != ROLE_INTERVIEWER:
        raise HTTPException(400, "Selected user is not an interviewer")
    if application.status not in (APP_APPROVED, APP_INTERVIEW):
        raise HTTPException(400, "Approve the candidate for interview before scheduling")
    if interviewer_is_busy(db, interviewer.id, data.scheduled_at, data.duration_minutes):
        raise HTTPException(409, "Interviewer already has an interview at that time")
    interview = Interview(application_id=application.id, interviewer_id=interviewer.id,
                          scheduled_at=data.scheduled_at, duration_minutes=data.duration_minutes,
                          interview_type=data.interview_type, meeting_link=data.meeting_link)
    db.add(interview)
    application.status = APP_INTERVIEW
    candidate = application.candidate
    when = data.scheduled_at.strftime("%d %b %Y %H:%M")
    notify(db, candidate.user_id, candidate.email, f"Interview scheduled: {application.job.title}",
           f"Your {data.interview_type} interview is on {when} ({data.duration_minutes} min). Link: {data.meeting_link or 'to be shared'}")
    notify(db, interviewer.id, interviewer.email, f"Interview assigned: {candidate.name}",
           f"You are assigned to interview {candidate.name} on {when}.")
    db.commit()
    return interview_to_dict(interview, include_feedback=True)


@router.get("")
def list_interviews(upcoming_only: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Role-aware list: admin sees all, interviewer sees assigned, candidate sees own."""
    from datetime import datetime
    query = db.query(Interview)
    if user.role == ROLE_INTERVIEWER:
        query = query.filter(Interview.interviewer_id == user.id)
    elif user.role == ROLE_CANDIDATE:
        candidate = get_candidate_for_user(db, user)
        query = query.join(Application, Interview.application_id == Application.id).filter(
            Application.candidate_id == candidate.id)
    if upcoming_only:
        query = query.filter(Interview.scheduled_at >= datetime.utcnow(), Interview.status == INTERVIEW_SCHEDULED)
    interviews = query.order_by(Interview.scheduled_at).all()
    # candidates must not see interviewer feedback
    return [interview_to_dict(i, include_feedback=user.role != ROLE_CANDIDATE) for i in interviews]


def get_interview_or_404(db: Session, interview_id: int) -> Interview:
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(404, "Interview not found")
    return interview


@router.put("/{interview_id}/reschedule", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def reschedule_interview(interview_id: int, data: InterviewReschedule, db: Session = Depends(get_db)):
    interview = get_interview_or_404(db, interview_id)
    if interview.status != INTERVIEW_SCHEDULED:
        raise HTTPException(400, "Only scheduled interviews can be rescheduled")
    minutes = data.duration_minutes or interview.duration_minutes
    if interviewer_is_busy(db, interview.interviewer_id, data.scheduled_at, minutes, ignore_id=interview.id):
        raise HTTPException(409, "Interviewer already has an interview at that time")
    interview.scheduled_at, interview.duration_minutes = data.scheduled_at, minutes
    if data.meeting_link is not None:
        interview.meeting_link = data.meeting_link
    candidate = interview.application.candidate
    notify(db, candidate.user_id, candidate.email, "Interview rescheduled",
           f"Your interview is now on {data.scheduled_at.strftime('%d %b %Y %H:%M')}.")
    notify(db, interview.interviewer_id, interview.interviewer.email, "Interview rescheduled",
           f"Interview with {candidate.name} moved to {data.scheduled_at.strftime('%d %b %Y %H:%M')}.")
    db.commit()
    return interview_to_dict(interview, include_feedback=True)


@router.post("/{interview_id}/cancel", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def cancel_interview(interview_id: int, db: Session = Depends(get_db)):
    interview = get_interview_or_404(db, interview_id)
    if interview.status != INTERVIEW_SCHEDULED:
        raise HTTPException(400, "Only scheduled interviews can be cancelled")
    interview.status = INTERVIEW_CANCELLED
    application = interview.application
    # candidate goes back to "approved" so the admin can schedule again
    if not any(i.status == INTERVIEW_SCHEDULED for i in application.interviews):
        application.status = APP_APPROVED
    candidate = application.candidate
    notify(db, candidate.user_id, candidate.email, "Interview cancelled",
           f"Your interview for {application.job.title} has been cancelled. We will contact you about a new time.")
    notify(db, interview.interviewer_id, interview.interviewer.email, "Interview cancelled",
           f"Interview with {candidate.name} was cancelled.")
    db.commit()
    return interview_to_dict(interview, include_feedback=True)


@router.post("/{interview_id}/feedback")
def submit_feedback(interview_id: int, data: FeedbackCreate, user: User = Depends(require_roles(ROLE_INTERVIEWER)),
                    db: Session = Depends(get_db)):
    """Scenario 11: only the ASSIGNED interviewer can submit; admins can then read it."""
    interview = get_interview_or_404(db, interview_id)
    if interview.interviewer_id != user.id:
        raise HTTPException(403, "This interview is not assigned to you")
    if interview.status == INTERVIEW_CANCELLED:
        raise HTTPException(400, "Cannot submit feedback for a cancelled interview")
    if interview.feedback is not None:
        raise HTTPException(409, "Feedback has already been submitted for this interview")
    interview.feedback = Feedback(**data.model_dump())
    interview.status = INTERVIEW_COMPLETED
    db.commit()
    return interview_to_dict(interview, include_feedback=True)
