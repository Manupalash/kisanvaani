from sqlalchemy import ForeignKey, String, Text, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Farmer(Base):
    __tablename__ = "farmers"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    village: Mapped[str | None] = mapped_column(String(120), nullable=True)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    land_area_acres: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(20), default="te", nullable=False)
    crops: Mapped[list["FarmCrop"]] = relationship(back_populates="farmer", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="farmer", cascade="all, delete-orphan")
    advisories: Mapped[list["Advisory"]] = relationship(back_populates="farmer", cascade="all, delete-orphan")
    documents: Mapped[list["AgriculturalDocument"]] = relationship(back_populates="farmer", cascade="all, delete-orphan")


class FarmCrop(Base):
    __tablename__ = "farm_crops"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    variety: Mapped[str | None] = mapped_column(String(100))
    season: Mapped[str | None] = mapped_column(String(60))
    stage: Mapped[str | None] = mapped_column(String(60))
    area_acres: Mapped[float | None] = mapped_column(Float, nullable=True)
    farmer: Mapped[Farmer] = relationship(back_populates="crops")


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(20), default="te", nullable=False)
    farmer: Mapped[Farmer] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan", order_by="Message.id")


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_mime_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Advisory(Base):
    __tablename__ = "advisories"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="general", nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    farmer: Mapped[Farmer] = relationship(back_populates="advisories")


class AgriculturalDocument(Base):
    __tablename__ = "agricultural_documents"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    farmer_id: Mapped[int | None] = mapped_column(ForeignKey("farmers.id", ondelete="SET NULL"), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str | None] = mapped_column(String(300), nullable=True)
    language: Mapped[str] = mapped_column(String(20), default="te", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    crop: Mapped[str | None] = mapped_column(String(100), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    farmer: Mapped[Farmer | None] = relationship(back_populates="documents")
