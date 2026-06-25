"""
Dashboard Stats API
Returns aggregate statistics for the dashboard UI.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.core.database import get_db
from app.models.base import Application, Job, ApplicationStatus
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    # Total applications
    total = (await db.execute(select(func.count(Application.id)))).scalar() or 0

    # By status
    status_counts = {}
    for status in ApplicationStatus:
        count = (await db.execute(
            select(func.count(Application.id)).where(Application.status == status)
        )).scalar() or 0
        status_counts[status.value] = count

    # Submitted today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
    submitted_today = (await db.execute(
        select(func.count(Application.id))
        .where(Application.status == ApplicationStatus.submitted)
        .where(Application.submitted_at >= today_start)
    )).scalar() or 0

    # Top companies applied to
    top_companies_raw = await db.execute(
        select(Job.company, func.count(Application.id).label("count"))
        .join(Application, Application.job_id == Job.id)
        .where(Application.status == ApplicationStatus.submitted)
        .group_by(Job.company)
        .order_by(func.count(Application.id).desc())
        .limit(5)
    )
    top_companies = [{"company": row[0], "count": row[1]} for row in top_companies_raw]

    # Daily applications last 14 days
    daily_raw = await db.execute(
        select(
            func.date(Application.created_at).label("day"),
            func.count(Application.id).label("count")
        )
        .where(Application.created_at >= datetime.utcnow() - timedelta(days=14))
        .group_by(func.date(Application.created_at))
        .order_by(func.date(Application.created_at))
    )
    daily_activity = [{"date": str(row[0]), "count": row[1]} for row in daily_raw]

    # Average match score for submitted jobs
    avg_score = (await db.execute(
        select(func.avg(Job.match_score))
        .join(Application, Application.job_id == Job.id)
        .where(Application.status == ApplicationStatus.submitted)
    )).scalar()

    # Success rate
    success_rate = round((status_counts.get("submitted", 0) / total * 100), 1) if total > 0 else 0

    return {
        "total_applications": total,
        "status_counts": status_counts,
        "submitted_today": submitted_today,
        "top_companies": top_companies,
        "daily_activity": daily_activity,
        "avg_match_score": round(float(avg_score or 0) * 100, 1),
        "success_rate": success_rate,
    }
