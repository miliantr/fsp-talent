"""Parametric item families (automatic item generation).

Each family is a template with a fixed cognitive operation and difficulty; only the surface
parameters change. Every draw renders an isomorphic variant, so the item cannot be "leaked" by
sharing the answer: the next candidate gets different numbers with the same difficulty.

A draw is rendered in every supported language from the same random parameters (`i18n`), with the
options in the same order, so the correct answer does not depend on the interface language.
"""

import math
import random
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Family:
    code: str
    specialization: str
    competency: str
    difficulty: int
    qtype: str  # single | numeric
    title: str
    render: Callable[[random.Random], dict]


def _numeric(text: str, answer: float, params: dict, en: str) -> dict:
    return {"text": text, "options": [], "correct": [answer], "params": params,
            "i18n": {"en": {"text": en, "options": []}}}


def _single(text: str, correct_value: str, distractors: list[str], params: dict, rng, en: str,
            en_option: Callable[[str], str] | None = None) -> dict:
    """`en_option` maps an option to English when it contains words (units etc.)."""
    opts = [correct_value]
    for d in distractors:
        if d not in opts:
            opts.append(d)
        if len(opts) == 4:
            break
    rng.shuffle(opts)
    en_opts = [en_option(o) for o in opts] if en_option else list(opts)
    return {"text": text, "options": opts, "correct": [opts.index(correct_value)], "params": params,
            "i18n": {"en": {"text": en, "options": en_opts}}}


# ---------------------------------------------------------------- backend
def binary_search_steps(rng: random.Random) -> dict:
    n = rng.choice([rng.randint(100, 999), rng.randint(1000, 99_999), rng.randint(100_000, 2_000_000)])
    ans = math.floor(math.log2(n)) + 1
    return _numeric(
        f"Сколько сравнений в худшем случае выполнит бинарный поиск в отсортированном массиве "
        f"из {n:,} элементов?".replace(",", " "),
        ans,
        {"n": n},
        f"How many comparisons does binary search make in the worst case on a sorted array of {n:,} elements?",
    )


_LOOP_TEMPLATES = [
    ("for i in range(n):\n    for j in range(i, n):\n        total += 1", "O(n²)"),
    ("i = 1\nwhile i < n:\n    i *= 2", "O(log n)"),
    ("for i in range(n):\n    j = 1\n    while j < n:\n        j *= 2", "O(n log n)"),
    ("for i in range(n):\n    for j in range(10):\n        total += 1", "O(n)"),
    ("for i in range(n):\n    for j in range(n):\n        for k in range(n):\n            total += 1", "O(n³)"),
    ("i = n\nwhile i > 0:\n    for j in range(i):\n        total += 1\n    i //= 2", "O(n)"),
    ("for i in range(1, n):\n    j = i\n    while j > 0:\n        j //= 2", "O(n log n)"),
]


def loop_complexity(rng: random.Random) -> dict:
    code, ans = rng.choice(_LOOP_TEMPLATES)
    var = rng.choice(["total", "acc", "cnt", "s"])
    code = code.replace("total", var)
    pool = ["O(n)", "O(n log n)", "O(n²)", "O(log n)", "O(n³)", "O(2ⁿ)"]
    distractors = [p for p in pool if p != ans]
    rng.shuffle(distractors)
    return _single(
        f"Какова асимптотическая сложность фрагмента?\n```python\n{code}\n```",
        ans, distractors, {"template": code}, rng,
        f"What is the asymptotic complexity of the snippet?\n```python\n{code}\n```",
    )


def python_range_len(rng: random.Random) -> dict:
    a = rng.randint(0, 20)
    b = a + rng.randint(11, 60)
    s = rng.randint(2, 7)
    return _numeric(
        f"Чему равно `len(range({a}, {b}, {s}))` в Python?", len(range(a, b, s)), {"a": a, "b": b, "s": s},
        f"What is `len(range({a}, {b}, {s}))` in Python?",
    )


