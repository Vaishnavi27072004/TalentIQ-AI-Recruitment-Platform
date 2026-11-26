# TalentFlow — AI-Powered Recruitment & Interview Management Platform

Candidate portal, admin recruitment portal and interviewer portal in one app. An LLM parses resumes, embeddings power semantic search, and a transparent maths formula (not the LLM) scores candidates against jobs.

TalentIQ is the repository/project name; TalentFlow is the product's user-facing app name.

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
- Backend Swagger: http://localhost:8001/docs

`setup.ps1` creates the virtual environment, installs dependencies, copies `.env.example` to `.env`, and seeds demo accounts, jobs, and resumes. `start.ps1` opens the backend and frontend in separate terminals.
The setup step seeds the fictional sample jobs and valid DOCX resumes from `sample_data/` into the database and upload store. It is safe to rerun; invalid test files are intentionally excluded.

To use the MCP server in VS Code, open this repository folder as the workspace after setup. Approve or start the `talentflow` server from `.vscode/mcp.json` and enter an admin email/password when prompted. If the backend is on a different port, update `TALENTFLOW_API_URL` in that config; the default is `http://127.0.0.1:8001`.

### Manual setup

```bash
# 1) Backend
cd backend
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example .env           # then edit .env; a Groq/Gemini key is optional
python seed_demo_data.py            # creates demo accounts, sample jobs and sample candidates/resumes
uvicorn app.main:app --reload --port 8001  # API on http://localhost:8001  (Swagger docs: /docs)

# 2) Frontend (new terminal)
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

The first time a resume is processed (or a job is created) the embedding model (~90 MB) downloads once from Hugging Face, so allow a minute and an internet connection. If no Groq/Gemini key is configured, a local section-based parser extracts common resume fields; review the editable profile after upload. Scanned image-only PDFs still need OCR and are not supported.

The default database is SQLite at `backend/recruitment.db`. The Analytics page filters applications by application date, interviews by scheduled date, and resumes by upload date; the funnel shows current progress for applications in the selected range. Dates are interpreted in the browser's local timezone.

To use MySQL instead, create the database first, install the PyMySQL driver with `pip install pymysql`, and set `DATABASE_URL=mysql+pymysql://USER:PASSWORD@localhost:3306/recruitment?charset=utf8mb4` in `backend/.env`. `create_all()` creates missing tables but does not copy or migrate existing SQLite records.

**Demo credentials** (fictional, created by `seed_demo_data.py`)

| Role | Email | Password |
|---|---|---|
| Admin | admin@demo.com | Admin@12345 |
| Interviewer | interviewer1@demo.com | Interview@123 |
| Interviewer | interviewer2@demo.com | Interview@123 |
| Candidate | candidate@demo.com | Candidate@123 |

Candidates can also register with their own email. All three roles use the same sign-in page; the account role determines the portal.

**Run the tests:** `cd backend && python -m pytest -q` (48 tests, work offline, see section 7).

**Sample data:** from `backend/`, run `python seed_demo_data.py` to load the included fictional job descriptions and valid DOCX resumes into the database. To regenerate the files, run `python sample_data/generate_sample_resumes.py` from the project root; it also writes invalid files used by the error-handling scenario. Job descriptions are in `sample_data/sample_jobs.md`.

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
  MCP[backend/mcp_server.py<br/>read-only stdio tools] -->|HTTP to loopback API + admin login| API
  API --> AUTH[auth.py: JWT, roles, ownership checks]
  API --> SVC[services]
  SVC --> P[resume_parser: PyMuPDF/python-docx + Groq/Gemini or offline rule-based fallback + Pydantic]
  SVC --> E[embedding_service: MiniLM]
  SVC --> M[matching_service: pure Python maths]
  SVC --> S[semantic_search]
  SVC --> R[rag_service: grounded answers with cited candidate IDs]
  SVC --> N[notification_service: SMTP or dev log]
  API --> DB[(SQLite via SQLAlchemy)]
  E --> V[(ChromaDB vectors)]
  S --> V
  R --> V
  R --> DB
```

**Resume pipeline:** upload → validate type/size → extract text → clean → parse with Groq/Gemini when a provider key is set, otherwise use `parse_resume_locally` (rule-based section extraction, not an LLM) → Pydantic validates → save in SQLite → build candidate text → embed → upsert into ChromaDB (id = candidate id).

**Folder map**
```
backend/app/
  routes/     one file per feature area (auth, candidates, jobs, matching, shortlist, interviews, analytics)
  models/     SQLAlchemy tables           schemas/   Pydantic request/response/LLM-output models
  services/   resume_parser.py (includes offline parse_resume_locally fallback)
              rag_service.py (grounded answers with cited candidate IDs)
              embedding_service.py, matching_service.py, semantic_search.py
              notification_service.py, resume_pipeline.py
  auth.py  config.py  database.py  main.py
backend/mcp_server.py  read-only MCP tools that call the loopback API
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

### Tool calling and retrieval

The stdio MCP server (`backend/mcp_server.py`) registers four read-only tools: `list_jobs`, `search_candidates`, `answer_candidate_question`, and `get_job_matches`. It calls the existing FastAPI endpoints using an admin login, so API role checks remain in force; it accepts connections only to a loopback API address and does not expose a network listener. VS Code prompts for the admin credentials rather than storing them in the committed MCP config.

**RAG flow:** `answer_candidate_question` embeds the admin's question with `all-MiniLM-L6-v2`, retrieves the nearest candidate IDs from ChromaDB, and hydrates their current profiles from SQLite. The API limits the context to the top 10 results and omits email and phone fields; the configured Groq/Gemini model then generates a concise answer using only that context and must cite candidate IDs. The response includes the answer and matching source IDs/names. If no candidates are retrieved, no LLM call is made. Retrieved profile excerpts are sent to the configured LLM provider for generation, so use fictional demo profiles for the recording.

