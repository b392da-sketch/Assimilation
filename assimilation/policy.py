"""Routine decisions over immutable local information."""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

Activity = Literal["eat", "rest", "work", "wait"]
VISIBLE_EXHAUSTION = 9


@dataclass(frozen=True)
class Room:
    name: str
    neighbors: tuple[str, ...]
    activities: tuple[Activity, ...] = ()
    outdoors: bool = False


@dataclass(frozen=True)
class Intent:
    action: str
    destination: str | None = None
    recipient: str | None = None
    subject: str | None = None


@dataclass(frozen=True)
class FoodBelief:
    available: bool
    observed_at: int
    sources: tuple[str, ...]
    confidence: int
    source_event: int | None = None


@dataclass(frozen=True)
class Disposition:
    cooperativeness: int = 0
    caution: int = 0

    def __post_init__(self) -> None:
        if not all(type(value) is int and -5 <= value <= 5
                   for value in (self.cooperativeness, self.caution)):
            raise ValueError("Disposition traits must be integers from -5 to 5.")


@dataclass(frozen=True)
class LocalPeer:
    name: str
    visibly_exhausted: bool
    contained: bool
    available_for_generator_help: bool
    concern: int
    help_expectation: int
    help_evidence_ids: tuple[int, ...]
    witnessed_at: int | None
    examination: str | None


@dataclass(frozen=True)
class DecisionView:
    tick: int
    room: str
    duty_room: str
    map_rooms: tuple[Room, ...]
    generator_room: str | None
    peers: tuple[LocalPeer, ...]
    disposition: Disposition
    hunger: int
    fatigue: int
    meal_threshold: int
    rest_threshold: int
    goal: Activity | None
    sleeping: bool
    working: bool
    food_belief: FoodBelief | None
    food_recipients: tuple[str, ...]
    warning_options: tuple[tuple[str, str], ...]
    felt_cold: bool
    checked_generator: bool
    already_requested_help: bool
    requester: str | None
    requester_trust: int
    generator_trust_bonus: int
    commitment_reliability: int
    requester_evidence_ids: tuple[int, ...]
    help_accepted: bool
    encounter_target: str | None
    can_start_encounter: bool
    known_converts: frozenset[str]


@dataclass(frozen=True)
class Evaluation:
    option: str
    reason: str
    intent: Intent | None = None
    evidence_event_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class Decision:
    intent: Intent
    goal: Activity | None
    evaluations: tuple[Evaluation, ...]


def first_step(rooms: dict[str, Room], start: str, matches: Callable[[Room], bool]) -> str | None:
    queue = deque([(start, None)])
    visited = {start}
    while queue:
        name, step = queue.popleft()
        room = rooms[name]
        if matches(room):
            return step
        for neighbor in room.neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, step or neighbor))
    return None


def toward(
    rooms: dict[str, Room], start: str, activity: Activity, target: str | None = None,
) -> Intent | None:
    def matches(room: Room) -> bool:
        return activity in room.activities and (target is None or target == room.name)

    if matches(rooms[start]):
        return Intent(activity)
    step = first_step(rooms, start, matches)
    return Intent("move", step) if step else None


def power_response(view: DecisionView, rooms: dict[str, Room]) -> Intent | None:
    generator = view.generator_room
    if generator is None:
        return None
    requester = view.requester
    if requester:
        if view.room == generator:
            return Intent("refuel")
        step = first_step(rooms, view.room, lambda room: room.name == generator)
        return Intent("move", step) if step else Intent("decline_help", recipient=requester)
    if not view.felt_cold or view.checked_generator:
        return None
    if view.room == generator:
        return Intent("refuel")
    if view.duty_room != generator:
        return None
    if not view.already_requested_help:
        peer = max(
            (peer for peer in view.peers if peer.available_for_generator_help),
            key=lambda peer: peer.help_expectation, default=None,
        )
        if peer:
            return Intent("request_help", recipient=peer.name)
    step = first_step(rooms, view.room, lambda room: room.name == generator)
    return Intent("move", step) if step else None


