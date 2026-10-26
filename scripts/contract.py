"""Check the reviewed OpenAPI contract; --write intentionally updates it."""

import sys
from pathlib import Path

import yaml
from app.main import app

path = Path("contracts/openapi.yaml")
schema = app.openapi()
if "--write" in sys.argv:
    path.parent.mkdir(exist_ok=True)
    path.write_text(yaml.safe_dump(schema, sort_keys=False), encoding="utf-8")
else:
    expected = yaml.safe_load(path.read_text(encoding="utf-8"))
    if expected != schema:
        raise SystemExit(
            "API differs from contracts/openapi.yaml. Review before updating the contract."
        )
print(f"OpenAPI contract verified: {len(schema['paths'])} paths.")
