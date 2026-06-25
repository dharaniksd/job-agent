"""
AI Client — Ollama-first with optional OpenAI.

Default behaviour: Ollama only (free, local, M3 Pro).
To enable OpenAI as fallback, set USE_OPENAI=true in .env.

Usage:
    from app.core.ai_client import chat_json, chat_text, ai_provider_status
"""
import json
import httpx
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
    prompt = system + "\n\n" + user
    if json_mode:
        prompt += "\n\nRespond with ONLY valid JSON. No markdown, no explanation, no code fences."

    async with httpx.AsyncClient(timeout=180) as client:
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


# ── OpenAI (only when USE_OPENAI=true) ─────────────────────────────────────────

async def _openai_chat(system: str, user: str, json_mode: bool = False) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        **kwargs,
    )
    return resp.choices[0].message.content.strip()


# ── Routing logic ───────────────────────────────────────────────────────────────

async def _call(system: str, user: str, json_mode: bool) -> str:
    """
    Priority:
      1. Ollama (always tried first — free + local)
      2. OpenAI (only if USE_OPENAI=true AND OPENAI_API_KEY is set)
    """
    # Try Ollama
    if await _ollama_available():
        try:
            return await _ollama_chat(system, user, json_mode)
        except Exception as e:
            print(f"[ai_client] Ollama error: {e}")

    # OpenAI fallback — only if explicitly enabled
    if settings.use_openai and settings.openai_api_key:
        print("[ai_client] Falling back to OpenAI (USE_OPENAI=true)")
        return await _openai_chat(system, user, json_mode)

    raise RuntimeError(
        "No AI provider available.\n"
        "• Make sure Ollama is running: docker compose up ollama\n"
        "• Or set USE_OPENAI=true and OPENAI_API_KEY in .env to use OpenAI."
    )


async def chat_text(system: str, user: str) -> str:
    return await _call(system, user, json_mode=False)


async def chat_json(system: str, user: str) -> dict:
    raw = await _call(system, user, json_mode=True)
    # Strip markdown fences some models add
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


async def ai_provider_status() -> dict:
    ollama_ok = await _ollama_available()
    return {
        "active": "ollama" if ollama_ok else ("openai" if (settings.use_openai and settings.openai_api_key) else "none"),
        "ollama": {
            "available": ollama_ok,
            "model": settings.ollama_model,
            "url": settings.ollama_url,
        },
        "openai": {
            "enabled": settings.use_openai,
            "configured": bool(settings.openai_api_key),
            "note": "Set USE_OPENAI=true in .env to enable as fallback",
        },
    }
