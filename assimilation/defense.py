"""Local cues for immediate danger and audible requests for help."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DangerCue:
    source: str
    event_id: int


@dataclass(frozen=True)
class DistressCue:
    caller: str
    room: str
    tick: int
    event_id: int
