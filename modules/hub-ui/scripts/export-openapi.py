"""Export frontend domain tags while retaining backend documentation labels."""

import json
import re

from app.main import create_app

schema = create_app().openapi()
for route, item in schema["paths"].items():
    for method, operation in item.items():
        if method not in {"get", "put", "post", "delete", "options", "head", "patch", "trace"}:
            continue
        tags = operation.get("tags", [])
        if not tags:
            raise ValueError(f"{method.upper()} {route}: declare a domain tag in the backend")
        # Secondary labels (e.g. Users/Admin) describe actions within the first domain.
        tag = re.sub(r"[^a-z0-9]+", "-", tags[0].lower()).strip("-")
        if tag in {"common", "index"}:
            tag = f"api-{tag}"
        operation["tags"] = [tag]
print(json.dumps(schema))
