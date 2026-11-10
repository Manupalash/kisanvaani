from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Advisory, AgriculturalDocument, Conversation, FarmCrop, Farmer, Message
from app.schemas.resources import (
    AdvisoryCreate, AdvisoryRead, ConversationCreate, ConversationRead,
    CropCreate, CropRead, DocumentCreate, DocumentRead, MessageCreate, MessageRead,
)

router = APIRouter()

def require_farmer(db: Session, farmer_id: int) -> Farmer:
    farmer = db.get(Farmer, farmer_id)
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return farmer

@router.post("/farmers/{farmer_id}/crops", response_model=CropRead, status_code=201)
def create_crop(farmer_id: int, data: CropCreate, db: Session = Depends(get_db)):
    require_farmer(db, farmer_id); item = FarmCrop(farmer_id=farmer_id, **data.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@router.get("/farmers/{farmer_id}/crops", response_model=list[CropRead])
def list_crops(farmer_id: int, db: Session = Depends(get_db)):
    require_farmer(db, farmer_id); return db.scalars(select(FarmCrop).where(FarmCrop.farmer_id == farmer_id).order_by(FarmCrop.id)).all()

@router.delete("/crops/{crop_id}", status_code=204)
def delete_crop(crop_id: int, db: Session = Depends(get_db)):
    item = db.get(FarmCrop, crop_id)
    if not item: raise HTTPException(status_code=404, detail="Crop not found")
    db.delete(item); db.commit(); return Response(status_code=204)

@router.post("/farmers/{farmer_id}/conversations", response_model=ConversationRead, status_code=201)
def create_conversation(farmer_id: int, data: ConversationCreate, db: Session = Depends(get_db)):
    require_farmer(db, farmer_id); item = Conversation(farmer_id=farmer_id, **data.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@router.get("/farmers/{farmer_id}/conversations", response_model=list[ConversationRead])
def list_conversations(farmer_id: int, db: Session = Depends(get_db)):
    require_farmer(db, farmer_id); return db.scalars(select(Conversation).where(Conversation.farmer_id == farmer_id).order_by(Conversation.id.desc())).all()

@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    item = db.get(Conversation, conversation_id)
    if not item: raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(item); db.commit(); return Response(status_code=204)

@router.post("/conversations/{conversation_id}/messages", response_model=MessageRead, status_code=201)
def create_message(conversation_id: int, data: MessageCreate, db: Session = Depends(get_db)):
    if not db.get(Conversation, conversation_id): raise HTTPException(status_code=404, detail="Conversation not found")
    item = Message(conversation_id=conversation_id, **data.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
def list_messages(conversation_id: int, db: Session = Depends(get_db)):
    if not db.get(Conversation, conversation_id): raise HTTPException(status_code=404, detail="Conversation not found")
    return db.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)).all()

@router.post("/farmers/{farmer_id}/advisories", response_model=AdvisoryRead, status_code=201)
def create_advisory(farmer_id: int, data: AdvisoryCreate, db: Session = Depends(get_db)):
    require_farmer(db, farmer_id); item = Advisory(farmer_id=farmer_id, **data.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@router.get("/farmers/{farmer_id}/advisories", response_model=list[AdvisoryRead])
def list_advisories(farmer_id: int, db: Session = Depends(get_db)):
    require_farmer(db, farmer_id); return db.scalars(select(Advisory).where(Advisory.farmer_id == farmer_id).order_by(Advisory.id.desc())).all()

@router.delete("/advisories/{advisory_id}", status_code=204)
def delete_advisory(advisory_id: int, db: Session = Depends(get_db)):
    item = db.get(Advisory, advisory_id)
    if not item: raise HTTPException(status_code=404, detail="Advisory not found")
    db.delete(item); db.commit(); return Response(status_code=204)

@router.post("/documents", response_model=DocumentRead, status_code=201)
def create_document(data: DocumentCreate, farmer_id: int | None = None, db: Session = Depends(get_db)):
    if farmer_id is not None: require_farmer(db, farmer_id)
    item = AgriculturalDocument(farmer_id=farmer_id, **data.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@router.get("/documents", response_model=list[DocumentRead])
def list_documents(farmer_id: int | None = None, db: Session = Depends(get_db)):
    query = select(AgriculturalDocument)
    if farmer_id is not None: query = query.where(AgriculturalDocument.farmer_id == farmer_id)
    return db.scalars(query.order_by(AgriculturalDocument.id)).all()

@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    item = db.get(AgriculturalDocument, document_id)
    if not item: raise HTTPException(status_code=404, detail="Document not found")
    db.delete(item); db.commit(); return Response(status_code=204)
