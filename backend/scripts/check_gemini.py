"""Make one explicit live Gemini connectivity check without showing secrets."""

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi import HTTPException  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.services.reasoning_provider import GeminiProvider  # noqa: E402


async def main() -> int:
    if not settings.gemini_api_key:
        print("Gemini configuration missing: GEMINI_API_KEY is not set. No request was sent.")
        return 2
    print(f"Gemini key configured: yes; model: {settings.gemini_model}")
    try:
        answer = await GeminiProvider().answer(
            question="Reply briefly in English confirming this connection test.",
            farmer_context="",
            sources=[],
            history=[],
        )
    except HTTPException as exc:
        print(f"Gemini request failed ({exc.status_code}): {exc.detail}")
        return 1
    print(f"Gemini request succeeded; model: {settings.gemini_model}")
    print(f"Response: {answer[:240].replace(chr(10), ' ')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
