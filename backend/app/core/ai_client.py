"""
AI Client — Ollama-first with OpenAI fallback.

Priority:
  1. Ollama (local, free) — uses llama3.1:14b on your M3 Pro
  2. OpenAI (cloud) — fallback if Ollama is not running or key is set

Usage:
    from app.core.ai_client import chat_json, chat_text
    result = await chat_json(system="...", user="...")
"""
import json
import httpx
from openai import AsyncOpenAI
from app.core.config import settings


# ── Ollama ──────────────────────────────────────────────────────────────────────

async def _ollama_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.ollama_url}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def _ollama_chat(system: str, user: str, json_mode: bool = False) -> str:
    """Call Ollama's /api/chat endpoint."""
    prompt = system + "\n\n" + user
    if json_mode:
        prompt += "\n\nRespond with ONLY valid JSON, no markdown, no explanation."

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{settings.ollama_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1},
            },
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()


# ── OpenAI ──────────────────────────────────────────────────────────────────────

def _openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def _openai_chat(system: str, user: str, json_mode: bool = False) -> str:
    client = _openai_client()
    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        **kwargs,
    )
    return resp.choices[0].message.content.strip()


# ── Public API ──────────────────────────────────────────────────────────────────

async def chat_text(system: str, user: str) -> str:
    """Return AI response as plain text. Tries Ollama first, falls back to OpenAI."""
    if await _ollama_available():
        try:
            return await _ollama_chat(system, user, json_mode=False)
        except Exception as e:
            print(f"[ai_client] Ollama failed: {e}, falling back to OpenAI")
    if settings.openai_api_key:
        return await _openai_chat(system, user, json_mode=False)
    raise RuntimeError("No AI provider available. Start Ollama or set OPENAI_API_KEY.")


async def chat_json(system: str, user: str) -> dict:
    """Return AI response parsed as JSON. Tries Ollama first, falls back to OpenAI."""
    if await _ollama_available():
        try:
            raw = await _ollama_chat(system, user, json_mode=True)
            # Strip markdown code fences if model adds them
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(raw)
        except Exception as e:
            print(f"[ai_client] Ollama failed: {e}, falling back to OpenAI")
    if settings.openai_api_key:
        raw = await _openai_chat(system, user, json_mode=True)
        return json.loads(raw)
    raise RuntimeError("No AI provider available. Start Ollama or set OPENAI_API_KEY.")


async def ai_provider_status() -> dict:
    """Returns which AI providers are available."""
    ollama_ok = await _ollama_available()
    openai_ok = bool(settings.openai_api_key)
    return {
        "ollama": {"available": ollama_ok, "model": settings.ollama_model, "url": settings.ollama_url},
        "openai": {"available": openai_ok, "model": "gpt-4o-mini"},
        "active": "ollama" if ollama_ok else ("openai" if openai_ok else "none"),
    }
