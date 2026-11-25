# TalentFlow — AI-Powered Recruitment & Interview Management Platform

Candidate portal, admin recruitment portal and interviewer portal in one app. An LLM parses resumes, embeddings power semantic search, and a transparent maths formula (not the LLM) scores candidates against jobs.

**Stack:** React + Vite + Tailwind · FastAPI + SQLAlchemy + SQLite · optional Groq/Gemini (resume parsing) · Sentence Transformers `all-MiniLM-L6-v2` · ChromaDB · PyMuPDF + python-docx · pandas · pytest

---

## 1. Run it (fresh machine)

You need Python 3.10+ and Node 18+.

### Beginner-friendly Windows setup

Open PowerShell in the project folder and run:

```powershell
.\setup.ps1
.\start.ps1
```

Then open:

- Frontend: http://localhost:5173
- Backend Swagger: http://localhost:8000/docs

`setup.ps1` creates the virtual environment, installs dependencies, copies `.env.example` to `.env`, and creates demo accounts. `start.ps1` opens the backend and frontend in separate terminals.

### Manual setup

```bash
# 1) Backend
cd backend
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example .env           # then edit .env; a Groq/Gemini key is optional
python seed_demo_users.py           # creates demo admin, candidate and interviewer accounts
uvicorn app.main:app --reload       # API on http://localhost:8000  (Swagger docs: /docs)

# 2) Frontend (new terminal)
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

The first time a resume is processed (or a job is created) the embedding model (~90 MB) downloads once from Hugging Face, so allow a minute and an internet connection. If no Groq/Gemini key is configured, a local section-based parser extracts common resume fields; review the editable profile after upload. Scanned image-only PDFs still need OCR and are not supported.

The default database is SQLite at `backend/recruitment.db`. The Analytics page filters applications by application date, interviews by scheduled date, and resumes by upload date; the funnel shows current progress for applications in the selected range. Dates are interpreted in the browser's local timezone.

To use MySQL instead, create the database first, install the PyMySQL driver with `pip install pymysql`, and set `DATABASE_URL=mysql+pymysql://USER:PASSWORD@localhost:3306/recruitment?charset=utf8mb4` in `backend/.env`. `create_all()` creates missing tables but does not copy or migrate existing SQLite records.

**Demo credentials** (fictional, created by `seed_demo_users.py`)

| Role | Email | Password |
|---|---|---|
| Admin | admin@demo.com | Admin@12345 |
| Interviewer | interviewer1@demo.com | Interview@123 |
| Interviewer | interviewer2@demo.com | Interview@123 |
| Candidate | candidate@demo.com | Candidate@123 |

Candidates can also register with their own email. All three roles use the same sign-in page; the account role determines the portal.

**Run the tests:** `cd backend && python -m pytest -q` (35 tests, work offline, see section 7).

**Sample data:** `python sample_data/generate_sample_resumes.py` writes 5 fictional DOCX resumes plus 2 invalid files into `sample_data/resumes/`. Job descriptions to copy are in `sample_data/sample_jobs.md`.

---

## 2. Architecture

```mermaid
flowchart LR
  subgraph Browser
    C[Candidate portal]
    A[Admin portal]
    I[Interviewer portal]
  end
  C & A & I -->|Axios + JWT| API[FastAPI routes]
  API --> AUTH[auth.py: JWT, roles, ownership checks]
  API --> SVC[services]
  SVC --> P[resume_parser: PyMuPDF/python-docx + Groq/Gemini + Pydantic]
  SVC --> E[embedding_service: MiniLM]
  SVC --> M[matching_service: pure Python maths]
  SVC --> S[semantic_search]
  SVC --> N[notification_service: SMTP or dev log]
  API --> DB[(SQLite via SQLAlchemy)]
  E --> V[(ChromaDB vectors)]
  S --> V
```

**Resume pipeline:** upload → validate type/size → extract text → clean → LLM returns JSON → Pydantic validates → save in SQLite → build candidate text → embed → upsert into ChromaDB (id = candidate id).

**Folder map**
```
backend/app/
  routes/     one file per feature area (auth, candidates, jobs, matching, shortlist, interviews, analytics)
  models/     SQLAlchemy tables           schemas/   Pydantic request/response/LLM-output models
  services/   resume_parser, embedding_service, matching_service, semantic_search, notification_service, resume_pipeline
  auth.py  config.py  database.py  main.py
frontend/src/ pages/{admin,candidate,interviewer}  components/  layouts/  context/  hooks/  services/
```

## 3. Database schema / ER diagram

```mermaid
erDiagram
  USER ||--o| CANDIDATE : "has profile"
  CANDIDATE ||--o{ RESUME : uploads
  CANDIDATE ||--o{ APPLICATION : makes
  JOB ||--o{ APPLICATION : receives
  JOB ||--o{ MATCH_RESULT : scored
  CANDIDATE ||--o{ MATCH_RESULT : scored
  APPLICATION ||--o{ INTERVIEW : has
  USER ||--o{ INTERVIEW : "interviewer"
  INTERVIEW ||--o| FEEDBACK : gets
  USER ||--o{ NOTIFICATION : receives
```
Key rules: `candidates.email` is unique and normalised (lowercase) so duplicates are caught; `applications` has a unique (candidate, job) constraint; `match_results` stores the AI score **and** the admin override separately, so a human decision is never lost when scores are recalculated. List-type fields (skills, education...) are JSON columns.

