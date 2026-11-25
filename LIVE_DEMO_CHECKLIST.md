# Live Demo Checklist

Use the fictional accounts and sample resumes. Do not include real personal data.

## Before Recording

- [ ] Copy `.env.example` to `.env`.
- [ ] Replace `SECRET_KEY` with a strong random value.
- [ ] Add a Groq or Gemini key only if testing real LLM extraction.
- [ ] Run `setup.ps1`.
- [ ] Run `start.ps1`.
- [ ] Confirm http://localhost:8000/api/health returns `{"status":"ok"}`.
- [ ] Confirm http://localhost:5173 opens.

## Record These 12 Scenarios

1. [ ] Candidate registration and resume upload.
2. [ ] Admin bulk upload of five resumes.
3. [ ] Invalid or corrupted resume upload.
4. [ ] Admin creates a complete job.
5. [ ] Candidate matching ranks candidates.
6. [x] Natural-language candidate search (verified locally on 2026-11-25; five results returned).
7. [ ] Open a candidate profile and explanation.
8. [ ] Shortlist candidates and export CSV/XLSX.
9. [ ] Approve a candidate and view notification.
10. [ ] Schedule and reschedule an interview.
11. [ ] Assigned interviewer submits feedback.
12. [ ] Candidate tries to open another candidate profile; access is denied.

After every scenario, record the observed result and any limitations in [README.md](README.md).

## Verification Status (2026-11-25)

- Backend health, demo-admin sign-in, and dashboard load were verified locally.
- Scenario 6 was run through the API with the cached MiniLM model and ChromaDB; it returned five ranked candidates.
- The backend test suite passes (38 tests). Automated tests are not a substitute for recording each live scenario.
- Admins can generate role- and skill-specific interview question suggestions from the Jobs page; this was verified through the live API and UI.
- Groq parsing was verified locally with a fictional sample resume using `openai/gpt-oss-20b`. The key stays in the ignored `backend/.env`. SMTP remains unconfigured, so email delivery is not verified.
- The remaining scenarios still need to be run and recorded in the browser. The video recording is also still outstanding.
