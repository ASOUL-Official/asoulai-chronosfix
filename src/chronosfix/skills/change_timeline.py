from __future__ import annotations

from ..models import ChangeEvent


def build_timeline(events: list[ChangeEvent]) -> list[ChangeEvent]:
    return sorted(events, key=lambda item: (item.timestamp, item.kind, item.source))

