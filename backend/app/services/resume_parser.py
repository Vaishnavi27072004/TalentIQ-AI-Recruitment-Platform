"""Resume text extraction + LLM-based structured parsing.

PIPELINE (explain this in the interview):
  file -> validate -> extract text (PyMuPDF / python-docx) -> clean text
       -> LLM returns JSON -> Pydantic validates -> saved to DB -> embedding -> ChromaDB

parse_resume(resume_text)
  What it does : turns free-form resume text into a structured ParsedResume object.
  Why needed   : recruiters search/filter on fields, not on raw text.
  Input        : cleaned resume text (str).
  Output       : ParsedResume (Pydantic model). Missing info = None / empty list.
  How it works : sends the text to Groq or Gemini with a strict JSON-only prompt,
                 parses the JSON, validates it with Pydantic. Invalid JSON gets ONE retry.
  Interview    : "The LLM only extracts. It is told never to invent data, and Pydantic
                 rejects anything with the wrong shape. We never let it score candidates."
"""
import json
import re
from datetime import date
from pathlib import Path

import fitz  # PyMuPDF
import httpx
from docx import Document
from pydantic import ValidationError

from app.config import settings
from app.schemas.schemas import ParsedResume


class ResumeError(Exception):
    """Raised for any problem we can explain to the user (bad file, LLM failure...)."""


# ---------------------------------------------------------------- file validation
def validate_resume_file(filename: str, file_bytes: bytes) -> str:
    """Return the lowercase extension if the file is acceptable, else raise ResumeError."""
    extension = Path(filename).suffix.lower()
    if extension not in settings.allowed_resume_extensions:
        raise ResumeError(f"Unsupported file type '{extension}'. Only PDF and DOCX are allowed.")
    if len(file_bytes) == 0:
        raise ResumeError("The file is empty.")
    max_bytes = settings.max_resume_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise ResumeError(f"File is larger than {settings.max_resume_size_mb} MB.")
    return extension


# ---------------------------------------------------------------- text extraction
def extract_text_from_pdf(path: str) -> str:
    try:
        with fitz.open(path) as pdf:
            return "\n".join(page.get_text() for page in pdf)
    except Exception as error:  # corrupted / encrypted PDF
        raise ResumeError(f"Could not read the PDF (corrupted or protected): {error}")


def extract_text_from_docx(path: str) -> str:
    try:
        document = Document(path)
        lines = [paragraph.text for paragraph in document.paragraphs]
        # resumes often put skills inside tables, so read those too
        for table in document.tables:
            for row in table.rows:
                lines.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(lines)
    except Exception as error:
        raise ResumeError(f"Could not read the DOCX (corrupted file?): {error}")


