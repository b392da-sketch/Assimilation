"""Semantic messages and private assessment of testimony."""

from dataclasses import dataclass, replace
from typing import Literal

from .allegations import SuspicionReport

MessageKind = Literal[
    "observation", "claim", "question", "answer", "doubt", "challenge",
    "proposal", "acceptance", "decline", "verification report",
    "suspicion report", "accusation", "explanation", "question evidence",
    "examination request", "examination consent", "examination refusal",
]
EVIDENCE_LIMIT = 12
MINIMUM_MARGIN = 20
QUESTION_TIMEOUT = 4
QUESTION_COOLDOWN = 8
VERIFICATION_TIMEOUT = 12
VERIFICATION_COOLDOWN = 18


@dataclass(frozen=True)
class FoodBelief:
    available: bool
    observed_at: int
    sources: tuple[str, ...]
    confidence: int
    source_event: int | None = None
    transmissions: tuple[int, ...] = ()


@dataclass(frozen=True)
class Message:
    kind: MessageKind
    topic: str
    content: FoodBelief | None = None
    reply_to: int | None = None
    reason: str | None = None
    suspicion: SuspicionReport | None = None


@dataclass(frozen=True)
class Verification:
    proposer: str
    proposal_id: int
    expires_at: int
    meeting_room: str
    acceptance_id: int | None = None
    result: FoodBelief | None = None


@dataclass(frozen=True)
class Evidence:
    claim: FoodBelief
    firsthand: bool = False

    @property
    def origin(self) -> int | tuple[str, int, bool]:
        claim = self.claim
        return claim.source_event if claim.source_event is not None else (
            claim.sources[0], claim.observed_at, claim.available,
        )


@dataclass(frozen=True)
class Assessment:
    available_score: int = 0
    unavailable_score: int = 0
    evidence_ids: tuple[int, ...] = ()
    belief: FoodBelief | None = None
    delivery_ids: tuple[int, ...] = ()

    @property
    def conflicted(self) -> bool:
        return bool(self.available_score and self.unavailable_score)

    @property
    def trace_ids(self) -> tuple[int, ...]:
        return tuple(sorted(set(self.evidence_ids + self.delivery_ids)))


def retain(ledger: list[Evidence], evidence: Evidence) -> None:
    for index, previous in enumerate(ledger):
        if previous.origin == evidence.origin:
            if (evidence.firsthand, evidence.claim.confidence) > (previous.firsthand, previous.claim.confidence):
                ledger[index] = evidence
            return
    ledger.append(evidence)
    ledger.sort(key=lambda item: (item.claim.observed_at, item.claim.source_event or 0))
    del ledger[:-EVIDENCE_LIMIT]


def assess(ledger: list[Evidence]) -> Assessment:
    firsthand = next((item for item in reversed(ledger) if item.firsthand), None)
    relevant = [
        item for item in ledger
        if firsthand is None or item.firsthand and item.origin == firsthand.origin
        or (item.claim.observed_at, item.claim.source_event or 0)
        > (firsthand.claim.observed_at, firsthand.claim.source_event or 0)
    ]
    available = min(100, sum(item.claim.confidence for item in relevant if item.claim.available))
    unavailable = min(100, sum(item.claim.confidence for item in relevant if not item.claim.available))
    margin = available - unavailable
    belief = None
    if abs(margin) >= MINIMUM_MARGIN:
        anchor = max(
            (item for item in relevant if item.claim.available == (margin > 0)),
            key=lambda item: (item.claim.confidence, item.claim.observed_at),
        )
        belief = replace(anchor.claim, confidence=abs(margin))
    return Assessment(
        available, unavailable,
        tuple(item.claim.source_event for item in relevant if item.claim.source_event is not None),
        belief,
        tuple(sorted({event_id for item in relevant for event_id in item.claim.transmissions})),
    )
