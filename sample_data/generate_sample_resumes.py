"""Generates FICTIONAL sample resumes (DOCX) + one invalid file for the test scenarios.
Run from the project root:  python sample_data/generate_sample_resumes.py"""
from pathlib import Path
from docx import Document

OUT = Path(__file__).parent / "resumes"
OUT.mkdir(exist_ok=True)

RESUMES = {
    "aarav_mehta_data_analyst.docx": """Aarav Mehta
aarav.mehta@example.com | +91 98765 00001 | Pune, India
SUMMARY
Data analyst with 3 years of experience turning business data into dashboards and insights.
SKILLS
Python, SQL, Power BI, Excel, Pandas, Tableau, Statistics
EXPERIENCE
Data Analyst, Brightwave Retail (Jun 2022 - Present)
- Built Power BI dashboards for sales and inventory used by 40 managers.
- Wrote SQL pipelines in PostgreSQL and automated reporting with Python and Pandas.
Junior Analyst, Northfield Logistics (Jan 2021 - May 2022)
- Cleaned shipment data and produced weekly KPI reports.
EDUCATION
B.Sc Statistics, Fergus Demo University, 2020
CERTIFICATIONS
Microsoft Power BI Data Analyst (fictional sample)""",
    "diya_nair_ml_engineer.docx": """Diya Nair
diya.nair@example.com | +91 98765 00002 | Bengaluru, India
SUMMARY
Machine learning engineer focused on NLP and recommendation systems, 4 years of experience.
SKILLS
Python, Machine Learning, Deep Learning, TensorFlow, PyTorch, NLP, scikit-learn, SQL, Docker
EXPERIENCE
ML Engineer, Lumen AI Labs (Aug 2021 - Present)
- Built a transformer-based text classifier for support tickets (NLP).
- Deployed models as REST APIs using FastAPI and Docker.
Data Scientist, Orchid Analytics (Jul 2020 - Jul 2021)
- Developed churn prediction models with scikit-learn.
PROJECTS
Resume Screening Assistant - NLP project that ranks resumes using sentence embeddings.
EDUCATION
M.Sc Data Science, Demo Institute of Technology, 2020
B.Sc Computer Science, Demo College, 2018""",
    "kabir_singh_fullstack.docx": """Kabir Singh
kabir.singh@example.com | +91 98765 00003 | Mumbai, India
SUMMARY
Full-stack developer, 2 years of experience building React and Node applications.
SKILLS
JavaScript, React, Node.js, Express, MongoDB, HTML, CSS, Git, SQL
EXPERIENCE
Software Developer, PixelForge Studio (Mar 2023 - Present)
- Built customer portals with React and REST APIs.
Intern, CodeNest (Jan 2023 - Feb 2023)
EDUCATION
B.Tech Information Technology, Demo Engineering College, 2022""",
    "meera_iyer_fresher_python.docx": """Meera Iyer
meera.iyer@example.com | +91 98765 00004 | Chennai, India
SUMMARY
Recent graduate interested in data and machine learning.
SKILLS
Python, SQL, Pandas, scikit-learn
PROJECTS
House Price Prediction - regression model using scikit-learn and Pandas.
Sentiment Analysis - NLP project classifying product reviews.
EDUCATION
B.Sc Computer Science, Demo Women's College, 2024""",
    "rohan_gupta_senior_data_scientist.docx": """Rohan Gupta
rohan.gupta@example.com | +91 98765 00005 | Hyderabad, India
SUMMARY
Senior data scientist with 9 years of experience leading analytics and machine learning teams.
SKILLS
Python, SQL, Machine Learning, Deep Learning, Spark, Power BI, Tableau, NLP, Statistics, AWS
EXPERIENCE
Lead Data Scientist, Vertex Insights (Jan 2019 - Present)
- Led a team of 6 building forecasting and NLP solutions.
Data Scientist, Cobalt Systems (Jun 2015 - Dec 2018)
EDUCATION
M.Tech Data Science, Demo Institute of Technology, 2015
PhD (coursework only, not completed) - not listed as a degree""",
}

for filename, text in RESUMES.items():
    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    document.save(OUT / filename)

# Deliberately invalid files for test scenario 3
(OUT / "corrupted_resume.pdf").write_bytes(b"This is not a real PDF file.")
(OUT / "notes.txt").write_text("Unsupported file type used to test validation.")
print(f"Wrote {len(RESUMES)} sample resumes + 2 invalid files to {OUT}")
