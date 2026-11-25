"""Embeddings + ChromaDB storage.

WHAT IS AN EMBEDDING?
  A list of numbers (384 for all-MiniLM-L6-v2) that represents the MEANING of a text.
  Texts with similar meaning get vectors pointing in similar directions.
WHY USEFUL?
  "ML engineer" and "machine learning developer" share no keywords, but their vectors are close.
  A SQL LIKE query would miss that match; vector search finds it.
WHAT DOES CHROMADB DO?
  Stores the vectors on disk and quickly returns the nearest ones to a query vector.
COSINE SIMILARITY
  cos(a, b) = (a . b) / (|a| |b|)  -> angle between vectors. 1 = same direction, 0 = unrelated.
  Chroma returns cosine *distance* = 1 - similarity, which we convert back.
SQL vs VECTOR SEARCH
  SQL matches exact values/keywords. Vector search ranks by meaning.

SQLite is the source of truth; Chroma holds a searchable copy keyed by candidate id.
Call sync_candidate() after every create/update, remove_candidate() after delete.
"""
import chromadb
import logging

from app.config import settings

_model = None  # loaded lazily because loading takes a few seconds
_client = None
logger = logging.getLogger(__name__)

CANDIDATE_COLLECTION = "candidates"
JOB_COLLECTION = "jobs"


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.embedding_model_name)
    return _model


def get_collection(name: str):
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_dir)
    # hnsw:space=cosine makes Chroma use cosine distance
    return _client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


def generate_embedding(text: str) -> list[float]:
    """Input: any text. Output: 384 floats. normalize_embeddings makes length 1 (cosine-friendly)."""
    vector = get_model().encode(text, normalize_embeddings=True)
    return vector.tolist()


def candidate_to_text(candidate) -> str:
    """Turn a Candidate row into one meaningful paragraph for embedding.
    Only real stored data is used - nothing invented."""
    parts = []
    if candidate.summary:
        parts.append(f"Summary: {candidate.summary}")
    if candidate.technical_skills:
        parts.append("Technical skills: " + ", ".join(candidate.technical_skills))
    if candidate.total_experience_years:
        parts.append(f"Total experience: {candidate.total_experience_years} years")
    for job in candidate.employment_history or []:
        parts.append(f"Worked as {job.get('title') or ''} at {job.get('company') or ''}. {job.get('description') or ''}")
    for project in candidate.projects or []:
        parts.append(f"Project {project.get('name') or ''}: {project.get('description') or ''}")
    for item in candidate.education or []:
        parts.append(f"Education: {item.get('degree') or ''} {item.get('institution') or ''}")
    if candidate.certifications:
        parts.append("Certifications: " + ", ".join(candidate.certifications))
    return "\n".join(parts)


def job_to_text(job) -> str:
    return (f"{job.title}. {job.description}. Required skills: {', '.join(job.required_skills or [])}. "
            f"Preferred skills: {', '.join(job.preferred_skills or [])}. Education: {job.education_requirement}")


def sync_candidate(candidate) -> None:
    """Upsert this candidate's vector so Chroma matches SQLite. Id = candidate id."""
    try:
        text = candidate_to_text(candidate)
        if not text.strip():
            remove_candidate(candidate.id)
            return
        get_collection(CANDIDATE_COLLECTION).upsert(
            ids=[str(candidate.id)],
            embeddings=[generate_embedding(text)],
            documents=[text],
            metadatas=[{"name": candidate.name or ""}],
        )
    except Exception as error:
        logger.warning("Candidate embedding sync failed for id %s: %s", candidate.id, error)


def remove_candidate(candidate_id: int) -> None:
    try:
        get_collection(CANDIDATE_COLLECTION).delete(ids=[str(candidate_id)])
    except Exception as error:
        logger.warning("Candidate embedding removal failed for id %s: %s", candidate_id, error)


def sync_job(job) -> None:
    try:
        get_collection(JOB_COLLECTION).upsert(
            ids=[str(job.id)], embeddings=[generate_embedding(job_to_text(job))],
            documents=[job_to_text(job)], metadatas=[{"title": job.title}],
        )
    except Exception as error:
        logger.warning("Job embedding sync failed for id %s: %s", job.id, error)


def remove_job(job_id: int) -> None:
    try:
        get_collection(JOB_COLLECTION).delete(ids=[str(job_id)])
    except Exception as error:
        logger.warning("Job embedding removal failed for id %s: %s", job_id, error)


def cosine_similarity_candidate_job(candidate_id: int, job_id: int) -> float | None:
    """Fetch the two stored vectors and compute cosine similarity (they are unit length, so dot product)."""
    try:
        cand = get_collection(CANDIDATE_COLLECTION).get(ids=[str(candidate_id)], include=["embeddings"])
        job = get_collection(JOB_COLLECTION).get(ids=[str(job_id)], include=["embeddings"])
        if len(cand["ids"]) == 0 or len(job["ids"]) == 0:
            return None
        candidate_vector, job_vector = cand["embeddings"][0], job["embeddings"][0]
        return float(sum(a * b for a, b in zip(candidate_vector, job_vector)))
    except Exception as error:
        logger.warning("Candidate-job cosine similarity failed: %s", error)
        return None
