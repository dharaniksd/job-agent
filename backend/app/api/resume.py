import os
import shutil
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.base import Resume
from app.services.resume_parser import extract_raw_text, parse_resume_with_ai
from app.core.config import settings

router = APIRouter()


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    allowed = {".pdf", ".doc", ".docx"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, "Only PDF and DOCX files are supported")

    os.makedirs(settings.upload_dir, exist_ok=True)
    filepath = os.path.join(settings.upload_dir, file.filename)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    raw_text = extract_raw_text(filepath)
    parsed_data = await parse_resume_with_ai(raw_text)

    resume = Resume(filename=file.filename, raw_text=raw_text, parsed_data=parsed_data)
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    return {"id": resume.id, "parsed": parsed_data}


@router.get("/{resume_id}")
async def get_resume(resume_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(404, "Resume not found")
    return {"id": resume.id, "filename": resume.filename, "parsed": resume.parsed_data}
