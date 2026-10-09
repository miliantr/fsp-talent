"""Build the accompanying documentation as a single PDF (TЗ 5.2: "документация в формате doc или pdf").

    pip install markdown playwright
    python backend/scripts/export_openapi.py    # refresh frontend/openapi.json (the endpoint appendix)
    python scripts/build_docs_pdf.py            # -> docs/FSP_Talent_documentation.pdf

Sources: README.md, docs/*.md, the screenshots in docs/img, the validation reports in
evaluation/results and the OpenAPI spec (frontend/openapi.json). The PDF is self-contained: the
reviewer needs neither the repository nor a running server to read the validation results or the API.
Rendered by the locally installed Google Chrome (Playwright, channel="chrome").
"""

import base64
import datetime as dt
import html as html_lib
import json
import re
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = DOCS / "FSP_Talent_documentation.pdf"

CHAPTERS = [
    ("README.md", "Обзор решения"),
    ("docs/clarifications.md", "Уточнения заказчика"),
    ("docs/architecture.md", "Архитектура"),
    ("docs/matching.md", "Механика подбора"),
    ("docs/testing.md", "Механика тестирования"),
    ("docs/fsp-integration.md", "Интеграция с реестром ФСП"),
    ("docs/api.md", "API"),
    ("docs/deployment.md", "Сборка и развёртывание"),
]

# TЗ 3.4: what the accompanying documentation must describe -> where it is in this PDF
REQUIREMENTS = [
    ("Функциональная и компонентная архитектура решения", "3. Архитектура — §1, §2, §3"),
    ("Механика тестирования и её устойчивость к распространению заданий",
     "5. Механика тестирования — §1–§6"),
    ("Механика подбора и логика категоризации кандидатов", "4. Механика подбора — §2–§5"),
    ("Собственная процедура валидации и её результаты",
     "5. Механика тестирования — §7; 4. Механика подбора — §6; приложения А и Б"),
    ("Схема интеграции с реестром ФСП", "6. Интеграция с реестром ФСП"),
    ("Описание API", "7. API; приложение В — все эндпоинты"),
    ("Используемые библиотеки и компоненты с версиями", "3. Архитектура — §6"),
    ("Пошаговая инструкция по сборке, развёртыванию и запуску", "8. Сборка и развёртывание; 1. Обзор — «Быстрый старт»"),
]

APPENDICES = [
    ("А", "Отчёт валидации тестирования", ["evaluation/results/tests_report.md"]),
    ("Б", "Отчёты валидации подбора", ["evaluation/results/matching_report.md", "evaluation/results/tuning_report.md"]),
]

