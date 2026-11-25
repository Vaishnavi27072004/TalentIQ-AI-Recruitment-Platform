"""All settings live here and are read from environment variables (.env file).
Interview tip: "Nothing secret or tunable is hardcoded - weights, limits and keys come from config."
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    # --- Database / storage ---
    database_url: str = f"sqlite:///{BACKEND_DIR / 'recruitment.db'}"
    upload_dir: str = str(BACKEND_DIR / "uploads")
    chroma_dir: str = str(BACKEND_DIR / "chroma_db")

    # --- Auth ---
    secret_key: str = "change-me-in-env"  # override in .env
    jwt_algorithm: str = "HS256"
    token_expire_minutes: int = 480
    login_max_attempts: int = 5
    login_attempt_window_seconds: int = 300

    # --- LLM (resume parsing). provider is "groq" or "gemini" ---
    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    llm_timeout_seconds: int = 60

    # --- Embeddings ---
    embedding_model_name: str = "all-MiniLM-L6-v2"

    # --- Resume upload rules ---
    max_resume_size_mb: int = 5
    allowed_resume_extensions: tuple = (".pdf", ".docx")
    min_resume_text_chars: int = 50  # below this we treat the file as empty/corrupt

    # --- Matching weights (must add up to 1.0) ---
    weight_skills: float = 0.35
    weight_experience: float = 0.25
    weight_education: float = 0.10
    weight_preferred: float = 0.10
    weight_semantic: float = 0.20

    # Cosine similarity of MiniLM text pairs rarely goes below LOW or above HIGH,
    # so we stretch that band onto 0-100 (see calculate_semantic_score).
    semantic_low: float = 0.15
    semantic_high: float = 0.75

    # Recommendation thresholds on the final 0-100 score
    strong_match_threshold: float = 75
    possible_match_threshold: float = 50

    # --- Email (SMTP). If smtp_host is empty we only write to the dev log ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "recruitment@example.com"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"


settings = Settings()
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)
