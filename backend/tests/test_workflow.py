"""End-to-end API tests that mirror the 12 mandatory assessment scenarios."""
from datetime import datetime, timedelta, timezone

from tests.conftest import (login, register_candidate, resume_file, JOB_PAYLOAD)


def test_s1_candidate_uploads_resume_profile_created(client):
    headers = register_candidate(client, "Asha Rao", "asha@example.com")
    response = client.post("/api/candidates/me/resume", headers=headers, files={"file": resume_file("Asha Rao", "asha@example.com", 3)})
    assert response.status_code == 200, response.text
    profile = response.json()["profile"]
    assert "Python" in profile["technical_skills"] and profile["total_experience_years"] == 3


def test_candidate_can_correct_extracted_data(client):
    headers = register_candidate(client, "Asha Rao", "asha@example.com")
    client.post("/api/candidates/me/resume", headers=headers, files={"file": resume_file("Asha Rao", "asha@example.com")})
    response = client.put("/api/candidates/me", headers=headers, json={"technical_skills": ["Python", "Spark"]})
    assert response.json()["technical_skills"] == ["Python", "Spark"]


def test_resume_reupload_preserves_existing_fields_when_parser_has_no_value(client, monkeypatch):
    from app.schemas.schemas import ParsedResume
    from app.services import resume_pipeline

    headers = register_candidate(client, "Asha Rao", "asha@example.com")
    client.post("/api/candidates/me/resume", headers=headers,
                files={"file": resume_file("Asha Rao", "asha@example.com")})
    monkeypatch.setattr(resume_pipeline, "parse_resume", lambda _text: ParsedResume())

    response = client.post("/api/candidates/me/resume", headers=headers,
                           files={"file": resume_file("Asha Rao", "asha@example.com")})
    assert response.status_code == 200
    profile = response.json()["profile"]
    assert "Python" in profile["technical_skills"]
    assert profile["summary"] == "Test summary"
    assert profile["total_experience_years"] == 3


def test_s2_s3_bulk_upload_handles_bad_file_without_stopping(client, admin_headers):
    files = [("files", resume_file(f"Person {i}", f"person{i}@example.com")) for i in range(5)]
    files.insert(2, ("files", ("broken.pdf", b"this is not a real pdf", "application/pdf")))
    files.append(("files", ("notes.txt", b"hello", "text/plain")))
    results = client.post("/api/candidates/bulk-upload", headers=admin_headers, files=files).json()
    statuses = [r["status"] for r in results]
    assert statuses.count("completed") == 5          # all 5 good resumes processed individually
    assert statuses.count("failed") == 2             # corrupted PDF + unsupported type, both reported
    assert len(client.get("/api/candidates", headers=admin_headers).json()) == 5


def test_duplicate_resume_detected_by_normalised_email(client, admin_headers):
    first = client.post("/api/candidates/bulk-upload", headers=admin_headers, files=[("files", resume_file(email="Dup@Example.com"))]).json()
    second = client.post("/api/candidates/bulk-upload", headers=admin_headers, files=[("files", resume_file(email=" dup@example.com "))]).json()
    assert first[0]["status"] == "completed" and second[0]["status"] == "duplicate"


def test_s4_admin_creates_job(client, admin_headers):
    response = client.post("/api/jobs", headers=admin_headers, json=JOB_PAYLOAD)
    assert response.status_code == 200
    job = response.json()
    assert job["required_skills"] == ["Python", "SQL", "Power BI"] and job["min_experience"] == 2


def test_job_rejects_maximum_experience_below_minimum(client, admin_headers):
    payload = {**JOB_PAYLOAD, "min_experience": 5, "max_experience": 2}
    assert client.post("/api/jobs", headers=admin_headers, json=payload).status_code == 422


def test_candidates_cannot_create_jobs(client):
    headers = register_candidate(client, "Asha Rao", "asha@example.com")
    assert client.post("/api/jobs", headers=headers, json=JOB_PAYLOAD).status_code == 403


def test_duplicate_application_blocked(client, admin_headers):
    job_id = client.post("/api/jobs", headers=admin_headers, json=JOB_PAYLOAD).json()["id"]
    headers = register_candidate(client, "Asha Rao", "asha@example.com")
    client.post("/api/candidates/me/resume", headers=headers, files={"file": resume_file("Asha Rao", "asha@example.com")})
    assert client.post(f"/api/jobs/{job_id}/apply", headers=headers).status_code == 200
    assert client.post(f"/api/jobs/{job_id}/apply", headers=headers).status_code == 409


