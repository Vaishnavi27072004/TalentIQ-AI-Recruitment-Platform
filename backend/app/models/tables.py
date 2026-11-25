"""Database tables (SQLAlchemy). List-like fields (skills, education...) are stored as JSON.

ER summary:
  User 1-1 Candidate (role=candidate)
  Candidate 1-N Resume, Candidate 1-N Application, Job 1-N Application
  Application 1-N Interview, Interview 1-1 Feedback, Interview N-1 User(interviewer)
  MatchResult = cached AI score for (job, candidate)
"""
from datetime import datetime
from sqlalchemy import (Column, Integer, String, Text, Float, DateTime, Date, ForeignKey,
                        JSON, Boolean, UniqueConstraint)
from sqlalchemy.orm import relationship

from app.database import Base

# ---- Allowed values (kept as constants so we never type magic strings twice) ----
ROLE_ADMIN, ROLE_CANDIDATE, ROLE_INTERVIEWER = "admin", "candidate", "interviewer"

APP_APPLIED, APP_SHORTLISTED, APP_APPROVED = "applied", "shortlisted", "approved_for_interview"
APP_INTERVIEW, APP_SELECTED, APP_REJECTED = "interview_scheduled", "selected", "rejected"
APPLICATION_STATUSES = [APP_APPLIED, APP_SHORTLISTED, APP_APPROVED, APP_INTERVIEW, APP_SELECTED, APP_REJECTED]

INTERVIEW_SCHEDULED, INTERVIEW_CANCELLED, INTERVIEW_COMPLETED = "scheduled", "cancelled", "completed"
RECOMMENDATIONS = ["Strongly Recommended", "Recommended", "On Hold", "Not Recommended"]


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)  # stored lowercase
    full_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null for admin-uploaded resumes
    name = Column(String)
    email = Column(String, unique=True, index=True)  # normalized (lowercase, trimmed) -> duplicate detection
    phone = Column(String)
    location = Column(String)
    summary = Column(Text)
    education = Column(JSON, default=list)       # [{degree, institution, year}]
    technical_skills = Column(JSON, default=list)
    soft_skills = Column(JSON, default=list)
    total_experience_years = Column(Float, default=0)
    employment_history = Column(JSON, default=list)  # [{title, company, start, end, description}]
    projects = Column(JSON, default=list)        # [{name, description}]
    certifications = Column(JSON, default=list)
    admin_notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=True)
    original_filename = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    # processing | completed | failed | duplicate
    status = Column(String, default="processing")
    error_message = Column(Text)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    candidate = relationship("Candidate", back_populates="resumes")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    required_skills = Column(JSON, default=list)
    preferred_skills = Column(JSON, default=list)
    min_experience = Column(Float, default=0)
    max_experience = Column(Float, nullable=True)
    education_requirement = Column(String, default="")
    location = Column(String, default="")
    employment_type = Column(String, default="Full-time")
    deadline = Column(Date, nullable=True)
    status = Column(String, default="active")  # active | closed | draft
    created_at = Column(DateTime, default=datetime.utcnow)
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("candidate_id", "job_id", name="one_application_per_job"),)
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    status = Column(String, default=APP_APPLIED)
    shortlisted = Column(Boolean, default=False)
    applied_at = Column(DateTime, default=datetime.utcnow)
    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    interviews = relationship("Interview", back_populates="application", cascade="all, delete-orphan")


class MatchResult(Base):
    """Cached AI match for one (job, candidate) pair + the admin's human override."""
    __tablename__ = "match_results"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="one_match_per_pair"),)
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    final_score = Column(Float)
    details = Column(JSON)  # component scores, matched/missing skills, explanation
    ai_recommendation = Column(String)
    admin_override = Column(String, nullable=True)  # human decision wins over AI
    override_reason = Column(Text, nullable=True)
    calculated_at = Column(DateTime, default=datetime.utcnow)


class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    interviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=45)
    interview_type = Column(String, default="Technical")
    meeting_link = Column(String, default="")
    status = Column(String, default=INTERVIEW_SCHEDULED)
    created_at = Column(DateTime, default=datetime.utcnow)
    application = relationship("Application", back_populates="interviews")
    interviewer = relationship("User")
    feedback = relationship("Feedback", back_populates="interview", uselist=False, cascade="all, delete-orphan")


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), unique=True, nullable=False)
    technical_score = Column(Integer)      # 1-5
    communication_score = Column(Integer)  # 1-5
    problem_solving_score = Column(Integer)  # 1-5
    remarks = Column(Text, default="")
    recommendation = Column(String)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    interview = relationship("Interview", back_populates="feedback")


class Notification(Base):
    """In-app notification shown in the candidate portal (separate from email)."""
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
