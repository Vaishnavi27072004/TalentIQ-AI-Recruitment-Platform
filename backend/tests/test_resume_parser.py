from pathlib import Path

from docx import Document

from app.services import resume_parser
from app.services.resume_parser import parse_resume_locally


def test_offline_parser_extracts_sections_from_spaced_pdf_headings():
    text = """Ravi Example
ravi@example.test | +91 98765 43210 | Pune, India
C A R E E R O BJ E CT I VE
Postgraduate student focused on data science and machine learning.
S KI L L S
Python SQL Machine Learning Deep Learning NLP
Problem-Solving Presentation Skills
V I RT UAL I NT ERN SHI P
Data Science Intern — Demo Labs
• Used Python to analyze customer data.
E DU CAT IO N D ET A IL S
M.Sc. Data Science
Jun 2027
Example Institute, Pune
P R O J E C T S
Resume Matcher — Semantic search for candidate profiles
• Built the prototype with Python and NLP.
A C HI E V EM EN T S & CE R T I F IC AT IO NS
• AWS Certified Cloud Practitioner (2026)
"""

    parsed = parse_resume_locally(text)

    assert parsed.name == "Ravi Example"
    assert parsed.email == "ravi@example.test"
    assert parsed.phone == "+91 98765 43210"
    assert parsed.location == "Pune, India"
    assert "Postgraduate student" in parsed.summary
    assert parsed.technical_skills == ["Python", "SQL", "Machine Learning", "Deep Learning", "NLP"]
    assert parsed.soft_skills == ["Problem-solving", "Presentation"]
    assert [item.model_dump() for item in parsed.education] == [
        {"degree": "M.Sc. Data Science", "institution": "Example Institute, Pune", "year": "Jun 2027"}
    ]
    assert parsed.employment_history[0].company == "Demo Labs"
    assert "analyze customer data" in parsed.employment_history[0].description
    assert parsed.projects[0].name == "Resume Matcher"
    assert "prototype" in parsed.projects[0].description
    assert parsed.certifications == ["AWS Certified Cloud Practitioner (2026)"]


def test_offline_parser_extracts_sample_resume_fields_and_dates():
    resume_path = (Path(__file__).resolve().parents[2] / "sample_data" / "resumes"
                   / "aarav_mehta_data_analyst.docx")
    document = Document(resume_path)
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    parsed = parse_resume_locally(text)

    assert parsed.name == "Aarav Mehta"
    assert parsed.email == "aarav.mehta@example.com"
    assert parsed.location == "Pune, India"
    assert parsed.technical_skills == ["Python", "SQL", "Power BI", "Excel", "Pandas", "Tableau", "Statistics"]
    assert parsed.education[0].model_dump() == {
        "degree": "B.Sc Statistics", "institution": "Fergus Demo University", "year": "2020",
    }
    assert len(parsed.employment_history) == 2
    assert parsed.employment_history[0].start == "Jun 2022"
    assert parsed.employment_history[0].end == "Present"
    assert parsed.certifications == ["Microsoft Power BI Data Analyst (fictional sample)"]


def test_missing_llm_key_uses_offline_parser(monkeypatch):
    monkeypatch.setattr(resume_parser.settings, "llm_provider", "groq")
    monkeypatch.setattr(resume_parser.settings, "groq_api_key", "")
    monkeypatch.setattr(resume_parser, "call_llm", lambda _text: (_ for _ in ()).throw(AssertionError("LLM called")))

    parsed = resume_parser.parse_resume("Asha Rao\nasha@example.test\nSKILLS\nPython SQL")

    assert parsed.name == "Asha Rao"
    assert parsed.technical_skills == ["Python", "SQL"]
