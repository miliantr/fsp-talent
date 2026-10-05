"""More parametric families: at least one leak-proof template per competency."""

import math
import random

from app.domain.question_bank.families import Family, _numeric, _single

# ---------------------------------------------------------------- backend


def sql_having_rows(rng: random.Random) -> dict:
    users = rng.sample(range(1, 10), k=rng.randint(4, 6))
    rows = [(u, rng.choice([100, 200, 300, 500, 700])) for u in users for _ in range(rng.randint(1, 3))]
    rng.shuffle(rows)
    x = rng.choice([400, 600, 800])
    totals: dict[int, int] = {}
    for u, a in rows:
        totals[u] = totals.get(u, 0) + a
    ans = sum(1 for v in totals.values() if v > x)
    table = "\n".join(f"({u}, {a})" for u, a in rows)
    return _numeric(
        f"Таблица `orders(user_id, amount)` содержит строки:\n```\n{table}\n```\n"
        f"Сколько строк вернёт запрос?\n```sql\nSELECT user_id, SUM(amount) FROM orders\nGROUP BY user_id\n"
        f"HAVING SUM(amount) > {x};\n```",
        ans, {"rows": rows, "x": x},
    )


def left_join_count(rng: random.Random) -> dict:
    n_users = rng.randint(3, 6)
    orders = [rng.randint(1, n_users + 1) for _ in range(rng.randint(3, 8))]  # some orders of unknown user
    ans = sum(max(1, orders.count(u)) for u in range(1, n_users + 1))
    return _numeric(
        f"В таблице `users` {n_users} строк с id от 1 до {n_users}. В таблице `orders` есть заказы со значениями "
        f"`user_id`: {', '.join(map(str, orders))}. Сколько строк вернёт запрос?\n"
        f"```sql\nSELECT * FROM users u LEFT JOIN orders o ON o.user_id = u.id;\n```",
        ans, {"n_users": n_users, "orders": orders},
    )


_STATUS = [
    ("ресурс успешно создан, в ответе — его представление", "201"),
    ("запрос без токена к защищённому ресурсу", "401"),
    ("токен валиден, но у пользователя нет прав на ресурс", "403"),
    ("клиент превысил лимит запросов", "429"),
    ("ресурс успешно удалён, тело ответа не возвращается", "204"),
    ("попытка создать пользователя с уже занятым e-mail", "409"),
    ("запрошенный заказ не существует", "404"),
]


def http_status(rng: random.Random) -> dict:
    scenario, code = rng.choice(_STATUS)
    others = [c for _, c in _STATUS if c != code] + ["200", "500"]
    rng.shuffle(others)
    return _single(f"Какой HTTP-код наиболее уместен: {scenario}?", code, others, {"scenario": scenario}, rng)


def kafka_consumers(rng: random.Random) -> dict:
    p = rng.choice([3, 4, 6, 8, 12])
    c = rng.choice([2, 4, 5, 8, 10, 16])
    ask_idle = rng.random() < 0.5 and c > p
    if ask_idle:
        return _numeric(
            f"Топик Kafka имеет {p} партиций, в consumer group {c} потребителей. "
            f"Сколько потребителей будут простаивать без назначенных партиций?",
            c - p, {"p": p, "c": c},
        )
    return _numeric(
        f"Топик Kafka имеет {p} партиций, в consumer group {c} потребителей. Какое наибольшее число партиций "
        f"может достаться одному потребителю при равномерном распределении?",
        math.ceil(p / min(c, p)), {"p": p, "c": c},
    )


def docker_cache(rng: random.Random) -> dict:
    head = [f"FROM python:3.{rng.choice([10, 11, 12])}-slim"]
    head += rng.sample(["WORKDIR /app", "ENV PYTHONUNBUFFERED=1", "RUN apt-get update && apt-get install -y curl",
                        "ARG APP_ENV=prod"], k=rng.randint(1, 3))
    deps = ["COPY requirements.txt .", "RUN pip install -r requirements.txt"]
    code = ["COPY . ."]
    tail = rng.sample(["RUN python -m compileall .", "RUN useradd -m app", "EXPOSE 8000", "USER app"],
                      k=rng.randint(1, 3)) + ['CMD ["python", "main.py"]']
    steps = head + deps + code + tail
    changed = rng.choice(["requirements.txt", "исходный код приложения"])
    k = len(head) + 1 if changed == "requirements.txt" else len(head) + len(deps) + 1
    numbered = "\n".join(steps)
    return _numeric(
        f"Dockerfile:\n```dockerfile\n{numbered}\n```\nИзменился только {changed}. Для скольких инструкций "
        f"(включая первую с инвалидированным кешем) кеш не будет использован при `docker build`?",
        len(steps) - k + 1, {"changed": changed, "steps": len(steps)},
    )


