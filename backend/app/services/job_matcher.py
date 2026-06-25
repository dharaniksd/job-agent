"""
Job Matcher Service
Uses AI to score job listings against resume profile.
Uses Ollama (local, free) with OpenAI fallback.
"""
import json
from app.core.ai_client import chat_json


async def score_job(resume_data: dict, job: dict) -> float:
    """Score a job listing against the resume (0.0 - 1.0)."""
    result = await chat_json(
        system=(
            "You are a job matching expert. Given a resume profile and a job listing, "
            "return a JSON object with: score (float 0-1), reason (string). "
            "Score 1.0 = perfect match, 0.0 = no match."
        ),
        user=json.dumps({
            "resume": resume_data,
            "job_title": job.get("title"),
            "job_company": job.get("company"),
            "job_description": job.get("description", "")[:2000],
        }),
    )
    return float(result.get("score", 0.0))


async def rank_jobs(resume_data: dict, jobs: list[dict], threshold: float = 0.5) -> list[dict]:
    """Score and filter jobs above threshold, sorted by score."""
    scored = []
    for job in jobs:
        score = await score_job(resume_data, job)
        if score >= threshold:
            job["match_score"] = score
            scored.append(job)
    return sorted(scored, key=lambda x: x["match_score"], reverse=True)
