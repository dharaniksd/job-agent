from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.base import Application, Job, Resume, User, ApplicationStatus
from app.services.auto_apply import apply_to_job, resume_apply_with_answers
from app.services.email import notify_application_submitted, notify_review_needed, notify_application_failed
from pydantic import BaseModel
from datetime import datetime
import uuid

router = APIRouter()


class StartApplicationRequest(BaseModel):
    job_id: str
    resume_id: str
    user_id: str | None = None


@router.post("/start")
async def start_application(req: StartApplicationRequest, db: AsyncSession = Depends(get_db)):
    job = (await db.execute(select(Job).where(Job.id == req.job_id))).scalar_one_or_none()
    resume = (await db.execute(select(Resume).where(Resume.id == req.resume_id))).scalar_one_or_none()
    if not job or not resume:
        raise HTTPException(404, "Job or Resume not found")

    result = await apply_to_job(job.url, resume.parsed_data)

    status_map = {"submitted": ApplicationStatus.submitted, "failed": ApplicationStatus.failed, "awaiting_review": ApplicationStatus.awaiting_review}
    app = Application(
        id=str(uuid.uuid4()),
        job_id=req.job_id,
        resume_id=req.resume_id,
        user_id=req.user_id,
        status=status_map.get(result["status"], ApplicationStatus.failed),
        form_data=result.get("form_data", {}),
        pending_questions=result.get("pending_questions", []),
        error_log=result.get("error"),
        submitted_at=datetime.utcnow() if result["status"] == "submitted" else None,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)

    # Send email notification if user is linked
    user = None
    if req.user_id:
        user = (await db.execute(select(User).where(User.id == req.user_id))).scalar_one_or_none()

    if user and user.email and user.email_notifications:
        if app.status == ApplicationStatus.submitted:
            await notify_application_submitted(user.email, job.title, job.company, app.id)
        elif app.status == ApplicationStatus.awaiting_review:
            await notify_review_needed(user.email, job.title, job.company, app.id, app.pending_questions)
        elif app.status == ApplicationStatus.failed:
            await notify_application_failed(user.email, job.title, job.company, app.id, app.error_log)

    return {
        "application_id": app.id,
        "status": app.status,
        "pending_questions": app.pending_questions,
    }


@router.get("/")
async def list_applications(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).order_by(Application.created_at.desc()))
    apps = result.scalars().all()
    items = []
    for a in apps:
        job = (await db.execute(select(Job).where(Job.id == a.job_id))).scalar_one_or_none()
        items.append({
            "id": a.id,
            "status": a.status,
            "job_title": job.title if job else "",
            "company": job.company if job else "",
            "match_score": job.match_score if job else 0,
            "created_at": a.created_at,
            "submitted_at": a.submitted_at,
        })
    return {"applications": items}