# ---------------------------------------------------------------- frontend


def react_batching(rng: random.Random) -> dict:
    v = rng.randint(0, 9)
    n = rng.randint(2, 4)
    functional = rng.random() < 0.5
    call = "setCount(c => c + 1);" if functional else "setCount(count + 1);"
    body = "\n  ".join([call] * n)
    ans = v + n if functional else v + 1
    return _numeric(
        f"Значение `count` равно {v}. Обработчик клика:\n```jsx\nfunction onClick() {{\n  {body}\n}}\n```\n"
        f"Каким будет `count` после следующего рендера?",
        ans, {"v": v, "n": n, "functional": functional},
    )


def http1_parallel(rng: random.Random) -> dict:
    n = rng.randint(7, 20)
    t = rng.choice([100, 120, 150, 200])
    return _numeric(
        f"Страница по HTTP/1.1 (без конвейеризации) загружает {n} скриптов с одного домена. Браузер открывает "
        f"до 6 соединений к домену, каждый скрипт грузится {t} мс. Какое минимальное время (мс) загрузки всех "
        f"скриптов?",
        math.ceil(n / 6) * t, {"n": n, "t": t},
    )


def semver_range(rng: random.Random) -> dict:
    major, minor, patch = rng.randint(1, 5), rng.randint(1, 9), rng.randint(0, 9)
    op = rng.choice(["^", "~"])
    if op == "^":
        good = f"{major}.{minor + rng.randint(1, 5)}.{rng.randint(0, 9)}"
        bad = [f"{major + 1}.0.0", f"{major}.{minor - 1}.{patch + 3}", f"{major - 1}.{minor + 2}.0"]
    else:
        good = f"{major}.{minor}.{patch + rng.randint(1, 9)}"
        bad = [f"{major}.{minor + 1}.0", f"{major + 1}.{minor}.{patch}", f"{major}.{minor - 1}.{patch + 1}"]
    return _single(f"Какая версия удовлетворяет диапазону `{op}{major}.{minor}.{patch}` в package.json?",
                   good, bad, {"range": f"{op}{major}.{minor}.{patch}"}, rng)


# ---------------------------------------------------------------- data / ml


def groupby_mean(rng: random.Random) -> dict:
    cities = rng.sample(["Москва", "Казань", "Томск", "Сочи"], 2)
    rows = [(rng.choice(cities), rng.choice([100, 120, 150, 180, 200, 240])) for _ in range(6)]
    target = rows[0][0]
    vals = [v for c, v in rows if c == target]
    ans = round(sum(vals) / len(vals), 2)
    data = "\n".join(f"{c:8s} {v}" for c, v in rows)
    return _numeric(
        f"DataFrame `df`:\n```\ncity     salary\n{data}\n```\n"
        f"Чему равно `df.groupby('city')['salary'].mean()['{target}']` (до сотых)?",
        ans, {"rows": rows, "target": target},
    )


def replicas_needed(rng: random.Random) -> dict:
    b = rng.choice([8, 16, 32])
    t = rng.choice([40, 50, 80, 100])
    r = rng.choice([500, 1200, 2000, 3500])
    per_replica = b * 1000 / t
    return _numeric(
        f"Реплика модели обрабатывает батч из {b} запросов за {t} мс (последовательно, батчи всегда полные). "
        f"Нагрузка — {r} запросов/с. Сколько реплик нужно минимум?",
        math.ceil(r / per_replica), {"b": b, "t": t, "r": r},
    )


# ---------------------------------------------------------------- devops


