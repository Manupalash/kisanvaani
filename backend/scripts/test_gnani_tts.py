"""Make one real Timbre v2.5 request and verify the returned WAV audio."""

import asyncio
import argparse
import io
import sys
import wave
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.services.tts_service import TimbreTTSService  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=("te-IN", "en-IN"), default="te-IN")
    language = parser.parse_args().language
    print(f"Gnani API key configured: {'yes' if bool(settings.gnani_api_key) else 'no'}")
    if not settings.gnani_api_key:
        print("Live check not run: set GNANI_API_KEY in backend/.env.")
        return 2
    try:
        sentence = "నమస్కారం, మీ పంట ఎలా ఉంది?" if language == "te-IN" else "Check the field moisture before irrigating the rice crop."
        result = await TimbreTTSService().synthesize(sentence, language)
        with wave.open(io.BytesIO(result.content), "rb") as audio:
            frames, channels = audio.getnframes(), audio.getnchannels()
            sample_rate = audio.getframerate()
            duration = frames / sample_rate
        if duration <= 0:
            raise ValueError("Audio has zero duration")
        print(f"Live TTS request: successful (HTTP {result.upstream_status})")
        print(f"Model: {result.model}; language: {result.language}; voice: {result.voice}")
        print(f"Audio: WAV, {channels} channel(s), {sample_rate} Hz, {duration:.2f} sec, {len(result.content)} bytes")
        print("Verified audio in memory; no audio file was written.")
        return 0
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        detail = getattr(exc, "detail", "")
        if status in {401, 403}:
            category = "authentication or TTS permission failure"
        elif status == 503:
            category = "service, quota, or temporary upstream failure"
        elif status == 504:
            category = "request timeout"
        else:
            category = "configuration, request, or connectivity failure"
        print(f"Live TTS request failed ({category})" + (f"; application status {status}" if status else ""))
        if detail:
            print(f"Safe diagnostic: {detail}")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
