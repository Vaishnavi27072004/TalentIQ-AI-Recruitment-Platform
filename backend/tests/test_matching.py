"""Unit tests for the scoring maths (no database, no AI model needed)."""
from types import SimpleNamespace

from app.services import matching_service as m


def test_skill_score_counts_matched_and_missing():
    score, matched, missing = m.calculate_skill_score(["Python", "SQL", "Power BI"], ["python", "sql"])
    assert score == 66.7 and matched == ["Python", "SQL"] and missing == ["Power BI"]


def test_skill_alias_and_text_mention():
    score, matched, _ = m.calculate_skill_score(["Machine Learning", "Power BI"], ["ML"], "built dashboards in Power BI")
    assert score == 100.0 and len(matched) == 2


def test_no_invented_skills():
    _, matched, missing = m.calculate_skill_score(["Kubernetes"], ["python"], "python scripts")
    assert matched == [] and missing == ["Kubernetes"]


def test_experience_score_rules():
    assert m.calculate_experience_score(1, 2, 5) == 50.0      # below minimum: proportional
    assert m.calculate_experience_score(3, 2, 5) == 100.0     # inside range
    assert m.calculate_experience_score(7, 2, 5) == 90.0      # 2 years over -> -10
    assert m.calculate_experience_score(20, 2, 5) == 70       # floor at 70
    assert m.calculate_experience_score(3, 0, None) is None   # job did not specify


def test_education_score_rules():
    bachelors = [{"degree": "B.Sc Computer Science"}]
    assert m.calculate_education_score(bachelors, "Bachelor's degree") == 100.0
    assert m.calculate_education_score(bachelors, "Master's degree") == 66.7
    assert m.calculate_education_score([{"degree": "PhD"}], "Master's degree") == 100.0
    assert m.calculate_education_score(bachelors, "") is None


def test_semantic_score_is_normalised_and_clipped():
    assert m.calculate_semantic_score(0.45) == 50.0
    assert m.calculate_semantic_score(0.95) == 100.0
    assert m.calculate_semantic_score(-0.2) == 0.0
    assert m.calculate_semantic_score(None) is None


def test_final_score_uses_required_skill_percentage():
    scores = {"skills": 100, "experience": 100, "education": 100, "preferred": 100, "semantic": 100}
    assert m.calculate_final_match_score(scores) == 100.0
    scores = {"skills": 70, "experience": 0, "education": 0, "preferred": 0, "semantic": 0}
    assert m.calculate_final_match_score(scores) == 70.0


def test_final_score_uses_weighted_fallback_when_required_skills_are_absent():
    scores = {"skills": None, "experience": 0, "education": 100, "preferred": None, "semantic": 100}
    assert m.calculate_final_match_score(scores) == 54.5


def test_seven_of_ten_required_skills_produces_seventy_percent():
    candidate = SimpleNamespace(
        technical_skills=["Python", "SQL", "Pandas", "NumPy", "Git", "Docker", "AWS"],
        total_experience_years=1,
        education=[],
        summary="",
        projects=[],
        employment_history=[],
    )
    job = SimpleNamespace(
        required_skills=["Python", "SQL", "Pandas", "NumPy", "Git", "Docker", "AWS", "Spark", "Airflow", "Linux"],
        preferred_skills=[],
        min_experience=5,
        max_experience=None,
        education_requirement="",
    )

    result = m.match_candidate_to_job(candidate, job, 0.1)

    assert len(result["details"]["matched_skills"]) == 7
    assert result["final_score"] == 70.0


def test_full_match_builds_explanation_from_real_data():
    candidate = SimpleNamespace(technical_skills=["Python", "SQL"], total_experience_years=3, education=[{"degree": "B.Tech"}],
                                summary="", projects=[], employment_history=[])
    job = SimpleNamespace(required_skills=["Python", "SQL", "Spark"], preferred_skills=[], min_experience=2,
                          max_experience=5, education_requirement="Bachelor", title="DE")
    result = m.match_candidate_to_job(candidate, job, 0.5)
    assert result["details"]["missing_skills"] == ["Spark"]
    assert "Spark" in result["details"]["explanation"]
    assert 0 <= result["final_score"] <= 100
