"""
Job Matcher Service
Uses AI to score job listings against resume profile.
"""
from openai import AsyncOpenAI
from app.core.config import settings
import json

client = AsyncOpenAI(api_key=settings.openai_api_key)


async def score_job(resume_data: dict, job: dict) -> float:
    """Score a job listing against the resume (0.0 - 1.0)."""
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a job matching expert. Given a resume profile and a job listing, "
                    "return a JSON object with: score (float 0-1), reason (string). "
                    "Score 1.0 = perfect match, 0.0 = no match."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "resume": resume_data,
                    "job_title": job.get("title"),
                    "job_company": job.get("company"),
                    "job_description": job.get("description", "")[:2000],
                }),
            },
        ],
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
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
