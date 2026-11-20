import json
import os
from pathlib import Path

from pydantic import TypeAdapter

from .schemas import Alert


def load_demo_alerts() -> tuple[Alert, ...]:
    """Load and validate only explicitly synthetic alerts; fail on invalid data."""
    if os.environ.get("BLUEGUARD_MODE", "demo") != "demo":
        raise RuntimeError("Only BLUEGUARD_MODE=demo is supported by v0.2.0")
    path = Path(os.environ.get("BLUEGUARD_ALERTS_FILE", str(Path(__file__).resolve().parent.parent / "demo" / "alerts.json")))
    raw = json.loads(path.read_text(encoding="utf-8"))
    alerts = TypeAdapter(list[Alert]).validate_python(raw)
    ids = [alert.id for alert in alerts]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate alert ids in fixture")
    return tuple(sorted(alerts, key=lambda alert: alert.detected_at, reverse=True))
