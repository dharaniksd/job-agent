"""
Auto Apply Service — Human-in-the-Loop
Uses Playwright to fill job application forms.
When AI can't answer a question, it flags it for human review.
"""
from playwright.async_api import async_playwright
from openai import AsyncOpenAI
from app.core.config import settings
import json

client = AsyncOpenAI(api_key=settings.openai_api_key)

# Questions AI knows how to answer from resume
KNOWN_FIELDS = {
    "first_name", "last_name", "email", "phone", "location",
    "linkedin", "github", "portfolio", "resume", "cover_letter",
    "years_of_experience", "current_company", "current_title",
}


async def ai_fill_field(field_label: str, field_type: str, resume_data: dict) -> dict:
    """
    Ask AI to fill a form field from resume data.
    Returns: {"answer": str, "confident": bool, "reason": str}
    """
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are filling a job application form. Given a form field and resume data, "
                    "provide the best answer. Return JSON: {answer: string, confident: boolean, reason: string}. "
                    "Set confident=false if you cannot determine the answer from the resume, "
                    "or if the question requires a personal preference/opinion the user should answer."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "field_label": field_label,
                    "field_type": field_type,
                    "resume_data": resume_data,
                }),
            },
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


async def apply_to_job(job_url: str, resume_data: dict) -> dict:
    """
    Attempt to auto-apply to a job.
    Returns: {
        status: "submitted" | "awaiting_review" | "failed",
        form_data: dict,
        pending_questions: list
    }
    """
    form_data = {}
    pending_questions = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(job_url, timeout=30000)

            # Find all form fields
            fields = await page.query_selector_all("input, textarea, select")

            for field in fields:
                label = await field.get_attribute("placeholder") or \
                        await field.get_attribute("name") or \
                        await field.get_attribute("aria-label") or ""
                field_type = await field.get_attribute("type") or "text"

                if not label or field_type in ("submit", "hidden", "file"):
                    continue

                result = await ai_fill_field(label, field_type, resume_data)

                if result.get("confident"):
                    answer = result["answer"]
                    form_data[label] = answer
                    if field_type == "checkbox":
                        if answer.lower() in ("yes", "true"):
                            await field.check()
                    else:
                        await field.fill(str(answer))
                else:
                    # AI doesn't know — flag for human review
                    pending_questions.append({
                        "field": label,
                        "type": field_type,
                        "reason": result.get("reason", "Needs human input"),
                    })

            if pending_questions:
                await browser.close()
                return {
                    "status": "awaiting_review",
                    "form_data": form_data,
                    "pending_questions": pending_questions,
                }

            # Submit the form
            submit_btn = await page.query_selector("button[type=submit], input[type=submit]")
            if submit_btn:
                await submit_btn.click()
                await page.wait_for_timeout(2000)

            await browser.close()
            return {"status": "submitted", "form_data": form_data, "pending_questions": []}

        except Exception as e:
            await browser.close()
            return {"status": "failed", "error": str(e), "form_data": form_data, "pending_questions": []}


async def resume_apply_with_answers(
    job_url: str,
    resume_data: dict,
    saved_form_data: dict,
    human_answers: dict,
) -> dict:
    """Resume application after human fills in missing answers."""
    merged = {**saved_form_data, **human_answers}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(job_url, timeout=30000)
            for field_name, value in merged.items():
                field = await page.query_selector(f"[name='{field_name}'], [placeholder='{field_name}']")
                if field:
                    await field.fill(str(value))

            submit_btn = await page.query_selector("button[type=submit], input[type=submit]")
            if submit_btn:
                await submit_btn.click()
                await page.wait_for_timeout(2000)

            await browser.close()
            return {"status": "submitted", "form_data": merged}
        except Exception as e:
            await browser.close()
            return {"status": "failed", "error": str(e)}