def test_s5_s7_matching_ranks_candidates_with_explanation(client, admin_headers):
    job_id = client.post("/api/jobs", headers=admin_headers, json=JOB_PAYLOAD).json()["id"]
    client.post("/api/candidates/bulk-upload", headers=admin_headers, files=[
        ("files", resume_file("Strong", "strong@example.com", years=3)),
        ("files", resume_file("Junior", "junior@example.com", years=0))])
    ranked = client.post(f"/api/matching/jobs/{job_id}/run", headers=admin_headers).json()
    assert ranked[0]["name"] == "Strong" and ranked[0]["final_score"] > ranked[1]["final_score"]
    details = ranked[0]["details"]
    assert details["missing_skills"] == ["Power BI"] and "Power BI" in details["explanation"]


def test_admin_override_is_kept_after_recalculation(client, admin_headers):
    job_id = client.post("/api/jobs", headers=admin_headers, json=JOB_PAYLOAD).json()["id"]
    client.post("/api/candidates/bulk-upload", headers=admin_headers, files=[("files", resume_file())])
    match = client.post(f"/api/matching/jobs/{job_id}/run", headers=admin_headers).json()[0]
    client.put(f"/api/matching/{match['match_id']}/override", headers=admin_headers, json={"decision": "Strong Match", "reason": "Great portfolio"})
    again = client.post(f"/api/matching/jobs/{job_id}/run", headers=admin_headers).json()[0]
    assert again["admin_override"] == "Strong Match" and again["effective_recommendation"] == "Strong Match"


def _setup_shortlisted_candidate(client, admin_headers):
    job_id = client.post("/api/jobs", headers=admin_headers, json=JOB_PAYLOAD).json()["id"]
    candidate_headers = register_candidate(client, "Asha Rao", "asha@example.com")
    client.post("/api/candidates/me/resume", headers=candidate_headers, files={"file": resume_file("Asha Rao", "asha@example.com")})
    candidate_id = client.get("/api/candidates/me", headers=candidate_headers).json()["id"]
    client.post("/api/shortlist", headers=admin_headers, json={"job_id": job_id, "candidate_ids": [candidate_id]})
    application_id = client.get("/api/shortlist", headers=admin_headers).json()[0]["id"]
    return job_id, candidate_id, application_id, candidate_headers


def test_s8_shortlisting_and_export(client, admin_headers):
    job_id, candidate_id, _app, _h = _setup_shortlisted_candidate(client, admin_headers)
    rows = client.get(f"/api/shortlist?job_id={job_id}", headers=admin_headers).json()
    assert rows[0]["candidate_id"] == candidate_id
    csv_response = client.get(f"/api/shortlist/export?job_id={job_id}&format=csv", headers=admin_headers)
    assert "Asha Rao" in csv_response.text
    assert client.get(f"/api/shortlist/export?job_id={job_id}&format=xlsx", headers=admin_headers).status_code == 200


def test_s9_s10_s11_approve_schedule_feedback(client, admin_headers, interviewer_headers):
    _job, _cand, application_id, candidate_headers = _setup_shortlisted_candidate(client, admin_headers)
    approve = client.post(f"/api/shortlist/{application_id}/approve", headers=admin_headers).json()
    assert approve["status"] == "approved_for_interview"
    assert any("approved" in n["message"].lower() for n in client.get("/api/notifications", headers=candidate_headers).json())

    interviewer_id = client.get("/api/auth/interviewers", headers=admin_headers).json()[0]["id"]
    payload = {"application_id": application_id, "interviewer_id": interviewer_id, "scheduled_at": "2030-01-15T10:00:00+05:30",
               "duration_minutes": 45, "interview_type": "Technical", "meeting_link": "https://meet.example.com/abc"}
    interview = client.post("/api/interviews", headers=admin_headers, json=payload)
    assert interview.status_code == 200, interview.text
    assert interview.json()["scheduled_at"].endswith("+00:00")
    interview_id = interview.json()["id"]

    # candidate sees it (and NOT the feedback field)
    mine = client.get("/api/interviews", headers=candidate_headers).json()
    assert mine[0]["meeting_link"] == "https://meet.example.com/abc" and "feedback" not in mine[0]

    # double-booking the same interviewer is rejected
    clash = client.post("/api/interviews", headers=admin_headers, json=payload)
    assert clash.status_code == 409

    feedback = {"technical_score": 4, "communication_score": 5, "problem_solving_score": 4,
                "remarks": "Strong fundamentals", "recommendation": "Recommended"}
    assert client.post(f"/api/interviews/{interview_id}/feedback", headers=interviewer_headers, json=feedback).status_code == 200
    seen_by_admin = client.get("/api/interviews", headers=admin_headers).json()[0]
    assert seen_by_admin["feedback"]["recommendation"] == "Recommended"


