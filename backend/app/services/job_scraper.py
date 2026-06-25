"""
Job Scraper Service
Searches for jobs using SerpAPI (Google Jobs) + direct site APIs.
"""
import httpx
from app.core.config import settings
from typing import Optional


async def search_jobs_serpapi(query: str, location: str = "", num: int = 20) -> list[dict]:
    """Search Google Jobs via SerpAPI."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://serpapi.com/search",
            params={
                "engine": "google_jobs",
                "q": query,
                "location": location,
                "num": num,
                "api_key": settings.serpapi_key,
            },
            timeout=30,
        )
        data = resp.json()
        jobs = []
        for item in data.get("jobs_results", []):
            jobs.append({
                "title": item.get("title"),
                "company": item.get("company_name"),
                "location": item.get("location"),
                "description": item.get("description", ""),
                "url": item.get("related_links", [{}])[0].get("link", ""),
                "source": "google_jobs",
                "raw_data": item,
            })
        return jobs


async def search_jobs_remotive(query: str) -> list[dict]:
    """Search Remotive.io for remote jobs (free, no API key needed)."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": query, "limit": 20},
            timeout=30,
        )
        data = resp.json()
        jobs = []
        for item in data.get("jobs", []):
            jobs.append({
                "title": item.get("title"),
                "company": item.get("company_name"),
                "location": item.get("candidate_required_location", "Remote"),
                "description": item.get("description", ""),
                "url": item.get("url"),
                "source": "remotive",
                "raw_data": item,
            })
        return jobs


async def search_all(query: str, location: str = "") -> list[dict]:
    """Aggregate results from all sources."""
    results = []

    # Always try Remotive (free)
    try:
        results += await search_jobs_remotive(query)
    except Exception:
        pass

    # SerpAPI if key is set
    if settings.serpapi_key:
        try:
            results += await search_jobs_serpapi(query, location)
        except Exception:
            pass

    return results
