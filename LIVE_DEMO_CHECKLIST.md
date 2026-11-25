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
6. [ ] Natural-language candidate search.
7. [ ] Open a candidate profile and explanation.
8. [ ] Shortlist candidates and export CSV/XLSX.
9. [ ] Approve a candidate and view notification.
10. [ ] Schedule and reschedule an interview.
11. [ ] Assigned interviewer submits feedback.
12. [ ] Candidate tries to open another candidate profile; access is denied.

After every scenario, record the observed result and any limitations in [README.md](README.md).
