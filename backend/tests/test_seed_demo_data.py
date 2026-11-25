from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base
from app.models.tables import Candidate, Job, Resume, User
from seed_demo_data import SAMPLE_DATA_DIR, load_demo_data
from app.services import embedding_service


def test_seed_demo_data_loads_sample_records_idempotently(monkeypatch, tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(embedding_service, "sync_job", lambda _job: None)
    monkeypatch.setattr(embedding_service, "sync_candidate", lambda _candidate: None)

    with test_session() as db:
        first = load_demo_data(db, SAMPLE_DATA_DIR)
        second = load_demo_data(db, SAMPLE_DATA_DIR)

        assert first == {
            "accounts_created": 4,
            "jobs_created": 3,
            "candidates_created": 5,
            "resumes_created": 5,
        }
        assert second == {
            "accounts_created": 0,
            "jobs_created": 0,
            "candidates_created": 0,
            "resumes_created": 0,
        }
        assert db.query(User).count() == 4
        assert db.query(Job).count() == 3
        assert db.query(Candidate).count() == 6
        assert db.query(Resume).count() == 5

    engine.dispose()
