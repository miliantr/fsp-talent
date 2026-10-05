"""Idempotent seeding of reference data and the item bank."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.catalog import COMPETENCIES, GRADES, SKILLS, SPECIALIZATIONS
from app.domain.question_bank import bank_items
from app.models import Competency, Grade, Question, Skill, Specialization


def seed_reference(db: Session) -> None:
    for i, s in enumerate(SPECIALIZATIONS):
        obj = db.get(Specialization, s["id"]) or Specialization(id=s["id"])
        obj.name, obj.description, obj.sort_order = s["name"], s["description"], i
        db.merge(obj)
    for g in GRADES:
        obj = db.get(Grade, g["id"]) or Grade(id=g["id"])
        obj.name, obj.rank, obj.description, obj.theta_cut = g["name"], g["rank"], g["description"], g["theta_cut"]
        db.merge(obj)
    db.flush()
    for i, (cid, spec, name, weight) in enumerate(COMPETENCIES):
        obj = db.get(Competency, cid) or Competency(id=cid)
        obj.specialization_id, obj.name, obj.weight, obj.sort_order = spec, name, weight, i
        db.merge(obj)
    existing = {s.slug: s for s in db.scalars(select(Skill))}
    for slug, name, kind, aliases, cmap, related in SKILLS:
        obj = existing.get(slug) or Skill(slug=slug)
        obj.name, obj.kind, obj.aliases, obj.competency_map, obj.related = name, kind, aliases, cmap, related
        db.add(obj)
    db.flush()
    seed_questions(db)
    db.commit()


def seed_questions(db: Session) -> None:
    """Questions are versioned by code: changed content creates a new version, the old one is
    deactivated (attempts keep referencing the exact version they were generated from)."""
    current = {(q.code, q.version): q for q in db.scalars(select(Question))}
    latest: dict[str, Question] = {}
    for q in current.values():
        if q.code not in latest or q.version > latest[q.code].version:
            latest[q.code] = q
    for item in bank_items():
        q = latest.get(item["code"])
        fields = ("text", "options", "correct", "difficulty", "qtype", "competency_id", "irt_a", "irt_b", "irt_c")
        if q and all(getattr(q, f) == item[f] for f in fields):
            if q.i18n != item.get("i18n"):
                q.i18n = item.get("i18n")  # a translation does not change the item: no new version
            continue
        version = (q.version + 1) if q else 1
        if q:
            q.is_active = False
        db.add(Question(version=version, **item))