SCREENS = [
    ("01-landing", "Главная страница: обратная механика подбора и демо-доступ"),
    ("02-candidate-dashboard", "Кабинет кандидата: подтверждённая категория, шкальный балл, приглашения"),
    ("03-test-runner", "Прохождение теста: индивидуальный вариант по единому плану, таймер, автосохранение"),
    ("04-test-result", "Результат теста: категория, положение на шкале грейдов, компетенции, уверенность"),
    ("05-fsp", "Достижения ФСП: автоматическое обогащение профиля из реестра"),
    ("06-employer-dashboard", "Кабинет работодателя: потребности, воронка приглашений"),
    ("07-need-form", "Описание потребности: разбор текста в специализацию, грейд, стек и вилку"),
    ("08-matches", "Подборка: рекомендованные категории, рейтинг, объяснение, вклад факторов"),
    ("09-compare", "Почему кандидат A выше кандидата B"),
    ("11-candidate-explanation", "Профиль кандидата для работодателя: объяснение совпадения, контакты скрыты"),
    ("10-candidate-invitation", "Приглашение у кандидата: компания, предложение и зарплата до ответа"),
    ("12-candidate-tasks", "Регулярные задания у кандидата: задача, предложенная системой, и почему именно она"),
    ("13-employer-task-review", "Проверка подхода: предварительная оценка по ключевым идеям и рубрика работодателя"),
]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Unbounded:wght@600&display=swap');
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
body { font-family: Manrope, 'Segoe UI', sans-serif; font-size: 10.5pt; line-height: 1.5; color: #1a1330; }
h1, h2, h3 { color: #2b0a5c; line-height: 1.25; break-after: avoid; page-break-after: avoid; }
h1 { font-family: Unbounded, Manrope, sans-serif; font-weight: 600; font-size: 20pt; margin: 0 0 10pt; }
h2 { font-size: 14pt; margin: 18pt 0 6pt; border-bottom: 1.5pt solid #e3dbf0; padding-bottom: 3pt; }
h3 { font-size: 12pt; margin: 14pt 0 4pt; }
a { color: #5a17b8; text-decoration: none; }
code { font-family: Consolas, 'JetBrains Mono', monospace; font-size: 9pt; background: #f3effa; padding: 0 3pt; border-radius: 3pt; }
pre { background: #1d1533; color: #efe9ff; padding: 8pt 10pt; border-radius: 6pt; white-space: pre-wrap;
      word-break: break-word; font-size: 8.5pt; line-height: 1.4; break-inside: avoid; }
pre code { background: none; color: inherit; padding: 0; font-size: inherit; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt; font-size: 9pt; break-inside: auto; }
th { background: #f3ecff; color: #47108f; text-align: left; }
th, td { border: 0.75pt solid #e3dbf0; padding: 4pt 6pt; vertical-align: top; }
tr { break-inside: avoid; }
blockquote { border-left: 3pt solid #6b21d6; margin: 8pt 0; padding: 4pt 10pt; background: #f8f5fd; color: #4a4263; }
.chapter { break-before: page; }
.cover { height: 250mm; display: flex; flex-direction: column; justify-content: space-between;
         background: linear-gradient(135deg, #1e0646 0%, #3d0e86 45%, #7d22c9 85%, #b73bd6 100%);
         color: #fff; padding: 22mm 18mm; margin: -18mm -16mm 0; border-radius: 0; }
.cover h1 { color: #fff; font-size: 30pt; margin-top: 40mm; }
.cover .sub { font-size: 13pt; opacity: .9; max-width: 150mm; }
.cover .meta { font-size: 10pt; opacity: .8; }
.toc li { margin: 3pt 0; font-size: 11pt; }
/* the endpoint list: fixed columns, long paths wrap — a table wider than the page would make Chrome
   shrink the whole document to fit */
table.api { table-layout: fixed; }
table.api td code { white-space: normal; word-break: break-all; }
table.api td { overflow-wrap: anywhere; }
figure { margin: 0 0 12pt; break-inside: avoid; text-align: center; }
figure img { width: 100%; border: 0.75pt solid #e3dbf0; border-radius: 6pt; }
figcaption { font-size: 9pt; color: #4a4263; margin-top: 4pt; }
"""


def md_to_html(text: str) -> str:
    # demote headings: chapter title is the only h1
    html = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    html = re.sub(r"<h1>.*?</h1>", "", html, count=1, flags=re.S)
    # cross-links between markdown files make no sense inside a single PDF
    return re.sub(r'<a href="(?!http)[^"]*">(.*?)</a>', r"\1", html)


def img_tag(name: str) -> str:
    data = base64.b64encode((DOCS / "img" / f"{name}.png").read_bytes()).decode()
    return f'<img src="data:image/png;base64,{data}">'


def report_html(paths: list[str]) -> str:
    """Validation reports as written by evaluation/*.py; each report keeps its own title as a subsection."""
    out = []
    for rel in paths:
        text = (ROOT / rel).read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip()
        out.append(f"<h2>{html_lib.escape(title)}</h2>{md_to_html(text)}"
                   f"<p style='font-size:8.5pt;color:#7a7194'>Источник: <code>{rel}</code></p>")
    return "".join(out)


def endpoints_html() -> str:
    """Every endpoint of the OpenAPI spec: method, path, purpose, request body, response codes."""
    spec = json.loads((ROOT / "frontend" / "openapi.json").read_text(encoding="utf-8"))
    by_tag: dict[str, list[str]] = {}
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            body = op.get("requestBody", {}).get("content", {})
            schema = next(iter(body.values()), {}).get("schema", {}) if body else {}
            ref = "файл (multipart)" if "multipart/form-data" in body else schema.get("$ref", "").rsplit("/", 1)[-1]
            codes = ", ".join(sorted(op.get("responses", {})))
            row = (f"<tr><td><b>{method.upper()}</b></td><td><code>{html_lib.escape(path)}</code></td>"
                   f"<td>{html_lib.escape(op.get('summary', ''))}</td><td>{html_lib.escape(ref)}</td><td>{codes}</td></tr>")
            by_tag.setdefault((op.get("tags") or ["Прочее"])[0], []).append(row)
    out = [f"<p>Сформировано из спецификации OpenAPI {spec.get('openapi', '')} ({len(spec['paths'])} адресов). "
           "Авторизация — <code>Authorization: Bearer &lt;JWT&gt;</code>; ошибки — "
           "<code>{code, message, details}</code>; язык — <code>Accept-Language</code>. Схемы запросов и ответов — "
           "в Swagger UI (<code>/api/docs</code>) и в <code>frontend/openapi.json</code>.</p>"]
    for tag, rows in by_tag.items():
        out.append(f"<h2>{html_lib.escape(tag)}</h2><table class='api'><colgroup><col style='width:9%'>"
                   "<col style='width:34%'><col style='width:31%'><col style='width:15%'><col style='width:11%'>"
                   "</colgroup><thead><tr><th>Метод</th><th>Путь</th><th>Назначение</th><th>Тело запроса</th>"
                   f"<th>Коды ответа</th></tr></thead><tbody>{''.join(rows)}</tbody></table>")
    return "".join(out)


def build_html() -> str:
    parts = [f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>"]
    parts.append(
        "<section class='cover'><div><div style='font-size:12pt;opacity:.85'>Федерация спортивного "
        "программирования России · спецтрек</div><h1>FSP Talent</h1><div class='sub'>Цифровая платформа подбора "
        "ИТ-специалистов с обратной механикой и верифицированным профилем достижений участника ФСП"
        "</div></div><div class='meta'>Команда Mytischi Dynamics · Сопроводительная документация · "
        f"{dt.date.today():%d.%m.%Y}</div></section>"
    )
    toc = "".join(f"<li>{i}. {title}</li>" for i, (_, title) in enumerate(CHAPTERS + [(None, 'Интерфейс')], 1))
    toc += "".join(f"<li>Приложение {letter}. {title}</li>" for letter, title, _ in APPENDICES)
    toc += "<li>Приложение В. Перечень эндпоинтов API</li>"
    req = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in REQUIREMENTS)
    parts.append(f"<section class='chapter'><h1>Содержание</h1><ol class='toc' style='list-style:none;padding:0'>{toc}</ol>"
                 "<h2>Требования к документации (п. 3.4 ТЗ) — где описано</h2>"
                 f"<table><thead><tr><th>Требование</th><th>Раздел</th></tr></thead><tbody>{req}</tbody></table>"
                 "<p>Документ собран из исходных файлов репозитория (<code>README.md</code>, <code>docs/*.md</code>, "
                 "<code>evaluation/results/*.md</code>, спецификация OpenAPI) и самодостаточен: полные отчёты валидации и "
                 "перечень эндпоинтов приведены в приложениях. Интерактивная спецификация — Swagger UI по адресу "
                 "<code>/api/docs</code>.</p></section>")
    for i, (src, title) in enumerate(CHAPTERS, 1):
        body = md_to_html((ROOT / src).read_text(encoding="utf-8"))
        parts.append(f"<section class='chapter'><h1>{i}. {title}</h1>{body}</section>")
    gallery = "".join(f"<figure>{img_tag(n)}<figcaption>{c}</figcaption></figure>" for n, c in SCREENS)
    parts.append(f"<section class='chapter'><h1>{len(CHAPTERS) + 1}. Интерфейс</h1>{gallery}</section>")
    for letter, title, paths in APPENDICES:
        parts.append(f"<section class='chapter'><h1>Приложение {letter}. {title}</h1>{report_html(paths)}</section>")
    parts.append(f"<section class='chapter'><h1>Приложение В. Перечень эндпоинтов API</h1>{endpoints_html()}</section>")
    parts.append("</body></html>")
    return "".join(parts)


def main() -> None:
    html = build_html()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        page.pdf(
            path=str(OUT), format="A4", print_background=True, display_header_footer=True,
            header_template="<span></span>",
            footer_template="<div style='font-size:8px;width:100%;text-align:center;color:#7a7194'>"
                            "FSP Talent · <span class='pageNumber'></span> / <span class='totalPages'></span></div>",
            margin={"top": "16mm", "bottom": "16mm", "left": "14mm", "right": "14mm"},
        )
        browser.close()
    print(f"written {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
