from fastapi import APIRouter

from app.domain.catalog import COMPETENCIES, GRADES, SKILLS, SPECIALIZATIONS
from app.schemas.reference import ReferenceOut
from app.services.matching.config import COMPONENT_LABELS, PRESET_LABELS, PRESETS

router = APIRouter(prefix="/reference", tags=["Справочники"])


@router.get("", response_model=ReferenceOut, summary="Специализации, грейды, компетенции, навыки")
def reference():
    return {
        "specializations": [
            {**s, "competencies": [{"id": c, "name": n, "weight": w}
                                   for c, sp, n, w in COMPETENCIES if sp == s["id"]]}
            for s in SPECIALIZATIONS
        ],
        "grades": [{**g, "score_threshold": round(50 + 25 * g["theta_cut"])} for g in GRADES],
        "skills": [{"slug": s, "name": n, "kind": k, "specializations": sorted(cm)}
                   for s, n, k, _a, cm, _r in sorted(SKILLS, key=lambda x: x[1].lower())],
        "weight_presets": [{"id": k, "label": PRESET_LABELS[k], "weights": v} for k, v in PRESETS.items()],
        "component_labels": COMPONENT_LABELS,
    }
