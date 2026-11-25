"""Pydantic models = request validation + response shape + LLM output validation."""
from datetime import date, datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ---------- Auth ----------
class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str


class UserCreateByAdmin(RegisterRequest):
    role: str = "interviewer"


# ---------- Resume parsing (the shape the LLM must return) ----------
class EducationItem(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    year: Optional[str] = None


class JobHistoryItem(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    description: Optional[str] = None


class ProjectItem(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ParsedResume(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    education: List[EducationItem] = []
    technical_skills: List[str] = []
    soft_skills: List[str] = []
    total_experience_years: Optional[float] = None
    employment_history: List[JobHistoryItem] = []
    projects: List[ProjectItem] = []
    certifications: List[str] = []

    @field_validator("technical_skills", "soft_skills", "certifications", mode="before")
    @classmethod
    def none_to_empty_list(cls, value):
        return value or []

    @field_validator("education", "employment_history", "projects", mode="before")
    @classmethod
    def none_to_empty_objects(cls, value):
        return value or []


# ---------- Candidate ----------
class CandidateUpdate(BaseModel):
    """Fields a candidate/admin may correct after AI extraction."""
    name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    education: Optional[List[EducationItem]] = None
    technical_skills: Optional[List[str]] = None
    soft_skills: Optional[List[str]] = None
    total_experience_years: Optional[float] = Field(default=None, ge=0, le=60)
    employment_history: Optional[List[JobHistoryItem]] = None
    projects: Optional[List[ProjectItem]] = None
    certifications: Optional[List[str]] = None


class NotesUpdate(BaseModel):
    admin_notes: str


# ---------- Jobs ----------
class JobBase(BaseModel):
    title: str = Field(min_length=2)
    description: str = Field(min_length=10)
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    min_experience: float = Field(default=0, ge=0)
    max_experience: Optional[float] = Field(default=None, ge=0)
    education_requirement: str = ""
    location: str = ""
    employment_type: str = "Full-time"
    deadline: Optional[date] = None
    status: str = "active"

    @model_validator(mode="after")
    def valid_experience_range(self):
        if self.max_experience is not None and self.max_experience < self.min_experience:
            raise ValueError("Maximum experience cannot be less than minimum experience")
        return self

    @field_validator("status")
    @classmethod
    def valid_status(cls, value):
        if value not in ("active", "closed", "draft"):
            raise ValueError("status must be active, closed or draft")
        return value


class JobCreate(JobBase):
    pass


class JobUpdate(JobBase):
    pass


# ---------- Shortlist / status / override ----------
class ShortlistRequest(BaseModel):
    job_id: int
    candidate_ids: List[int]


class StatusUpdate(BaseModel):
    status: str


class OverrideRequest(BaseModel):
    decision: str  # e.g. "Strong Match", "Possible Match", "Not a Match"
    reason: str = ""


# ---------- Interviews ----------
class InterviewCreate(BaseModel):
    application_id: int
    interviewer_id: int
    scheduled_at: datetime
    duration_minutes: int = Field(default=45, ge=10, le=240)
    interview_type: str = "Technical"
    meeting_link: str = ""

    @field_validator("scheduled_at")
    @classmethod
    def scheduled_time_must_be_future(cls, value):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        if value <= datetime.utcnow():
            raise ValueError("Interview time must be in the future")
        return value


class InterviewReschedule(BaseModel):
    scheduled_at: datetime
    duration_minutes: Optional[int] = Field(default=None, ge=10, le=240)
    meeting_link: Optional[str] = None

    @field_validator("scheduled_at")
    @classmethod
    def scheduled_time_must_be_future(cls, value):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        if value <= datetime.utcnow():
            raise ValueError("Interview time must be in the future")
        return value


class FeedbackCreate(BaseModel):
    technical_score: int = Field(ge=1, le=5)
    communication_score: int = Field(ge=1, le=5)
    problem_solving_score: int = Field(ge=1, le=5)
    remarks: str = ""
    recommendation: str

    @field_validator("recommendation")
    @classmethod
    def valid_recommendation(cls, value):
        allowed = ["Strongly Recommended", "Recommended", "On Hold", "Not Recommended"]
        if value not in allowed:
            raise ValueError(f"recommendation must be one of {allowed}")
        return value


class SearchRequest(BaseModel):
    query: str = Field(min_length=2)
    top_k: int = Field(default=10, ge=1, le=50)


class RagRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)
