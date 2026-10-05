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
    query = f"```sql\nSELECT user_id, SUM(amount) FROM orders\nGROUP BY user_id\nHAVING SUM(amount) > {x};\n```"
    return _numeric(
        f"Таблица `orders(user_id, amount)` содержит строки:\n```\n{table}\n```\nСколько строк вернёт запрос?\n{query}",
        ans, {"rows": rows, "x": x},
        f"The table `orders(user_id, amount)` contains the rows:\n```\n{table}\n```\n"
        f"How many rows does the query return?\n{query}",
    )


def left_join_count(rng: random.Random) -> dict:
    n_users = rng.randint(3, 6)
    orders = [rng.randint(1, n_users + 1) for _ in range(rng.randint(3, 8))]  # some orders of unknown user
    ans = sum(max(1, orders.count(u)) for u in range(1, n_users + 1))
    ids = ", ".join(map(str, orders))
    query = "```sql\nSELECT * FROM users u LEFT JOIN orders o ON o.user_id = u.id;\n```"
    return _numeric(
        f"В таблице `users` {n_users} строк с id от 1 до {n_users}. В таблице `orders` есть заказы со значениями "
        f"`user_id`: {ids}. Сколько строк вернёт запрос?\n{query}",
        ans, {"n_users": n_users, "orders": orders},
        f"The `users` table has {n_users} rows with ids from 1 to {n_users}. The `orders` table has orders with "
        f"`user_id` values: {ids}. How many rows does the query return?\n{query}",
    )


_STATUS = [
    ("ресурс успешно создан, в ответе — его представление", "201",
     "a resource was created successfully and its representation is returned"),
    ("запрос без токена к защищённому ресурсу", "401", "a request without a token to a protected resource"),
    ("токен валиден, но у пользователя нет прав на ресурс", "403",
     "the token is valid, but the user has no rights to the resource"),
    ("клиент превысил лимит запросов", "429", "the client exceeded the request limit"),
    ("ресурс успешно удалён, тело ответа не возвращается", "204",
     "a resource was deleted successfully, no response body is returned"),
    ("попытка создать пользователя с уже занятым e-mail", "409",
     "an attempt to create a user with an e-mail that is already taken"),
    ("запрошенный заказ не существует", "404", "the requested order does not exist"),
]


def http_status(rng: random.Random) -> dict:
    scenario, code, scenario_en = rng.choice(_STATUS)
    others = [c for _, c, _ in _STATUS if c != code] + ["200", "500"]
    rng.shuffle(others)
    return _single(f"Какой HTTP-код наиболее уместен: {scenario}?", code, others, {"scenario": scenario}, rng,
                   f"Which HTTP status code fits best: {scenario_en}?")


