# KisanVaani

KisanVaani is a voice-first agricultural assistant for Telugu-speaking Indian farmers. It includes a responsive Next.js interface and an independently runnable FastAPI + SQLite backend. Phase 2A connects Gnani Prisma v2.5 speech-to-text. Phase 2B adds retrieval-backed agricultural chat when a reasoning provider is configured. Advisory cards and conversation examples are labeled sample content.

## Structure

```text
frontend/  Next.js, TypeScript, Tailwind application
backend/   FastAPI service with versioned routes, SQLAlchemy, and SQLite
```

## Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. Microphone recording requires HTTPS or `localhost` and browser permission.

## Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload
```

The API runs at http://localhost:8000. Health check: `/health`; interactive docs: `/docs`. SQLite tables are created at startup.

Copy `backend/.env.example` to `backend/.env`. Set `GNANI_API_KEY` to a valid key; the secret is only read by the backend and sent in `X-API-Key-ID`. `GNANI_STT_URL` defaults to `https://api.vachana.ai/stt/v3` and `GNANI_TIMEOUT_SECONDS` defaults to 45. `FFMPEG_BINARY` defaults to `ffmpeg`.

Phase 2B adds `POST /api/v1/assistant/chat` with crop-aware SQLite keyword retrieval and curated source-linked guidance for rice, cotton, chilli, maize, groundnut and tomato. Gemini is the configured default reasoning provider; set `GEMINI_API_KEY` in `backend/.env` to enable generated answers. OpenAI remains an optional adapter, and `ASSISTANT_PROVIDER=none` retains retrieval-only behavior. See [docs/architecture.md](docs/architecture.md) for setup and the live diagnostic command.

Install FFmpeg and make it available on the backend PATH. The voice route accepts WAV, MP3, OGG, FLAC, AAC, M4A, and browser WebM recordings. WebM is converted to mono 16 kHz PCM WAV. Uploads are limited to 10 MB and 30 seconds, validated for decodability, and temporary files are removed after processing. Audio is not stored. Transcription uses the documented Prisma v2.5 default and does not submit a model parameter. Real transcription requires user-provided Gnani credentials; automated tests mock the upstream service. See [docs/architecture.md](docs/architecture.md).
