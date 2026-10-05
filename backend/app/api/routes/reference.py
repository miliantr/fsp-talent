from fastapi import APIRouter

from app.domain.catalog import COMPETENCIES, GRADES, SKILLS, SPECIALIZATIONS
from app.i18n import competency_name, component_labels, preset_label, skill_name, t
from app.schemas.reference import ReferenceOut
from app.services.matching.config import PRESETS

router = APIRouter(prefix="/reference", tags=["Справочники"])


@router.get("", response_model=ReferenceOut, summary="Специализации, грейды, компетенции, навыки")
def reference():
    """Reference data in the request language (Accept-Language)."""
    skills = [{"slug": s, "name": skill_name(s), "kind": k, "specializations": sorted(cm)}
              for s, _n, k, _a, cm, _r in SKILLS]
    return {
        "specializations": [
            {**s, "description": t(f"ref.spec.{s['id']}.description"),
             "competencies": [{"id": c, "name": competency_name(c), "weight": w}
                              for c, sp, _n, w in COMPETENCIES if sp == s["id"]]}
            for s in SPECIALIZATIONS
        ],
        "grades": [{**g, "description": t(f"ref.grade.{g['id']}.description"),
                    "score_threshold": round(50 + 25 * g["theta_cut"])} for g in GRADES],
        "skills": sorted(skills, key=lambda x: x["name"].lower()),
        "weight_presets": [{"id": k, "label": preset_label(k), "weights": v} for k, v in PRESETS.items()],
        "component_labels": component_labels(),
    }
