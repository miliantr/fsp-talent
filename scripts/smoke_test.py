"""End-to-end smoke test against a running instance (default: docker-compose on :8080).

    python scripts/smoke_test.py [--base http://localhost:8080]

Walks the main demo scenario through the public HTTP API: candidate registration with e-mail
confirmation, survey, test (answered by a simulated strong candidate is impossible from outside, so
answers are picked at random and the lower-grade fallback is exercised), employer need, ranking,
explanation, invitation with salary, acceptance and contact disclosure.
"""

import argparse
import random
import sys
import time

import httpx


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8080")
    base = ap.parse_args().base.rstrip("/") + "/api"
    c = httpx.Client(base_url=base, timeout=30)
    ok = lambda r, code=200: (r.status_code == code) or sys.exit(f"{r.request.method} {r.request.url} -> {r.status_code} {r.text[:300]}")  # noqa: E731,E501

    assert c.get("/health").json()["status"] == "ok"
    email = f"smoke{int(time.time())}@example.com"
    r = c.post("/auth/register", json={"email": email, "password": "smoketest123", "role": "candidate",
                                       "consent_processing": True, "first_name": "Смоук", "last_name": "Тестов"})
    ok(r, 201)
    code = r.json()["dev_code"]
    r = c.post("/auth/verify-email", json={"email": email, "code": code})
    ok(r)
    cand = {"Authorization": f"Bearer {r.json()['access_token']}"}
    ok(c.put("/candidate/profile", headers=cand, json={
        "specialization_id": "backend", "declared_grade_id": "middle", "telegram": "@smoke",
        "skills": [{"slug": "python", "level": 4, "years": 3}, {"slug": "fastapi", "level": 4, "years": 2}]}))

    rng = random.Random(1)
    grade, result = "middle", None
    while True:
        r = c.post("/candidate/testing/start", headers=cand, json={"specialization_id": "backend", "target_grade": grade})
        ok(r, 201)
        att = r.json()
        for item in att["items"]:
            ans = [rng.randint(1, 50)] if item["qtype"] == "numeric" else [rng.randrange(len(item["options"]))]
            ok(c.post("/candidate/testing/answer", headers=cand,
                      json={"attempt_id": att["id"], "item_id": item["id"], "answer": ans}))
        result = c.post("/candidate/testing/finish", headers=cand, json={"attempt_id": att["id"]}).json()
        print(f"test {grade}: outcome={result['outcome']} score={result['scaled_score']}")
        if result["passed"] or grade == "junior":
            break
        grade = "junior"  # fallback to a lower grade is available immediately
    ok(c.put("/candidate/settings", headers=cand, json={"consent_publication": True}))
    cand_id = c.get("/candidate/profile", headers=cand).json()["id"]

    # a throwaway employer, so the demo accounts stay untouched
    emp_email = f"smoke-hr{int(time.time())}@example.com"
    r = c.post("/auth/register", json={"email": emp_email, "password": "smoketest123", "role": "employer",
                                       "consent_processing": True, "company_name": "Smoke Co"})
    ok(r, 201)
    r = c.post("/auth/verify-email", json={"email": emp_email, "code": r.json()["dev_code"]})
    ok(r)
    emp = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = c.post("/employer/requirements", headers=emp, json={
        "title": "Smoke Backend", "specialization_id": "backend", "grade_id": "middle", "is_public": True,
        "must_skills": ["python", "fastapi", "postgresql", "docker"], "salary_from": 180000, "salary_to": 250000})
    ok(r, 201)
    job_id = r.json()["id"]
    m = c.get(f"/employer/requirements/{job_id}/matches", headers=emp).json()
    top = m["items"][0]
    print(f"ranking: {m['total']} candidates, top {top['display_name']} {top['match']['percent']}%")
    assert top["match"]["reasons"] and top["match"]["components"]
    target = cand_id if result["passed"] else top["candidate_id"]
    d = c.get(f"/employer/candidates/{top['candidate_id']}", headers=emp, params={"requirement_id": job_id}).json()
    assert d["match"]["percent"] == top["match"]["percent"]

    if result["passed"]:
        r = c.post("/employer/invitations", headers=emp, json={
            "candidate_id": target, "job_id": job_id, "position_title": "Smoke Backend",
            "description": "Тестовое приглашение smoke-теста", "salary_from": 200000, "salary_to": 240000,
            "contact_method": "@hr"})
        ok(r, 201)
        inv = r.json()
        assert inv["contacts"] is None
        ok(c.post(f"/candidate/invitations/{inv['id']}/accept", headers=cand, json={}))
        d = c.get(f"/employer/candidates/{target}", headers=emp).json()
        assert d["contacts"] and d["contacts"]["email"] == email
        print("invitation accepted, contacts disclosed:", d["contacts"]["email"])
    else:
        # secondary scenario: the candidate applies to the published vacancy -> contacts are disclosed
        ok(c.post("/applications", headers=cand, json={"job_id": job_id, "cover_letter": "smoke"}), 201)
        apps = c.get("/employer/applications", headers=emp, params={"job_id": job_id}).json()
        assert apps and apps[0]["contacts"]["email"] == email
        print("application received, contacts disclosed:", apps[0]["contacts"]["email"])
    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
