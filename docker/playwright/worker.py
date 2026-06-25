"""
Playwright Worker
Runs as a separate container; polls the backend for pending auto-apply tasks.
The backend's auto_apply service is also imported directly into the backend
container — this worker is optional for high-volume/isolated browser execution.
"""
import asyncio
import httpx
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))


async def poll_and_apply():
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=60) as client:
        while True:
            try:
                # Check for any pending applications that haven't been attempted
                resp = await client.get("/api/applications/", params={"status": "pending"})
                if resp.status_code == 200:
                    apps = resp.json().get("applications", [])
                    for app in apps[:3]:  # Process max 3 at a time
                        print(f"[worker] Processing application {app['id']} for {app.get('job_title', '?')}")
                        # The actual apply is triggered via the backend API
                        # This worker can trigger retries for failed applications
            except Exception as e:
                print(f"[worker] Error: {e}")
            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    print(f"[worker] Starting Playwright worker, polling {BACKEND_URL} every {POLL_INTERVAL}s")
    asyncio.run(poll_and_apply())
