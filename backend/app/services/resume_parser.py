"""
Resume Parser Service
Extracts structured data from uploaded PDF/DOCX resumes using AI.
Uses Ollama (local, free) with OpenAI fallback.
"""
import pdfplumber
import docx
from pathlib import Path
from app.core.ai_client import chat_json


def extract_text_from_pdf(path: str) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def extract_text_from_docx(path: str) -> str:
    doc = docx.Document(path)
    return "\n".join(para.text for para in doc.paragraphs)


def extract_raw_text(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(filepath)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(filepath)
    raise ValueError(f"Unsupported file type: {ext}")


async def parse_resume_with_ai(raw_text: str) -> dict:
    """Extract structured data from resume text using AI."""
    return await chat_json(
        system=(
            "You are a resume parser. Extract structured data from the resume text. "
            "Return ONLY valid JSON with these fields: "
            "name, email, phone, location, summary, skills (array), "
            "experience (array of {title, company, duration, description}), "
            "education (array of {degree, institution, year}), "
            "preferred_roles (array), preferred_locations (array)"
        ),
        user=raw_text[:6000],  # trim to avoid context overflow on smaller models
    )

