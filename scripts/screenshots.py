"""Capture product screenshots for the documentation and the presentation.

    pip install playwright httpx
    python scripts/screenshots.py [--base http://localhost:8080] [--out docs/img]

Uses the locally installed Google Chrome (no browser download). Runs against a freshly seeded
instance; afterwards reset demo data with `docker compose exec backend python -m app.seed --reset`
(opening an invitation changes its status to "viewed").
"""

import argparse
import time
from pathlib import Path

import httpx
from playwright.sync_api import Page, sync_playwright

PASSWORD = "demo12345"


def token(api: httpx.Client, email: str, password: str = PASSWORD) -> str:
    r = api.post("/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def throwaway_candidate(api: httpx.Client) -> str:
    email = f"screens{int(time.time())}@example.com"
    r = api.post("/auth/register", json={"email": email, "password": "screens123", "role": "candidate",
                                         "consent_processing": True, "first_name": "Ирина", "last_name": "Смирнова"})
    r.raise_for_status()
    t = api.post("/auth/verify-email", json={"email": email, "code": r.json()["dev_code"]}).json()["access_token"]
    api.put("/candidate/profile", headers={"Authorization": f"Bearer {t}"},
            json={"specialization_id": "backend", "declared_grade_id": "middle"}).raise_for_status()
    return t


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8080")
    ap.add_argument("--out", default="docs/img")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    api = httpx.Client(base_url=args.base + "/api", timeout=30)

    cand_t = token(api, "candidate@demo.ru")
    hr_t = token(api, "hr@demo.ru")
    ch = {"Authorization": f"Bearer {cand_t}"}
    eh = {"Authorization": f"Bearer {hr_t}"}
    result_id = api.get("/candidate/testing", headers=ch).json()["history"][0]["attempt_id"]
    inv_id = next(i["id"] for i in api.get("/candidate/invitations", headers=ch).json() if i["status"] == "sent")
    job = next(j for j in api.get("/employer/requirements", headers=eh).json() if j["title"] == "Python Backend Developer")
    matches = api.get(f"/employer/requirements/{job['id']}/matches", headers=eh).json()["items"]
    top_id = matches[0]["candidate_id"]
    runner_t = throwaway_candidate(api)
    attempt = api.post("/candidate/testing/start", headers={"Authorization": f"Bearer {runner_t}"},
                       json={"specialization_id": "backend", "target_grade": "middle"}).json()

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")

        def ctx(tok: str | None):
            c = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5, locale="ru-RU")
            if tok:
                c.add_init_script(f"localStorage.setItem('fsp_talent_token', '{tok}')")
            return c

        def shot(page: Page, path: str, name: str, full: bool = False, wait: str | None = None) -> None:
            page.goto(args.base + path)
            page.wait_for_load_state("networkidle")
            if wait:
                page.wait_for_selector(wait)
            page.wait_for_timeout(700)  # ring/bar transitions
            page.screenshot(path=str(out / f"{name}.png"), full_page=full)
            print("saved", name)

        anon = ctx(None).new_page()
        shot(anon, "/", "01-landing")

        cp = ctx(cand_t).new_page()
        shot(cp, "/candidate", "02-candidate-dashboard", wait=".ring")
        shot(cp, f"/candidate/results/{result_id}", "04-test-result", wait=".scale")
        shot(cp, "/candidate/fsp", "05-fsp", wait=".medal")
        shot(cp, f"/candidate/invitations/{inv_id}", "10-candidate-invitation", wait="text=Способ связи с работодателем")

        rp = ctx(runner_t).new_page()
        rp.goto(f"{args.base}/candidate/testing/{attempt['id']}")
        rp.wait_for_selector(".q-text")
        # show a question with options, one of them selected
        for _ in range(attempt["total"]):
            if rp.locator(".option").count():
                rp.locator(".option").nth(1).click()
                break
            rp.get_by_role("button", name="Далее").click()
        rp.wait_for_timeout(600)
        rp.screenshot(path=str(out / "03-test-runner.png"))
        print("saved 03-test-runner")

        ep = ctx(hr_t).new_page()
        shot(ep, "/employer", "06-employer-dashboard", wait=".stat")
        ep.goto(args.base + "/employer/requirements/new")
        ep.wait_for_selector("textarea")
        ep.locator("textarea").first.fill("Ищем Middle бэкенд-разработчика в команду платежей: Python, FastAPI, "
                                          "PostgreSQL, Docker, желательно Redis. Вилка 180 000 – 250 000 ₽, "
                                          "удалёнка, опыт от 2 лет.")
        ep.get_by_role("button", name="Разобрать описание").click()
        ep.wait_for_selector("text=Распознано")
        ep.wait_for_timeout(500)
        ep.screenshot(path=str(out / "07-need-form.png"))
        print("saved 07-need-form")
        shot(ep, f"/employer/requirements/{job['id']}", "08-matches", wait=".cand")
        # A vs B comparison
        compare_buttons = ep.locator("button[title='Сравнить']")
        compare_buttons.nth(0).click()
        compare_buttons.nth(2).click()
        ep.get_by_role("button", name="Почему A выше B?").click()
        ep.wait_for_selector(".modal")
        ep.wait_for_timeout(700)
        ep.screenshot(path=str(out / "09-compare.png"))
        print("saved 09-compare")
        shot(ep, f"/employer/candidates/{top_id}?requirement_id={job['id']}", "11-candidate-explanation",
             full=True, wait=".table")
        browser.close()


if __name__ == "__main__":
    main()
