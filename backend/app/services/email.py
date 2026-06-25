"""
Email Notification Service
Supports SendGrid (recommended) and fallback SMTP.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings


def _build_html(title: str, body: str, cta_label: str = "", cta_url: str = "") -> str:
    cta_block = ""
    if cta_label and cta_url:
        cta_block = f"""
        <a href="{cta_url}" style="display:inline-block;margin-top:16px;padding:12px 24px;
           background:#2563eb;color:#fff;border-radius:6px;text-decoration:none;font-weight:bold;">
          {cta_label}
        </a>"""
    return f"""
    <html><body style="font-family:sans-serif;background:#f9fafb;padding:32px;">
      <div style="max-width:520px;margin:auto;background:#fff;padding:32px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08);">
        <h2 style="color:#1e293b;margin-top:0;">🤖 AI Job Agent — {title}</h2>
        <div style="color:#475569;line-height:1.6;">{body}</div>
        {cta_block}
        <hr style="margin:32px 0;border:none;border-top:1px solid #e2e8f0;">
        <p style="font-size:12px;color:#94a3b8;">You received this because you have email notifications enabled.
           <a href="{settings.app_url}/settings" style="color:#2563eb;">Manage preferences</a></p>
      </div>
    </html>"""


async def send_email(to: str, subject: str, html: str):
    """Send via SendGrid if key is set, else fall back to SMTP."""
    if settings.sendgrid_api_key:
        await _send_via_sendgrid(to, subject, html)
    elif settings.smtp_host:
        _send_via_smtp(to, subject, html)
    else:
        print(f"[EMAIL SKIPPED] No email provider configured. Would send to {to}: {subject}")


async def _send_via_sendgrid(to: str, subject: str, html: str):
    import httpx
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
            json={
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": settings.email_from, "name": "AI Job Agent"},
                "subject": subject,
                "content": [{"type": "text/html", "value": html}],
            },
        )


def _send_via_smtp(to: str, subject: str, html: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_tls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.email_from, to, msg.as_string())


# --- Notification Templates ---

async def notify_application_submitted(email: str, job_title: str, company: str, app_id: str):
    html = _build_html(
        "Application Submitted ✅",
        f"<p>Great news! Your application for <strong>{job_title}</strong> at <strong>{company}</strong> was successfully submitted by the AI agent.</p>",
        "View Application",
        f"{settings.app_url}/applications/{app_id}",
    )
    await send_email(email, f"✅ Applied to {job_title} at {company}", html)


async def notify_review_needed(email: str, job_title: str, company: str, app_id: str, questions: list):
    q_list = "".join(f"<li>{q['field']} — <em>{q['reason']}</em></li>" for q in questions)
    html = _build_html(
        "Your Input Needed 🧑",
        f"""<p>The AI started your application for <strong>{job_title}</strong> at <strong>{company}</strong>
        but couldn't answer {len(questions)} question(s):</p>
        <ul style="margin:12px 0;padding-left:20px;">{q_list}</ul>
        <p>Please review and answer them to continue.</p>""",
        "Answer Questions Now",
        f"{settings.app_url}/review/{app_id}",
    )
    await send_email(email, f"🧑 Action needed: {job_title} at {company}", html)


async def notify_application_failed(email: str, job_title: str, company: str, app_id: str, error: str):
    html = _build_html(
        "Application Failed ❌",
        f"""<p>The AI couldn't complete the application for <strong>{job_title}</strong> at <strong>{company}</strong>.</p>
        <p style="background:#fef2f2;padding:12px;border-radius:6px;color:#b91c1c;font-size:14px;">
        {error or 'Unknown error'}</p>
        <p>You can retry or apply manually via the link below.</p>""",
        "View & Retry",
        f"{settings.app_url}/applications/{app_id}",
    )
    await send_email(email, f"❌ Application failed: {job_title} at {company}", html)
