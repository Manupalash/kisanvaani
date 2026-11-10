# KisanVaani

KisanVaani is a voice-first agricultural assistant for Telugu-speaking Indian farmers. It lets a farmer ask a question by voice or text, review the transcript, receive a source-grounded answer, and optionally listen to that answer.

## Problem and solution

Agricultural information can be difficult to access quickly and in a farmer's preferred language. KisanVaani combines Telugu and English speech transcription, a curated Indian agriculture knowledge base, retrieval-augmented answers, and spoken responses in one mobile-first interface. It supports Telugu, English, and Telugu-English questions, including common Latin-script Telugu transliterations.

## What is implemented

- **Speech-to-text:** Gnani Prisma v2.5 transcribes browser recordings to text. The transcript remains editable before it is sent to the assistant.
- **Agricultural retrieval:** SQLite keyword retrieval selects curated crop guidance and returns the stored source title, organization, URL, crop, and topic.
- **Reasoning:** Gemini generates an answer when `ASSISTANT_PROVIDER=gemini` and a valid `GEMINI_API_KEY` are configured. Transient upstream errors receive a bounded retry; unavailable reasoning returns an error instead of a fabricated answer.
- **Safety:** The prompt requires source-grounded, cautious advice. Server-side checks block unsupported chemical dosages/mixtures and definitive diagnosis language; high-risk situations are directed to an agricultural officer.
- **Text-to-speech:** Gnani Timbre v2.5 generates answer audio on request. The UI supports playback, pause, resume, replay, and retry. TTS failure leaves the text answer visible.
- **Persistence:** FastAPI, SQLAlchemy and SQLite store farmer profiles, crops, conversations and messages. Repeated chat submissions with the same request ID do not duplicate messages.

## Architecture and stack

```text
Browser (Next.js 14, React, TypeScript, Tailwind)
   ├── MediaRecorder ── multipart ──> FastAPI ──> Gnani Prisma v2.5 STT
   ├── edited question ────────────> FastAPI ──> SQLite retrieval ──> Gemini
   └── answer text ────────────────> FastAPI ──> Gnani Timbre v2.5 TTS ──> audio playback
                                      └────────> SQLite conversations/messages
```

The frontend and backend run independently. Provider keys stay in backend environment configuration and are never sent to the browser. Prisma is used for STT, Timbre for TTS, Gemini for reasoning, and RAG for retrieving agricultural documents. **Evon is not integrated.**

## Technology

- Frontend: Next.js 14, TypeScript, Tailwind CSS, Lucide icons
- Backend: Python, FastAPI, Pydantic, HTTPX
- Data: SQLite, SQLAlchemy
- Speech: Gnani Prisma v2.5 (STT), Gnani Timbre v2.5 (TTS)
- Reasoning: Google Gen AI SDK (`google-genai`), Gemini model configured by environment
- Recording: Browser `MediaRecorder` API; FFmpeg required by backend for WebM-to-WAV STT conversion

## Agricultural knowledge sources

The starter corpus covers rice, cotton, chilli, maize, groundnut and tomato, with cultivation, irrigation, soil, nutrient, pest/disease, prevention and harvesting topics. Retrieved citations come from the stored document metadata; Gemini does not provide citation URLs.

