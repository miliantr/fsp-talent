from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.catalog import COMPETENCIES, SKILLS
from app.models import Skill
from app.services.matching.engine import SkillGraph, SkillInfo

COMPETENCY_NAMES = {c[0]: c[2] for c in COMPETENCIES}


@lru_cache
def skill_graph() -> SkillGraph:
    """The skill graph is static reference data, built once from the catalog."""
    return SkillGraph([SkillInfo(slug, name, cm, rel) for slug, name, _k, _a, cm, rel in SKILLS])


def skills_by_slug(db: Session, slugs: list[str]) -> dict[str, Skill]:
    if not slugs:
        return {}
    return {s.slug: s for s in db.scalars(select(Skill).where(Skill.slug.in_(slugs)))}
