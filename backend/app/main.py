from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import resume, jobs, applications, review_queue, auth, dashboard
from app.core.database import engine
from app.models import base

app = FastAPI(title="AI Job Application Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router, prefix="/api/resume", tags=["resume"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(review_queue.router, prefix="/api/review", tags=["review-queue"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])


@app.get("/health")
async def health():
    return {"status": "ok"}