## 4. AI design (LLM, embeddings, vector DB)

| Choice | Why |
|---|---|
| **Groq / Gemini LLM** (configurable) | Fast, free tier, JSON mode. Used **only to extract** fields from text, `temperature=0`. |
| **all-MiniLM-L6-v2** | Small (90 MB), runs on CPU, 384-dim vectors, good quality for short professional text. |
| **ChromaDB (persistent, cosine)** | Zero-setup local vector store. SQLite stays the source of truth; Chroma holds a searchable copy and is re-synced on every create/update/delete. |
| **No LangChain** | Plain Python functions so the whole pipeline can be explained line by line. |

**Hallucination handling:** the prompt forbids inventing data and requires `null`/`[]` for missing info; Pydantic rejects malformed output; invalid JSON gets one retry then the resume is marked *failed* (never half-saved). The LLM never produces scores or recommendations; the explanation text is assembled from the real matched/missing lists and numbers.

**Human-in-the-loop:** AI recommends, the admin can override per candidate (reason stored), shortlisting and approval are manual, candidates can correct anything the AI extracted.

## 5. Matching methodology

`final = Σ weight × component`, each component 0–100, weights in `.env` (default below).

| Component | Weight | Rule |
|---|---:|---|
| Required skills | 35% | % of the job's required skills the candidate has (aliases handled, e.g. ML = machine learning; also found in project/work text) |
| Experience | 25% | below minimum → years/min × 100; inside range → 100; above max → −5 per extra year, floored at 70 |
| Education | 10% | highest detected level (diploma < bachelor < master < PhD) vs required level |
| Preferred skills | 10% | % of nice-to-have skills present |
| Semantic similarity | 20% | cosine(candidate vector, job vector), stretched from the band 0.15–0.75 onto 0–100 (raw MiniLM scores rarely leave that band) |

If a job leaves a component empty (e.g. no preferred skills) that component is skipped and the other weights are re-scaled, so jobs are not punished for what they did not ask. Recommendation: ≥75 Strong Match, ≥50 Possible Match, else Weak Match (thresholds configurable).

## 6. API documentation

Swagger UI is generated automatically at **http://localhost:8000/docs** (use *Authorize* with `admin@demo.com`). All endpoints are under `/api`.

## 7. Mandatory test scenarios, results

**Automated results** (`backend/tests`, 26 tests passing). These run the real API, database, auth, scoring and workflow code, but use a *stub* in place of the LLM and the embedding model so they work offline. They prove the logic, not the live AI quality.

| # | Scenario | Automated test | Live demo result (fill in after your run) |
|---|---|---|---|
| 1 | Candidate uploads resume → profile created | `test_s1_candidate_uploads_resume_profile_created` ✅ | ☐ Requires a live browser/API run |
| 2 | Admin uploads 5 resumes → each processed individually | `test_s2_s3_bulk_upload_handles_bad_file_without_stopping` ✅ | ☐ Requires a live browser/API run |
| 3 | Invalid file → error without affecting others | same test (corrupted PDF + .txt reported as *failed*, 5 good ones *completed*) ✅ | ☐ Requires a live browser/API run |
| 4 | Admin creates job | `test_s4_admin_creates_job` ✅ | ☐ Requires a live browser/API run |
| 5 | Select job → ranked candidates with scores | `test_s5_s7_matching_ranks_candidates_with_explanation` ✅ | ☐ Requires real embeddings |
| 6 | Natural-language semantic search | **Not covered by automated test** (needs the real embedding model) | ☐ Requires MiniLM download and a live run |
| 7 | Candidate profile + match explanation | `test_s5_s7_...` ✅ | ☐ Requires a live browser/API run |
| 8 | Shortlist → job-specific shortlist | `test_s8_shortlisting_and_export` ✅ | ☐ Requires a live browser/API run |
| 9 | Approve candidate → notification | `test_s9_s10_s11_approve_schedule_feedback` ✅ | ☐ Requires a live browser/API run |
| 10 | Schedule interview → visible to candidate | same test ✅ | ☐ Requires a live browser/API run |
| 11 | Interviewer feedback → visible to admin | same test ✅ | ☐ Requires a live browser/API run |
| 12 | Candidate opens another profile → denied (403) | `test_s12_candidate_cannot_view_another_candidate` ✅ | ☐ Requires a live browser/API run |

Extra tests cover duplicate detection, duplicate applications, override survival, double-booking, shared-link expiry, and the scoring functions.

## 8. Honest limitations

- **Not yet verified end-to-end with a real LLM key and the downloaded MiniLM model**; no Groq/Gemini key was configured in the current workspace, and the automated tests stub these two. Run scenarios 1, 2 and 6 with real credentials and update the table above.
- **Emails:** with no `SMTP_HOST` set, nothing is sent. Messages are appended to `backend/notification_log.txt` as `[DEV LOG - NOT SENT]`. Candidates also get in-app notifications.
- Scanned (image-only) PDFs are rejected; there is no OCR.
- Skill matching uses an alias table + whole-word text search, not embeddings per skill.
- Not built: live video interviews and the stretch goals (agents, MCP, interview question generation, Docker).
- Passwords are bcrypt-hashed, but there is no rate limiting or password reset.

See `documentation/INTERVIEW_GUIDE.md` for how to explain each part in the technical interview.