**Chunking:** this project does not split profiles into fixed-size chunks. It assembles each candidate into one text document and stores one 384-dimensional vector per profile; job descriptions are stored similarly. This keeps retrieval simple and returns candidate-level sources, but long profiles are represented by a single embedding rather than independently retrievable passages.

## 5. Matching methodology

When a job lists required skills, the headline match percentage is `matched required skills / total required skills × 100` (so 7 of 10 is 70%). Experience, education, preferred skills, and semantic similarity remain visible as additional fit signals; they do not dilute the required-skill percentage. Candidates tied on required-skill percentage are ordered by the weighted fit signals as a secondary ranking. For jobs with no required skills, the available signals use the weighted fallback (weights in `.env`, defaults below).

| Component | Weight | Rule |
|---|---:|---|
| Required skills | 35%* | % of the job's required skills the candidate has (aliases handled, e.g. ML = machine learning; also found in project/work text) |
| Experience | 25%* | below minimum → years/min × 100; inside range → 100; above max → −5 per extra year, floored at 70 |
| Education | 10%* | highest detected level (diploma < bachelor < master < PhD) vs required level |
| Preferred skills | 10%* | % of nice-to-have skills present |
| Semantic similarity | 20%* | cosine(candidate vector, job vector), stretched from the band 0.15–0.75 onto 0–100 (raw MiniLM scores rarely leave that band) |

*These weights are used as secondary-ranking signals and as a fallback for jobs without a required-skills list. For those jobs, empty components are skipped and remaining weights are re-scaled. Recommendation: ≥75 Strong Match, ≥50 Possible Match, else Weak Match (thresholds configurable).

## 6. API documentation

Swagger UI is generated automatically at **http://localhost:8001/docs** (use *Authorize* with `admin@demo.com`). All endpoints are under `/api`.

## 7. Mandatory test scenarios, results

**Automated results** (`backend/tests`, 48 tests passing). These run the real API, database, auth, scoring and workflow code, but use a *stub* in place of the LLM and the embedding model so they work offline. They prove the logic, not the live AI quality.

| # | Scenario | Automated test | Live verification |
|---|---|---|---|
| 1 | Candidate uploads resume → profile created | `test_s1_candidate_uploads_resume_profile_created` ✅ | ☐ Requires a live browser/API run |
| 2 | Admin uploads 5 resumes → each processed individually | `test_s2_s3_bulk_upload_handles_bad_file_without_stopping` ✅ | ☐ Requires a live browser/API run |
| 3 | Invalid file → error without affecting others | same test (corrupted PDF + .txt reported as *failed*, 5 good ones *completed*) ✅ | ☐ Requires a live browser/API run |
| 4 | Admin creates job | `test_s4_admin_creates_job` ✅ | ☐ Requires a live browser/API run |
| 5 | Select job → ranked candidates with scores | `test_s5_s7_matching_ranks_candidates_with_explanation` ✅ | ☐ Requires real embeddings |
| 6 | Natural-language semantic search | **Not covered by automated test** (needs the real embedding model) | ✅ Verified 2026-11-25: local API + cached MiniLM and Chroma returned 5 ranked results |
| 7 | Candidate profile + match explanation | `test_s5_s7_...` ✅ | ☐ Requires a live browser/API run |
| 8 | Shortlist → job-specific shortlist | `test_s8_shortlisting_and_export` ✅ | ☐ Requires a live browser/API run |
| 9 | Approve candidate → notification | `test_s9_s10_s11_approve_schedule_feedback` ✅ | ☐ Requires a live browser/API run |
| 10 | Schedule interview → visible to candidate | same test ✅ | ☐ Requires a live browser/API run |
| 11 | Interviewer feedback → visible to admin | same test ✅ | ☐ Requires a live browser/API run |
| 12 | Candidate opens another profile → denied (403) | `test_s12_candidate_cannot_view_another_candidate` ✅ | ☐ Requires a live browser/API run |

Extra tests cover duplicate detection, duplicate applications, override survival, double-booking, shared-link expiry, interview-question generation and role access, and the scoring functions.

## 8. Honest limitations

- **Groq resume parsing was verified on 2026-11-25** with the fictional sample resume using `openai/gpt-oss-20b`. Add your own provider key to `backend/.env`; that file is ignored by Git. Gemini parsing has not been verified.
- **Natural-language semantic search was verified locally** with the cached MiniLM model and ChromaDB; the automated tests still stub embeddings.
- **Emails:** with no `SMTP_HOST` set, nothing is sent. Messages are appended to `backend/notification_log.txt` as `[DEV LOG - NOT SENT]`. Candidates also get in-app notifications.
- **Interview questions:** admins can generate role- and skill-specific question suggestions from each job. They use transparent templates, not an LLM, and should be reviewed before use.
- Scanned (image-only) PDFs are rejected; there is no OCR.
- Skill matching uses an alias table + whole-word text search, not embeddings per skill.
- Not built: live video interviews and the other stretch goals (multi-agent workflow, Docker). MCP tools and RAG answers are implemented.
- Passwords are bcrypt-hashed. The login page links to a password-reset flow; reset tokens are emailed when SMTP is configured (otherwise recorded in `backend/notification_log.txt`) and expire after 30 minutes. Login throttling is intended for a single local instance, not a multi-instance production deployment.

See `documentation/INTERVIEW_GUIDE.md` for how to explain each part in the technical interview.
