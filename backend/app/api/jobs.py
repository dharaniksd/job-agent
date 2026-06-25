from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.base import Resume, Job
from app.services.job_scraper import search_all
from app.services.job_matcher import rank_jobs
import uuid

router = APIRouter()


@router.get("/search")
async def search_and_match_jobs(
    resume_id: str,
    location: str = Query(default=""),
    threshold: float = Query(default=0.5, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(404, "Resume not found")

    parsed = resume.parsed_data
    # Build a search query from resume skills and preferred roles
    roles = parsed.get("preferred_roles", []) or [parsed.get("summary", "software engineer")]
    skills = parsed.get("skills", [])[:5]
    query = f"{roles[0]} {' '.join(skills[:3])}"

    raw_jobs = await search_all(query, location)
    matched_jobs = await rank_jobs(parsed, raw_jobs, threshold)

    # Persist matched jobs to DB
    saved = []
    for job_data in matched_jobs:
        existing = await db.execute(select(Job).where(Job.url == job_data.get("url", "")))
        if existing.scalar_one_or_none():
            continue
        job = Job(
            id=str(uuid.uuid4()),
            title=job_data.get("title"),
            company=job_data.get("company"),
            location=job_data.get("location"),
            description=job_data.get("description", ""),
            url=job_data.get("url", ""),
            source=job_data.get("source"),
            match_score=job_data.get("match_score", 0.0),
            raw_data=job_data.get("raw_data"),
        )
        db.add(job)
        saved.append(job)

    await db.commit()
    return {"jobs": [{"id": j.id, "title": j.title, "company": j.company,
                      "match_score": j.match_score, "url": j.url} for j in saved]}


@router.get("/")
async def list_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).order_by(Job.match_score.desc()).limit(50))
    return {"jobs": result.scalars().all()}