def clean_text(raw_text: str) -> str:
    """Collapse repeated spaces/blank lines so we send fewer tokens to the LLM."""
    text = raw_text.replace("\x00", " ").replace("\ufffd", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_resume_text(path: str) -> str:
    extension = Path(path).suffix.lower()
    raw = extract_text_from_pdf(path) if extension == ".pdf" else extract_text_from_docx(path)
    text = clean_text(raw)
    if len(text) < settings.min_resume_text_chars:
        raise ResumeError("No readable text found (scanned image or empty document).")
    return text


# ---------------------------------------------------------------- LLM call
PARSER_SYSTEM_PROMPT = """You are a resume information extractor.
Return ONLY one JSON object, no markdown, no commentary.
STRICT RULES:
- Use ONLY information that is written in the resume text.
- NEVER invent skills, employers, degrees, dates or experience.
- If something is missing use null (for single values) or [] (for lists).
- technical_skills: tools, languages, frameworks, technologies. soft_skills: communication, leadership etc.
- total_experience_years: number of years of professional work ONLY if it can be computed from the
  dates in the resume, otherwise null. Internships count, education does not.
JSON schema:
{"name": str|null, "email": str|null, "phone": str|null, "location": str|null, "summary": str|null,
 "education": [{"degree": str|null, "institution": str|null, "year": str|null}],
 "technical_skills": [str], "soft_skills": [str], "total_experience_years": number|null,
 "employment_history": [{"title": str|null, "company": str|null, "start": str|null, "end": str|null, "description": str|null}],
 "projects": [{"name": str|null, "description": str|null}],
 "certifications": [str]}"""


def call_llm(resume_text: str) -> str:
    """Send the resume to the configured provider and return the raw text reply."""
    if settings.llm_provider == "gemini":
        return _call_gemini(resume_text)
    return _call_groq(resume_text)


def _call_groq(resume_text: str) -> str:
    if not settings.groq_api_key:
        raise ResumeError("GROQ_API_KEY is not configured. Add it to backend/.env")
    response = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.groq_api_key}"},
        json={
            "model": settings.groq_model,
            "temperature": 0,  # deterministic extraction
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": PARSER_SYSTEM_PROMPT},
                {"role": "user", "content": f"RESUME TEXT:\n{resume_text}"},
            ],
        },
        timeout=settings.llm_timeout_seconds,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _call_gemini(resume_text: str) -> str:
    if not settings.gemini_api_key:
        raise ResumeError("GEMINI_API_KEY is not configured. Add it to backend/.env")
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}")
    response = httpx.post(
        url,
        json={
            "systemInstruction": {"parts": [{"text": PARSER_SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": f"RESUME TEXT:\n{resume_text}"}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        },
        timeout=settings.llm_timeout_seconds,
    )
    response.raise_for_status()
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]


def extract_json_object(reply_text: str) -> dict:
    """Models sometimes wrap JSON in ```json fences or add words; pull out the {...} part."""
    start, end = reply_text.find("{"), reply_text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in model reply")
    return json.loads(reply_text[start:end + 1])


MAX_LLM_ATTEMPTS = 2  # first try + one retry when the JSON is invalid


_SECTION_ALIASES = {
    "summary": ("SUMMARY", "PROFESSIONAL SUMMARY", "PROFILE", "CAREER OBJECTIVE", "OBJECTIVE"),
    "skills": ("SKILLS", "TECHNICAL SKILLS", "CORE SKILLS", "SKILL SET"),
    "experience": ("EXPERIENCE", "WORK EXPERIENCE", "EMPLOYMENT", "PROFESSIONAL EXPERIENCE",
                   "INTERNSHIP", "VIRTUAL INTERNSHIP"),
    "education": ("EDUCATION", "EDUCATION DETAILS", "ACADEMIC BACKGROUND", "QUALIFICATIONS"),
    "projects": ("PROJECTS", "PERSONAL PROJECTS", "RESEARCH PROJECT", "RESEARCH PROJECTS"),
    "certifications": ("CERTIFICATIONS", "CERTIFICATES", "ACHIEVEMENTS & CERTIFICATIONS"),
    "soft_skills": ("SOFT SKILLS", "INTERPERSONAL SKILLS"),
}
_HEADING_LOOKUP = {
    re.sub(r"[^A-Z0-9]", "", alias): section
    for section, aliases in _SECTION_ALIASES.items()
    for alias in aliases
}
_SKILL_NAMES = {
    "python": "Python", "java": "Java", "javascript": "JavaScript", "typescript": "TypeScript",
    "react": "React", "node.js": "Node.js", "node": "Node.js", "express": "Express",
    "sql": "SQL", "mysql": "MySQL", "postgresql": "PostgreSQL", "mongodb": "MongoDB",
    "html": "HTML", "css": "CSS", "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    "machine learning": "Machine Learning", "deep learning": "Deep Learning", "nlp": "NLP",
    "generative ai": "Generative AI", "prompt engineering": "Prompt Engineering",
    "data analysis": "Data Analysis", "big data analysis": "Big Data Analysis",
    "time series analysis": "Time Series Analysis", "statistical analysis": "Statistical Analysis",
    "statistics": "Statistics", "pandas": "Pandas", "numpy": "NumPy", "matplotlib": "Matplotlib",
    "seaborn": "Seaborn", "tensorflow/keras": "TensorFlow/Keras", "tensorflow": "TensorFlow",
    "pytorch": "PyTorch", "nltk": "NLTK", "scikit-learn": "scikit-learn", "sklearn": "scikit-learn",
    "docker": "Docker", "kubernetes": "Kubernetes", "aws": "AWS", "azure": "Azure",
    "gcp": "GCP", "databricks": "Databricks", "hugging face": "Hugging Face", "git": "Git",
    "github": "GitHub", "excel": "Excel", "tableau": "Tableau", "power bi": "Power BI",
    "spark": "Spark", "rest api": "REST APIs", "rest apis": "REST APIs",
}
_SOFT_SKILL_NAMES = {
    "problem solving": "Problem-solving", "presentation skills": "Presentation",
    "communication": "Communication", "team management": "Team management",
    "teamwork": "Teamwork", "leadership": "Leadership", "collaboration": "Collaboration",
    "adaptability": "Adaptability", "critical thinking": "Critical thinking",
    "time management": "Time management",
}
_MONTHS = {name.lower(): number for number, name in enumerate(
    ("January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"), start=1)}
_MONTHS.update({name[:3].lower(): number for name, number in list(_MONTHS.items())})


def _compact_heading(line: str) -> str:
    # PDF text extraction may insert spaces inside headings, e.g. "E DU CAT IO N".
    return re.sub(r"[^A-Z0-9]", "", line.upper())


def _resume_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {section: [] for section in _SECTION_ALIASES}
    current = ""
    for line in lines:
        content = line.strip()
        normalized = re.sub(r"^[\s•·▪\-–]+", "", line).strip()
        heading = _HEADING_LOOKUP.get(_compact_heading(normalized.rstrip(":")))
        if heading:
            current = heading
            continue
        inline = re.match(r"^([A-Za-z &/]+?)\s*:\s*(.+)$", normalized)
        if inline:
            heading = _HEADING_LOOKUP.get(_compact_heading(inline.group(1)))
            if heading:
                current = heading
                content = inline.group(2).strip()
        if current and content:
            sections[current].append(content)
    return sections


def _extract_named_terms(text: str, names: dict[str, str]) -> list[str]:
    matches = []
    searchable_text = re.sub(r"[-‐‑]", " ", text)
    for term, canonical in names.items():
        pattern = r"(?<![\w])" + re.escape(term) + r"(?![\w])"
        pattern = pattern.replace(r"\ ", r"\s+")
        matches.extend((match.start(), match.end(), canonical) for match in re.finditer(pattern, searchable_text, re.I))
    result, seen, occupied = [], set(), []
    for start, end, name in sorted(matches, key=lambda match: (match[0], -(match[1] - match[0]))):
        if name.casefold() not in seen:
            if any(start < prev_end and prev_start < end for prev_start, prev_end in occupied):
                continue
            seen.add(name.casefold())
            result.append(name)
            occupied.append((start, end))
    return result


def _year_or_date(line: str) -> str | None:
    match = re.search(r"\b(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+)?(?:19|20)\d{2}\b", line, re.I)
    return match.group(0).strip() if match else None


def _education_entries(lines: list[str]) -> list[dict]:
    entries = []
    index = 0
    while index < len(lines):
        line = lines[index].strip(" •·▪")
        if not _is_degree_line(line):
            index += 1
            continue
        if re.search(r"\b(coursework only|not completed|incomplete)\b", line, re.I):
            index += 1
            continue
        parts = [part.strip() for part in re.split(r"\s*[|,]\s*", line) if part.strip()]
        degree = parts[0] if parts else line
        institution = next((part for part in parts[1:] if not _year_or_date(part)), None)
        year = next((_year_or_date(part) for part in parts[1:] if _year_or_date(part)), None)
        lookahead = index + 1
        while lookahead < len(lines) and lookahead <= index + 3:
            following = lines[lookahead].strip(" •·▪")
            if _is_degree_line(following):
                break
            if not year:
                year = _year_or_date(following)
            if not institution and re.search(r"[A-Za-z]", following) and not re.search(
                r"(percentage|gpa|cgpa|grade|score)", following, re.I
            ) and not _year_or_date(following):
                institution = following
            lookahead += 1
        entries.append({"degree": degree, "institution": institution, "year": year})
        index += 1
    return entries


def _is_degree_line(line: str) -> bool:
    return bool(re.search(
        r"\b(?:b|m)\.?\s*(?:sc|s|tech|e|com|a)\b|\b(?:bca|mca|mba|ph\.?d|phd|"
        r"bachelor|master|diploma|hsc|ssc|higher secondary|secondary)\b",
        line, re.I,
    ))


def _parse_work_entry(line: str) -> dict | None:
    cleaned = re.sub(r"^[\s•·▪\-–]+", "", line).strip()
    if not cleaned:
        return None
    date_match = re.search(
        r"\b((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+)?(?:19|20)\d{2})"
        r"\s*[-–—]\s*(Present|Current|(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+)?(?:19|20)\d{2})\b",
        cleaned, re.I,
    )
    title_company = cleaned[:date_match.start()].strip(" ,|()–—-") if date_match else cleaned
    pieces = re.split(r"\s+[—–]\s+|\s+-\s+|,\s*", title_company, maxsplit=1)
    title = pieces[0].strip() if pieces else title_company
    company = pieces[1].strip() if len(pieces) > 1 else None
    return {
        "title": title or None,
        "company": company,
        "start": date_match.group(1).strip() if date_match else None,
        "end": date_match.group(2).strip() if date_match else None,
        "description": None,
    }


def _month_year(value: str, use_current_month: bool = False) -> int | None:
    if value.lower() in ("present", "current"):
        today = date.today()
        return today.year * 12 + today.month
    match = re.search(
        r"(?:(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+)?((?:19|20)\d{2})",
        value, re.I,
    )
    if not match:
        return None
    month = _MONTHS.get(match.group(1)[:3].lower(), 12 if use_current_month else 1) if match.group(1) else (
        12 if use_current_month else 1
    )
    return int(match.group(2)) * 12 + month


def _experience_years(entries: list[dict], resume_text: str) -> float | None:
    explicit = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:\+?\s*years?|yrs?)\s+(?:of\s+)?(?:professional\s+)?experience"
        r"|(?:total\s+)?(?:professional\s+)?experience[^.\n]{0,30}?(\d+(?:\.\d+)?)\s*(?:\+?\s*years?|yrs?)",
        resume_text, re.I,
    )
    if explicit:
        return float(explicit.group(1) or explicit.group(2))

    intervals: list[tuple[int, int]] = []
    for entry in entries:
        if not entry["start"] or not entry["end"]:
            continue
        start, end = _month_year(entry["start"]), _month_year(entry["end"], use_current_month=True)
        if start is not None and end is not None and end >= start:
            intervals.append((start, end))
    if not intervals:
        return None
    intervals.sort()
    total_months = 0
    start, end = intervals[0]
    for next_start, next_end in intervals[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            total_months += end - start + 1
            start, end = next_start, next_end
    total_months += end - start + 1
    return round(total_months / 12, 1)


def _contact_location(lines: list[str]) -> str | None:
    for line in lines[:15]:
        if "@" not in line and not re.search(r"\+?\d[\d\s().-]{7,}\d", line):
            continue
        for part in re.split(r"\s*[|•]\s*", line):
            part = part.strip()
            if not part or "@" in part or re.search(r"\+?\d[\d\s().-]{7,}\d", part):
                continue
            if re.search(r"\b(linkedin|github|portfolio|website)\b", part, re.I):
                continue
            if "," in part and len(part) <= 80:
                return part
    return None


def parse_resume_locally(resume_text: str) -> ParsedResume:
    """Best-effort section-based extraction for offline use; candidates can edit the result."""
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    sections = _resume_sections(lines)
    email_match = re.search(r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", resume_text, re.I)
    phone_match = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", resume_text)

    name = None
    for line in lines[:10]:
        if "@" in line or _HEADING_LOOKUP.get(_compact_heading(line.rstrip(":"))):
            continue
        if re.search(r"(resume|curriculum vitae|phone|email|linkedin|github)", line, re.I):
            continue
        name = re.sub(r"\s+", " ", line).strip(" |,-")
        if name and 2 <= len(name) <= 80:
            break
        name = None

    skill_text = "\n".join(sections["skills"]) + "\n" + "\n".join(sections["soft_skills"])
    technical_skills = _extract_named_terms(skill_text or resume_text, _SKILL_NAMES)
    soft_skills = _extract_named_terms(resume_text, _SOFT_SKILL_NAMES)

    raw_experience = sections["experience"]
    employment_history = []
    for line in raw_experience:
        if line.startswith(("•", "-", "–", "▪")) and employment_history:
            description = employment_history[-1]["description"] or ""
            employment_history[-1]["description"] = (description + " " + line.lstrip("•-–▪ ").strip()).strip()
            continue
        entry = _parse_work_entry(line)
        if entry:
            employment_history.append(entry)

    projects = []
    for line in sections["projects"]:
        if line.startswith(("•", "-", "–", "▪")) and projects:
            projects[-1]["description"] = (projects[-1]["description"] + " " + line.lstrip("•-–▪ ").strip()).strip()
            continue
        cleaned = re.sub(r"^[\s•·▪\-–]+", "", line).strip()
        if cleaned:
            if projects and len(cleaned) < 70 and projects[-1]["description"]:
                projects[-1]["description"] = (projects[-1]["description"] + " " + cleaned).strip()
                continue
            parts = re.split(r"\s+[—–]\s+|\s+-\s+", cleaned, maxsplit=1)
            projects.append({"name": parts[0].strip(), "description": parts[1].strip() if len(parts) > 1 else ""})

    certifications = []
    for line in sections["certifications"]:
        cleaned = re.sub(r"^[\s•·▪\-–]+", "", line).strip()
        if cleaned and not re.search(r"\b(3rd|2nd|1st|place|published article|competition)\b", cleaned, re.I):
            certifications.append(cleaned)

    summary = " ".join(sections["summary"])
    if not summary:
        summary = next((line for line in lines[:10] if re.search(
            r"\b(student|engineer|developer|analyst|professional|experience|focused|interested)\b", line, re.I
        )), "")

    return ParsedResume(
        name=name,
        email=email_match.group(0) if email_match else None,
        phone=re.sub(r"\s+", " ", phone_match.group(0)).strip() if phone_match else None,
        location=_contact_location(lines),
        summary=summary or None,
        education=_education_entries(sections["education"]),
        technical_skills=technical_skills,
        soft_skills=soft_skills,
        total_experience_years=_experience_years(employment_history, resume_text),
        employment_history=employment_history,
        projects=projects,
        certifications=certifications,
    )


def parse_resume(resume_text: str) -> ParsedResume:
    """Main entry point. See module docstring for the interview explanation."""
    if (settings.llm_provider == "groq" and not settings.groq_api_key) or (
        settings.llm_provider == "gemini" and not settings.gemini_api_key
    ):
        return parse_resume_locally(resume_text)

    last_problem = ""
    for _attempt in range(MAX_LLM_ATTEMPTS):
        try:
            reply = call_llm(resume_text)
        except ResumeError:
            raise
        except httpx.HTTPError as error:
            raise ResumeError(f"LLM API error: {error}")
        try:
            data = extract_json_object(reply)
            return ParsedResume(**data)
        except (ValueError, ValidationError) as error:  # invalid JSON or wrong shape
            last_problem = str(error)
    raise ResumeError(f"LLM returned invalid structured data after retry: {last_problem[:200]}")


def normalize_email(email: str | None) -> str | None:
    """Lowercase + trim so 'Rahul@X.com ' and 'rahul@x.com' count as the same person."""
    return email.strip().lower() if email and email.strip() else None
