# KisanVaani architecture

## Phase 2A voice transcription

The browser records with `MediaRecorder` and keeps a local playback URL. When the farmer chooses transcription, the client posts the actual recording MIME type and bytes to `POST /api/v1/voice/transcribe` using multipart fields `audio`, optional `farmer_id`, optional `conversation_id`, and `language=te-IN`.

FastAPI checks the 10 MB limit, identifies the audio container from bytes, verifies decodability and duration (maximum 30 seconds), and converts WebM to mono 16 kHz PCM WAV using FFmpeg. Temporary audio files are deleted after the upstream request or on any error. Other supported formats (WAV, MP3, OGG, FLAC, AAC, M4A) are passed through after decoding validation.

`PrismaService` sends only `audio_file` and `language_code` to `https://api.vachana.ai/stt/v3`, with the secret backend environment variable in `X-API-Key-ID`. It omits `model`, which selects the documented Prisma v2.5 default. No key or audio is persisted. A user message is saved only if transcription succeeds and a valid conversation was supplied. Transcription does not generate an assistant answer.

## Backend configuration

Configure `GNANI_API_KEY`, `GNANI_STT_URL` (default official endpoint), `GNANI_TIMEOUT_SECONDS` (default 45), `FFMPEG_BINARY` (default `ffmpeg`), `DATABASE_URL`, `FRONTEND_ORIGINS`, `APP_NAME`, and `API_V1_PREFIX` in the backend environment. Install FFmpeg and ensure the configured binary is available to the backend process.

## Phase 2B retrieval and reasoning

`POST /api/v1/assistant/chat` validates the farmer/conversation relationship, loads registered crops and recent messages, detects crop/topic phrases in English and Telugu, retrieves source-linked records from SQLite, calls the configured provider, applies an agricultural safety guard, then saves both messages. The response returns the answer, language, conversation ID and retrieved source content/metadata. Sources come only from database documents; model-generated URLs are not used.

The small, idempotently seeded corpus covers rice, cotton, chilli, maize, groundnut and tomato. It contains conservative summaries linked to Tamil Nadu Agricultural University crop guides, ICAR-CIWA rice water guidance, an ICAR maize advisory and Government of Meghalaya IPM principles. The TNAU material is state-specific context; recommendations must be checked against the farmer's state, season, variety, soil test and local crop advisory. It does not provide current weather or universal fertilizer/pesticide doses. The SQLite keyword retriever supports crop and topic synonyms in Telugu and English, but the source passages are currently English.

Source links used in the seed set include [TNAU rice crop guide](https://agritech.tnau.ac.in/ta/pdf/2013/CPG%202012.pdf), [TNAU rice irrigation](https://www.agritech.tnau.ac.in/agriculture/agri_irrigationmgt_cereals_rice.html), [ICAR-CIWA rice water guidance](https://www.ciwa.icar.gov.in/gks/crop-production), [TNAU cotton guide](https://agritech.tnau.ac.in/agriculture/CropProduction/Fibre%20crops/fibrecrops_cotton.html), [TNAU chilli guide](https://agritech.tnau.ac.in/horticulture/horti_vegetables_chilli_cultural.html), [TNAU maize guide](https://agritech.tnau.ac.in/agriculture/millets_maize_irrigated_maize.html), [ICAR Kharif maize advisory](https://icar.gov.in/sites/default/files/2025-10/ICAR-En-Kharif-Agro-Advisories-for-Farmers-2025.pdf), [TNAU groundnut guide](https://agritech.tnau.ac.in/CropProduction/Oilseeds/oilseeds_groundnut01.html), [TNAU tomato guide](https://agritech.tnau.ac.in/horticulture/horti_vegetables_tomato_index.html), and the linked crop-protection and [Government of Meghalaya IPM overview](https://megagriculture.gov.in/PUBLIC/IPM_ipm.aspx).

### Reasoning provider configuration

The backend defines a `ReasoningProvider` interface. Gemini uses Google's official `google-genai` Python SDK and its asynchronous client; the default model is `gemini-3.8-flash`, with `thinking_level=low` for lower latency. The prompt includes the farmer question, relevant registered crop profile, retrieved passages with source names and URLs, and up to eight recent conversation turns. Source citations returned to the frontend continue to come only from SQLite retrieval. Gemini is not allowed to invent citations. Configure the provider in the backend environment:

- `ASSISTANT_PROVIDER=gemini`
- `GEMINI_API_KEY` (backend only; do not put it in frontend variables)
- `GEMINI_MODEL=gemini-3.8-flash`
- `GEMINI_TIMEOUT_SECONDS=60`

The official SDK is installed from `backend/requirements.txt`. From the backend directory, run `python scripts/check_gemini.py` to make one live request. It reports whether configuration exists without printing the key, and prints a short response only after an actual request succeeds. Mocked tests do not establish live API access. If no key is configured, the Gemini adapter returns HTTP 503 without attempting a request.

The OpenAI Chat Completions adapter remains available with `ASSISTANT_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL`, and `OPENAI_TIMEOUT_SECONDS`. Setting `ASSISTANT_PROVIDER=none` or `retrieval` preserves retrieval-only behavior and returns HTTP 503 from answer generation. No provider is silently substituted. All provider credentials belong only in `backend/.env` and must never be included in frontend configuration or logs.

Existing Phase 1 agricultural documents receive missing metadata columns at startup. The seed routine removes only the exact prior Phase 2B starter rows before adding the updated curated corpus; other farmer documents are retained.
