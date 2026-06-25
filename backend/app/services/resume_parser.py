"""
Resume Parser Service
Extracts structured data from uploaded PDF/DOCX resumes using AI.
"""
import pdfplumber
import docx
from pathlib import Path
from openai import AsyncOpenAI
from app.core.config import settings
import json

client = AsyncOpenAI(api_key=settings.openai_api_key)


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
    """Use GPT-4 to extract structured data from resume text."""
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a resume parser. Extract structured data from the resume text. "
                    "Return ONLY valid JSON with these fields: "
                    "name, email, phone, location, summary, skills (array), "
                    "experience (array of {title, company, duration, description}), "
                    "education (array of {degree, institution, year}), "
                    "preferred_roles (array), preferred_locations (array)"
                ),
            },
            {"role": "user", "content": raw_text},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)
