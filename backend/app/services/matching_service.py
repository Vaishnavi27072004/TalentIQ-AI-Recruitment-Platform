"""Hybrid candidate-job matching. 100% plain Python maths - the LLM is NOT involved in scoring.

FINAL SCORE = weighted sum of five 0-100 components (weights come from config):
    skills 35% + experience 25% + education 10% + preferred skills 10% + semantic 20%

If a component does not apply (e.g. the job lists no preferred skills) it is dropped and the
remaining weights are re-scaled to add up to 100%, so a job is never punished for what it did not ask.

Interview explanation for every function: input -> output -> rule, shown in each docstring.
"""
import re
from app.config import settings

# Small alias table so "ML" == "machine learning". Extend as needed.
SKILL_ALIASES = {
    "ml": "machine learning", "dl": "deep learning", "js": "javascript", "ts": "typescript",
    "nlp": "natural language processing", "postgres": "postgresql", "sklearn": "scikit-learn",
    "powerbi": "power bi", "reactjs": "react", "node": "node.js", "nodejs": "node.js",
    "tf": "tensorflow", "py": "python", "k8s": "kubernetes",
}

# Education levels, highest wins. Order matters only for display.
EDUCATION_LEVELS = [
    (4, ["phd", "ph.d", "doctorate", "doctoral"]),
    (3, ["master", "m.sc", "msc", "m.tech", "mtech", "mba", "m.e", "m.s.", "mca"]),
    (2, ["bachelor", "b.sc", "bsc", "b.tech", "btech", "b.e", "b.s.", "bca", "b.com", "bcom", "undergraduate", "degree"]),
    (1, ["diploma", "associate", "certificate"]),
]


def normalize_skill(skill: str) -> str:
    cleaned = re.sub(r"\s+", " ", skill.strip().lower())
    return SKILL_ALIASES.get(cleaned, cleaned)


def skill_is_present(required_skill: str, candidate_skills: set[str], candidate_text: str) -> bool:
    """A skill counts if it is in the candidate's skill list, OR written as a whole word in
    their projects/experience text (people mention skills inside project descriptions)."""
    skill = normalize_skill(required_skill)
    if skill in candidate_skills:
        return True
    return re.search(rf"(?<![a-z0-9]){re.escape(skill)}(?![a-z0-9])", candidate_text) is not None


def split_skills(required_skills: list[str], candidate_skills: list[str], candidate_text: str):
    """Return (matched, missing) lists, keeping the job's original spelling."""
    skill_set = {normalize_skill(s) for s in candidate_skills or []}
    text = (candidate_text or "").lower()
    matched, missing = [], []
    for skill in required_skills or []:
        (matched if skill_is_present(skill, skill_set, text) else missing).append(skill)
    return matched, missing


def calculate_skill_score(required_skills: list[str], candidate_skills: list[str], candidate_text: str = ""):
    """Input: job required skills + candidate skills. Output: (score 0-100 or None, matched, missing).
    Rule: percentage of required skills the candidate has."""
    if not required_skills:
        return None, [], []
    matched, missing = split_skills(required_skills, candidate_skills, candidate_text)
    return round(100 * len(matched) / len(required_skills), 1), matched, missing


def calculate_preferred_score(preferred_skills: list[str], candidate_skills: list[str], candidate_text: str = ""):
    """Same rule as skills but for the nice-to-have list."""
    if not preferred_skills:
        return None, [], []
    matched, missing = split_skills(preferred_skills, candidate_skills, candidate_text)
    return round(100 * len(matched) / len(preferred_skills), 1), matched, missing


OVERQUALIFIED_PENALTY_PER_YEAR = 5   # points lost per year above the job's maximum
OVERQUALIFIED_MIN_SCORE = 70         # never punish extra experience below this


def calculate_experience_score(candidate_years: float | None, min_years: float, max_years: float | None) -> float | None:
    """Input: candidate years, job min/max. Output: 0-100.
    Rule: below minimum -> proportional (2 of 4 years = 50). Inside range -> 100.
    Above maximum -> small penalty, floored at 70."""
    years = candidate_years or 0
    if not min_years and max_years is None:
        return None  # job did not specify experience
    if min_years and years < min_years:
        return round(100 * years / min_years, 1)
    if max_years is not None and years > max_years:
        penalty = (years - max_years) * OVERQUALIFIED_PENALTY_PER_YEAR
        return max(OVERQUALIFIED_MIN_SCORE, round(100 - penalty, 1))
    return 100.0


def education_level_from_text(text: str) -> int:
    """Find the highest level mentioned in a text. 0 = nothing recognised."""
    lowered = (text or "").lower()
    for level, keywords in EDUCATION_LEVELS:
        if any(re.search(rf"(?<![a-z]){re.escape(word)}", lowered) for word in keywords):
            return level
    return 0


def candidate_education_level(education: list[dict]) -> int:
    levels = [education_level_from_text(f"{item.get('degree') or ''}") for item in education or []]
    return max(levels, default=0)