def immediate_action(
    view: DecisionView, rooms: dict[str, Room], evaluations: list[Evaluation],
) -> Intent | None:
    if view.sleeping:
        return record(evaluations, "sleep", "A sleep block is active.", Intent("sleep"))
    record(evaluations, "sleep", "No sleep block is active.")
    if view.encounter_target:
        return record(evaluations, "continue encounter", "An encounter already has a target.",
                      Intent("assimilate", recipient=view.encounter_target))
    record(evaluations, "continue encounter", "No pending encounter.")
    for peer in view.peers:
        if (peer.examination == "anomaly" and not peer.contained
                and peer.visibly_exhausted and view.fatigue < VISIBLE_EXHAUSTION):
            return record(evaluations, "contain", "Local evidence and fatigue permit containment.",
                          Intent("contain", subject=peer.name))
    record(evaluations, "contain", "No local peer met the evidence and fatigue conditions.")
    exits = rooms[view.room].neighbors
    caution = view.disposition.caution
    threshold = 32 - (caution + 5) * 4 // 10
    concern = max((peer.concern for peer in view.peers if not peer.contained), default=0)
    evidence = f"Local concern {concern}. Avoidance threshold {threshold} (caution {caution})."
    if exits and concern >= threshold:
        return record(evaluations, "avoid", evidence,
                      Intent("move", exits[0]))
    record(evaluations, "avoid", evidence if exits else evidence + " No exit is known.")
    for peer in view.peers:
        if (peer.witnessed_at is not None and peer.examination is None and not peer.contained
                and view.tick >= peer.witnessed_at + 2):
            return record(evaluations, "examine", "Local firsthand evidence is at least two ticks old.",
                          Intent("examine", subject=peer.name))
    record(evaluations, "examine", "No local peer met the firsthand evidence conditions.")
    if view.generator_room and view.requester and not view.help_accepted:
        cooperation = 2 * view.disposition.cooperativeness
        hunger_cost = 2 * max(0, view.hunger - view.meal_threshold)
        fatigue_cost = 3 * max(0, view.fatigue - view.rest_threshold + 2)
        score = (view.requester_trust + view.generator_trust_bonus + view.commitment_reliability
                 + cooperation - hunger_cost - fatigue_cost)
        willing = score >= 65 and view.fatigue < view.rest_threshold
        reason = (
            f"Help score {score} (minimum 65): trust {view.requester_trust}, "
            f"generator experience {view.generator_trust_bonus}, cooperation bias {cooperation}, "
            f"commitment reliability {view.commitment_reliability}, hunger cost {hunger_cost}, "
            f"fatigue cost {fatigue_cost}. "
            f"Fatigue {view.fatigue} must be below {view.rest_threshold}."
        )
        return record(
            evaluations, "generator response", reason,
            Intent("accept_help" if willing else "decline_help", recipient=view.requester),
            view.requester_evidence_ids,
        )
    response = power_response(view, rooms)
    if response and view.requester:
        reason = "An accepted request guides the generator response."
    elif response and response.action == "request_help":
        eligible = [peer for peer in view.peers if peer.available_for_generator_help]
        scores = ", ".join(f"{peer.name} {peer.help_expectation}" for peer in eligible)
        evidence_ids = tuple(sorted({event_id for peer in eligible for event_id in peer.help_evidence_ids}))
        reason = f"Selected {response.recipient} by local willingness to help. Scores were {scores}."
        return record(evaluations, "generator response", reason, response, evidence_ids)
    elif response:
        reason = "Local cold and the agent's location or duty permit a generator response."
    else:
        reason = "No feasible response to local cold or a help request."
    return record(evaluations, "generator response", reason, response)


def record(
    evaluations: list[Evaluation], option: str, reason: str, intent: Intent | None = None,
    evidence_event_ids: tuple[int, ...] = (),
) -> Intent | None:
    evaluations.append(Evaluation(option, reason, intent, evidence_event_ids))
    return intent


def choose(view: DecisionView) -> Decision:
    rooms = {room.name: room for room in view.map_rooms}
    evaluations: list[Evaluation] = []
    action = immediate_action(view, rooms, evaluations)
    if action:
        return Decision(action, view.goal, tuple(evaluations))

    belief = view.food_belief
    food_ruled_out = belief is not None and not belief.available and belief.confidence >= 60
    needs = [(view.fatigue - view.rest_threshold, "rest")]
    if not food_ruled_out:
        needs.append((view.hunger - view.meal_threshold, "eat"))
    else:
        record(evaluations, "eat", f"Food believed unavailable (confidence {belief.confidence}).")

    ranked = sorted(needs, key=lambda need: (need[1] != view.goal, -need[0]))
    for urgency, activity in ranked:
        target = toward(rooms, view.room, activity) if urgency >= 0 else None
        reason = f"Need minus threshold is {urgency}."
        if activity == view.goal:
            reason += " Existing goal takes precedence."
        if urgency >= 0 and target is None:
            reason += " No reachable location."
        record(evaluations, activity, reason, target)
        if target:
            return Decision(target, activity, tuple(evaluations))

    action = None
    reason = "The controller is unavailable or there is no private pair."
    if view.can_start_encounter and len(view.peers) == 1:
        target = view.peers[0].name
        if target not in view.known_converts:
            action = Intent("assimilate", recipient=target)
            reason = "The controller is ready and perceives one eligible local peer."
        else:
            reason = "The controller remembers converting this peer."
    record(evaluations, "start encounter", reason, action)
    if action:
        return Decision(action, None, tuple(evaluations))

    if view.warning_options:
        recipient, subject = view.warning_options[0]
        intent = Intent("warn", recipient=recipient, subject=subject)
        record(evaluations, "warn", "The speaker has not sent this firsthand report to the local recipient.", intent)
        return Decision(intent, None, tuple(evaluations))
    record(evaluations, "warn", "No eligible local recipient for firsthand concerns.")
    if food_ruled_out and view.food_recipients:
        intent = Intent("tell", recipient=view.food_recipients[0])
        record(evaluations, "tell", "A confident shortage belief can be shared locally.", intent)
        return Decision(intent, None, tuple(evaluations))
    record(evaluations, "tell", "No confident shortage belief or eligible recipient.")
    if view.working:
        intent = Intent("continue_work")
        record(evaluations, "work", "The current work block is active.", intent)
    else:
        intent = toward(rooms, view.room, "work", view.duty_room)
        reason = "The assigned duty is reachable." if intent else "No route to the assigned duty."
        record(evaluations, "work", reason, intent)
    if intent is None:
        intent = Intent("wait")
        record(evaluations, "wait", "No earlier option produced an intent.", intent)
    return Decision(intent, None, tuple(evaluations))
