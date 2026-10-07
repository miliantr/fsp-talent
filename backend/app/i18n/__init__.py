"""Localization of server-generated text.

The request locale comes from `Accept-Language` (the web client sends the UI language with every
request) and is kept in a context variable for the duration of the request, so services simply call
`t(key, **params)`.

Text that is *stored* (match explanations, invitation reasons) is kept as a message object
`{"code": key, "params": {...}}` and rendered on read: an employer reading in English and a
candidate reading in Russian see the same snapshot in their own language. Params are
language-neutral (ids, numbers, proper names); a param that itself needs translation is a nested
message object, and `{"money": n}` is a monetary amount formatted per locale.
"""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import date
from typing import Any

from app.domain.catalog import SKILLS
from app.i18n import en, ru

SKILL_NAMES = {s[0]: s[1] for s in SKILLS}

SUPPORTED = ("ru", "en")
DEFAULT = "ru"
CATALOGS: dict[str, dict[str, Any]] = {"ru": ru.MESSAGES, "en": en.MESSAGES}

_current: ContextVar[str] = ContextVar("locale", default=DEFAULT)


# ---------------------------------------------------------------- locale selection

def normalize(tag: str | None) -> str | None:
    """'en-GB' -> 'en'; unsupported or empty -> None."""
    if not tag:
        return None
    base = tag.strip().lower().replace("_", "-").split("-")[0]
    return base if base in SUPPORTED else None


def negotiate(header: str | None, default: str = DEFAULT) -> str:
    """Pick the best supported language from an Accept-Language header (RFC 9110 q-values)."""
    best, best_q = default, -1.0
    for i, part in enumerate((header or "").split(",")):
        tag, _, rest = part.strip().partition(";")
        q = 1.0
        if rest.strip().startswith("q="):
            try:
                q = float(rest.strip()[2:])
            except ValueError:
                q = 0.0
        lang = normalize(tag)
        # earlier entries win ties, as browsers list preferences in order
        if lang and q > 0 and q - i * 1e-6 > best_q:
            best, best_q = lang, q - i * 1e-6
    return best


def get_locale() -> str:
    return _current.get()


def set_locale(locale: str) -> Token:
    return _current.set(normalize(locale) or DEFAULT)


def reset_locale(token: Token) -> None:
    _current.reset(token)


@contextmanager
def use_locale(locale: str | None) -> Iterator[str]:
    token = set_locale(locale or DEFAULT)
    try:
        yield get_locale()
    finally:
        reset_locale(token)


# ---------------------------------------------------------------- formatting

def plural_form(n: float, locale: str) -> str:
    """CLDR plural category for cardinal numbers (ru: one/few/many/other, en: one/other)."""
    if locale == "ru":
        if not float(n).is_integer():
            return "other"
        i = abs(int(n))
        if i % 10 == 1 and i % 100 != 11:
            return "one"
        if 2 <= i % 10 <= 4 and not 12 <= i % 100 <= 14:
            return "few"
        return "many"
    return "one" if n == 1 else "other"


def number(x: float, locale: str | None = None) -> str:
    """1.5 -> '1,5' (ru) / '1.5' (en); integers ≥ 10 000 are grouped: '180 000' / '180,000'."""
    locale = locale or get_locale()
    if isinstance(x, float) and not x.is_integer():
        s = f"{x:g}"
        return s.replace(".", ",") if locale == "ru" else s
    n = int(x)
    if abs(n) < 10_000:
        return str(n)
    s = f"{n:,}"
    return s.replace(",", " ") if locale == "ru" else s


def money(x: int, locale: str | None = None) -> str:
    locale = locale or get_locale()
    s = f"{int(x):,}"
    return (s.replace(",", " ") if locale == "ru" else s) + " ₽"


_MONTHS_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def date_text(value: date | str, locale: str | None = None) -> str:
    """05.10.2026 (ru) / 5 Oct 2026 (en)."""
    locale = locale or get_locale()
    d = date.fromisoformat(value[:10]) if isinstance(value, str) else value
    return f"{d:%d.%m.%Y}" if locale == "ru" else f"{d.day} {_MONTHS_EN[d.month - 1]} {d.year}"


def ordinal(n: int, locale: str | None = None) -> str:
    """'2' (ru: «2 место») / '2nd' (en: '2nd place')."""
    locale = locale or get_locale()
    if locale != "en":
        return str(n)
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class _Params(dict):
    def __missing__(self, key: str) -> str:  # a missing placeholder never breaks a response
        return "{" + key + "}"


def _resolve(value: Any, locale: str) -> Any:
    if isinstance(value, Mapping):
        if "money" in value:
            return money(value["money"], locale)
        if "skill" in value:
            return skill_name(value["skill"], locale)
        if "competency" in value:
            return competency_name(value["competency"], locale)
        if "date" in value:
            return date_text(value["date"], locale)
        if "ordinal" in value:
            return ordinal(value["ordinal"], locale)
        if "code" in value:
            return render(value, locale)
    if isinstance(value, list):
        return ", ".join(str(_resolve(v, locale)) for v in value)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return number(value, locale)
    return value


def t(key: str, /, locale: str | None = None, **params: Any) -> str:
    """Translate `key` into the current (or given) locale, falling back to Russian, then to the key."""
    locale = locale or get_locale()
    template = CATALOGS.get(locale, {}).get(key)
    if template is None:
        template = CATALOGS[DEFAULT].get(key, key)
    if isinstance(template, dict):  # plural forms, selected by the `n` param
        n = params.get("n", 0)
        form = plural_form(n, locale)
        template = template.get(form) or template.get("other") or next(iter(template.values()))
    if not params:
        return template
    return template.format_map(_Params({k: _resolve(v, locale) for k, v in params.items()}))


# ---------------------------------------------------------------- stored message objects

def msg(code: str, **params: Any) -> dict:
    """A language-neutral message object, safe to persist as JSON."""
    return {"code": code, "params": params} if params else {"code": code}


def render(message: Mapping | str | None, locale: str | None = None) -> str:
    """Render a stored message object; legacy rows stored plain text and are returned as is."""
    if message is None:
        return ""
    if isinstance(message, str):
        return message
    if "code" not in message:
        return str(message.get("text", ""))
    return t(message["code"], locale, **message.get("params", {}))


# ---------------------------------------------------------------- localized reference names

def has(key: str, locale: str | None = None) -> bool:
    return key in CATALOGS.get(locale or get_locale(), {}) or key in CATALOGS[DEFAULT]


def skill_name(slug: str, locale: str | None = None) -> str:
    """Technology names are proper nouns; only the few descriptive ones are translated."""
    key = f"ref.skill.{slug}"
    return t(key, locale) if has(key, locale) else SKILL_NAMES.get(slug, slug)


def competency_name(competency_id: str, locale: str | None = None) -> str:
    key = f"ref.competency.{competency_id}"
    return t(key, locale) if has(key, locale) else competency_id


def component_label(key: str, locale: str | None = None) -> str:
    return t(f"ref.component.{key}", locale)


def component_labels(locale: str | None = None) -> dict[str, str]:
    from app.services.matching.config import COMPONENTS
    return {k: component_label(k, locale) for k in COMPONENTS}


def preset_label(preset: str, locale: str | None = None) -> str:
    return t(f"ref.preset.{preset}", locale)


__all__ = ["CATALOGS", "DEFAULT", "SUPPORTED", "competency_name", "component_label", "component_labels",
           "date_text", "get_locale", "has", "money", "msg", "negotiate", "normalize", "number", "ordinal",
           "plural_form", "preset_label", "render", "reset_locale", "set_locale", "skill_name", "t",
           "use_locale"]
