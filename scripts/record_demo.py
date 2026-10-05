"""Record the end-to-end demo video (TЗ 3.3) against the running docker compose stack.

    docker compose up -d --build
    pip install playwright imageio-ffmpeg && python -m playwright install ffmpeg
    python scripts/record_demo.py                 # -> presentation/FSP_Talent_demo.mp4 (and .webm)

The scenario follows the TЗ: candidate registration (auto-linked to the FSP registry), PDF resume
parsing, survey and grade test, category assignment, publication consent; the employer describes a
need, gets the explained shortlist, compares candidates and invites one with a salary range; the
candidate accepts and the contacts open; finally the classic flow — an application to a vacancy.
Captions explain the testing and matching mechanics on screen.

The demo database is reset (`python -m app.seed --reset` in the backend container) before and after
recording. The scripted candidate reads its attempt's answer key from PostgreSQL to produce a
realistic Middle result (the six hardest items are answered wrong); the key never reaches the UI.
Requires Google Chrome (Playwright channel="chrome").
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import Locator, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8080"
W, H = 1440, 810
PASSWORD = "demo12345"
CANDIDATE = {"first": "Олег", "last": "Олимпиев", "email": "olymp@demo.ru"}  # in the mock FSP registry
NEED_TEXT = ("Ищем Middle Python-разработчика в команду платёжного шлюза: FastAPI, PostgreSQL, Docker, "
             "желательно Redis. Вилка 190–260 тыс., гибрид, Москва, опыт от 2 лет.")

RESUME_HTML = """<!doctype html><html lang="ru"><meta charset="utf-8"><style>
body{font-family:Arial,sans-serif;margin:48px;color:#1c1d22;line-height:1.45}h1{margin:0;font-size:28px}
h2{font-size:16px;margin:22px 0 6px;color:#520978}p{margin:4px 0}</style>
<h1>Олимпиев Олег</h1><p>Python backend-разработчик, Middle</p>
<p>Москва · +7 916 555-12-34 · Telegram: @oleg_olymp · olymp@demo.ru</p>
<h2>Навыки</h2><p>Python, FastAPI, PostgreSQL, Docker, Redis, Git, Linux</p>
<h2>Опыт работы — 3 года</h2>
<p>2023–2026 · ООО «Платёжные решения» — backend-разработчик: REST API на FastAPI, PostgreSQL,
очереди и кэширование на Redis, контейнеризация в Docker.</p>
<h2>Пожелания</h2><p>Зарплата от 220 000 ₽, гибридный формат.</p>
<h2>Достижения</h2><p>Призёр Всероссийских соревнований по продуктовому программированию (ФСП).</p>
</html>"""

# Overlay: captions, chapter cards and a visible mouse cursor (Playwright videos have no cursor).
OVERLAY_JS = """
(() => {
  if (window.__demo) return; window.__demo = true;
  const css = `
  #__cap{position:fixed;left:50%;bottom:26px;transform:translateX(-50%);max-width:78%;z-index:2147483646;
    background:rgba(28,13,48,.92);color:#fff;font:600 19px/1.4 Manrope,Arial,sans-serif;padding:12px 22px;
    border-radius:14px;box-shadow:0 10px 30px rgba(0,0,0,.25);text-align:center;transition:opacity .3s;pointer-events:none}
  #__cap:empty{opacity:0}
  #__card{position:fixed;inset:0;z-index:2147483645;display:flex;flex-direction:column;align-items:center;
    justify-content:center;gap:14px;background:linear-gradient(135deg,#310f53,#6a1b9a 60%,#ff0053);color:#fff;
    font-family:Manrope,Arial,sans-serif;text-align:center;transition:opacity .45s;opacity:0;pointer-events:none}
  #__card.on{opacity:1}
  #__card b{font-size:46px;letter-spacing:-.5px}#__card span{font-size:22px;opacity:.85;max-width:70%}
  #__cur{position:fixed;left:0;top:0;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;
    background:rgba(255,0,83,.35);border:2px solid #ff0053;z-index:2147483647;pointer-events:none;
    transition:transform .12s, background .12s}
  #__cur.down{transform:scale(.7);background:rgba(255,0,83,.7)}
  .toast{top:22px!important;bottom:auto!important}`;
  const mount = () => {
    const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    for (const id of ['__card', '__cap', '__cur']) { const d = document.createElement('div'); d.id = id; document.body.appendChild(d); }
    const cur = document.getElementById('__cur');
    const pos = JSON.parse(sessionStorage.getItem('__cur') || '[720,405]');
    cur.style.left = pos[0] + 'px'; cur.style.top = pos[1] + 'px';
    document.addEventListener('mousemove', (e) => { cur.style.left = e.clientX + 'px'; cur.style.top = e.clientY + 'px';
      sessionStorage.setItem('__cur', JSON.stringify([e.clientX, e.clientY])); }, true);
    document.addEventListener('mousedown', () => cur.classList.add('down'), true);
    document.addEventListener('mouseup', () => cur.classList.remove('down'), true);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
  window.__say = (t) => { const c = document.getElementById('__cap'); if (c) c.textContent = t || ''; };
  window.__card = (t, s) => { const c = document.getElementById('__card'); if (!c) return;
    c.innerHTML = t ? `<b>${t}</b><span>${s || ''}</span>` : c.innerHTML; c.classList.toggle('on', !!t); };
})();
"""


def sh(*cmd: str) -> str:
    return subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8").stdout


def reset_db() -> None:
    print("resetting demo data…")
    sh("docker", "compose", "exec", "-T", "backend", "python", "-m", "app.seed", "--reset")


def answer_key(attempt_id: int) -> list[dict]:
    q = ("select json_agg(json_build_object('qtype', qtype, 'correct', correct, 'n', json_array_length(options),"
         f" 'b', irt_b) order by position) from test_items where attempt_id = {int(attempt_id)}")
    out = sh("docker", "compose", "exec", "-T", "db", "psql", "-U", "fsp", "-d", "fsp_talent", "-tAc", q)
    return json.loads(out)


class Demo:
    def __init__(self, page: Page, pace: float):
        self.pg = page
        self.pace = pace

    # -- timing and overlay
    def wait(self, sec: float) -> None:
        self.pg.wait_for_timeout(int(sec * 1000 * self.pace))

    def say(self, text: str, sec: float = 0) -> None:
        self.pg.evaluate("t => window.__say(t)", text)
        if sec:
            self.wait(sec)

    def card(self, title: str, sub: str = "", sec: float = 3.2) -> None:
        self.say("")
        self.pg.evaluate("([t, s]) => window.__card(t, s)", [title, sub])
        self.wait(sec)
        self.pg.evaluate("() => window.__card('')")
        self.wait(0.5)

    # -- input that looks like a person using the app
    def point(self, loc: Locator) -> tuple[float, float]:
        loc.scroll_into_view_if_needed()
        box = loc.bounding_box()
        assert box, f"not visible: {loc}"
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        self.pg.mouse.move(x, y, steps=16)
        return x, y

    def click(self, loc: Locator, after: float = 0.6) -> None:
        loc = loc.first
        loc.wait_for(state="visible")
        self.point(loc)
        self.wait(0.25)
        loc.click()
        self.wait(after)

    def type(self, loc: Locator, text: str, delay: int = 28) -> None:
        self.click(loc, after=0.1)
        loc.first.press_sequentially(text, delay=delay)
        self.wait(0.2)

    def show(self, loc: Locator, sec: float = 0) -> None:
        """Smoothly scroll an element to the middle of the screen."""
        loc.first.wait_for(state="visible")
        loc.first.evaluate("e => e.scrollIntoView({behavior: 'smooth', block: 'center'})")
        self.wait(0.9 + sec)

    def top(self) -> None:
        self.pg.evaluate("() => window.scrollTo({top: 0, behavior: 'smooth'})")
        self.wait(0.7)

    def btn(self, name: str, exact: bool = False) -> Locator:
        return self.pg.get_by_role("button", name=name, exact=exact)

    def nav(self, label: str) -> None:
        self.click(self.pg.locator("aside a.nav-link").filter(has_text=label), after=1.2)

    # -- session
    def login(self, email: str) -> None:
        if "/login" not in self.pg.url:  # signing out lands on the login page, the start on the landing
            self.click(self.pg.get_by_role("link", name="Войти"), after=0.5)
        self.type(self.pg.locator("#email"), email)
        self.type(self.pg.locator("#pwd"), PASSWORD, delay=18)
        self.click(self.btn("Войти", exact=True), after=1.5)

    def logout(self) -> None:
        self.click(self.btn("Выйти"), after=1.0)


def make_resume_pdf(browser, folder: Path) -> Path:
    path = folder / "Олимпиев_Олег_резюме.pdf"
    ctx = browser.new_context()
    p = ctx.new_page()
    p.set_content(RESUME_HTML)
    p.pdf(path=str(path), format="A4")
    ctx.close()
    return path


def candidate_part(d: Demo, resume: Path) -> None:
    pg = d.pg
    d.card("1 · Кандидат", "Регистрация, профиль, опрос и тест на грейд")
    d.say("Регистрация кандидата. E-mail совпадает с записью участника в реестре ФСП")
    d.click(pg.get_by_role("link", name="Я ищу работу"), after=0.8)
    d.type(pg.locator("#fn"), CANDIDATE["first"])
    d.type(pg.locator("#ln"), CANDIDATE["last"])
    d.type(pg.locator("#em"), CANDIDATE["email"])
    d.type(pg.locator("#pw"), PASSWORD, delay=18)
    d.say("Согласие на обработку персональных данных (152-ФЗ). Публикация профиля — отдельным согласием")
    d.click(pg.locator("label.check input[type=checkbox]"), after=1.2)
    d.click(d.btn("Зарегистрироваться"), after=1.2)

    d.say("Подтверждение e-mail. В демо-режиме код виден на экране и в Mailpit", 1.5)
    d.click(d.btn("Подставить"), after=0.6)
    d.click(d.btn("Подтвердить"), after=2.0)

    d.say("Достижения ФСП подтянулись автоматически по подтверждённому e-mail", 3.0)
    d.nav("Достижения ФСП")
    d.say("Реестр ФСП подключён через порт с адаптерами: мок-реестр сейчас, реальный API — без изменения логики", 3.2)
    d.say("Сила сигнала: уровень соревнования × место × давность × роль. Нет истории — нейтральная база, без штрафа", 3.6)

    d.nav("Профиль и резюме")
    d.say("Профиль можно заполнить из PDF-резюме: разбираем контакты, стек, грейд, опыт и ожидания", 1.5)
    pg.locator("input[type=file]").set_input_files(str(resume))
    pg.get_by_text("Найдено в «").wait_for()
    d.show(pg.get_by_text("Найдено в «"), 2.5)
    d.click(d.btn("Применить", exact=True), after=1.0)
    d.show(pg.get_by_role("heading", name="Навыки и стек"), 2.0)
    d.say("Резюме дополняет профиль, но категорию работодатель видит только по результату теста", 1.0)
    d.top()
    d.click(d.btn("Сохранить"), after=1.5)

    d.nav("Тестирование")
    d.say("Опрос: отрасль, специализация и предполагаемый грейд — гипотеза, которую проверяет тест", 3.0)
    d.show(pg.get_by_role("heading", name="Как устроен тест"))
    d.say("Вариант индивидуальный, но план един для всех: одинаковые квоты компетенций и профиль сложности", 3.6)
    card = pg.locator(".card.flat").filter(has_text="Middle")
    d.show(card)
    d.click(card.get_by_role("button", name="Начать тест"), after=0.5)
    pg.wait_for_url("**/candidate/testing/*")
    attempt_id = int(pg.url.rstrip("/").split("/")[-1])
    pg.locator(".option, #num").first.wait_for()
    key = answer_key(attempt_id)
    wrong = set(sorted(range(len(key)), key=lambda i: key[i]["b"])[-6:])  # six hardest items: a typical Middle

    notes = {
        0: "20 заданий из калиброванного банка (252 задания + 25 параметрических семейств). Ответы сохраняются сразу",
        1: "Часть заданий параметрическая: числа генерируются для каждого кандидата — выученные ответы не помогают",
        2: "Контроль показов: задания, которые часто выдавались, реже попадают в новые варианты",
        3: "Таймер — на сервере; можно возвращаться к любому вопросу",
    }
    for i, item in enumerate(key):
        d.say(notes.get(i, f"Вопрос {i + 1} из {len(key)}"))
        if item["qtype"] == "numeric":
            value = float(item["correct"][0]) + (7 if i in wrong else 0)
            text = str(int(value)) if value == int(value) else str(value)
            d.type(pg.locator("#num"), text, delay=40)
            pg.locator("#num").press("Tab")
        else:
            opts = pg.locator(".option")
            assert opts.count() == item["n"], f"item {i}: {opts.count()} options on screen, {item['n']} in DB"
            picks = [x for x in range(item["n"]) if x not in item["correct"]][:1] if i in wrong else item["correct"]
            for x in picks:
                d.click(opts.nth(x), after=0.15)
        d.wait(2.6 if i in notes else 0.35)
        if i < len(key) - 1:
            d.click(d.btn("Далее"), after=0.25)
    d.say("Все ответы даны — завершаем тест")
    d.click(d.btn("Завершить тест"), after=0.6)
    d.click(d.btn("Завершить и узнать результат"), after=0.5)
    pg.wait_for_url("**/candidate/results/*")
    pg.locator(".ring").first.wait_for()
    pg.get_by_text("Категория подтверждена").wait_for(timeout=5000)  # the captions below assume a pass
    d.wait(1.0)
    d.say("Оценка по IRT (3PL, EAP) учитывает сложность именно этих заданий — баллы разных вариантов сопоставимы", 4.0)
    d.say("Шкала 0–100, пороги 25 / 50 / 75 — Junior / Middle / Senior. Присвоена категория «Backend · Middle»", 3.6)
    d.show(pg.get_by_role("heading", name="Компетенции"))
    d.say("Результат по компетенциям подтверждает навыки профиля — это учитывается в подборе", 3.4)
    d.say("Не прошёл — тест на грейд ниже доступен сразу. Повтор — через 30 дней, смена грейда — раз в 90 дней", 3.6)

    d.nav("Настройки")
    d.say("Профиль попадает в поиск только после отдельного согласия на публикацию", 1.2)
    sw = pg.locator("label").filter(has_text="Публикация профиля для работодателей").locator(".switch")
    d.show(sw)
    d.click(sw, after=1.6)
    d.nav("Обзор")
    d.say("Кабинет кандидата: категория, шкальный балл и путь к приглашениям", 3.2)
    d.say("")
    d.logout()


def employer_part(d: Demo) -> None:
    pg = d.pg
    d.card("2 · Работодатель", "Потребность → объяснимая подборка → приглашение с зарплатой")
    d.say("Работодатель «Технологии Будущего» входит в кабинет")
    d.login("hr@demo.ru")
    d.say("Инициатива у работодателя: он описывает потребность, а не ждёт откликов", 2.4)
    d.click(pg.get_by_role("link", name="Новая потребность"), after=1.0)
    d.say("Потребность можно описать своими словами")
    d.type(pg.locator("textarea").first, NEED_TEXT, delay=12)
    d.click(d.btn("Разобрать описание"), after=1.2)
    d.say("Разбор текста: специализация, грейд, обязательный и желательный стек, вилка, формат, опыт", 3.4)
    d.show(pg.get_by_text("Обязательный стек (must-have)"), 1.0)
    d.say("«Желательно Redis» распознано как nice-to-have; вилка обязательна — без неё подборку не сохранить", 3.0)
    title = pg.locator("#requirementform-f1")
    d.show(title)
    title.fill("")
    d.type(title, "Python-разработчик, платёжный шлюз")
    d.show(pg.get_by_role("heading", name="Стратегия ранжирования"))
    d.say("Стратегия ранжирования задаёт веса факторов; по умолчанию — «Сбалансированный» профиль", 3.0)
    d.top()
    d.click(d.btn("Получить подборку"), after=0.5)
    pg.locator(".cand").first.wait_for()
    d.wait(1.0)
    d.say("Рекомендованные категории и подборка, ранжированная по проценту совпадения", 3.2)
    first = pg.locator(".cand").first
    d.show(first)
    d.say("Каждый процент объяснён: причины ✓/✗, совпадение стека и вклад 9 факторов", 3.6)
    d.say("Навык засчитывается с учётом доказательности: подтверждён ли он тестом. Близкие навыки — частично", 3.6)
    weights = pg.get_by_role("heading", name="Как считается совпадение")
    d.show(weights)
    d.say("Нет данных по фактору — вес перераспределяется. Нет истории ФСП — нейтральная база", 3.4)

    d.say("Сравнение двух кандидатов: почему A выше B")
    cards = pg.locator(".cand")
    for i in (0, 1):
        d.show(cards.nth(i))
        d.click(cards.nth(i).locator('button[title="Сравнить"]'), after=0.4)
    d.click(d.btn("Почему A выше B?"), after=1.2)
    d.say("Разница по каждому фактору — работодателю понятно, что решило порядок", 4.2)
    pg.keyboard.press("Escape")
    d.wait(0.6)

    ours = pg.locator(".cand").filter(has_text=f"{CANDIDATE['first']} {CANDIDATE['last'][0]}.")
    d.show(ours)
    rank = ours.locator(".rank").inner_text().lstrip("#")
    d.say(f"Новый кандидат — {CANDIDATE['first']} {CANDIDATE['last'][0]}. — уже в подборке, на {rank}-м месте", 3.0)
    d.click(ours.get_by_role("link", name="Профиль и объяснение"), after=1.4)
    d.say("Профиль и объяснение совпадения. Контакты скрыты до согласия кандидата", 3.0)
    d.show(pg.get_by_text("Контакты", exact=True), 2.2)
    d.show(pg.locator(".table").first)
    d.say("Разложение балла: оценка, вес и вклад каждого фактора — сумма вкладов равна итогу", 3.6)
    d.top()
    d.click(d.btn("Пригласить"), after=1.0)
    d.say("Приглашение без зарплатной вилки отправить нельзя — кандидат видит условия до ответа", 3.4)
    d.click(d.btn("Отправить приглашение"), after=1.6)
    d.say("")
    d.logout()


def accept_part(d: Demo) -> None:
    pg = d.pg
    d.card("3 · Ответ кандидата", "Зарплата видна до общения, контакты — только с согласия")
    d.login(CANDIDATE["email"])
    d.nav("Приглашения")
    d.click(pg.locator("button.card.hover").first, after=1.4)
    d.say("Компания, предложение и зарплатная вилка — до начала общения", 3.0)
    d.show(pg.get_by_text("Почему выбрали вас"))
    d.say("Кандидат видит, почему выбрали именно его", 3.0)
    d.click(d.btn("Принять"), after=0.8)
    d.click(d.btn("Подтвердить"), after=1.6)
    d.say("Приглашение принято — работодателю открываются контакты", 2.4)
    d.say("")
    d.logout()

    d.login("hr@demo.ru")
    d.nav("Приглашения")
    d.say("У работодателя: приглашение принято")
    d.click(pg.locator("table a").filter(has_text=CANDIDATE["first"]), after=1.4)
    d.show(pg.get_by_text("Кандидат принял ваше приглашение"))
    d.say("ФИО, e-mail, телефон и Telegram открыты; каждое раскрытие контактов записывается в журнал", 3.8)
    d.say("")
    d.logout()


def application_part(d: Demo) -> None:
    pg = d.pg
    d.card("4 · Классический сценарий", "Отклик кандидата на опубликованную вакансию")
    d.login(CANDIDATE["email"])
    d.nav("Вакансии и отклики")
    d.say("Публичные вакансии с процентом совпадения для кандидата", 2.6)
    job = pg.locator(".cand").filter(has_text="Python Backend Developer").filter(has=d.btn("Откликнуться"))
    d.show(job)
    d.click(job.get_by_role("button", name="Откликнуться"), after=1.0)
    d.say("Откликаясь, кандидат сам открывает контакты этому работодателю")
    d.type(pg.locator("#jobs-f1"), "Здравствуйте! Интересны высоконагруженные API — готов обсудить детали.", delay=14)
    d.wait(1.2)
    d.click(d.btn("Отправить отклик"), after=1.6)
    d.say("")
    d.logout()

    d.login("hr@demo.ru")
    d.nav("Отклики на вакансии")
    d.say("Работодатель видит отклик с контактами и процентом совпадения", 3.6)
    d.say("")
    d.logout()


def language_part(d: Demo) -> None:
    pg = d.pg
    d.card("5 · Два языка", "Интерфейс, объяснения подбора и тест — на русском и английском")
    d.login("hr@demo.ru")
    d.nav("Потребности и подборки")
    d.click(pg.get_by_text("Python-разработчик, платёжный шлюз"), after=1.5)
    d.say("Переключатель RU / EN есть на любом экране; выбор сохраняется в учётной записи", 2.6)
    d.click(d.btn("English"), after=2.0)
    d.show(pg.locator(".cand").first)
    d.say("Та же подборка на английском: причины, факторы и вилка формируются на языке читателя", 4.0)
    d.say("")
    d.click(d.btn("Русский"), after=1.5)
    d.logout()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(ROOT / "presentation" / "FSP_Talent_demo"))
    ap.add_argument("--pace", type=float, default=1.0, help="multiply all pauses (e.g. 0.5 for a dry run)")
    ap.add_argument("--keep-data", action="store_true", help="do not reset the demo data after recording")
    args = ap.parse_args()

    reset_db()
    tmp = Path(tempfile.mkdtemp(prefix="fsp_demo_"))
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")
            resume = make_resume_pdf(browser, tmp)
            ctx = browser.new_context(viewport={"width": W, "height": H}, locale="ru-RU",
                                      record_video_dir=str(tmp), record_video_size={"width": W, "height": H})
            ctx.add_init_script(OVERLAY_JS)
            ctx.set_default_timeout(20_000)
            page = ctx.new_page()
            d = Demo(page, args.pace)
            started = time.time()
            try:
                page.goto(BASE + "/")
                page.locator("h1").first.wait_for()
                d.card("FSP Talent", "Обратный подбор ИТ-специалистов с верифицированным профилем · демонстрация MVP", 4.0)
                d.say("Работодатель сам находит кандидата по подтверждённым навыкам и приглашает с зарплатой", 4.0)
                candidate_part(d, resume)
                employer_part(d)
                accept_part(d)
                application_part(d)
                language_part(d)
                d.card("FSP Talent", "docker compose up --build → http://localhost:8080 · документация: docs/", 4.5)
            except Exception:
                page.screenshot(path=str(ROOT / "presentation" / "record_demo_error.png"))
                raise
            finally:
                video = page.video.path()
                ctx.close()
                browser.close()
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        webm = out.with_suffix(".webm")
        shutil.move(video, webm)
        print(f"recorded {time.time() - started:.0f} s -> {webm}")
        try:
            import imageio_ffmpeg

            mp4 = out.with_suffix(".mp4")
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", "0.6", "-i", str(webm),
                            "-vf", "scale=1920:1080:flags=lanczos", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)], check=True)
            print("mp4 ->", mp4)
        except ImportError:
            print("imageio-ffmpeg is not installed: only .webm was written", file=sys.stderr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if not args.keep_data:
            reset_db()


if __name__ == "__main__":
    main()
