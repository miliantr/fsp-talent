"""Deterministic synthetic personas: candidates, companies, needs and FSP registry records.

All people and companies are fictional.
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

MALE = [("Алексей", "Смирнов"), ("Дмитрий", "Кузнецов"), ("Иван", "Попов"), ("Максим", "Васильев"),
        ("Артём", "Петров"), ("Никита", "Соколов"), ("Егор", "Михайлов"), ("Кирилл", "Новиков"),
        ("Михаил", "Фёдоров"), ("Андрей", "Морозов"), ("Илья", "Волков"), ("Сергей", "Алексеев"),
        ("Павел", "Лебедев"), ("Роман", "Семёнов"), ("Тимур", "Егоров"), ("Глеб", "Павлов"),
        ("Владимир", "Козлов"), ("Денис", "Степанов"), ("Арсений", "Николаев"), ("Матвей", "Орлов"),
        ("Константин", "Андреев"), ("Ярослав", "Макаров"), ("Фёдор", "Никитин"), ("Георгий", "Захаров"),
        ("Олег", "Зайцев"), ("Руслан", "Соловьёв"), ("Даниил", "Борисов")]
FEMALE = [("Анна", "Яковлева"), ("Мария", "Григорьева"), ("Екатерина", "Романова"), ("Дарья", "Воробьёва"),
          ("Полина", "Сергеева"), ("Алина", "Кузьмина"), ("Виктория", "Фролова"), ("Софья", "Александрова"),
          ("Ксения", "Дмитриева"), ("Елизавета", "Королёва"), ("Ольга", "Гусева"), ("Юлия", "Киселёва"),
          ("Татьяна", "Ильина"), ("Валерия", "Максимова"), ("Ирина", "Полякова"), ("Наталья", "Сорокина"),
          ("Вера", "Виноградова"), ("Алиса", "Ковалёва"), ("Диана", "Белова"), ("Евгения", "Медведева"),
          ("Марина", "Антонова")]
CITIES = ["Москва", "Санкт-Петербург", "Казань", "Новосибирск", "Екатеринбург", "Нижний Новгород",
          "Иннополис", "Томск", "Самара", "Краснодар"]
REGIONS = {"Москва": "г. Москва", "Санкт-Петербург": "г. Санкт-Петербург", "Казань": "Республика Татарстан",
           "Новосибирск": "Новосибирская область", "Екатеринбург": "Свердловская область",
           "Нижний Новгород": "Нижегородская область", "Иннополис": "Республика Татарстан",
           "Томск": "Томская область", "Самара": "Самарская область", "Краснодар": "Краснодарский край"}

STACKS = {
    "backend": [
        ["python", "fastapi", "postgresql", "docker", "redis"],
        ["python", "django", "postgresql", "celery", "redis"],
        ["go", "postgresql", "kafka", "docker", "grpc"],
        ["java", "spring", "postgresql", "kafka", "docker"],
        ["python", "flask", "mysql", "rabbitmq", "docker"],
        ["nodejs", "nestjs", "typescript", "mongodb", "docker"],
        ["kotlin", "spring", "postgresql", "kafka"],
        ["python", "fastapi", "sqlalchemy", "postgresql", "kafka", "kubernetes"],
    ],
    "frontend": [
        ["javascript", "typescript", "react", "redux", "css", "html"],
        ["typescript", "react", "nextjs", "tailwind", "jest"],
        ["javascript", "vue", "css", "html", "webpack"],
        ["typescript", "angular", "css", "html"],
        ["typescript", "react", "mobx", "css", "vite", "playwright"],
    ],
    "data_ml": [
        ["python", "pandas", "numpy", "sklearn", "sql", "statistics"],
        ["python", "pytorch", "nlp", "llm", "mlflow"],
        ["python", "catboost", "pandas", "sql", "airflow"],
        ["python", "pytorch", "cv", "numpy", "docker"],
        ["python", "spark", "airflow", "sql", "clickhouse"],
        ["python", "tensorflow", "pandas", "sklearn"],
    ],
    "devops": [
        ["linux", "docker", "kubernetes", "gitlab_ci", "terraform", "prometheus"],
        ["linux", "bash", "ansible", "docker", "nginx", "grafana"],
        ["kubernetes", "helm", "terraform", "aws", "prometheus", "grafana"],
        ["docker", "github_actions", "yandex_cloud", "terraform", "elk"],
        ["linux", "kubernetes", "security", "gitlab_ci", "python"],
    ],
}
EXTRAS = {
    "backend": ["git", "rest", "linux", "sql", "microservices", "clickhouse", "algorithms", "cicd", "nginx"],
    "frontend": ["git", "a11y", "graphql", "vite", "webpack", "jest", "playwright", "nodejs"],
    "data_ml": ["git", "docker", "statistics", "sql", "postgresql", "kafka", "llm"],
    "devops": ["git", "bash", "python", "nginx", "cicd", "grafana", "elk", "openshift"],
}
HEADLINES = {
    "backend": ["Python-разработчик", "Backend-разработчик", "Go-разработчик", "Java-разработчик",
                "Разработчик серверной части"],
    "frontend": ["Frontend-разработчик", "React-разработчик", "Frontend-инженер"],
    "data_ml": ["Data Scientist", "ML-инженер", "Аналитик данных", "NLP-инженер"],
    "devops": ["DevOps-инженер", "SRE-инженер", "Платформенный инженер"],
}
ROLE_FOR_SPEC = {"backend": "backend", "frontend": "frontend", "data_ml": "ml", "devops": "devops"}
SALARY = {"junior": (70_000, 130_000), "middle": (150_000, 270_000), "senior": (280_000, 460_000)}
EXPERIENCE = {"junior": (0.5, 2.0), "middle": (2.0, 5.0), "senior": (5.0, 11.0)}
THETA = {"junior": -0.45, "middle": 0.55, "senior": 1.65}
NEXT = {"junior": "middle", "middle": "senior", "senior": "senior"}

EVENTS = [
    ("Всероссийские соревнования по продуктовому программированию", "Продуктовое программирование",
     "all_russian"),
    ("Кубок ФСП по продуктовому программированию", "Продуктовое программирование", "all_russian"),
    ("Межрегиональный хакатон «Код города»", "Продуктовое программирование", "interregional"),
    ("Региональные соревнования по продуктовому программированию", "Продуктовое программирование", "regional"),
    ("Чемпионат по алгоритмическому программированию", "Алгоритмическое программирование", "all_russian"),
    ("Региональный этап по алгоритмическому программированию", "Алгоритмическое программирование", "regional"),
    ("Международный турнир по информационной безопасности (CTF)",
     "Программирование систем информационной безопасности", "international"),
    ("Всероссийские соревнования по кибербезопасности", "Программирование систем информационной безопасности",
     "all_russian"),
    ("Всероссийские соревнования по программированию БАС", "Программирование беспилотных авиационных систем",
     "all_russian"),
    ("Межрегиональные соревнования по программированию робототехники", "Программирование робототехники",
     "interregional"),
]
TEAMS = ["Byte Busters", "NullPointer", "Сибирский код", "Kernel Panic", "404 Team", "Мыслящие машины",
         "Квантовый скачок", "Stack Overflowers", "Green Threads", "Бит и Байт", "Ctrl+Alt+Win", "Дедлайн"]
RANKS = [None, None, None, None, "III разряд", "II разряд", "I разряд", "КМС"]


@dataclass
class Achievement:
    id: str
    event_name: str
    discipline: str
    level: str
    date: date
    place: int | None
    participants_total: int
    team_name: str | None
    role: str | None
    score: float | None
    specialization_hint: str | None

    def to_registry(self) -> dict:
        return {
            "id": self.id, "event_name": self.event_name, "discipline": self.discipline, "level": self.level,
            "date": self.date.isoformat(), "place": self.place, "participants_total": self.participants_total,
            "team_name": self.team_name, "role": self.role, "score": self.score,
            "specialization_hint": self.specialization_hint,
            "certificate_url": f"https://registry.fsp.example/certificates/{self.id}",
        }


@dataclass
class Persona:
    key: str
    email: str
    first_name: str
    last_name: str
    city: str
    specialization: str
    grade: str             # true level
    declared_grade: str    # what the person claims in the survey
    theta: float
    skills: dict[str, int]
    experience_years: float
    expected_salary: int
    work_format: str
    headline: str
    about: str
    phone: str
    telegram: str
    days_ago: int          # when the test was taken
    fsp_id: str | None = None
    sport_rank: str | None = None
    achievements: list[Achievement] = field(default_factory=list)
    take_test: bool = True
    open_to_offers: bool = True
    # additional categories: (specialization, grade, ability θ in that specialization)
    extra_categories: list[tuple[str, str, float]] = field(default_factory=list)
    experience: list[dict] = field(default_factory=list)  # places of work, the most recent first


_TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
               ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s",
                "t", "u", "f", "kh", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"], strict=True))


def translit(s: str) -> str:
    return "".join(_TR.get(c, c) for c in s.lower())


LEAD_SKILL_TITLE = {
    "python": "Python-разработчик", "go": "Go-разработчик", "java": "Java-разработчик",
    "kotlin": "Kotlin-разработчик", "nodejs": "Node.js-разработчик", "react": "React-разработчик",
    "vue": "Vue-разработчик", "angular": "Angular-разработчик", "typescript": "Frontend-разработчик (TypeScript)",
    "javascript": "Frontend-разработчик",
}


def headline_for(spec: str, stack: list[str], rng: random.Random) -> str:
    if spec in ("backend", "frontend"):
        for s in stack:
            if s in LEAD_SKILL_TITLE:
                return LEAD_SKILL_TITLE[s]
    return rng.choice(HEADLINES[spec])


def _achievements(rng: random.Random, spec: str, strength: float, n: int, today: date) -> list[Achievement]:
    out = []
    for _ in range(n):
        name, disc, level = rng.choice(EVENTS)
        if spec == "devops" and rng.random() < 0.5:
            name, disc, level = EVENTS[rng.choice([6, 7])]
        total = rng.choice([40, 60, 80, 120, 200, 350])
        if rng.random() < strength:
            place = rng.choice([1, 2, 3, 3, 4, 5, 6])
        elif rng.random() < 0.6:
            place = rng.randint(7, total // 3)
        else:
            place = None
        d = today - timedelta(days=rng.randint(60, 1400))
        out.append(Achievement(
            id=f"ACH-{d.year}-{rng.randint(10000, 99999)}", event_name=name, discipline=disc, level=level,
            date=d, place=place, participants_total=total,
            team_name=rng.choice(TEAMS) if disc == "Продуктовое программирование" or rng.random() < 0.4 else None,
            role=ROLE_FOR_SPEC[spec] if disc == "Продуктовое программирование" and rng.random() < 0.8
            else (rng.choice(["captain", None]) if rng.random() < 0.3 else None),
            score=round(rng.uniform(40, 100), 1),
            specialization_hint=spec if rng.random() < 0.5 else None,
        ))
    out.sort(key=lambda a: a.date, reverse=True)
    return out


def _about(spec: str, grade: str, skills: list[str], years: float) -> str:
    from app.domain.catalog import SKILLS

    names = {s[0]: s[1] for s in SKILLS}
    stack = ", ".join(names[s] for s in skills[:4])
    lead = {"junior": "Начинающий специалист", "middle": "Разработчик", "senior": "Опытный инженер"}[grade]
    if spec == "data_ml":
        lead = {"junior": "Начинающий аналитик", "middle": "Data Scientist", "senior": "Ведущий ML-инженер"}[grade]
    if spec == "devops":
        lead = {"junior": "Начинающий DevOps-инженер", "middle": "DevOps-инженер", "senior": "SRE / платформенный инженер"}[grade]
    return (f"{lead} с опытом {years:g} {'года' if 1 < years < 5 else 'лет'}. Основной стек: {stack}. "
            f"Интересны продуктовые задачи, работа в сильной команде и измеримый результат.")


# fictional companies for synthetic work histories
WORKPLACES = ["ИнфоЛайн", "Цифровой ритейл", "ГородСофт", "Логистик Тех", "ФинПоток", "Медиасеть",
              "Облачные системы", "ДатаПром", "Умный транспорт", "Студия «Пиксель»", "ТелекомСервис", "АгроДата"]
POSITIONS = {
    "backend": ("Backend-разработчик", "Младший backend-разработчик", "Ведущий backend-разработчик"),
    "frontend": ("Frontend-разработчик", "Младший frontend-разработчик", "Ведущий frontend-разработчик"),
    "data_ml": ("Data Scientist", "Junior Data Scientist", "Ведущий ML-инженер"),
    "devops": ("DevOps-инженер", "Младший DevOps-инженер", "Ведущий SRE-инженер"),
}


def work_history(key: str, spec: str, grade: str, years: float, today: date) -> list[dict]:
    """1–3 places of work covering the years of experience; the last one is current. Own RNG per
    persona, so the main persona stream does not change."""
    rng = random.Random(f"{key}:jobs")
    n = {"junior": 1, "middle": rng.randint(1, 2), "senior": rng.randint(2, 3)}[grade]
    months = max(6, round(years * 12))
    if months < 12 * n:
        n = 1
    weights = [rng.uniform(0.7, 1.3) for _ in range(n)]
    spans = [round(months * w / sum(weights)) for w in weights]
    bounds = [0]  # months ago, from now backwards
    for span in spans:
        bounds.append(bounds[-1] + span)
    bounds[-1] = months
    middle, junior, senior = POSITIONS[spec]
    title = {"junior": junior, "middle": middle, "senior": senior}
    companies = rng.sample(WORKPLACES, n)
    out = []
    for k in range(n):
        end_ago, start_ago = bounds[k], bounds[k + 1]
        level = grade if k == 0 else ("junior" if k == n - 1 and n > 1 else "middle")

        def ym(ago: int) -> str:
            m = today.year * 12 + today.month - 1 - ago
            return f"{m // 12}-{m % 12 + 1:02d}"

        out.append({"company": companies[k], "position": title[level], "period_from": ym(start_ago),
                    "period_to": None if k == 0 else ym(end_ago), "description": ""})
    return out


def build_personas(today: date, seed: int = 2026) -> list[Persona]:
    rng = random.Random(seed)
    plan = ([("backend", g) for g in ["junior"] * 4 + ["middle"] * 7 + ["senior"] * 5]
            + [("frontend", g) for g in ["junior"] * 4 + ["middle"] * 5 + ["senior"] * 3]
            + [("data_ml", g) for g in ["junior"] * 3 + ["middle"] * 4 + ["senior"] * 3]
            + [("devops", g) for g in ["junior"] * 3 + ["middle"] * 4 + ["senior"] * 3])
    names = MALE + FEMALE
    rng.shuffle(names)
    personas: list[Persona] = []
    fsp_counter = 104200
    for i, (spec, grade) in enumerate(plan):
        first, last = names[i % len(names)]
        stack = list(rng.choice(STACKS[spec]))
        extras = rng.sample(EXTRAS[spec], k=rng.randint(1, 3))
        lvl = {"junior": (2, 3), "middle": (3, 4), "senior": (4, 5)}[grade]
        skills = {s: rng.randint(*lvl) for s in dict.fromkeys(stack + extras)}
        exp = round(rng.uniform(*EXPERIENCE[grade]), 1)
        # ~15% overclaim their grade in the survey: they will fail and fall back to a lower test
        declared = NEXT[grade] if (grade != "senior" and rng.random() < 0.15) else grade
        theta = rng.gauss(THETA[grade], 0.3)
        has_fsp = rng.random() < 0.55
        city = rng.choice(CITIES)
        p = Persona(
            key=f"cand{i + 1:02d}", email=f"cand{i + 1:02d}@talent.demo", first_name=first, last_name=last,
            city=city, specialization=spec, grade=grade, declared_grade=declared, theta=theta, skills=skills,
            experience_years=exp, expected_salary=round(rng.randint(*SALARY[grade]), -4),
            work_format=rng.choice(["remote", "remote", "hybrid", "office", "any"]),
            headline=headline_for(spec, stack, rng), about=_about(spec, grade, stack, exp),
            phone=f"+7 9{rng.randint(10, 99)} {rng.randint(100, 999)}-{rng.randint(10, 99)}-{rng.randint(10, 99)}",
            telegram=f"@{translit(first)[:6]}_{translit(last)[:4]}{i + 1:02d}",
            days_ago=rng.choice([2, 5, 9, 14, 21, 35, 50, 80, 120, 200, 260]),
        )
        if has_fsp:
            fsp_counter += rng.randint(3, 40)
            p.fsp_id = f"FSP-{fsp_counter}"
            p.sport_rank = rng.choice(RANKS)
            strength = {"junior": 0.2, "middle": 0.35, "senior": 0.5}[grade]
            p.achievements = _achievements(rng, spec, strength, rng.randint(1, 4), today)
        p.experience = work_history(p.key, spec, grade, exp, today)
        personas.append(p)
    # a few people are verified in a second, adjacent specialization (own RNG: the main stream is unchanged)
    xr = random.Random(seed + 1)
    for p in personas:
        if p.grade == "junior":
            continue
        if p.specialization == "backend" and "docker" in p.skills and xr.random() < 0.45:
            p.extra_categories.append(("devops", "junior", round(p.theta - 0.9, 2)))
        elif p.specialization == "data_ml" and "python" in p.skills and xr.random() < 0.35:
            p.extra_categories.append(("backend", "junior", round(p.theta - 1.0, 2)))
        elif p.specialization == "devops" and p.grade == "senior" and xr.random() < 0.5:
            p.extra_categories.append(("backend", "junior", round(p.theta - 1.1, 2)))
    return personas


def demo_personas(today: date) -> list[Persona]:
    """Hand-crafted accounts used in the demo scenario (documented in README)."""
    rng = random.Random(7)
    star = Persona(
        key="demo_candidate", email="candidate@demo.ru", first_name="Алексей", last_name="Демидов",
        city="Москва", specialization="backend", grade="middle", declared_grade="middle", theta=1.05,
        skills={"python": 5, "fastapi": 4, "postgresql": 4, "docker": 4, "redis": 3, "sqlalchemy": 4,
                "kafka": 3, "git": 4, "algorithms": 4},
        experience_years=3.5, expected_salary=220_000, work_format="hybrid",
        headline="Python backend-разработчик",
        about="Backend-разработчик: 3,5 года на Python. Проектирую API на FastAPI, PostgreSQL, очереди на Kafka, "
              "покрываю код тестами и выкатываю через Docker и CI. Призёр соревнований ФСП по продуктовому "
              "программированию.",
        phone="+7 915 123-45-67", telegram="@alexey_demidov", days_ago=6,
        fsp_id="FSP-100777", sport_rank="I разряд", extra_categories=[("devops", "junior", 0.0)],
        experience=[
            {"company": "ФинПоток", "position": "Backend-разработчик", "period_from": "2024-02", "period_to": None,
             "description": "Платёжный API на FastAPI и PostgreSQL, очереди на Kafka, выкладка через Docker и CI."},
            {"company": "Студия «Пиксель»", "position": "Младший Python-разработчик", "period_from": "2022-06",
             "period_to": "2024-01", "description": "Интеграции с внешними API, Celery, покрытие тестами."},
        ],
        achievements=[
            Achievement("ACH-2025-31415", "Всероссийские соревнования по продуктовому программированию",
                        "Продуктовое программирование", "all_russian", today - timedelta(days=150), 2, 180,
                        "Byte Busters", "backend", 91.5, "backend"),
            Achievement("ACH-2024-27182", "Кубок ФСП по продуктовому программированию",
                        "Продуктовое программирование", "all_russian", today - timedelta(days=420), 5, 120,
                        "Byte Busters", "backend", 84.0, "backend"),
            Achievement("ACH-2024-16180", "Региональный этап по алгоритмическому программированию",
                        "Алгоритмическое программирование", "regional", today - timedelta(days=600), 3, 90,
                        None, None, 77.0, None),
        ],
    )
    fresh = Persona(
        key="demo_fresh", email="fresh@demo.ru", first_name="Мария", last_name="Тестова", city="Казань",
        specialization="backend", grade="middle", declared_grade="middle", theta=0.6,
        skills={"python": 4, "django": 4, "postgresql": 3, "docker": 3, "celery": 3},
        experience_years=2.5, expected_salary=190_000, work_format="remote",
        headline="Python / Django разработчик",
        about="Разрабатываю backend на Django и DRF 2,5 года. Хочу пройти тест и получить подтверждённую категорию.",
        phone="+7 917 555-12-34", telegram="@maria_test", days_ago=1, take_test=False,
        experience=[{"company": "ГородСофт", "position": "Python-разработчик (Django)", "period_from": "2024-03",
                     "period_to": None, "description": "Сервисы на Django и DRF для городских заявок."}],
    )
    _ = rng
    return [star, fresh]


# Participants in the mock registry who are NOT yet on the platform (for the live demo).
UNCLAIMED = [
    {"fsp_id": "FSP-200001", "full_name": "Олимпиев Олег", "email": "olymp@demo.ru", "region": "г. Москва",
     "sport_rank": "КМС", "spec": "backend"},
    {"fsp_id": "FSP-200002", "full_name": "Хакатонова Ева", "email": "hack@demo.ru",
     "region": "г. Санкт-Петербург", "sport_rank": None, "spec": "frontend"},
    {"fsp_id": "FSP-200003", "full_name": "Нейронов Лев", "email": "ml@demo.ru", "region": "Томская область",
     "sport_rank": "I разряд", "spec": "data_ml"},
]

COMPANIES = [
    {"key": "demo_employer", "email": "hr@demo.ru", "company_name": "Технологии Будущего",
     "industry": "FinTech", "city": "Москва", "size": "500–1000", "website": "https://future-tech.example",
     "description": "Платёжная платформа для малого бизнеса: высоконагруженные сервисы, данные в реальном времени.",
     "contact_name": "Ирина Кадрова", "contact_telegram": "@future_tech_hr", "contact_phone": "+7 495 000-11-22"},
    {"key": "emp2", "email": "jobs@severcode.demo", "company_name": "Северный Код", "industry": "E-commerce",
     "city": "Санкт-Петербург", "size": "200–500", "website": "https://severcode.example",
     "description": "Маркетплейс товаров для дома. Микросервисы на Go и Kotlin, React на фронтенде.",
     "contact_name": "Павел Наймов", "contact_telegram": "@severcode_hr", "contact_phone": "+7 812 000-22-33"},
    {"key": "emp3", "email": "team@datalab.demo", "company_name": "ДатаЛаб", "industry": "AI / ML",
     "city": "Москва", "size": "50–200", "website": "https://datalab.example",
     "description": "Разрабатываем NLP- и CV-решения для промышленности и ретейла.",
     "contact_name": "Анна Подборова", "contact_telegram": "@datalab_hr", "contact_phone": "+7 495 000-33-44"},
    {"key": "emp4", "email": "hr@oblakotech.demo", "company_name": "ОблакоТех", "industry": "Cloud / Infra",
     "city": "Новосибирск", "size": "200–500", "website": "https://oblakotech.example",
     "description": "Облачная платформа и managed Kubernetes для enterprise-клиентов.",
     "contact_name": "Сергей Облачный", "contact_telegram": "@oblakotech_hr", "contact_phone": "+7 383 000-44-55"},
    {"key": "emp5", "email": "people@mediaplatform.demo", "company_name": "Медиа Платформа",
     "industry": "Media / Streaming", "city": "Казань", "size": "100–200", "website": "https://mediaplatform.example",
     "description": "Стриминговый сервис: веб-плееры, рекомендательная система, CDN.",
     "contact_name": "Дарья Талантова", "contact_telegram": "@media_hr", "contact_phone": "+7 843 000-55-66"},
]

NEEDS = [
    {"company": "demo_employer", "title": "Python Backend Developer", "specialization_id": "backend",
     "grade_id": "middle", "must": ["python", "fastapi", "postgresql", "docker"], "nice": ["redis", "kafka"],
     "salary": (180_000, 250_000), "work_format": "hybrid", "city": "Москва", "exp": 2, "public": True,
     "description": "Развиваем платёжный шлюз: API для мерчантов, интеграции с банками, антифрод.",
     "team": "Команда из 6 backend-разработчиков, QA и продакт. Код-ревью, CI/CD, дежурства раз в квартал."},
    {"company": "demo_employer", "title": "Senior Data Scientist (антифрод)", "specialization_id": "data_ml",
     "grade_id": "senior", "must": ["python", "catboost", "sql", "statistics"], "nice": ["airflow", "spark"],
     "salary": (330_000, 450_000), "work_format": "remote", "city": None, "exp": 5, "public": True,
     "description": "Модели антифрода в реальном времени: признаки, обучение, мониторинг дрейфа.",
     "team": "ML-команда из 5 человек, свой feature store."},
    {"company": "demo_employer", "title": "Junior Python-разработчик", "specialization_id": "backend",
     "grade_id": "junior", "must": ["python", "sql"], "nice": ["django", "git"],
     "salary": (80_000, 120_000), "work_format": "office", "city": "Москва", "exp": 0, "public": True,
     "description": "Внутренние сервисы бэк-офиса, автоматизация отчётности.",
     "team": "Наставник, понятный план развития на 6 месяцев."},
    {"company": "emp2", "title": "Senior Go Developer", "specialization_id": "backend", "grade_id": "senior",
     "must": ["go", "postgresql", "kafka"], "nice": ["kubernetes", "grpc"], "salary": (350_000, 480_000),
     "work_format": "remote", "city": None, "exp": 5, "public": True,
     "description": "Сервис каталога и поиска: 30k RPS, шардирование, event-driven архитектура.",
     "team": "Платформенная команда каталога."},
    {"company": "emp2", "title": "Frontend Developer (React)", "specialization_id": "frontend",
     "grade_id": "middle", "must": ["react", "typescript"], "nice": ["redux", "nextjs", "jest"],
     "salary": (170_000, 240_000), "work_format": "remote", "city": None, "exp": 2, "public": True,
     "description": "Витрина маркетплейса: SSR, производительность, A/B-эксперименты.",
     "team": "Фронтенд-гильдия из 12 человек, дизайн-система."},
    {"company": "emp2", "title": "Java/Kotlin Backend Developer", "specialization_id": "backend",
     "grade_id": "middle", "must": ["java", "spring", "postgresql"], "nice": ["kotlin", "kafka"],
     "salary": (220_000, 300_000), "work_format": "hybrid", "city": "Санкт-Петербург", "exp": 3, "public": False,
     "description": "Сервисы заказов и логистики.", "team": "Команда заказов, 8 человек."},
    {"company": "emp3", "title": "NLP / LLM Engineer", "specialization_id": "data_ml", "grade_id": "senior",
     "must": ["python", "pytorch", "nlp"], "nice": ["llm", "mlflow"], "salary": (380_000, 500_000),
     "work_format": "remote", "city": None, "exp": 4, "public": True,
     "description": "RAG-системы и дообучение языковых моделей для промышленных заказчиков.",
     "team": "R&D-группа, публикации и open source."},
    {"company": "emp3", "title": "Data Scientist (Middle)", "specialization_id": "data_ml", "grade_id": "middle",
     "must": ["python", "pandas", "sklearn", "sql"], "nice": ["catboost", "airflow"],
     "salary": (200_000, 280_000), "work_format": "hybrid", "city": "Москва", "exp": 2, "public": True,
     "description": "Прогноз спроса и оптимизация запасов для ретейла.", "team": "Команда из 4 DS и 2 DE."},
    {"company": "emp4", "title": "DevOps Engineer", "specialization_id": "devops", "grade_id": "middle",
     "must": ["docker", "kubernetes", "gitlab_ci", "terraform"], "nice": ["prometheus", "grafana"],
     "salary": (220_000, 300_000), "work_format": "remote", "city": None, "exp": 2, "public": True,
     "description": "Managed Kubernetes: автоматизация, IaC, CI/CD для клиентов.", "team": "Платформенная команда."},
    {"company": "emp4", "title": "Senior SRE", "specialization_id": "devops", "grade_id": "senior",
     "must": ["kubernetes", "prometheus", "terraform", "linux"], "nice": ["helm", "security"],
     "salary": (350_000, 450_000), "work_format": "hybrid", "city": "Новосибирск", "exp": 5, "public": False,
     "description": "Надёжность облака: SLO, инциденты, capacity planning.", "team": "SRE-команда, on-call 1/6."},
    {"company": "emp5", "title": "Junior Frontend Developer", "specialization_id": "frontend", "grade_id": "junior",
     "must": ["javascript", "html", "css"], "nice": ["react", "git"], "salary": (70_000, 110_000),
     "work_format": "office", "city": "Казань", "exp": 0, "public": True,
     "description": "Промо-страницы и личный кабинет зрителя.", "team": "Наставник и ревью каждого PR."},
    {"company": "emp5", "title": "Senior Frontend Engineer (Player)", "specialization_id": "frontend",
     "grade_id": "senior", "must": ["typescript", "react", "nextjs"], "nice": ["playwright", "a11y"],
     "salary": (300_000, 400_000), "work_format": "remote", "city": None, "exp": 5, "public": False,
     "description": "Веб-плеер: адаптивный стриминг, производительность, доступность.",
     "team": "Команда плеера, 5 человек."},
]

# Regular tasks. «approach» answers come in three qualities (strong / partial / weak) so that the
# demo shows the automatic pre-score and the rubric review; «solve» tasks are checked automatically.
TASKS = [
    {"company": "demo_employer", "spec": "backend", "title": "Идемпотентность платежей", "mode": "approach",
     "audience": "targeted", "grade": "middle", "job": "Python Backend Developer", "competency": "be_api",
     "description": "Клиент повторяет POST /payments после таймаута. Предложите схему, исключающую двойное "
                    "списание: что храните, где, какие гарантии и как поведёт себя система при сбое БД?",
     "key_points": ["Клиент передаёт ключ идемпотентности в заголовке запроса",
                    "Ключ и результат операции хранятся в базе с уникальным индексом",
                    "Повторный запрос возвращает сохранённый ответ без нового списания",
                    "Списание и запись ключа выполняются в одной транзакции",
                    "Ключи хранятся ограниченное время (TTL)"],
     "answers": [
         "Клиент генерирует ключ идемпотентности и передаёт его в заголовке Idempotency-Key. Сервер хранит ключ и "
         "результат операции в базе с уникальным индексом по ключу. Списание и запись ключа выполняются в одной "
         "транзакции, поэтому при сбое базы не будет списания без ключа. Повторный запрос с тем же ключом "
         "возвращает сохранённый ответ без нового списания. Ключи храним ограниченное время — TTL 24 часа.",
         "Нужен ключ идемпотентности в заголовке запроса. Сохраняем его в таблице с уникальным индексом и при "
         "повторе возвращаем сохранённый ответ. Если база упала — клиент просто повторит запрос позже.",
         "Можно проверять, был ли уже такой платёж с той же суммой за последние минуты, и не списывать второй раз.",
     ]},
    {"company": "demo_employer", "spec": "backend", "title": "Пропускная способность пула воркеров", "mode": "solve",
     "audience": "targeted", "grade": None, "job": None, "competency": "be_arch",
     "description": "Обработка одного запроса занимает 40 мс, запросы не блокируют друг друга, в пуле 8 воркеров. "
                    "Какую максимальную пропускную способность (запросов в секунду) выдержит сервис? Ответ — число.",
     "answer_spec": {"kind": "number", "value": 200, "tolerance": 0},
     "answers": ["200", "200", "320"]},
    {"company": "emp2", "spec": "backend", "title": "Поиск в сбалансированном дереве", "mode": "solve",
     "audience": "category", "grade": None, "job": None, "competency": "be_algo",
     "description": "Какова асимптотическая сложность поиска элемента в сбалансированном бинарном дереве поиска "
                    "из n элементов? Ответ — в нотации «О большое».",
     "answer_spec": {"kind": "text", "accepted": ["O(log n)", "log n", "O(logn)", "логарифмическая"]},
     "answers": ["O(log n)", "O(log n)", "O(n)"]},
    {"company": "emp2", "spec": "frontend", "title": "Виртуализация длинного списка", "mode": "approach",
     "audience": "category", "grade": None, "job": None, "competency": "fe_browser",
     "description": "Каталог из 10 000 карточек тормозит при прокрутке. Опишите подход к оптимизации и как "
                    "проверите эффект метриками.",
     "key_points": ["Рендерить только видимые элементы списка (виртуализация, windowing)",
                    "Мемоизация карточек и стабильные ключи элементов",
                    "Измерить метрики FPS, INP и Long Tasks до и после изменений",
                    "Ленивая загрузка изображений карточек"],
     "answers": [
         "Рендерим только видимые элементы списка — виртуализация (windowing, react-window). Карточки оборачиваем "
         "в memo, ключи элементов стабильные. Изображения карточек — ленивая загрузка (loading=lazy). Эффект "
         "измеряем: FPS при прокрутке, INP и Long Tasks в Performance до и после изменений.",
         "Подключу react-window, чтобы рендерить только видимые элементы, и проверю в DevTools, что стало быстрее.",
         "Добавлю пагинацию по 50 карточек и кнопку «Показать ещё».",
     ]},
    {"company": "emp4", "spec": "devops", "title": "Zero-downtime деплой", "mode": "approach",
     "audience": "targeted", "grade": "middle", "job": "DevOps Engineer", "competency": "do_containers",
     "description": "Сервис с долгими WebSocket-соединениями нужно обновлять без разрывов. Предложите стратегию "
                    "выката в Kubernetes.",
     "key_points": ["RollingUpdate с maxUnavailable 0 и readiness probe",
                    "preStop hook и graceful shutdown, terminationGracePeriodSeconds больше времени слива",
                    "Клиенты переподключаются с экспоненциальным backoff",
                    "PodDisruptionBudget защищает от одновременного вывода подов"],
     "answers": [
         "Стратегия RollingUpdate с maxUnavailable 0, новые поды получают трафик только после readiness probe. "
         "В preStop hook сервис перестаёт принимать новые соединения и делает graceful shutdown, "
         "terminationGracePeriodSeconds больше времени слива соединений. Клиенты переподключаются с "
         "экспоненциальным backoff. PodDisruptionBudget защищает от одновременного вывода подов.",
         "RollingUpdate и readiness probe, а клиенты пусть переподключаются при разрыве.",
         "Обновлять ночью, когда пользователей меньше.",
     ]},
    {"company": "emp3", "spec": "data_ml", "title": "Метрика для редкого класса", "mode": "solve",
     "audience": "category", "grade": None, "job": None, "competency": "ml_classic",
     "description": "Модель антифрода: мошеннических операций 0,5%, пропустить мошенничество дороже, чем лишний раз "
                    "проверить операцию. Какую метрику классификатора нужно максимизировать в первую очередь? "
                    "Ответ — одно слово.",
     "answer_spec": {"kind": "text", "accepted": ["recall", "полнота", "TPR", "sensitivity", "чувствительность"]},
     "answers": ["Recall", "полнота", "accuracy"]},
]