def pods_per_node(rng: random.Random) -> dict:
    cpu = rng.choice([4, 8, 16])
    mem = rng.choice([16, 32, 64])
    req_cpu = rng.choice([250, 500, 750, 1000])
    req_mem = rng.choice([512, 1024, 1536, 2048])
    ans = min(cpu * 1000 // req_cpu, mem * 1024 // req_mem)
    return _numeric(
        f"Узел Kubernetes: {cpu} vCPU и {mem} GiB памяти (без системных резервов). Поды запрашивают "
        f"`cpu: {req_cpu}m`, `memory: {req_mem}Mi`. Сколько таких подов планировщик разместит на узле?",
        ans, {"cpu": cpu, "mem": mem, "req_cpu": req_cpu, "req_mem": req_mem},
    )


def hpa_replicas(rng: random.Random) -> dict:
    cur = rng.randint(2, 8)
    target = rng.choice([50, 60, 70])
    util = rng.choice([80, 90, 105, 120, 140])
    return _numeric(
        f"HPA с целевой загрузкой CPU {target}%. Сейчас {cur} подов при средней загрузке {util}%. "
        f"Сколько реплик выставит HPA (desired = ceil(current × текущая/целевая))?",
        math.ceil(cur * util / target), {"cur": cur, "target": target, "util": util},
    )


def pipeline_time(rng: random.Random) -> dict:
    stages = []
    for name in ("build", "test", "deploy"):
        jobs = [rng.choice([2, 3, 4, 5, 6, 8]) for _ in range(rng.randint(1, 3))]
        stages.append((name, jobs))
    desc = "\n".join(f"- {n}: параллельные job по {', '.join(map(str, j))} мин" for n, j in stages)
    return _numeric(
        f"Пайплайн из последовательных стадий, job внутри стадии идут параллельно:\n{desc}\n"
        f"Сколько минут займёт пайплайн при достаточном числе раннеров?",
        sum(max(j) for _, j in stages), {"stages": stages},
    )


def transfer_time(rng: random.Random) -> dict:
    tb = rng.choice([1, 2, 5, 10])
    gbit = rng.choice([1, 10])
    hours = tb * 8 * 1000 / gbit / 3600
    fmt = lambda h: f"≈ {h:.1f} ч" if h >= 1 else f"≈ {h * 60:.0f} мин"  # noqa: E731
    return _single(
        f"Сколько минимум займёт передача {tb} ТБ по каналу {gbit} Гбит/с (без накладных расходов, 1 ТБ = 1000 ГБ)?",
        fmt(hours), [fmt(hours * 8), fmt(hours / 8), fmt(hours * 3.6)], {"tb": tb, "gbit": gbit}, rng,
    )


EXTRA_FAMILIES: list[Family] = [
    Family("BE-FAM-HAVING", "backend", "be_db", 3, "numeric", "SQL: GROUP BY / HAVING", sql_having_rows),
    Family("BE-FAM-LJOIN", "backend", "be_db", 4, "numeric", "SQL: LEFT JOIN", left_join_count),
    Family("BE-FAM-HTTP", "backend", "be_api", 2, "single", "HTTP-статусы", http_status),
    Family("BE-FAM-KAFKA", "backend", "be_arch", 4, "numeric", "Партиции Kafka", kafka_consumers),
    Family("BE-FAM-DOCKER", "backend", "be_ops", 3, "numeric", "Кеш слоёв Docker", docker_cache),
    Family("FE-FAM-BATCH", "frontend", "fe_framework", 3, "numeric", "Батчинг setState", react_batching),
    Family("FE-FAM-HTTP1", "frontend", "fe_browser", 4, "numeric", "Параллельная загрузка HTTP/1.1",
           http1_parallel),
    Family("FE-FAM-SEMVER", "frontend", "fe_quality", 3, "single", "Диапазоны semver", semver_range),
    Family("ML-FAM-GROUPBY", "data_ml", "ml_data", 2, "numeric", "pandas groupby", groupby_mean),
    Family("ML-FAM-REPLICAS", "data_ml", "ml_prod", 3, "numeric", "Пропускная способность инференса",
           replicas_needed),
    Family("DO-FAM-PODS", "devops", "do_containers", 3, "numeric", "Ёмкость узла Kubernetes", pods_per_node),
    Family("DO-FAM-HPA", "devops", "do_containers", 4, "numeric", "Формула HPA", hpa_replicas),
    Family("DO-FAM-PIPE", "devops", "do_cicd", 2, "numeric", "Длительность пайплайна", pipeline_time),
    Family("DO-FAM-XFER", "devops", "do_cloud", 3, "single", "Передача данных", transfer_time),
]
