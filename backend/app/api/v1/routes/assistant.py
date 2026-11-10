import re
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Conversation, FarmCrop, Farmer, Message
from app.schemas.assistant import ChatRequest, ChatResponse
from app.services.knowledge_service import retrieve_documents
from app.services.reasoning_provider import ReasoningProvider, get_reasoning_provider

router = APIRouter()
logger = logging.getLogger("kisanvaani.assistant")
_DOSE_PATTERN = re.compile(r"\b(?:spray|apply|dose|mix|use)\b[^.\n]{0,100}\b\d+(?:\.\d+)?\s*(?:ml|millilit(?:er|re)s?|g|gram(?:s)?|kg|kilogram(?:s)?|lit(?:er|re)s?)\b", re.IGNORECASE)
_DIAGNOSIS_PATTERN = re.compile(r"\b(?:definitely|certainly|confirmed|you have|this is)\b[^.\n]{0,80}\b(?:blight|blast|rot|wilt|borer|virus|disease|deficiency)\b", re.IGNORECASE)
_TELUGU_DIAGNOSIS_PATTERN = re.compile(r"(?:ఖచ్చితంగా|నిశ్చయంగా|ఇది)\s*[^.\n]{0,80}(?:వైరస్|తెగులు|వ్యాధి|లోపం)")
_TELUGU_DOSE_PATTERN = re.compile(r"(?:పిచికారీ|చల్లండి|వాడండి|మోతాదు|పురుగుమందు)[^.\n]{0,80}\d+(?:\.\d+)?\s*(?:మి\.?లీ|గ్రా|కిలో|లీటర్|ml|grams?|kg|lit(?:er|re)s?)", re.IGNORECASE)
_MIX_PATTERN = re.compile(r"\b(?:mix|combine|tank mix)\b[^.\n]{0,100}\b(?:pesticide|insecticide|fungicide|chemical)s?\b|(?:పురుగుమందు|ఫంగిసైడ్|రసాయన)[^.\n]{0,80}కలప", re.IGNORECASE)


def detect_language(text: str) -> str:
    has_telugu = any("\u0c00" <= char <= "\u0c7f" for char in text)
    has_latin = any(char.isascii() and char.isalpha() for char in text)
    return "te-en" if has_telugu and has_latin else "te" if has_telugu else "en"


def validate_answer_safety(answer: str, language: str) -> str:
    if _DOSE_PATTERN.search(answer) or _TELUGU_DOSE_PATTERN.search(answer) or _MIX_PATTERN.search(answer):
        if language.startswith("te"):
            return "ఈ వివరాల ఆధారంగా మందు మోతాదు లేదా కలయికను సురక్షితంగా సూచించలేను. పంట, దశ, లక్షణాల ఫోటోతో స్థానిక వ్యవసాయ అధికారిని లేదా అర్హత కలిగిన నిపుణుడిని సంప్రదించండి."
        return "I can’t safely recommend a chemical dose or mixture from this information. Please share the crop, growth stage and clear symptom photos with your local agricultural officer or a qualified expert before applying anything."
    if _DIAGNOSIS_PATTERN.search(answer) or _TELUGU_DIAGNOSIS_PATTERN.search(answer):
        if language.startswith("te"):
            return "ఈ లక్షణాలతో మాత్రమే ఖచ్చితమైన తెగులు లేదా లోపాన్ని నిర్ధారించలేను. పంట దశ, ప్రభావిత మొక్కల సంఖ్య, నీటి పరిస్థితి, లక్షణాల ఫోటో వివరాలు చెప్పండి; చికిత్సకు ముందు స్థానిక వ్యవసాయ అధికారిని సంప్రదించండి."
        return "These symptoms alone are not enough for a confirmed diagnosis. Please share the crop stage, how many plants are affected, field water conditions and clear photos; consult a local agricultural officer before treatment."
    return answer


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    provider: ReasoningProvider = Depends(get_reasoning_provider),
):
    question = request.message.strip()
    if not question:
        raise HTTPException(status_code=422, detail="message must contain text")
    farmer = db.get(Farmer, request.farmer_id)
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    conversation = db.get(Conversation, request.conversation_id)
    if not conversation or conversation.farmer_id != farmer.id:
        raise HTTPException(status_code=404, detail="Conversation not found for this farmer")
    crops = db.scalars(select(FarmCrop).where(FarmCrop.farmer_id == farmer.id)).all()
    crop_names = [crop.name for crop in crops]
    sources = retrieve_documents(db, question, crop_names)
    if request.request_id:
        prior_user_message = db.scalar(select(Message).where(Message.request_id == request.request_id))
        if prior_user_message and prior_user_message.conversation_id != conversation.id:
            raise HTTPException(status_code=409, detail="This request ID is already associated with another conversation.")
        if prior_user_message:
            later_messages = db.scalars(
                select(Message).where(
                    Message.conversation_id == conversation.id,
                    Message.id > prior_user_message.id,
                ).order_by(Message.id)
            ).all()
            for prior_reply in later_messages:
                if prior_reply.role == "user":
                    break
                if prior_reply.role == "assistant" and prior_reply.text:
                    return ChatResponse(answer=prior_reply.text, language=detect_language(prior_user_message.text or question),
                                        retrieved_sources=[source.as_public() for source in sources], conversation_id=conversation.id)
    history_rows = db.scalars(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.id.desc()).limit(8)).all()
    history = [{"role": row.role, "content": row.text or ""} for row in reversed(history_rows) if row.role in {"user", "assistant"} and row.text]
    language = detect_language(question)
    profile = ", ".join(filter(None, [farmer.village, farmer.district, "; crops: " + ", ".join(crop_names) if crop_names else None]))
    try:
        raw_answer = await provider.answer(question=question, farmer_context=profile, sources=sources, history=history)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("reasoning_provider_failed exception_class=%s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="The configured reasoning provider failed. Check its availability and retry.") from exc
    answer = validate_answer_safety(raw_answer, language)
    if not request.request_id or not prior_user_message:
        db.add(Message(conversation_id=conversation.id, role="user", text=question, request_id=request.request_id))
    db.add(Message(conversation_id=conversation.id, role="assistant", text=answer))
    db.commit()
    return ChatResponse(answer=answer, language=language, retrieved_sources=[source.as_public() for source in sources], conversation_id=conversation.id)
