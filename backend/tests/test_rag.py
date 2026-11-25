import pytest

from app.config import settings
from app.database import SessionLocal
from app.models.tables import Candidate
from app.routes import matching_routes
from app.services import rag_service
from app.services.rag_service import RagGenerationError


def test_rag_endpoint_uses_retrieved_profile_without_contact_details(
    client, admin_headers, monkeypatch
):
    db = SessionLocal()
    candidate = Candidate(
        name="Demo Candidate",
        email="private@example.com",
        phone="555-0100",
        summary="Built NLP classifiers.",
        technical_skills=["Python", "NLP"],
    )
    db.add(candidate)
    db.commit()
    candidate_id = candidate.id
    db.close()

    captured = {}
    monkeypatch.setattr(matching_routes, "semantic_search", lambda _query, _top_k: [(candidate_id, 0.9)])

    def fake_answer(question, evidence):
        captured["question"] = question
        captured["evidence"] = evidence
        return f"Demo Candidate has NLP experience [candidate_id: {candidate_id}]."

    monkeypatch.setattr(matching_routes, "generate_grounded_answer", fake_answer)
    response = client.post(
        "/api/search/answer",
        headers=admin_headers,
        json={"question": "Who has NLP experience?", "top_k": 3},
    )

    assert response.status_code == 200
    assert response.json()["answer"].endswith(f"[candidate_id: {candidate_id}].")
    assert response.json()["sources"] == [
        {"candidate_id": candidate_id, "name": "Demo Candidate", "similarity": 0.9}
    ]
    assert captured["question"] == "Who has NLP experience?"
    assert "private@example.com" not in str(captured["evidence"])
    assert "555-0100" not in str(captured["evidence"])


def test_rag_provider_request_uses_retrieved_evidence(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "test-only")
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "Evidence-backed answer."}}]}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["request"] = json
        return FakeResponse()

    monkeypatch.setattr(rag_service.httpx, "post", fake_post)
    answer = rag_service.generate_grounded_answer(
        "Who has Python?",
        [{"candidate_id": 7, "skills": ["Python"]}],
    )

    assert answer == "Evidence-backed answer."
    assert "candidate_id" in captured["request"]["messages"][1]["content"]
    assert "[candidate_id: N]" in captured["request"]["messages"][0]["content"]


def test_rag_generation_requires_provider_key(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "")

    with pytest.raises(RagGenerationError, match="GROQ_API_KEY is required"):
        rag_service.generate_grounded_answer("Question?", [{"candidate_id": 1}])
