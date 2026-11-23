"""Bounded, firsthand interpersonal evidence and domain-specific expectations."""

from dataclasses import dataclass, field
from typing import Literal

ExperienceKind = Literal[
    "generator_assistance", "commitment_fulfilled", "commitment_withdrawn",
    "help_declined", "food_report_supported", "food_report_contradicted",
]
EVIDENCE_LIMIT = 12


@dataclass(frozen=True)
class Experience:
    kind: ExperienceKind
    event_id: int
    basis: Literal["firsthand", "verified testimony"] = "firsthand"
    related_event_id: int | None = None
    origin_event_id: int | None = None


@dataclass
class Relationship:
    trust: int
    familiarity: int = 0
    last_contact_event: int | None = None
    generator_assists: int = 0
    last_generator_assist_event: int | None = None
    commitment_reliability: int = 0
    willingness_to_help: int = 0
    food_report_credibility: int = 0
    evidence: list[Experience] = field(default_factory=list)
    latest_by_kind: dict[str, int] = field(default_factory=dict)
    verified_food_origin_event: int = 0

    @property
    def generator_trust_bonus(self) -> int:
        return min(15, self.generator_assists * 5)

    def learn(self, experience: Experience, caution: int) -> None:
        # Evidence arrives in event order. Retain a watermark per category
        # so replayed evidence stays suppressed after the detail rolls off.
        kind = experience.kind
        if experience.event_id <= self.latest_by_kind.get(kind, 0):
            return
        self.latest_by_kind[kind] = experience.event_id
        self.evidence.append(experience)
        if len(self.evidence) > EVIDENCE_LIMIT:
            del self.evidence[0]
        if kind == "generator_assistance":
            self.generator_assists += 1
            self.last_generator_assist_event = experience.event_id
            self.willingness_to_help = min(15, self.willingness_to_help + 3)
        elif kind == "commitment_fulfilled":
            self.commitment_reliability = min(15, self.commitment_reliability + 5)
        elif kind == "commitment_withdrawn":
            self.commitment_reliability = max(-15, self.commitment_reliability - 5 - max(0, caution))
        elif kind == "help_declined":
            self.willingness_to_help = max(-15, self.willingness_to_help - 2)
        elif kind == "food_report_supported":
            self.food_report_credibility = min(15, self.food_report_credibility + 4)
        elif kind == "food_report_contradicted":
            self.food_report_credibility = max(-15, self.food_report_credibility - 4 - max(0, caution))