def calculate_education_score(candidate_education: list[dict], education_requirement: str) -> float | None:
    """Input: candidate education list, job requirement text. Output: 0-100.
    Rule: meets/exceeds required level = 100, otherwise level ratio (Bachelor vs Master req = 66.7)."""
    required_level = education_level_from_text(education_requirement)
    if required_level == 0:
        return None  # requirement empty or not recognisable
    candidate_level = candidate_education_level(candidate_education)
    if candidate_level >= required_level:
        return 100.0
    return round(100 * candidate_level / required_level, 1)


def calculate_semantic_score(cosine_similarity: float | None) -> float | None:
    """Input: raw cosine similarity (-1..1). Output: 0-100.
    Why normalise: MiniLM similarity between a resume and a job rarely leaves ~0.15..0.75,
    so raw 0.45 would look like a 45 even though it is a decent match. We stretch that band:
        score = (sim - LOW) / (HIGH - LOW) * 100, clipped to 0..100."""
    if cosine_similarity is None:
        return None
    span = settings.semantic_high - settings.semantic_low
    stretched = (cosine_similarity - settings.semantic_low) / span * 100
    return round(min(100.0, max(0.0, stretched)), 1)


def get_weights() -> dict:
    return {
        "skills": settings.weight_skills, "experience": settings.weight_experience,
        "education": settings.weight_education, "preferred": settings.weight_preferred,
        "semantic": settings.weight_semantic,
    }


def calculate_final_match_score(component_scores: dict) -> float:
    """Input: {"skills": 80, "experience": None, ...}. Output: weighted 0-100.
    Components that are None are skipped and the other weights are re-scaled."""
    weights = get_weights()
    available = {name: score for name, score in component_scores.items() if score is not None}
    total_weight = sum(weights[name] for name in available)
    if total_weight == 0:
        return 0.0
    weighted_sum = sum(score * weights[name] for name, score in available.items())
    return round(weighted_sum / total_weight, 1)


def recommend_from_score(final_score: float) -> str:
    if final_score >= settings.strong_match_threshold:
        return "Strong Match"
    if final_score >= settings.possible_match_threshold:
        return "Possible Match"
    return "Weak Match"


def build_explanation(candidate, job, details: dict) -> str:
    """Explanation assembled from REAL numbers and lists (no LLM, so it cannot hallucinate)."""
    parts = []
    required_total = len(details["matched_skills"]) + len(details["missing_skills"])
    if required_total:
        parts.append(f"Has {len(details['matched_skills'])} of {required_total} required skills"
                     + (f" ({', '.join(details['matched_skills'])})" if details["matched_skills"] else "") + ".")
    if details["missing_skills"]:
        parts.append(f"Missing: {', '.join(details['missing_skills'])}.")
    if details["scores"]["experience"] is not None:
        max_text = f"-{job.max_experience:g}" if job.max_experience is not None else "+"
        parts.append(f"Experience: {candidate.total_experience_years or 0:g} years vs {job.min_experience:g}{max_text} required.")
    if details["scores"]["education"] is not None:
        parts.append(f"Education score {details['scores']['education']:g}/100 against requirement '{job.education_requirement}'.")
    if details["semantic_similarity"] is not None:
        parts.append(f"Resume-to-job semantic similarity is {details['semantic_similarity']:.2f} "
                     f"({details['scores']['semantic']:g}/100 after normalisation).")
    return " ".join(parts)


def _candidate_text(candidate) -> str:
    """Free text where skills may be mentioned (projects, work history, summary)."""
    pieces = [candidate.summary or ""]
    pieces += [f"{p.get('name') or ''} {p.get('description') or ''}" for p in candidate.projects or []]
    pieces += [f"{j.get('title') or ''} {j.get('description') or ''}" for j in candidate.employment_history or []]
    return " ".join(pieces)


def match_candidate_to_job(candidate, job, cosine_similarity: float | None) -> dict:
    """Run all components for one candidate and return a JSON-friendly result."""
    text = _candidate_text(candidate)
    skill_score, matched, missing = calculate_skill_score(job.required_skills, candidate.technical_skills, text)
    preferred_score, preferred_matched, preferred_missing = calculate_preferred_score(
        job.preferred_skills, candidate.technical_skills, text)
    scores = {
        "skills": skill_score,
        "experience": calculate_experience_score(candidate.total_experience_years, job.min_experience, job.max_experience),
        "education": calculate_education_score(candidate.education, job.education_requirement),
        "preferred": preferred_score,
        "semantic": calculate_semantic_score(cosine_similarity),
    }
    final_score = calculate_final_match_score(scores)
    details = {
        "scores": scores, "weights": get_weights(),
        "matched_skills": matched, "missing_skills": missing,
        "preferred_matched": preferred_matched, "preferred_missing": preferred_missing,
        "candidate_experience_years": candidate.total_experience_years or 0,
        "job_min_experience": job.min_experience, "job_max_experience": job.max_experience,
        "semantic_similarity": cosine_similarity,
    }
    details["explanation"] = build_explanation(candidate, job, details)
    return {"final_score": final_score, "recommendation": recommend_from_score(final_score), "details": details}
