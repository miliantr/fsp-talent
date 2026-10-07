"""Localization core: locale negotiation, plural rules, formatting, catalogs and the translated
item bank. Catalog parity tests make a missing or mistyped translation fail the build."""

import random
import re
from datetime import date

import pytest

from app.domain.question_bank import FAMILIES, TRANSLATIONS, bank_items
from app.i18n import (
    CATALOGS,
    date_text,
    money,
    msg,
    negotiate,
    number,
    ordinal,
    plural_form,
    render,
    skill_name,
    t,
    use_locale,
)
from app.i18n import en as en_catalog
from app.services.fsp.scoring import AchievementLike, summarize
from app.services.testing.scoring import recommendation

PLACEHOLDER = re.compile(r"\{(\w+)\}")
CYRILLIC = re.compile(r"[А-Яа-яЁё]")


def _placeholders(value) -> set[str]:
    texts = value.values() if isinstance(value, dict) else [value]
    return {p for s in texts for p in PLACEHOLDER.findall(s)}


# ---------------------------------------------------------------- catalogs

def test_catalogs_define_the_same_keys():
    ru, en = set(CATALOGS["ru"]), set(CATALOGS["en"])
    assert ru - en == set(), f"missing in en: {sorted(ru - en)}"
    assert en - ru == set(), f"missing in ru: {sorted(en - ru)}"


@pytest.mark.parametrize("key", sorted(CATALOGS["ru"]))
def test_translations_use_the_same_placeholders(key):
    assert _placeholders(CATALOGS["ru"][key]) == _placeholders(CATALOGS["en"][key]), key


def test_plural_messages_cover_the_language_categories():
    for key, value in CATALOGS["ru"].items():
        if isinstance(value, dict):
            assert {"one", "few", "many"} <= set(value), key
    for key, value in CATALOGS["en"].items():
        if isinstance(value, dict):
            assert {"one", "other"} <= set(value), key


def test_english_catalog_has_no_untranslated_russian():
    leftovers = [k for k, v in en_catalog.MESSAGES.items()
                 if CYRILLIC.search(" ".join(v.values()) if isinstance(v, dict) else v)]
    assert leftovers == []


# ---------------------------------------------------------------- negotiation and formatting

@pytest.mark.parametrize("header, expected", [
    (None, "ru"),
    ("", "ru"),
    ("en", "en"),
    ("en-GB,en;q=0.9", "en"),
    ("ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7", "ru"),
    ("de-DE,de;q=0.9,en;q=0.5", "en"),          # first *supported* language wins
    ("fr, de", "ru"),                           # nothing supported -> default
    ("en;q=0.2, ru;q=0.8", "ru"),               # q-values beat order
    ("ru;q=0, en", "en"),                       # q=0 means "not acceptable"
    ("EN-us", "en"),
    ("en;q=abc, ru", "ru"),                     # malformed q is ignored
])
def test_accept_language_negotiation(header, expected):
    assert negotiate(header) == expected


@pytest.mark.parametrize("n, ru, en", [
    (1, "one", "one"), (2, "few", "other"), (4, "few", "other"), (5, "many", "other"),
    (11, "many", "other"), (12, "many", "other"), (21, "one", "other"), (22, "few", "other"),
    (111, "many", "other"), (0, "many", "other"), (1.5, "other", "other"),
])
def test_plural_rules(n, ru, en):
    assert plural_form(n, "ru") == ru and plural_form(n, "en") == en


def test_number_money_date_and_ordinals_follow_the_locale():
    assert number(1.5, "ru") == "1,5" and number(1.5, "en") == "1.5"
    assert number(180000, "ru") == "180 000" and number(180000, "en") == "180,000"
    assert number(2026, "ru") == "2026"  # years and small numbers are not grouped
    assert money(220000, "ru") == "220 000 ₽" and money(220000, "en") == "220,000 ₽"
    assert date_text(date(2026, 10, 5), "ru") == "05.10.2026"
    assert date_text("2026-10-05T12:00:00", "en") == "5 Oct 2026"
    assert [ordinal(n, "en") for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 101)] == \
        ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "101st"]
    assert ordinal(2, "ru") == "2"


def test_t_plural_interpolation_and_fallbacks():
    assert t("match.reason.fsp", "ru", n=3) == "3 подтверждённых достижения ФСП"
    assert t("match.reason.fsp", "ru", n=5) == "5 подтверждённых достижений ФСП"
    assert t("match.reason.fsp", "en", n=1) == "1 verified FSP achievement"
    assert t("no.such.key", "en") == "no.such.key"
    assert t("match.reason.test", "en", score=70) == "Test: 70/100 (confidence {confidence}%)"  # never raises


