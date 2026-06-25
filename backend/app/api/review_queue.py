"""
Review Queue API — Human-in-the-Loop
Lists applications that need human answers, accepts answers, then resumes auto-apply.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.base import Application, Job, Resume, User, ApplicationStatus
from app.services.auto_apply import resume_apply_with_answers
from app.services.email import notify_application_submitted, notify_application_failed
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class AnswerSubmission(BaseModel):
    answers: dict  # {field_label: answer}


@router.get("/pending")
async def get_pending_reviews(db: AsyncSession = Depends(get_db)):
    """Get all applications waiting for human input."""
    result = await db.execute(
        select(Application).where(Application.status == ApplicationStatus.awaiting_review)
    )
    apps = result.scalars().all()
    items = []
    for a in apps:
        job = (await db.execute(select(Job).where(Job.id == a.job_id))).scalar_one_or_none()
        items.append({
            "application_id": a.id,
            "job_id": a.job_id,
            "job_title": job.title if job else "",
            "company": job.company if job else "",
            "pending_questions": a.pending_questions,
            "form_data_so_far": a.form_data,
        })
    return {"pending": items}


@router.post("/{application_id}/answer")
async def submit_answers(
    application_id: str,
    submission: AnswerSubmission,
    db: AsyncSession = Depends(get_db),
):
    """Human submits answers → AI resumes application."""
    app = (await db.execute(
        select(Application).where(Application.id == application_id)
    )).scalar_one_or_none()

    if not app:
        raise HTTPException(404, "Application not found")
    if app.status != ApplicationStatus.awaiting_review:
        raise HTTPException(400, f"Application is not pending review (status: {app.status})")

    job = (await db.execute(select(Job).where(Job.id == app.job_id))).scalar_one_or_none()
    resume = (await db.execute(select(Resume).where(Resume.id == app.resume_id))).scalar_one_or_none()

    result = await resume_apply_with_answers(
        job_url=job.url,
        resume_data=resume.parsed_data,
        saved_form_data=app.form_data or {},
        human_answers=submission.answers,
    )

    app.status = ApplicationStatus.submitted if result["status"] == "submitted" else ApplicationStatus.failed
    app.form_data = result.get("form_data", app.form_data)
    app.pending_questions = []
    app.error_log = result.get("error")
    if app.status == ApplicationStatus.submitted:
        app.submitted_at = datetime.utcnow()

    await db.commit()

    # Email notification after human completes review
    if app.user_id:
        user = (await db.execute(select(User).where(User.id == app.user_id))).scalar_one_or_none()
        if user and user.email and user.email_notifications:
            if app.status == ApplicationStatus.submitted:
                await notify_application_submitted(user.email, job.title, job.company, app.id)
            else:
                await notify_application_failed(user.email, job.title, job.company, app.id, app.error_log)

    return {"status": app.status, "application_id": app.id}
