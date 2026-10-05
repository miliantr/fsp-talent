"""Lightweight NLP: extraction of skills, specialization, grade, experience, salary and contacts
from free text (a PDF resume or an employer's description of a need).

Dictionary + rules approach over the skill catalog with Russian/English aliases: deterministic,
explainable and dependency-free. The interface (`parse_resume_text`, `parse_need_text`) allows
replacing it with an ML NER model later without touching callers.
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache

from app.domain.catalog import SKILLS

SPEC_KEYWORDS = {
    "backend": ["backend", "back-end", "бэкенд", "бекенд", "бэк-энд", "серверн", "api"],
    "frontend": ["frontend", "front-end", "фронтенд", "фронт-энд", "вёрстк", "верстк", "spa", "ui"],
    "data_ml": ["data scien", "machine learning", "машинн", "ml-", "ml ", "data analyst", "аналитик данных",
                "data engineer", "нейросет", "computer vision", "nlp"],
    "devops": ["devops", "девопс", "sre", "инфраструктур", "platform engineer", "администрир"],
}
GRADE_KEYWORDS = {
    "senior": ["senior", "сеньор", "синьор", "ведущ", "lead", "тимлид", "архитектор"],
    "middle": ["middle", "мидл", "миддл"],
    "junior": ["junior", "джун", "стажёр", "стажер", "intern", "начинающ"],
}
FORMAT_KEYWORDS = {
    "remote": ["удалён", "удален", "remote", "из дома"],
    "hybrid": ["гибрид", "hybrid"],
    "office": ["офис", "office"],
}
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+7|8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}")
TG_RE = re.compile(r"(?:t\.me/|telegram[:\s]*|tg[:\s]*)@?([A-Za-z][\w]{4,31})|(?<![\w.])@([A-Za-z][\w]{4,31})\b")
EXP_RE = re.compile(r"(\d{1,2}(?:[.,]\d)?)\s*\+?\s*(?:год|года|лет|years?|yrs)", re.I)
SALARY_RE = re.compile(r"(\d{2,3}(?:[\s ]?\d{3})?)\s*(тыс|k|к|000|₽|руб)?", re.I)
NAME_RE = re.compile(r"^([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+)(?:\s+[А-ЯЁ][а-яё]+)?$")


@lru_cache
def _alias_patterns() -> list[tuple[str, re.Pattern]]:
    out = []
    for slug, name, _kind, aliases, _cm, _rel in SKILLS:
        for alias in {slug.replace("_", " "), name.lower(), *[a.lower() for a in aliases]}:
            if len(alias) < 2:
                continue
            out.append((slug, re.compile(rf"(?<![\w+#]){re.escape(alias)}(?![\w+#])", re.I)))
    return out


def extract_skills(text: str) -> list[str]:
    found: Counter = Counter()
    for slug, pat in _alias_patterns():
        n = len(pat.findall(text))
        if n:
            found[slug] += n
    return [s for s, _ in found.most_common()]


def detect_specialization(text: str, skills: list[str]) -> str | None:
    low = text.lower()
    votes: Counter = Counter()
    for spec, kws in SPEC_KEYWORDS.items():
        votes[spec] += 2 * sum(low.count(k) for k in kws)
    skill_map = {s[0]: s[4] for s in SKILLS}
    for slug in skills:
        for spec in skill_map.get(slug, {}):
            votes[spec] += 1
    if not votes or votes.most_common(1)[0][1] == 0:
        return None
    return votes.most_common(1)[0][0]


def detect_grade(text: str) -> str | None:
    low = text.lower()
    for grade in ("senior", "middle", "junior"):
        if any(k in low for k in GRADE_KEYWORDS[grade]):
            return grade
    return None


def detect_experience(text: str) -> float | None:
    vals = [float(m.replace(",", ".")) for m in EXP_RE.findall(text)]
    vals = [v for v in vals if 0 < v <= 40]
    return max(vals) if vals else None


def detect_format(text: str) -> str | None:
    low = text.lower()
    for fmt, kws in FORMAT_KEYWORDS.items():
        if any(k in low for k in kws):
            return fmt
    return None


def detect_salary(text: str) -> tuple[int | None, int | None]:
    vals = []
    for num, unit in SALARY_RE.findall(text):
        v = int(re.sub(r"\D", "", num))
        if unit and unit.lower() in ("тыс", "k", "к"):
            v *= 1000
        if 20_000 <= v <= 2_000_000:
            vals.append(v)
    if not vals:
        return None, None
    return (min(vals), max(vals)) if len(vals) > 1 else (vals[0], None)


@dataclass
class ParsedText:
    skills: list[str] = field(default_factory=list)
    specialization: str | None = None
    grade: str | None = None
    experience_years: float | None = None
    work_format: str | None = None
    salary_from: int | None = None
    salary_to: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    telegram: str | None = None


def parse_need_text(text: str) -> ParsedText:
    skills = extract_skills(text)
    s_from, s_to = detect_salary(text)
    return ParsedText(skills=skills, specialization=detect_specialization(text, skills),
                      grade=detect_grade(text), experience_years=detect_experience(text),
                      work_format=detect_format(text), salary_from=s_from, salary_to=s_to)


def parse_resume_text(text: str) -> ParsedText:
    p = parse_need_text(text)  # salary_from = expected salary if mentioned
    m = EMAIL_RE.search(text)
    p.email = m.group(0) if m else None
    m = PHONE_RE.search(text)
    p.phone = re.sub(r"[^\d+]", "", m.group(0)) if m else None
    for tg in TG_RE.findall(text):
        handle = tg[0] or tg[1]
        if handle and (not p.email or handle not in p.email):
            p.telegram = "@" + handle
            break
    for line in text.splitlines()[:8]:
        nm = NAME_RE.match(line.strip())
        if nm:
            p.last_name, p.first_name = nm.group(1), nm.group(2)  # Russian CVs: "Фамилия Имя"
            break
    return p


def pdf_to_text(data: bytes) -> str:
    import io

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages[:10])