def test_t_falls_back_to_russian_for_a_missing_translation(monkeypatch):
    monkeypatch.delitem(CATALOGS["en"], "error.auth_required")
    assert t("error.auth_required", "en") == CATALOGS["ru"]["error.auth_required"]


def test_current_locale_is_scoped():
    with use_locale("en"):
        assert t("error.auth_required") == "Authentication required"
        with use_locale("ru"):
            assert t("error.auth_required") == "Требуется авторизация"
        assert t("error.auth_required") == "Authentication required"
    assert t("error.auth_required") == "Требуется авторизация"
    with use_locale("xx"):  # unsupported -> default
        assert t("error.auth_required") == "Требуется авторизация"


def test_stored_messages_render_in_every_language():
    stored = msg("match.reason.salary_out", salary={"money": 260000},
                 detail=msg("match.detail.salary_over", pct=4))
    assert render(stored, "ru") == "Ожидания 260 000 ₽ — выше вилки на 4%"
    assert render(stored, "en") == "Expectation 260,000 ₽ — 4% above the range"
    related = msg("match.reason.related", pairs=[msg("match.reason.related_pair", via={"skill": "flask"},
                                                     skill={"skill": "fastapi"})])
    assert render(related, "en") == "Related skills: Flask instead of FastAPI"
    missing = msg("match.reason.missing_must", skills=[{"skill": "microservices"}, {"skill": "kafka"}])
    assert render(missing, "ru") == "Нет обязательных навыков: Микросервисы, Kafka"
    assert render(missing, "en") == "Missing must-have skills: Microservices, Kafka"
    assert render({"kind": "positive", "text": "Старый текст"}) == "Старый текст"  # legacy snapshot rows
    assert render("plain") == "plain" and render(None) == ""


def test_skill_names_are_translated_only_when_descriptive():
    assert skill_name("python", "en") == "Python" and skill_name("python", "ru") == "Python"
    assert skill_name("algorithms", "en") == "Algorithms" and skill_name("algorithms", "ru") == "Алгоритмы"
    assert skill_name("unknown-skill", "en") == "unknown-skill"


# ---------------------------------------------------------------- domain texts

def test_fsp_achievement_description_is_localized():
    a = AchievementLike("Кубок ФСП", "Продуктовое программирование", "all_russian", date(2026, 5, 1), 2, 120,
                        "backend", None)
    s = summarize([a], "backend", date(2026, 10, 1))
    assert render(s.best, "ru") == "2 место — Кубок ФСП (2026) · профильная дисциплина"
    # event names are registry data and stay as published
    assert render(s.best, "en") == "2nd place — Кубок ФСП (2026) · core discipline"
    p = AchievementLike("Олимпиада", "Алгоритмическое программирование", "regional", date(2025, 1, 1), None,
                        None, None, None)
    assert render(summarize([p], "frontend", date(2026, 1, 1)).best, "en") == \
        "participant — Олимпиада (2025) · adjacent discipline"


@pytest.mark.parametrize("outcome, grade, expected", [
    ("passed", "middle", "Grade Middle verified."),
    ("passed_upgrade", "middle", "you can take the Senior test right away"),
    ("passed_upgrade", "senior", "Grade Senior verified."),  # no grade above Senior
    ("not_passed", "middle", "You can take the Junior test right away"),
    ("not_passed", "junior", "A new attempt will be available after the waiting period."),
    ("needs_confirmation", "middle", "confirmation form"),
])
def test_recommendation_is_derived_from_the_outcome(outcome, grade, expected):
    with use_locale("en"):
        assert expected in recommendation(outcome, grade)
    with use_locale("en"):
        assert recommendation("passed", "middle", expired=True).endswith("Time ran out.")


# ---------------------------------------------------------------- translated item bank

def test_every_static_item_has_an_english_version_with_the_same_options():
    static = [i for i in bank_items() if not i["family"]]
    assert len(static) == len(TRANSLATIONS["en"])
    for item in static:
        en = item["i18n"]["en"]
        assert len(en["options"]) == len(item["options"]), item["code"]
        assert not CYRILLIC.search(en["text"] + " ".join(en["options"])), item["code"]
        # code fragments and code-like options are kept verbatim, so the answer cannot change meaning
        assert re.findall(r"```.*?```", item["text"], re.S) == re.findall(r"```.*?```", en["text"], re.S), item["code"]


@pytest.mark.parametrize("fam", FAMILIES, ids=lambda f: f.code)
def test_parametric_families_render_both_languages_from_one_draw(fam):
    for seed in range(40):
        r = fam.render(random.Random(seed))
        en = r["i18n"]["en"]
        assert len(en["options"]) == len(r["options"])
        assert not CYRILLIC.search(en["text"] + " ".join(en["options"]))
        # the same parameters (every number of the question) in both languages
        assert sorted(re.findall(r"\d+", r["text"])) == sorted(re.findall(r"\d+", en["text"]))
