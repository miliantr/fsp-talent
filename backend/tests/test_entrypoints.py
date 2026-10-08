"""Entry points of the backend and the error format for unknown routes."""

from tests.conftest import auth, register


def test_bare_backend_address_leads_to_the_api_docs(client):
    for path, target in (("/", "/api/docs"), ("/docs", "/api/docs"), ("/redoc", "/api/redoc"),
                         ("/openapi.json", "/api/openapi.json")):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 307 and r.headers["location"] == target, path
    assert client.get("/").status_code == 200  # the docs page itself


def test_api_index_lists_the_entry_points(client):
    for path in ("/api", "/api/"):
        r = client.get(path)
        assert r.status_code == 200
        assert r.json()["docs"] == "/api/docs" and r.json()["health"] == "/api/health"


def test_unknown_route_answers_in_the_common_error_format(client):
    r = client.get("/api/no-such-thing", headers={"Accept-Language": "en"})
    assert r.status_code == 404
    assert r.json() == {"code": "route_not_found",
                        "message": "There is no /api/no-such-thing in the API. See /api/docs for the endpoints",
                        "details": {"path": "/api/no-such-thing"}}
    assert client.get("/api/no-such-thing").json()["message"].startswith("Адреса /api/no-such-thing в API нет")


def test_wrong_method_is_reported(client):
    token = register(client, "wrong.method@example.com", "candidate")
    r = client.delete("/api/candidate/profile", headers=auth(token, "en"))
    assert r.status_code == 405 and r.json()["code"] == "method_not_allowed"
    assert r.json()["message"] == "Method DELETE is not allowed for this address"


def test_domain_404_keeps_its_own_message(client):
    # the mock FSP registry raises HTTPException with its own detail — it is kept
    r = client.get("/api/mock-fsp/v1/participants/FSP-NOPE")
    assert r.status_code == 404 and r.json()["message"] == "participant not found"
