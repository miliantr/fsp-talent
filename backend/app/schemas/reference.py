from pydantic import BaseModel


class GradeOut(BaseModel):
    id: str
    name: str
    rank: int
    description: str
    theta_cut: float
    score_threshold: int


class CompetencyOut(BaseModel):
    id: str
    name: str
    weight: float


class SpecializationOut(BaseModel):
    id: str
    name: str
    description: str
    competencies: list[CompetencyOut]


class SkillOut(BaseModel):
    slug: str
    name: str
    kind: str
    specializations: list[str]


class PresetOut(BaseModel):
    id: str
    label: str
    weights: dict[str, float]


class ReferenceOut(BaseModel):
    specializations: list[SpecializationOut]
    grades: list[GradeOut]
    skills: list[SkillOut]
    weight_presets: list[PresetOut]
    component_labels: dict[str, str]
