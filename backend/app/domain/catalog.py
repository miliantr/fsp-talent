"""Reference catalog: specializations, grades, competencies (test blueprint) and IT skills.

This is pure data shared by the seed, the services and the offline evaluation scripts.
"""

SPECIALIZATIONS = [
    {
        "id": "backend",
        "name": "Backend",
        "description": "Серверная разработка: API, базы данных, архитектура сервисов.",
    },
    {
        "id": "frontend",
        "name": "Frontend",
        "description": "Клиентская разработка: веб-интерфейсы, SPA, производительность в браузере.",
    },
    {
        "id": "data_ml",
        "name": "Data / ML",
        "description": "Анализ данных и машинное обучение: модели, метрики, MLOps.",
    },
    {
        "id": "devops",
        "name": "DevOps",
        "description": "Инфраструктура, CI/CD, контейнеры, наблюдаемость и надёжность.",
    },
]

# theta_cut — порог способности (шкала IRT), с которого грейд считается подтверждённым.
# Шкальный балл 0–100 = 50 + 25·θ, поэтому пороги читаются как 25 / 50 / 75 баллов.
GRADES = [
    {
        "id": "junior",
        "name": "Junior",
        "rank": 1,
        "theta_cut": -1.0,
        "description": "Опыт до 1–2 лет: решает типовые задачи под руководством.",
    },
    {
        "id": "middle",
        "name": "Middle",
        "rank": 2,
        "theta_cut": 0.0,
        "description": "Самостоятельно решает задачи, понимает компромиссы и инструменты.",
    },
    {
        "id": "senior",
        "name": "Senior",
        "rank": 3,
        "theta_cut": 1.0,
        "description": "Проектирует системы, отвечает за качество и развитие команды.",
    },
]
GRADE_RANK = {g["id"]: g["rank"] for g in GRADES}
GRADE_BY_RANK = {g["rank"]: g["id"] for g in GRADES}
GRADE_CUTS = {g["id"]: g["theta_cut"] for g in GRADES}
GRADE_NAMES = {g["id"]: g["name"] for g in GRADES}
SPEC_NAMES = {s["id"]: s["name"] for s in SPECIALIZATIONS}

# Test blueprint: competency shares within a specialization (sum = 1.0).
COMPETENCIES = [
    # backend
    ("be_lang", "backend", "Язык и рантайм (Python и др.)", 0.22),
    ("be_db", "backend", "Базы данных и SQL", 0.20),
    ("be_api", "backend", "API, HTTP и безопасность", 0.18),
    ("be_arch", "backend", "Архитектура и распределённые системы", 0.18),
    ("be_algo", "backend", "Алгоритмы и структуры данных", 0.12),
    ("be_ops", "backend", "Эксплуатация: Docker, CI, наблюдаемость", 0.10),
    # frontend
    ("fe_js", "frontend", "JavaScript и TypeScript", 0.26),
    ("fe_layout", "frontend", "HTML, CSS и доступность", 0.18),
    ("fe_framework", "frontend", "React и управление состоянием", 0.24),
    ("fe_browser", "frontend", "Браузер, сеть и производительность", 0.18),
    ("fe_quality", "frontend", "Тестирование и инструменты сборки", 0.14),
    # data / ml
    ("ml_math", "data_ml", "Статистика и математика", 0.20),
    ("ml_classic", "data_ml", "Классическое ML и метрики", 0.26),
    ("ml_dl", "data_ml", "Глубокое обучение", 0.18),
    ("ml_data", "data_ml", "Работа с данными: SQL, pandas", 0.20),
    ("ml_prod", "data_ml", "MLOps и вывод в продакшн", 0.16),
    # devops
    ("do_linux", "devops", "Linux и сети", 0.22),
    ("do_containers", "devops", "Контейнеры и оркестрация", 0.24),
    ("do_cicd", "devops", "CI/CD и инфраструктура как код", 0.20),
    ("do_observe", "devops", "Мониторинг и надёжность", 0.18),
    ("do_cloud", "devops", "Облака и безопасность", 0.16),
]

# Related specializations (for soft matching when an employer is open to adjacent profiles).
SPEC_SIMILARITY = {
    ("backend", "devops"): 0.35,
    ("backend", "data_ml"): 0.25,
    ("backend", "frontend"): 0.2,
    ("frontend", "devops"): 0.05,
    ("frontend", "data_ml"): 0.05,
    ("data_ml", "devops"): 0.15,
}