The curated records link to [Tamil Nadu Agricultural University crop guides](https://agritech.tnau.ac.in/), [ICAR-CIWA rice water guidance](https://www.ciwa.icar.gov.in/gks/crop-production), [ICAR crop advisories](https://icar.gov.in/), and [Government of Meghalaya integrated pest management guidance](https://megagriculture.gov.in/PUBLIC/IPM_ipm.aspx). Some crop guides are state-specific; farmers should follow current local, season- and soil-specific guidance.

## Requirements and local setup

- Python 3.10+
- Node.js 18+
- FFmpeg installed and on the backend `PATH`
- A Gnani API key with Prisma and Timbre access for live speech features
- A Google Gemini API key for generated answers

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set provider credentials; never commit this file.
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. Startup creates SQLite tables and seeds the curated knowledge records. Health check: `http://localhost:8000/api/v1/health`; interactive API docs: `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
printf 'NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1\n' > .env.local
npm run dev
```

Open `http://localhost:3000`. Microphone recording requires browser permission and a secure context (`localhost` or HTTPS). TTS playback starts from a user click; if browser autoplay policy blocks playback, press the listen button again.

## Environment variables

Set provider secrets only in `backend/.env` or the backend deployment's secret manager. Do not put them in frontend variables.

| Variable | Purpose | Default |
| --- | --- | --- |
| `GNANI_API_KEY` | Shared backend credential for Prisma STT and Timbre TTS | empty |
| `GNANI_STT_URL` | Prisma STT endpoint | `https://api.vachana.ai/stt/v3` |
| `GNANI_TIMEOUT_SECONDS` | STT request timeout | `45` |
| `GNANI_TTS_URL` | Timbre TTS endpoint | `https://api.vachana.ai/api/v1/tts/inference` |
| `GNANI_TTS_MODEL` | TTS model | `timbre-v2.5` |
| `GNANI_TTS_DEFAULT_LANGUAGE` | Default TTS language | `te-IN` |
| `GNANI_TTS_TELUGU_VOICE` | Telugu TTS voice | `Yukti` |
| `GNANI_TTS_ENGLISH_VOICE` | English TTS voice | `Shlok` |
| `GNANI_TTS_TIMEOUT_SECONDS` | TTS overall timeout | `45` |
| `GNANI_TTS_MAX_RETRIES` | Maximum transient retries (hard capped at 2) | `2` |
| `GNANI_TTS_MAX_TEXT_CHARS` | Maximum synthesis text length | `5000` |
| `ASSISTANT_PROVIDER` | Reasoning adapter (`gemini`, `openai`, or `none`) | `gemini` in example |
| `GEMINI_API_KEY` | Gemini credential (backend only) | empty |
| `GEMINI_MODEL` | Gemini model ID | `gemini-3.8-flash` |
| `GEMINI_TIMEOUT_SECONDS` | Gemini overall request timeout including retries | `60` |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | Optional existing OpenAI adapter configuration | empty |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./kisanvaani.db` |
| `FRONTEND_ORIGINS` | Comma-separated CORS allowlist | `http://localhost:3000` |
| `FFMPEG_BINARY` | FFmpeg executable | `ffmpeg` |
| `NEXT_PUBLIC_API_URL` | Frontend API base URL; not a secret | `http://localhost:8000/api/v1` |

Both `.env.example` files contain templates. Copy `backend/.env.example` to `backend/.env`; configure `frontend/.env.local` separately. The backend loads its own `.env` by absolute project path, independent of current working directory.

## API endpoints

- `GET /health`, `GET /api/v1/health` — health checks
- `POST /api/v1/voice/transcribe` — audio multipart upload and Prisma transcription
- `POST /api/v1/assistant/chat` — RAG + configured reasoning; accepts farmer ID, conversation ID, message and optional idempotency `request_id`
- `POST /api/v1/voice/synthesize` — answer text to Timbre WAV audio
- `/api/v1/farmers/` and nested farmer crop/conversation endpoints — profile and history data

Audio uploads are limited to 10 MB and 30 seconds, are decoded/validated, and temporary conversion files are removed. WebM is converted to mono 16 kHz PCM WAV. TTS audio is generated on demand and returned with `Cache-Control: no-store`; it is not persisted.

## Testing and diagnostics

```bash
cd backend
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app scripts
.venv/bin/python scripts/check_gemini.py
.venv/bin/python scripts/test_gnani_tts.py
.venv/bin/python scripts/test_gnani_tts.py --language en-IN

cd ../frontend
npm run lint
npm run build
```

The test suite mocks provider calls and does not consume API credits. The Gemini and Gnani scripts make real requests, report whether credentials are configured without printing them, and should only be run when live provider access is intended.

## Safety and known limitations

- KisanVaani provides information, not a definitive diagnosis or substitute for local extension services. Symptom-only questions should trigger clarification; high-risk treatment decisions should be escalated.
- It does not invent pesticide dosages or chemical combinations. Current weather, live market data and location-specific recommendations are not implemented.
- Retrieval is lightweight SQLite keyword ranking; curated passages are currently mostly English. Retrieval quality can vary for transliteration and uncommon regional terminology.
- Gemini and Gnani availability, account permissions, quotas and network connectivity are external dependencies. Errors are shown honestly; no fake answer fallback is used.
- SQLite is suitable for local demonstration. A production deployment needs a persistent volume or managed database, HTTPS, backups, rate limiting, monitoring and a platform-specific secret/CORS setup.
- The demo profile/advisory cards may show clearly labeled demonstration content when no saved data exists.

## Demo runbook

1. Install FFmpeg and start the backend with configured Gnani and Gemini credentials.
2. Start the frontend and open `/profile`; create or confirm the farmer profile, then add rice/paddy under `/crops` if needed.
3. Open `/assistant`, ask “What is the best way to manage water for rice cultivation?” or use the microphone, review/edit the transcript, then submit it.
4. Confirm the answer and retrieved sources appear. Select **Listen to answer** to synthesize and play it; test pause, resume and replay.
5. Ask a Telugu question: “వరి పంటలో నీటి యాజమాన్యం ఎలా ఉండాలి?” Then try “Rice crop lo yellow leaves vastunnayi, em cheyyali?” and confirm the assistant asks for useful missing details rather than diagnosing from symptoms alone.
6. Open `/history` and verify saved conversations. For a presentation, capture screenshots of the profile/crop setup, editable transcript, source-linked answer, and audio controls in desktop and narrow mobile viewports. No screenshots are bundled yet.

## Deployment notes

The repository is prepared to run frontend and backend as separate services, but no deployment target has been selected. Before deployment, choose the platform, provision persistent storage for SQLite (or a managed SQL database), set backend secrets and CORS origins, configure the frontend API URL to the HTTPS backend, install FFmpeg in the backend runtime, and enable HTTPS for microphone access. No deployment has been performed.
