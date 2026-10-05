"""FSP registry integration.

`FSPRegistry` is the port; the platform depends only on it. Two adapters are provided:
  * MockFSPRegistry — reads a synthetic registry snapshot (JSON) in-process;
  * HttpFSPRegistry — calls a REST API with the same contract (the mock API is exposed by this
    backend at /api/mock-fsp/v1, so the HTTP adapter can be exercised end-to-end).
A real integration (FSP ID on Keycloak + achievements API) is another adapter of the same port.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import httpx

from app.core.config import get_settings

DATA_FILE = Path(__file__).parent / "mock_data" / "fsp_registry.json"


@dataclass
class RegistryAchievement:
    id: str
    event_name: str
    discipline: str
    level: str
    date: date
    place: int | None
    participants_total: int | None
    team_name: str | None
    role: str | None
    score: float | None
    specialization_hint: str | None
    certificate_url: str | None


@dataclass
class RegistryParticipant:
    fsp_id: str
    full_name: str
    email: str
    region: str | None
    sport_rank: str | None
    achievements: list[RegistryAchievement] = field(default_factory=list)

    def to_public_dict(self) -> dict:
        d = asdict(self)
        d.pop("email")
        for a in d["achievements"]:
            a["date"] = a["date"].isoformat()
        return d


class FSPRegistry(Protocol):
    source: str

    def get_participant(self, fsp_id: str) -> RegistryParticipant | None: ...

    def find_by_email(self, email: str) -> RegistryParticipant | None: ...


def _parse(raw: dict) -> RegistryParticipant:
    achs = [
        RegistryAchievement(**{**a, "date": date.fromisoformat(a["date"])})
        for a in raw.get("achievements", [])
    ]
    return RegistryParticipant(
        fsp_id=raw["fsp_id"], full_name=raw["full_name"], email=raw.get("email", ""),
        region=raw.get("region"), sport_rank=raw.get("sport_rank"), achievements=achs,
    )


class MockFSPRegistry:
    source = "mock"

    def __init__(self, path: Path = DATA_FILE):
        raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"participants": []}
        self._by_id = {p["fsp_id"].upper(): p for p in raw["participants"]}
        self._by_email = {p["email"].lower(): p for p in raw["participants"] if p.get("email")}

    def get_participant(self, fsp_id: str) -> RegistryParticipant | None:
        raw = self._by_id.get(fsp_id.strip().upper())
        return _parse(raw) if raw else None

    def find_by_email(self, email: str) -> RegistryParticipant | None:
        raw = self._by_email.get(email.strip().lower())
        return _parse(raw) if raw else None

    def raw_participant(self, fsp_id: str) -> dict | None:
        return self._by_id.get(fsp_id.strip().upper())

    def all_raw(self) -> list[dict]:
        return list(self._by_id.values())


class HttpFSPRegistry:
    """Adapter for a REST registry: GET /participants/{id}, GET /participants?email=."""

    source = "http"

    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: dict | None = None) -> dict | None:
        r = httpx.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def get_participant(self, fsp_id: str) -> RegistryParticipant | None:
        raw = self._get(f"/participants/{fsp_id}")
        return _parse(raw) if raw else None

    def find_by_email(self, email: str) -> RegistryParticipant | None:
        raw = self._get("/participants", {"email": email})
        return _parse(raw) if raw else None


@lru_cache
def get_mock_registry() -> MockFSPRegistry:
    return MockFSPRegistry()


def get_registry() -> FSPRegistry:
    s = get_settings()
    if s.fsp_registry_mode == "http":
        return HttpFSPRegistry(s.fsp_registry_url)
    return get_mock_registry()
