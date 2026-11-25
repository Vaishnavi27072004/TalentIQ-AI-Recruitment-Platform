# Technical Walkthrough Guide

## Architecture

The React frontend calls role-protected FastAPI routes. FastAPI uses SQLAlchemy with SQLite by default. Resume text is parsed into a Pydantic model, candidate data is stored in SQLite, and MiniLM vectors are stored in persistent ChromaDB.

## Explain Resume Parsing

1. Validate PDF/DOCX type and size.
2. Extract text with PyMuPDF or python-docx.
3. Ask Groq or Gemini for structured JSON.
4. Validate the response with Pydantic.
5. Store only extracted or human-corrected fields.
6. Generate a candidate embedding and upsert it into ChromaDB.

Missing values become `null` or empty lists. The system never asks the LLM to invent missing fields or produce match scores.

## Explain Matching

The final match score is deterministic:

- 35% required skills
- 25% experience
- 10% education
- 10% preferred skills
- 20% resume/job semantic similarity

Unavailable components are skipped and remaining weights are re-scaled. Matched skills, missing skills, component scores and the final explanation are stored in JSON for auditability.

## Explain Semantic Search

Candidate profiles and recruiter queries are represented with the same MiniLM embedding model. ChromaDB performs cosine-similarity search and returns candidate IDs. SQLite supplies the complete candidate records.

## Explain Security

- Passwords use bcrypt.
- JWT bearer tokens carry user identity and role.
- FastAPI dependencies enforce roles on each endpoint.
- Candidate endpoints enforce ownership.
- Interviewer feedback requires assignment to that interview.
- Password-reset tokens expire after 30 minutes.
- Login attempts are rate-limited in memory.

## Demonstration Sequence

1. Register or log in as a candidate.
2. Upload a fictional DOCX or PDF resume.
3. Review and correct extracted fields.
4. Create or browse a job.
5. Run matching and explain a candidate's score.
6. Run natural-language candidate search.
7. Shortlist, approve and schedule an interview.
8. Log in as the assigned interviewer and submit feedback.
9. Log in as the candidate and confirm schedule visibility.

## Common Interview Questions

**Why SQLite?** It is zero-setup and correct for a local assessment/demo; the SQLAlchemy layer permits PostgreSQL or MySQL.

**Where could hallucinations occur?** Resume extraction can still be uncertain, so Pydantic validation, empty defaults, source-text review and manual correction reduce this risk.

**Can the LLM change match scores?** No. It only extracts resume fields. Matching is deterministic Python code.
