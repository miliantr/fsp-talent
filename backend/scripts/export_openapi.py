"""Write the OpenAPI spec to frontend/openapi.json (source of the generated TypeScript types)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

out = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"
out.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=1), encoding="utf-8")
print(f"OpenAPI written to {out}")
