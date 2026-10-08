"""Build the accompanying documentation as a single PDF (TЗ 5.2: "документация в формате doc или pdf").

    pip install markdown playwright
    python scripts/build_docs_pdf.py            # -> docs/FSP_Talent_documentation.pdf

Sources: README.md, docs/*.md and the screenshots in docs/img. Rendered by the locally installed
Google Chrome (Playwright, channel="chrome").
"""

import base64
import datetime as dt
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


def build_html() -> str:
    parts = [f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>"]
    parts.append(
        "<section class='cover'><div><div style='font-size:12pt;opacity:.85'>Федерация спортивного "
        "программирования России · спецтрек</div><h1>FSP Talent</h1><div class='sub'>Цифровая платформа подбора "
        "ИТ-специалистов с обратной механикой и верифицированным профилем достижений участника ФСП"
        "</div></div><div class='meta'>Сопроводительная документация · "
        f"{dt.date.today():%d.%m.%Y}</div></section>"
    )
    toc = "".join(f"<li>{i}. {title}</li>" for i, (_, title) in enumerate(CHAPTERS + [(None, 'Интерфейс')], 1))
    parts.append(f"<section class='chapter'><h1>Содержание</h1><ol class='toc' style='list-style:none;padding:0'>{toc}</ol>"
                 "<p>Документ собран из исходных файлов репозитория (<code>README.md</code>, <code>docs/*.md</code>). "
                 "Отчёты валидации — <code>evaluation/results/</code>, API — Swagger UI по адресу "
                 "<code>/api/docs</code>.</p></section>")
    for i, (src, title) in enumerate(CHAPTERS, 1):
        body = md_to_html((ROOT / src).read_text(encoding="utf-8"))
        parts.append(f"<section class='chapter'><h1>{i}. {title}</h1>{body}</section>")
    gallery = "".join(f"<figure>{img_tag(n)}<figcaption>{c}</figcaption></figure>" for n, c in SCREENS)
    parts.append(f"<section class='chapter'><h1>{len(CHAPTERS) + 1}. Интерфейс</h1>{gallery}</section>")
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