# ---------------------------------------------------------------- frontend
def css_specificity(rng: random.Random) -> dict:
    ids = rng.randint(0, 2)
    classes = rng.randint(0, 3)
    elems = rng.randint(1, 3)
    parts = [f"#{rng.choice(['app', 'main', 'nav', 'root'])}{k}" for k in range(ids)]
    parts += [f".{rng.choice(['card', 'item', 'active', 'title', 'btn'])}{k}" for k in range(classes)]
    tags = ["div", "ul", "li", "span", "a", "p", "section"]
    parts += [rng.choice(tags) for _ in range(elems)]
    rng.shuffle(parts)
    # attach classes/ids to previous tags sometimes to look realistic; specificity is unchanged
    selector = " ".join(parts)
    ans = f"({ids}, {classes}, {elems})"
    distractors = [
        f"({classes}, {ids}, {elems})",
        f"({ids}, {classes + elems}, 0)",
        f"(0, {ids + classes}, {elems})",
        f"({ids}, {elems}, {classes})",
        f"({ids + 1}, {classes}, {elems})",
        f"({ids}, {classes + 1}, {elems})",
        f"({ids}, {classes}, {elems + 1})",
    ]
    return _single(
        f"Какова специфичность селектора `{selector}` в формате (id, классы, элементы)?",
        ans, distractors, {"selector": selector}, rng,
        f"What is the specificity of the selector `{selector}` in the format (ids, classes, elements)?",
    )


def js_array_chain(rng: random.Random) -> dict:
    arr = [rng.randint(1, 15) for _ in range(5)]
    k = rng.randint(2, 5)
    ans = sum(x * k for x in arr if x % 2 == 0)
    code = (f"```js\n[{', '.join(map(str, arr))}]\n"
            f"  .filter(x => x % 2 === 0)\n  .map(x => x * {k})\n  .reduce((s, x) => s + x, 0)\n```")
    return _numeric(f"Чему равен результат выражения?\n{code}", ans, {"arr": arr, "k": k},
                    f"What is the result of the expression?\n{code}")


# ---------------------------------------------------------------- data / ml
def precision_recall(rng: random.Random) -> dict:
    tp = rng.randint(20, 90)
    fp = rng.randint(5, 40)
    fn = rng.randint(5, 40)
    p = tp / (tp + fp)
    r = tp / (tp + fn)
    f1 = 2 * p * r / (p + r)
    metric = rng.choice(["precision", "recall", "F1"])
    value = {"precision": p, "recall": r, "F1": f1}[metric]
    fmt = lambda x: f"{x:.2f}"  # noqa: E731
    others = [fmt(v) for v in (p, r, f1, (p + r) / 2, tp / (tp + fp + fn), value + 0.07, value - 0.09,
                               1 - value)]
    return _single(
        f"Классификатор дал TP = {tp}, FP = {fp}, FN = {fn}. Чему равен {metric} (округлите до сотых)?",
        fmt(value), [o for o in others if o != fmt(value)], {"tp": tp, "fp": fp, "fn": fn, "metric": metric}, rng,
        f"A classifier produced TP = {tp}, FP = {fp}, FN = {fn}. What is the {metric} (round to two decimals)?",
    )


def bayes_test(rng: random.Random) -> dict:
    prev = rng.choice([0.01, 0.02, 0.05])
    sens = rng.choice([0.9, 0.95, 0.99])
    spec = rng.choice([0.9, 0.95, 0.98])
    post = prev * sens / (prev * sens + (1 - prev) * (1 - spec))
    pct = lambda x: f"{x * 100:.0f}%"  # noqa: E731
    distractors = [pct(sens), pct(spec), pct(prev * sens), pct(1 - spec), pct(min(0.99, post * 3)),
                   pct(post / 2), pct(min(0.99, post + 0.25))]
    return _single(
        f"Заболеванием страдает {prev * 100:g}% популяции. Тест выявляет больных с чувствительностью "
        f"{sens * 100:g}% и специфичностью {spec * 100:g}%. Тест положительный. "
        f"Какова вероятность, что человек болен (округлите до процента)?",
        pct(post), [d for d in distractors if d != pct(post)], {"prev": prev, "sens": sens, "spec": spec}, rng,
        f"A disease affects {prev * 100:g}% of the population. A test detects it with a sensitivity of "
        f"{sens * 100:g}% and a specificity of {spec * 100:g}%. The test is positive. "
        f"What is the probability that the person is ill (round to a whole percent)?",
    )


def conv_output(rng: random.Random) -> dict:
    while True:
        w = rng.choice([28, 32, 64, 96, 128, 224])
        k = rng.choice([3, 5, 7])
        p = rng.choice([0, 1, 2, 3])
        s = rng.choice([1, 2])
        if (w - k + 2 * p) % s == 0 and w - k + 2 * p > 0:
            break
    ans = (w - k + 2 * p) // s + 1
    return _numeric(
        f"Вход свёрточного слоя {w}×{w}, ядро {k}×{k}, padding = {p}, stride = {s}. "
        f"Какова ширина выходной карты признаков?",
        ans, {"w": w, "k": k, "p": p, "s": s},
        f"A convolutional layer has a {w}×{w} input, a {k}×{k} kernel, padding = {p}, stride = {s}. "
        f"What is the width of the output feature map?",
    )


