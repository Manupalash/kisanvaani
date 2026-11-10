from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import File, HTTPException, UploadFile, status
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import Base, engine, migrate_agricultural_documents, migrate_farmer_columns, migrate_message_request_id, SessionLocal
from app import models  # noqa: F401 - registers SQLAlchemy models
from app.services.knowledge_service import seed_knowledge_base

Base.metadata.create_all(bind=engine)
migrate_farmer_columns()
migrate_agricultural_documents()
migrate_message_request_id()
with SessionLocal() as seed_session:
    seed_knowledge_base(seed_session)

app = FastAPI(title=settings.app_name, version="0.1.0", description="KisanVaani service foundation")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router, prefix=settings.api_v1_prefix)

MAX_AUDIO_BYTES = 10 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/wav", "audio/mpeg", "audio/mp4", "audio/x-m4a"}


@app.post(f"{settings.api_v1_prefix}/audio/validate", tags=["audio"])
async def validate_audio(file: UploadFile = File(...)) -> dict[str, str | int]:
    """Validate bounded audio input in memory. Contents are discarded after validation."""
    if file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported audio format")
    size = 0
    prefix = b""
    while chunk := await file.read(64 * 1024):
        size += len(chunk)
        if len(prefix) < 16:
            prefix += chunk[:16 - len(prefix)]
        if size > MAX_AUDIO_BYTES:
            await file.close()
            raise HTTPException(status_code=413, detail="Audio exceeds 10 MB limit")
    await file.close()
    if size == 0:
        raise HTTPException(status_code=400, detail="Audio file is empty")
    signatures = {
        "audio/wav": (b"RIFF", b"WAVE"),
        "audio/ogg": (b"OggS",),
        "audio/mpeg": (b"ID3",),
    }
    expected = signatures.get(file.content_type)
    if expected and not any(prefix.startswith(signature) for signature in expected):
        raise HTTPException(status_code=400, detail="Audio content does not match declared format")
    return {"status": "validated", "bytes": size, "content_type": file.content_type}


@app.get("/health", tags=["health"])
def root_health() -> dict[str, str]:
    return {"status": "ok", "service": "kisanvaani-api"}
