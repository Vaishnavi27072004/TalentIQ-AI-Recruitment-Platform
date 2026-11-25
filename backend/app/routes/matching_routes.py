"""AI matching, human override, and semantic search (admin only)."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.database import get_db
from app.models.tables import Job, Candidate, MatchResult, ROLE_ADMIN
from app.routes.candidate_routes import candidate_to_dict
from app.schemas.schemas import OverrideRequest, SearchRequest
from app.services import embedding_service
from app.services.matching_service import match_candidate_to_job
from app.services.semantic_search import semantic_search

router = APIRouter(prefix="/api", tags=["AI Matching & Search"], dependencies=[Depends(require_roles(ROLE_ADMIN))])

OVERRIDE_CHOICES = ["Strong Match", "Possible Match", "Weak Match", "Not a Match"]


def match_to_dict(match: MatchResult, candidate: Candidate) -> dict:
    return {
        "match_id": match.id, "candidate_id": candidate.id, "name": candidate.name, "email": candidate.email,
        "final_score": match.final_score, "ai_recommendation": match.ai_recommendation,
        "admin_override": match.admin_override, "override_reason": match.override_reason,
        # the decision shown to the admin: human override wins over AI
        "effective_recommendation": match.admin_override or match.ai_recommendation,
        "details": match.details,
    }


def calculate_and_store_match(db: Session, job: Job, candidate: Candidate) -> MatchResult:
    similarity = embedding_service.cosine_similarity_candidate_job(candidate.id, job.id)
    result = match_candidate_to_job(candidate, job, similarity)
    match = db.query(MatchResult).filter_by(job_id=job.id, candidate_id=candidate.id).first()
    if match is None:
        match = MatchResult(job_id=job.id, candidate_id=candidate.id)
        db.add(match)
    match.final_score, match.details = result["final_score"], result["details"]
    match.ai_recommendation, match.calculated_at = result["recommendation"], datetime.utcnow()
    # NOTE: admin_override is deliberately kept - recalculating never erases a human decision.
    return match


@router.post("/matching/jobs/{job_id}/run")
def run_matching(job_id: int, db: Session = Depends(get_db)):
    """Scenario 5: score every candidate against the job and return them ranked."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    embedding_service.sync_job(job)  # make sure the job vector is current
    candidates = db.query(Candidate).all()
    matches = [(calculate_and_store_match(db, job, c), c) for c in candidates]
    db.commit()
    matches.sort(key=lambda pair: pair[0].final_score or 0, reverse=True)
    return [match_to_dict(m, c) for m, c in matches]


@router.get("/matching/jobs/{job_id}")
def get_stored_matches(job_id: int, db: Session = Depends(get_db)):
    rows = (db.query(MatchResult, Candidate).join(Candidate, Candidate.id == MatchResult.candidate_id)
            .filter(MatchResult.job_id == job_id).order_by(MatchResult.final_score.desc()).all())
    return [match_to_dict(m, c) for m, c in rows]


@router.get("/matching/jobs/{job_id}/candidates/{candidate_id}")
def get_candidate_match(job_id: int, candidate_id: int, db: Session = Depends(get_db)):
    """Scenario 7: profile page shows the match explanation (calculated on demand if missing)."""
    job, candidate = db.get(Job, job_id), db.get(Candidate, candidate_id)
    if job is None or candidate is None:
        raise HTTPException(404, "Job or candidate not found")
    match = calculate_and_store_match(db, job, candidate)
    db.commit()
    return match_to_dict(match, candidate)


@router.put("/matching/{match_id}/override")
def override_recommendation(match_id: int, data: OverrideRequest, db: Session = Depends(get_db)):
    """Human-in-the-loop: the admin can disagree with the AI. The AI result stays stored for audit."""
    if data.decision not in OVERRIDE_CHOICES:
        raise HTTPException(400, f"Decision must be one of {OVERRIDE_CHOICES}")
    match = db.get(MatchResult, match_id)
    if match is None:
        raise HTTPException(404, "Match not found")
    match.admin_override, match.override_reason = data.decision, data.reason
    db.commit()
    return match_to_dict(match, db.get(Candidate, match.candidate_id))


@router.post("/search/candidates")
def search_candidates(data: SearchRequest, db: Session = Depends(get_db)):
    """Scenario 6: natural-language search. Chroma finds ids, SQLite supplies the full records."""
    hits = semantic_search(data.query, data.top_k)
    results = []
    for candidate_id, similarity in hits:
        candidate = db.get(Candidate, candidate_id)
        if candidate is None:  # vector exists but row was deleted: skip (should not happen)
            continue
        results.append({**candidate_to_dict(candidate), "similarity": similarity})
    return results