# ---------------------------------------------------------------- devops
def cidr_hosts(rng: random.Random) -> dict:
    prefix = rng.randint(20, 29)
    octets = [10, rng.randint(0, 255), rng.randint(0, 255), 0]
    net = f"{'.'.join(map(str, octets))}/{prefix}"
    return _numeric(
        f"Сколько адресов для хостов доступно в подсети {net} (без адреса сети и broadcast)?",
        2 ** (32 - prefix) - 2, {"prefix": prefix},
        f"How many host addresses are available in the subnet {net} (excluding the network and broadcast addresses)?",
    )


def chmod_octal(rng: random.Random) -> dict:
    def triad() -> str:
        return "".join(c if rng.random() < 0.6 else "-" for c in "rwx")

    owner = "rwx" if rng.random() < 0.5 else triad()  # owner usually has full access
    s = owner + triad() + triad()
    octal = "".join(
        str(sum(v for c, v in zip(s[i:i + 3], (4, 2, 1), strict=True) if c != "-")) for i in (0, 3, 6)
    )
    distractors = [octal[::-1], octal[0] + octal[2] + octal[1], "".join(str(7 - int(d)) for d in octal)]
    while len({*distractors} - {octal}) < 3:
        distractors.append("".join(str(rng.randint(0, 7)) for _ in range(3)))
    distractors = [d for d in dict.fromkeys(distractors) if d != octal]
    return _single(
        f"Какой восьмеричной записи соответствуют права `-{s}`?", octal, distractors, {"perms": s}, rng,
        f"Which octal notation corresponds to the permissions `-{s}`?",
    )


def sla_downtime(rng: random.Random) -> dict:
    avail = rng.choice([99.0, 99.5, 99.9, 99.95, 99.99])
    days = rng.choice([30, 7])
    minutes = days * 24 * 60 * (100 - avail) / 100
    labels = {}  # ru option -> en option

    def fmt(m: float) -> str:
        ru, en = (f"≈ {m:.1f} мин", f"≈ {m:.1f} min") if m < 100 else (f"≈ {m / 60:.1f} ч", f"≈ {m / 60:.1f} h")
        labels[ru] = en
        return ru

    distractors = [fmt(minutes * 10), fmt(minutes / 10), fmt(minutes * 2), fmt(minutes * 60)]
    return _single(
        f"SLO доступности {avail:g}% за {days} дней. Какой допустимый суммарный простой?",
        fmt(minutes), [d for d in distractors if d != fmt(minutes)], {"availability": avail, "days": days}, rng,
        f"An availability SLO of {avail:g}% over {days} days. What is the total allowed downtime?",
        labels.__getitem__,
    )


FAMILIES: list[Family] = [
    Family("BE-FAM-BSEARCH", "backend", "be_algo", 3, "numeric", "Бинарный поиск: число сравнений", binary_search_steps),
    Family("BE-FAM-BIGO", "backend", "be_algo", 4, "single", "Асимптотика циклов", loop_complexity),
    Family("BE-FAM-RANGE", "backend", "be_lang", 2, "numeric", "Длина range()", python_range_len),
    Family("FE-FAM-SPEC", "frontend", "fe_layout", 3, "single", "Специфичность CSS", css_specificity),
    Family("FE-FAM-CHAIN", "frontend", "fe_js", 2, "numeric", "Цепочка методов массива", js_array_chain),
    Family("ML-FAM-PR", "data_ml", "ml_classic", 3, "single", "Precision / Recall / F1", precision_recall),
    Family("ML-FAM-BAYES", "data_ml", "ml_math", 4, "single", "Теорема Байеса", bayes_test),
    Family("ML-FAM-CONV", "data_ml", "ml_dl", 4, "numeric", "Размер выхода свёртки", conv_output),
    Family("DO-FAM-CIDR", "devops", "do_linux", 3, "numeric", "Размер подсети CIDR", cidr_hosts),
    Family("DO-FAM-CHMOD", "devops", "do_linux", 2, "single", "Права доступа chmod", chmod_octal),
    Family("DO-FAM-SLO", "devops", "do_observe", 3, "single", "Бюджет простоя SLO", sla_downtime),
]
FAMILY_BY_CODE = {f.code: f for f in FAMILIES}
