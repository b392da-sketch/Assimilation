"""Personal evidence and local accusation exchanges."""

from dataclasses import dataclass

CONVERSATION_TICKS = 4


@dataclass(frozen=True)
class SuspicionReport:
    witness: str
    subject: str
    observed_at: int
    concern: int
    origin_event: int | None = None


@dataclass(frozen=True)
class Accusation:
    accuser: str
    report: SuspicionReport
    event_id: int
    expires_at: int


@dataclass(frozen=True)
class ExaminationRequest:
    examiner: str
    event_id: int
    expires_at: int


@dataclass(frozen=True)
class Reconsideration:
    origin_event: int
    response_event: int
    reduction: int


@dataclass(frozen=True)
class AccusationView:
    accusation: Accusation | None = None
    can_explain_cold: bool = False
    accuser_trust: int = 0
    examination_request: ExaminationRequest | None = None
    examiner_trust: int = 0
    confrontation: tuple[str, int, int] | None = None
    invitation: tuple[str, int] | None = None
    consent: tuple[str, int] | None = None
