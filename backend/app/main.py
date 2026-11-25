"""FastAPI entry point. Run:  uvicorn app.main:app --reload   (from the backend folder)
Swagger API docs are generated automatically at http://localhost:8000/docs"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.models import tables  # noqa: F401  (importing registers the tables)
from app.routes import (auth_routes, candidate_routes, job_routes, matching_routes,
                        shortlist_routes, interview_routes, analytics_routes)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TalentFlow Recruitment Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

for module in (auth_routes, candidate_routes, job_routes, matching_routes, shortlist_routes,
               interview_routes, analytics_routes):
    app.include_router(module.router)
app.include_router(shortlist_routes.public_router)


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
