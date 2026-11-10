from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import Conversation, Farmer, Message
from app.schemas.voice import TranscriptionResponse
from app.services.audio_service import prepare_audio
from app.services.prisma_service import PrismaService

router = APIRouter()


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_voice(
    audio: UploadFile = File(...),
    farmer_id: int | None = Form(default=None),
    conversation_id: int | None = Form(default=None),
    language: str = Form(default="te-IN", pattern=r"^[a-z]{2}-[A-Z]{2}$"),
    duration_seconds: float | None = Form(default=None),
    db: Session = Depends(get_db),
):
    conversation = None
    if conversation_id is not None:
        conversation = db.get(Conversation, conversation_id)
        if not conversation:
            await audio.close()
            raise HTTPException(status_code=404, detail="Conversation not found")
        if farmer_id is not None and conversation.farmer_id != farmer_id:
            await audio.close()
            raise HTTPException(status_code=400, detail="Conversation does not belong to the supplied farmer")
    if farmer_id is not None and not db.get(Farmer, farmer_id):
        await audio.close()
        raise HTTPException(status_code=404, detail="Farmer not found")
    prepared = await prepare_audio(audio, ffmpeg_binary=settings.ffmpeg_binary)
    if duration_seconds is not None and (duration_seconds < 0 or abs(prepared.duration - duration_seconds) > 1.5):
        prepared.cleanup()
        await audio.close()
        raise HTTPException(status_code=400, detail="Reported recording duration does not match the uploaded audio")
    try:
        result = await PrismaService().transcribe(prepared, language=language)
    finally:
        prepared.cleanup()
        await audio.close()

    if conversation is not None:
        db.add(Message(conversation_id=conversation_id, role="user", text=result["transcript"]))
        db.commit()
    return result