def test_past_interview_schedule_and_reschedule_are_rejected(client, admin_headers):
    _job, _candidate, application_id, _candidate_headers = _setup_shortlisted_candidate(client, admin_headers)
    client.post(f"/api/shortlist/{application_id}/approve", headers=admin_headers)
    interviewer_id = client.get("/api/auth/interviewers", headers=admin_headers).json()[0]["id"]

    past_schedule = {
        "application_id": application_id,
        "interviewer_id": interviewer_id,
        "scheduled_at": "2020-01-15T10:00:00",
    }
    assert client.post("/api/interviews", headers=admin_headers, json=past_schedule).status_code == 422

    future_schedule = {**past_schedule, "scheduled_at": "2030-01-15T10:00:00"}
    interview = client.post("/api/interviews", headers=admin_headers, json=future_schedule)
    assert interview.status_code == 200, interview.text
    response = client.put(
        f"/api/interviews/{interview.json()['id']}/reschedule",
        headers=admin_headers,
        json={"scheduled_at": "2020-01-15T10:00:00"},
    )
    assert response.status_code == 422


def test_notification_read_all_marks_user_notifications_read(client, admin_headers):
    job_id = client.post("/api/jobs", headers=admin_headers, json=JOB_PAYLOAD).json()["id"]
    candidate_headers = register_candidate(client, "Asha Rao", "asha@example.com")
    client.post(f"/api/candidates/me/resume", headers=candidate_headers,
                files={"file": resume_file("Asha Rao", "asha@example.com")})
    client.post(f"/api/jobs/{job_id}/apply", headers=candidate_headers)

    notifications = client.get("/api/notifications", headers=candidate_headers).json()
    assert notifications and not notifications[0]["is_read"]
    assert client.post("/api/notifications/read-all", headers=candidate_headers).status_code == 200
    assert all(item["is_read"] for item in client.get("/api/notifications", headers=candidate_headers).json())


def test_feedback_only_by_assigned_interviewer(client, admin_headers):
    _job, _cand, application_id, _h = _setup_shortlisted_candidate(client, admin_headers)
    client.post(f"/api/shortlist/{application_id}/approve", headers=admin_headers)
    interviewers = client.get("/api/auth/interviewers", headers=admin_headers).json()
    interview_id = client.post("/api/interviews", headers=admin_headers, json={
        "application_id": application_id, "interviewer_id": interviewers[0]["id"], "scheduled_at": "2030-01-15T10:00:00"}).json()["id"]
    other = login(client, "int2@test.com", "Interview@2")
    body = {"technical_score": 3, "communication_score": 3, "problem_solving_score": 3, "recommendation": "On Hold"}
    assert client.post(f"/api/interviews/{interview_id}/feedback", headers=other, json=body).status_code == 403


def test_s12_candidate_cannot_view_another_candidate(client, admin_headers):
    first = register_candidate(client, "Asha Rao", "asha@example.com")
    second = register_candidate(client, "Ravi Kumar", "ravi@example.com")
    second_id = client.get("/api/candidates/me", headers=second).json()["id"]
    first_id = client.get("/api/candidates/me", headers=first).json()["id"]
    assert client.get(f"/api/candidates/{second_id}", headers=first).status_code == 403
    assert client.get(f"/api/candidates/{first_id}", headers=first).status_code == 200
    assert client.get("/api/candidates", headers=first).status_code == 403  # admin list is blocked too


def test_interviewer_cannot_open_unassigned_candidate(client, admin_headers, interviewer_headers):
    candidate_headers = register_candidate(client, "Asha Rao", "asha@example.com")
    candidate_id = client.get("/api/candidates/me", headers=candidate_headers).json()["id"]
    assert client.get(f"/api/candidates/{candidate_id}", headers=interviewer_headers).status_code == 403


def test_requests_without_token_are_rejected(client):
    assert client.get("/api/candidates").status_code == 401


def test_password_reset_request_does_not_reveal_user(client):
    unknown = client.post("/api/auth/password-reset/request", json={"email": "unknown@example.com"})
    assert unknown.status_code == 200
    assert "if the email exists" in unknown.json()["message"].lower()


