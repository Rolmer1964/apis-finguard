"""Instância única de Jinja2 + filtro `tojson` (usado por report.html.j2)."""

import json as _json
from pathlib import Path

from fastapi.templating import Jinja2Templates
from markupsafe import Markup

_BASE = Path(__file__).parent

templates = Jinja2Templates(directory=str(_BASE / "templates"))
templates.env.filters["tojson"] = lambda v, indent=None: Markup(
    _json.dumps(v, ensure_ascii=False, indent=indent)
)
