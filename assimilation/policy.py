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


@dataclass(frozen=True)
class LocalPeer:
    name: str
    visibly_exhausted: bool
    contained: bool
    available_for_generator_help: bool
    concern: int
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
    help_accepted: bool
    encounter_target: str | None
    can_start_encounter: bool
    known_converts: frozenset[str]


@dataclass(frozen=True)
class Decision:
    intent: Intent
    goal: Activity | None


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
        if not view.help_accepted:
            willing = view.fatigue < view.rest_threshold and view.requester_trust >= 65
            return Intent("accept_help" if willing else "decline_help", recipient=requester)
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
        for peer in view.peers:
            if peer.available_for_generator_help:
                return Intent("request_help", recipient=peer.name)
    step = first_step(rooms, view.room, lambda room: room.name == generator)
    return Intent("move", step) if step else None


def immediate_action(view: DecisionView, rooms: dict[str, Room]) -> Intent | None:
    if view.sleeping:
        return Intent("sleep")
    if view.encounter_target:
        return Intent("assimilate", recipient=view.encounter_target)
    for peer in view.peers:
        if (peer.examination == "anomaly" and not peer.contained
                and peer.visibly_exhausted and view.fatigue < VISIBLE_EXHAUSTION):
            return Intent("contain", subject=peer.name)
    exits = rooms[view.room].neighbors
    if exits and any(peer.concern >= 30 for peer in view.peers if not peer.contained):
        return Intent("move", exits[0])
    for peer in view.peers:
        if (peer.witnessed_at is not None and peer.examination is None and not peer.contained
                and view.tick >= peer.witnessed_at + 2):
            return Intent("examine", subject=peer.name)
    return power_response(view, rooms)


def choose(view: DecisionView) -> Decision:
    rooms = {room.name: room for room in view.map_rooms}
    action = immediate_action(view, rooms)
    if action:
        return Decision(action, view.goal)

    belief = view.food_belief
    food_ruled_out = belief is not None and not belief.available and belief.confidence >= 60
    needs = [(view.fatigue - view.rest_threshold, "rest")]
    if not food_ruled_out:
        needs.append((view.hunger - view.meal_threshold, "eat"))

    ranked = sorted(needs, key=lambda need: (need[1] != view.goal, -need[0]))
    for urgency, activity in ranked:
        if urgency >= 0:
            target = toward(rooms, view.room, activity)
            if target:
                return Decision(target, activity)

    if view.can_start_encounter and len(view.peers) == 1:
        target = view.peers[0].name
        if target not in view.known_converts:
            return Decision(Intent("assimilate", recipient=target), None)

    if view.warning_options:
        recipient, subject = view.warning_options[0]
        return Decision(Intent("warn", recipient=recipient, subject=subject), None)
    if food_ruled_out and view.food_recipients:
        return Decision(Intent("tell", recipient=view.food_recipients[0]), None)
    if view.working:
        return Decision(Intent("continue_work"), None)
    return Decision(toward(rooms, view.room, "work", view.duty_room) or Intent("wait"), None)