def spec_similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    return SPEC_SIMILARITY.get((a, b)) or SPEC_SIMILARITY.get((b, a)) or 0.0


# Skills: slug, name, kind, aliases, {specialization: competency confirming the skill}, related.
SKILLS = [
    # --- languages ---
    ("python", "Python", "language", ["питон", "python3"],
     {"backend": "be_lang", "data_ml": "ml_data", "devops": "do_cicd"}, {"go": 0.3, "java": 0.25}),
    ("go", "Go", "language", ["golang"], {"backend": "be_lang", "devops": "do_cicd"},
     {"python": 0.3, "java": 0.3}),
    ("java", "Java", "language", ["джава"], {"backend": "be_lang"}, {"kotlin": 0.7, "csharp": 0.5}),
    ("kotlin", "Kotlin", "language", ["котлин"], {"backend": "be_lang"}, {"java": 0.7}),
    ("csharp", "C#", "language", ["c#", "c sharp", ".net", "dotnet"], {"backend": "be_lang"},
     {"java": 0.5}),
    ("php", "PHP", "language", ["пхп"], {"backend": "be_lang"}, {}),
    ("javascript", "JavaScript", "language", ["js", "ecmascript", "джаваскрипт", "es6"],
     {"frontend": "fe_js", "backend": "be_lang"}, {"typescript": 0.75}),
    ("typescript", "TypeScript", "language", ["ts", "тайпскрипт"],
     {"frontend": "fe_js", "backend": "be_lang"}, {"javascript": 0.8}),
    ("sql", "SQL", "language", ["скл"], {"backend": "be_db", "data_ml": "ml_data"},
     {"postgresql": 0.6, "mysql": 0.6, "clickhouse": 0.4}),
    ("bash", "Bash", "language", ["shell", "баш"], {"devops": "do_linux"}, {"linux": 0.5}),
    # --- backend frameworks & infra ---
    ("fastapi", "FastAPI", "framework", ["fast api", "фастапи"], {"backend": "be_api"},
     {"flask": 0.7, "django": 0.55}),
    ("django", "Django", "framework", ["джанго", "drf", "django rest framework"],
     {"backend": "be_api"}, {"fastapi": 0.55, "flask": 0.6}),
    ("flask", "Flask", "framework", ["фласк"], {"backend": "be_api"},
     {"fastapi": 0.7, "django": 0.6}),
    ("spring", "Spring", "framework", ["spring boot", "спринг"], {"backend": "be_api"},
     {"java": 0.4}),
    ("nodejs", "Node.js", "framework", ["node", "node.js", "нода", "express"],
     {"backend": "be_lang"}, {"nestjs": 0.7, "javascript": 0.4}),
    ("nestjs", "NestJS", "framework", ["nest.js"], {"backend": "be_api"}, {"nodejs": 0.7}),
    ("sqlalchemy", "SQLAlchemy", "framework", ["sqla"], {"backend": "be_db"},
     {"postgresql": 0.3, "django": 0.3}),
    ("celery", "Celery", "tool", ["селери"], {"backend": "be_arch"}, {"rabbitmq": 0.4, "redis": 0.3}),
    ("rest", "REST API", "practice", ["rest", "restful", "рест", "rest api"], {"backend": "be_api"},
     {"graphql": 0.5, "grpc": 0.4}),
    ("graphql", "GraphQL", "practice", ["графкл"], {"backend": "be_api", "frontend": "fe_browser"},
     {"rest": 0.5}),
    ("grpc", "gRPC", "practice", ["protobuf"], {"backend": "be_api"}, {"rest": 0.4}),
    ("microservices", "Микросервисы", "practice", ["microservices", "микросервисная архитектура"],
     {"backend": "be_arch"}, {"kafka": 0.3, "docker": 0.3}),
    ("postgresql", "PostgreSQL", "db", ["postgres", "постгрес", "psql"],
     {"backend": "be_db", "data_ml": "ml_data"}, {"mysql": 0.65, "sql": 0.6}),
    ("mysql", "MySQL", "db", ["mariadb"], {"backend": "be_db"}, {"postgresql": 0.65, "sql": 0.6}),
    ("mongodb", "MongoDB", "db", ["mongo", "монго"], {"backend": "be_db"}, {"postgresql": 0.2}),
    ("redis", "Redis", "db", ["редис"], {"backend": "be_arch"}, {}),
    ("clickhouse", "ClickHouse", "db", ["кликхаус"], {"backend": "be_db", "data_ml": "ml_data"},
     {"sql": 0.4, "postgresql": 0.3}),
    ("kafka", "Kafka", "tool", ["apache kafka", "кафка"], {"backend": "be_arch", "data_ml": "ml_prod"},
     {"rabbitmq": 0.6}),
    ("rabbitmq", "RabbitMQ", "tool", ["rabbit", "кролик", "amqp"], {"backend": "be_arch"},
     {"kafka": 0.6, "celery": 0.3}),
    # --- frontend ---
    ("react", "React", "framework", ["reactjs", "react.js", "реакт"], {"frontend": "fe_framework"},
     {"nextjs": 0.7, "vue": 0.5, "angular": 0.4}),
    ("vue", "Vue", "framework", ["vue.js", "vuejs", "вью", "nuxt"], {"frontend": "fe_framework"},
     {"react": 0.5, "angular": 0.45}),
    ("angular", "Angular", "framework", ["ангуляр"], {"frontend": "fe_framework"},
     {"react": 0.4, "vue": 0.45}),
    ("nextjs", "Next.js", "framework", ["next.js", "nextjs"], {"frontend": "fe_framework"},
     {"react": 0.75}),
    ("redux", "Redux", "framework", ["redux toolkit", "rtk", "редакс"], {"frontend": "fe_framework"},
     {"mobx": 0.6, "react": 0.4}),
    ("mobx", "MobX", "framework", ["мобикс"], {"frontend": "fe_framework"}, {"redux": 0.6}),
    ("html", "HTML", "language", ["html5", "вёрстка", "верстка"], {"frontend": "fe_layout"},
     {"css": 0.5}),
    ("css", "CSS", "language", ["css3", "scss", "sass", "less"], {"frontend": "fe_layout"},
     {"tailwind": 0.6, "html": 0.5}),
    ("tailwind", "Tailwind CSS", "framework", ["tailwindcss"], {"frontend": "fe_layout"},
     {"css": 0.6}),
    ("webpack", "Webpack", "tool", ["вебпак"], {"frontend": "fe_quality"}, {"vite": 0.7}),
    ("vite", "Vite", "tool", [], {"frontend": "fe_quality"}, {"webpack": 0.7}),
    ("jest", "Jest", "tool", ["vitest", "testing library"], {"frontend": "fe_quality"},
     {"playwright": 0.4}),
    ("playwright", "Playwright", "tool", ["cypress", "e2e"], {"frontend": "fe_quality"},
     {"jest": 0.4}),
    ("a11y", "Доступность (a11y)", "practice", ["accessibility", "a11y", "доступность"],
     {"frontend": "fe_layout"}, {}),
    # --- data / ml ---
    ("pandas", "pandas", "framework", ["пандас"], {"data_ml": "ml_data"}, {"numpy": 0.6, "spark": 0.4}),
    ("numpy", "NumPy", "framework", ["нампай"], {"data_ml": "ml_math"}, {"pandas": 0.6}),
    ("sklearn", "scikit-learn", "framework", ["sklearn", "scikit learn", "склерн"],
     {"data_ml": "ml_classic"}, {"catboost": 0.55, "xgboost": 0.55}),
    ("catboost", "CatBoost", "framework", ["кэтбуст"], {"data_ml": "ml_classic"},
     {"xgboost": 0.75, "sklearn": 0.55}),
    ("xgboost", "XGBoost / LightGBM", "framework", ["lightgbm", "xgb", "lgbm", "градиентный бустинг"],
     {"data_ml": "ml_classic"}, {"catboost": 0.75, "sklearn": 0.55}),
    ("pytorch", "PyTorch", "framework", ["torch", "пайторч"], {"data_ml": "ml_dl"},
     {"tensorflow": 0.7}),
    ("tensorflow", "TensorFlow", "framework", ["keras"], {"data_ml": "ml_dl"},
     {"pytorch": 0.7}),
    ("nlp", "NLP", "practice", ["обработка текстов", "natural language processing", "transformers"],
     {"data_ml": "ml_dl"}, {"llm": 0.6}),
    ("cv", "Computer Vision", "practice", ["компьютерное зрение", "opencv", "computer vision"],
     {"data_ml": "ml_dl"}, {"pytorch": 0.3}),
    ("llm", "LLM", "practice", ["large language models", "gpt", "rag", "языковые модели"],
     {"data_ml": "ml_dl"}, {"nlp": 0.6}),
    ("statistics", "Статистика", "practice", ["statistics", "a/b тесты", "ab testing", "матстат"],
     {"data_ml": "ml_math"}, {}),
    ("spark", "Spark", "framework", ["pyspark", "apache spark", "спарк"], {"data_ml": "ml_data"},
     {"pandas": 0.4, "airflow": 0.3}),
    ("airflow", "Airflow", "tool", ["apache airflow", "эирфлоу"], {"data_ml": "ml_prod"},
     {"spark": 0.3}),
    ("mlflow", "MLflow", "tool", ["ml flow"], {"data_ml": "ml_prod"}, {"airflow": 0.3}),
    # --- devops ---
    ("docker", "Docker", "tool", ["докер", "docker compose", "контейнеры"],
     {"devops": "do_containers", "backend": "be_ops", "data_ml": "ml_prod"},
     {"kubernetes": 0.45, "podman": 0.7}),
    ("podman", "Podman", "tool", ["подман"], {"devops": "do_containers"}, {"docker": 0.7}),
    ("kubernetes", "Kubernetes", "tool", ["k8s", "кубернетес", "кубер"], {"devops": "do_containers"},
     {"helm": 0.6, "docker": 0.45, "openshift": 0.7}),
    ("openshift", "OpenShift", "tool", [], {"devops": "do_containers"}, {"kubernetes": 0.7}),
    ("helm", "Helm", "tool", ["хелм"], {"devops": "do_containers"}, {"kubernetes": 0.6}),
    ("linux", "Linux", "tool", ["линукс", "unix", "ubuntu", "debian"],
     {"devops": "do_linux", "backend": "be_ops"}, {"bash": 0.5}),
    ("nginx", "Nginx", "tool", ["нжинкс", "nginx"], {"devops": "do_linux", "backend": "be_ops"},
     {}),
    ("terraform", "Terraform", "tool", ["терраформ", "opentofu"], {"devops": "do_cicd"},
     {"ansible": 0.45}),
    ("ansible", "Ansible", "tool", ["ансибл"], {"devops": "do_cicd"}, {"terraform": 0.45}),
    ("cicd", "CI/CD", "practice", ["continuous integration", "ci/cd", "ci cd"],
     {"devops": "do_cicd", "backend": "be_ops", "frontend": "fe_quality"},
     {"gitlab_ci": 0.8, "github_actions": 0.8}),
    ("gitlab_ci", "GitLab CI", "tool", ["gitlab", "гитлаб"], {"devops": "do_cicd"},
     {"github_actions": 0.75, "cicd": 0.8}),
    ("github_actions", "GitHub Actions", "tool", ["gha"], {"devops": "do_cicd"},
     {"gitlab_ci": 0.75, "cicd": 0.8}),
    ("prometheus", "Prometheus", "tool", ["прометеус"], {"devops": "do_observe", "backend": "be_ops"},
     {"grafana": 0.6}),
    ("grafana", "Grafana", "tool", ["графана"], {"devops": "do_observe"}, {"prometheus": 0.6}),
    ("elk", "ELK / OpenSearch", "tool", ["elasticsearch", "kibana", "logstash", "opensearch"],
     {"devops": "do_observe"}, {"grafana": 0.3}),
    ("aws", "AWS", "tool", ["amazon web services"], {"devops": "do_cloud"},
     {"yandex_cloud": 0.6}),
    ("yandex_cloud", "Yandex Cloud", "tool", ["яндекс облако", "yc"], {"devops": "do_cloud"},
     {"aws": 0.6}),
    ("security", "DevSecOps", "practice", ["безопасность", "devsecops", "vault"],
     {"devops": "do_cloud", "backend": "be_api"}, {}),
    # --- common ---
    ("git", "Git", "tool", ["гит"], {}, {}),
    ("algorithms", "Алгоритмы", "practice", ["algorithms", "алгоритмы", "структуры данных",
                                              "спортивное программирование"],
     {"backend": "be_algo"}, {}),
]