def test_dashboard_numbers_come_from_database(client, admin_headers):
    client.post("/api/jobs", headers=admin_headers, json=JOB_PAYLOAD)
    client.post("/api/candidates/bulk-upload", headers=admin_headers, files=[("files", resume_file())])
    kpis = client.get("/api/analytics/dashboard", headers=admin_headers).json()["kpis"]
    assert kpis["total_candidates"] == 1 and kpis["active_jobs"] == 1 and kpis["total_resumes"] == 1


def test_dashboard_interviewed_funnel_counts_completed_interviews_only(client, admin_headers, interviewer_headers):
    _job, _candidate, application_id, _candidate_headers = _setup_shortlisted_candidate(client, admin_headers)
    client.post(f"/api/shortlist/{application_id}/approve", headers=admin_headers)
    interviewer_id = client.get("/api/auth/interviewers", headers=admin_headers).json()[0]["id"]
    interview = client.post("/api/interviews", headers=admin_headers, json={
        "application_id": application_id,
        "interviewer_id": interviewer_id,
        "scheduled_at": "2030-01-15T10:00:00+05:30",
    })
    assert interview.status_code == 200, interview.text

    dashboard = client.get("/api/analytics/dashboard", headers=admin_headers).json()
    funnel = {row["stage"]: row["count"] for row in dashboard["funnel"]}
    assert funnel["Interviewed"] == 0

    feedback = {"technical_score": 4, "communication_score": 4, "problem_solving_score": 4,
                "remarks": "Completed interview", "recommendation": "Recommended"}
    completed = client.post(f"/api/interviews/{interview.json()['id']}/feedback",
                            headers=interviewer_headers, json=feedback)
    assert completed.status_code == 200, completed.text

    dashboard = client.get("/api/analytics/dashboard", headers=admin_headers).json()
    funnel = {row["stage"]: row["count"] for row in dashboard["funnel"]}
    assert funnel["Interviewed"] == 1
    assert dashboard["conversion_rates"]["interviewed"] == 100.0


def test_dashboard_date_range_uses_each_record_event_date(client, admin_headers):
    _job, _candidate, application_id, _candidate_headers = _setup_shortlisted_candidate(client, admin_headers)
    client.post(f"/api/shortlist/{application_id}/approve", headers=admin_headers)
    interviewer_id = client.get("/api/auth/interviewers", headers=admin_headers).json()[0]["id"]
    scheduled = client.post("/api/interviews", headers=admin_headers, json={
        "application_id": application_id,
        "interviewer_id": interviewer_id,
        "scheduled_at": "2030-01-15T10:00:00+05:30",
    })
    assert scheduled.status_code == 200, scheduled.text

    now = datetime.now(timezone.utc)
    current_period = {
        "start_at": (now - timedelta(days=1)).isoformat(),
        "end_at": (now + timedelta(days=1)).isoformat(),
    }
    data = client.get("/api/analytics/dashboard", headers=admin_headers, params=current_period).json()
    assert data["kpis"]["total_applications"] == 1
    assert data["kpis"]["scheduled_interviews"] == 0
    assert data["interview_stats"] == [
        {"status": "scheduled", "count": 0},
        {"status": "completed", "count": 0},
        {"status": "cancelled", "count": 0},
    ]
    assert data["resume_processing"] == {"completed": 1}
    assert data["conversion_rates"] == {"shortlisted": 100.0, "interviewed": 0.0, "selected": 0.0}

    future_period = {
        "start_at": "2030-01-15T00:00:00+05:30",
        "end_at": "2030-01-16T00:00:00+05:30",
    }
    future_data = client.get("/api/analytics/dashboard", headers=admin_headers, params=future_period).json()
    assert future_data["kpis"]["total_applications"] == 0
    assert future_data["kpis"]["scheduled_interviews"] == 1
    assert future_data["interview_stats"][0] == {"status": "scheduled", "count": 1}

    invalid_period = client.get("/api/analytics/dashboard", headers=admin_headers, params={
        "start_at": "2030-01-16T00:00:00Z",
        "end_at": "2030-01-15T00:00:00Z",
    })
    assert invalid_period.status_code == 422


def test_shared_shortlist_link_works_and_hides_email(client, admin_headers):
    job_id, *_ = _setup_shortlisted_candidate(client, admin_headers)
    token = client.post(f"/api/shortlist/share/{job_id}", headers=admin_headers).json()["token"]
    rows = client.get(f"/api/shared/shortlist?token={token}").json()
    assert rows[0]["candidate_name"] == "Asha Rao" and "candidate_email" not in rows[0]
    assert client.get("/api/shared/shortlist?token=garbage").status_code == 401