def kafka_consumers(rng: random.Random) -> dict:
    p = rng.choice([3, 4, 6, 8, 12])
    c = rng.choice([2, 4, 5, 8, 10, 16])
    ask_idle = rng.random() < 0.5 and c > p
    if ask_idle:
        return _numeric(
            f"Топик Kafka имеет {p} партиций, в consumer group {c} потребителей. "
            f"Сколько потребителей будут простаивать без назначенных партиций?",
            c - p, {"p": p, "c": c},
            f"A Kafka topic has {p} partitions, and the consumer group has {c} consumers. "
            f"How many consumers will stay idle without assigned partitions?",
        )
    return _numeric(
        f"Топик Kafka имеет {p} партиций, в consumer group {c} потребителей. Какое наибольшее число партиций "
        f"может достаться одному потребителю при равномерном распределении?",
        math.ceil(p / min(c, p)), {"p": p, "c": c},
        f"A Kafka topic has {p} partitions, and the consumer group has {c} consumers. What is the largest number "
        f"of partitions one consumer can get with an even assignment?",
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
    changed_en = "requirements.txt" if changed == "requirements.txt" else "the application source code"
    k = len(head) + 1 if changed == "requirements.txt" else len(head) + len(deps) + 1
    numbered = "\n".join(steps)
    return _numeric(
        f"Dockerfile:\n```dockerfile\n{numbered}\n```\nИзменился только {changed}. Для скольких инструкций "
        f"(включая первую с инвалидированным кешем) кеш не будет использован при `docker build`?",
        len(steps) - k + 1, {"changed": changed, "steps": len(steps)},
        f"Dockerfile:\n```dockerfile\n{numbered}\n```\nOnly {changed_en} has changed. For how many instructions "
        f"(including the first one with an invalidated cache) will the cache not be used in `docker build`?",
    )


# ---------------------------------------------------------------- frontend


def react_batching(rng: random.Random) -> dict:
    v = rng.randint(0, 9)
    n = rng.randint(2, 4)
    functional = rng.random() < 0.5
    call = "setCount(c => c + 1);" if functional else "setCount(count + 1);"
    body = "\n  ".join([call] * n)
    ans = v + n if functional else v + 1
    handler = f"```jsx\nfunction onClick() {{\n  {body}\n}}\n```"
    return _numeric(
        f"Значение `count` равно {v}. Обработчик клика:\n{handler}\nКаким будет `count` после следующего рендера?",
        ans, {"v": v, "n": n, "functional": functional},
        f"`count` equals {v}. The click handler:\n{handler}\nWhat will `count` be after the next render?",
    )


def http1_parallel(rng: random.Random) -> dict:
    n = rng.randint(7, 20)
    t = rng.choice([100, 120, 150, 200])
    return _numeric(
        f"Страница по HTTP/1.1 (без конвейеризации) загружает {n} скриптов с одного домена. Браузер открывает "
        f"до 6 соединений к домену, каждый скрипт грузится {t} мс. Какое минимальное время (мс) загрузки всех "
        f"скриптов?",
        math.ceil(n / 6) * t, {"n": n, "t": t},
        f"A page loads {n} scripts from one domain over HTTP/1.1 (no pipelining). The browser opens up to 6 "
        f"connections per domain, and each script takes {t} ms to load. What is the minimum time (ms) to load "
        f"all the scripts?",
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
    spec = f"{op}{major}.{minor}.{patch}"
    return _single(f"Какая версия удовлетворяет диапазону `{spec}` в package.json?",
                   good, bad, {"range": spec}, rng,
                   f"Which version satisfies the range `{spec}` in package.json?")


# ---------------------------------------------------------------- data / ml

_CITIES_EN = {"Москва": "Moscow", "Казань": "Kazan", "Томск": "Tomsk", "Сочи": "Sochi"}


def groupby_mean(rng: random.Random) -> dict:
    cities = rng.sample(["Москва", "Казань", "Томск", "Сочи"], 2)
    rows = [(rng.choice(cities), rng.choice([100, 120, 150, 180, 200, 240])) for _ in range(6)]
    target = rows[0][0]
    vals = [v for c, v in rows if c == target]
    ans = round(sum(vals) / len(vals), 2)
    data = "\n".join(f"{c:8s} {v}" for c, v in rows)
    data_en = "\n".join(f"{_CITIES_EN[c]:8s} {v}" for c, v in rows)
    return _numeric(
        f"DataFrame `df`:\n```\ncity     salary\n{data}\n```\n"
        f"Чему равно `df.groupby('city')['salary'].mean()['{target}']` (до сотых)?",
        ans, {"rows": rows, "target": target},
        f"DataFrame `df`:\n```\ncity     salary\n{data_en}\n```\n"
        f"What is `df.groupby('city')['salary'].mean()['{_CITIES_EN[target]}']` (to two decimals)?",
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
        f"A model replica processes a batch of {b} requests in {t} ms (sequentially, batches are always full). "
        f"The load is {r} requests/s. What is the minimum number of replicas needed?",
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
        f"A Kubernetes node has {cpu} vCPU and {mem} GiB of memory (no system reservations). Pods request "
        f"`cpu: {req_cpu}m`, `memory: {req_mem}Mi`. How many such pods will the scheduler place on the node?",
    )


def hpa_replicas(rng: random.Random) -> dict:
    cur = rng.randint(2, 8)
    target = rng.choice([50, 60, 70])
    util = rng.choice([80, 90, 105, 120, 140])
    return _numeric(
        f"HPA с целевой загрузкой CPU {target}%. Сейчас {cur} подов при средней загрузке {util}%. "
        f"Сколько реплик выставит HPA (desired = ceil(current × текущая/целевая))?",
        math.ceil(cur * util / target), {"cur": cur, "target": target, "util": util},
        f"An HPA targets {target}% CPU utilization. There are {cur} pods now with an average utilization of {util}%. "
        f"How many replicas will the HPA set (desired = ceil(current × current/target utilization))?",
    )


def pipeline_time(rng: random.Random) -> dict:
    stages = []
    for name in ("build", "test", "deploy"):
        jobs = [rng.choice([2, 3, 4, 5, 6, 8]) for _ in range(rng.randint(1, 3))]
        stages.append((name, jobs))
    desc = "\n".join(f"- {n}: параллельные job по {', '.join(map(str, j))} мин" for n, j in stages)
    desc_en = "\n".join(f"- {n}: parallel jobs of {', '.join(map(str, j))} min" for n, j in stages)
    return _numeric(
        f"Пайплайн из последовательных стадий, job внутри стадии идут параллельно:\n{desc}\n"
        f"Сколько минут займёт пайплайн при достаточном числе раннеров?",
        sum(max(j) for _, j in stages), {"stages": stages},
        f"A pipeline of sequential stages; jobs within a stage run in parallel:\n{desc_en}\n"
        f"How many minutes will the pipeline take with enough runners?",
    )


def transfer_time(rng: random.Random) -> dict:
    tb = rng.choice([1, 2, 5, 10])
    gbit = rng.choice([1, 10])
    hours = tb * 8 * 1000 / gbit / 3600
    labels = {}  # ru option -> en option

    def fmt(h: float) -> str:
        ru, en = (f"≈ {h:.1f} ч", f"≈ {h:.1f} h") if h >= 1 else (f"≈ {h * 60:.0f} мин", f"≈ {h * 60:.0f} min")
        labels[ru] = en
        return ru

    return _single(
        f"Сколько минимум займёт передача {tb} ТБ по каналу {gbit} Гбит/с (без накладных расходов, 1 ТБ = 1000 ГБ)?",
        fmt(hours), [fmt(hours * 8), fmt(hours / 8), fmt(hours * 3.6)], {"tb": tb, "gbit": gbit}, rng,
        f"What is the minimum time to transfer {tb} TB over a {gbit} Gbit/s link (no overhead, 1 TB = 1000 GB)?",
        labels.__getitem__,
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
