import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.agricultural_documents import DOCUMENTS
from app.models import AgriculturalDocument


@dataclass
class RetrievedSource:
    id: int
    title: str
    content: str
    crop: str | None
    topic: str | None
    source_name: str | None
    source_url: str | None
    score: float

    def as_public(self) -> dict[str, str | int | None]:
        return {"id": self.id, "title": self.title, "content": self.content, "source_name": self.source_name,
                "source_url": self.source_url, "crop": self.crop, "topic": self.topic}


def seed_knowledge_base(db: Session) -> int:
    # Remove only the exact Phase 2B starter rows that were superseded by the
    # crop-specific corpus; farmer-uploaded records and other documents remain.
    stale_titles = {
        "Rice field water management",
        "Rice nutrient management should follow field-specific guidance",
        "Inspect paddy symptoms before deciding on treatment",
        "Use current local weather advisories for farm decisions",
    }
    stale = db.scalars(select(AgriculturalDocument).where(
        AgriculturalDocument.farmer_id.is_(None), AgriculturalDocument.title.in_(stale_titles)
    )).all()
    for document in stale:
        db.delete(document)
    inserted = 0
    for source in DOCUMENTS:
        existing = db.scalar(select(AgriculturalDocument.id).where(AgriculturalDocument.source_url == source["source_url"], AgriculturalDocument.title == source["title"]))
        if existing:
            continue
        db.add(AgriculturalDocument(**source))
        inserted += 1
    if inserted or stale:
        db.commit()
    return inserted


def _terms(text: str) -> set[str]:
    return {term for term in re.findall(r"[\w]+", text.lower(), flags=re.UNICODE) if len(term) > 1}


CROP_ALIASES = {
    "rice": ("rice", "paddy", "వరి", "धान", "നെല്ല്"),
    "cotton": ("cotton", "పత్తి", "ప్రత్తి"),
    "chilli": ("chilli", "chili", "pepper", "మిరప", "మిర్చి"),
    "maize": ("maize", "corn", "మొక్కజొన్న"),
    "groundnut": ("groundnut", "peanut", "వేరుశనగ", "పల్లీ"),
    "tomato": ("tomato", "టమాటా", "టమాట"),
}

TOPIC_ALIASES = {
    "cultivation": ("cultivation", "grow", "growing", "సాగు", "పెంపకం"),
    "soil": ("soil", "land preparation", "seedbed", "నేల", "భూమి", "మట్టి"),
    "irrigation": ("irrigation", "water", "watering", "నీరు", "నీటిపారుదల", "నీటి"),
    "fertilizer": ("fertilizer", "fertiliser", "nutrient", "ఎరువు", "పోషకం"),
    "pest": ("pest", "insect", "worm", "పురుగు", "కీటకం"),
    "disease": ("disease", "symptom", "rot", "wilt", "spot", "వ్యాధి", "తెగులు", "మచ్చ", "వాడటం"),
    "prevention": ("prevention", "prevent", "scouting", "monitor", "నివారణ", "గమనించ"),
    "harvest": ("harvest", "harvesting", "pick", "కోత", "పంట కోయ"),
}


def _has_alias(text: str, alias: str) -> bool:
    if any(ord(char) > 127 for char in alias):
        return alias in text
    return re.search(r"(?<![\w])" + re.escape(alias) + r"(?![\w])", text) is not None


def identify_crops_and_topics(text: str) -> tuple[set[str], set[str]]:
    normalized = text.casefold()
    crops = {crop for crop, aliases in CROP_ALIASES.items() if any(_has_alias(normalized, alias.casefold()) for alias in aliases)}
    topics = {topic for topic, aliases in TOPIC_ALIASES.items() if any(_has_alias(normalized, alias.casefold()) for alias in aliases)}
    return crops, topics


def _metadata_crops(crop_field: str | None) -> set[str]:
    if not crop_field:
        return set()
    return identify_crops_and_topics(crop_field)[0]


def retrieve_documents(db: Session, query: str, crops: list[str] | None = None, limit: int = 4) -> list[RetrievedSource]:
    query_terms = _terms(query)
    detected_crops, detected_topics = identify_crops_and_topics(query)
    profile_crops: set[str] = set()
    for crop_name in crops or []:
        profile_crops.update(identify_crops_and_topics(crop_name)[0])
    # Use profile crops as context only when the question does not name a crop.
    relevant_crops = detected_crops or profile_crops
    documents = db.scalars(select(AgriculturalDocument).where(AgriculturalDocument.source_url.is_not(None))).all()
    ranked: list[RetrievedSource] = []
    for doc in documents:
        searchable = _terms(" ".join(filter(None, [doc.title, doc.content, doc.crop, doc.topic])))
        doc_crops = _metadata_crops(doc.crop)
        _, doc_topics = identify_crops_and_topics(doc.topic or "")
        title_terms = _terms(doc.title)
        score = float(len(query_terms & searchable)) + 2.0 * len(query_terms & title_terms)
        score += 6.0 * len(relevant_crops & doc_crops)
        score += 3.0 * len(detected_topics & doc_topics)
        if score > 0:
            ranked.append(RetrievedSource(doc.id, doc.title, doc.content, doc.crop, doc.topic, doc.source_name, doc.source_url, score))
    return sorted(ranked, key=lambda item: (-item.score, item.title))[:limit]
