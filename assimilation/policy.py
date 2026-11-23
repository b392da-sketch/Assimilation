"""Routine decisions over immutable local information."""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from .allegations import AccusationView
from .defense import DangerCue, DistressCue
from .communication import Assessment, FoodBelief, Verification

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
    food_assessment: Assessment
    food_question_target: str | None
    food_reply_target: str | None
    food_objection: tuple[str, int] | None
    food_proposal: tuple[str, int] | None
    food_verification: Verification | None
    verification_partner_local: bool
    verification_trust: int
    verification_wait: int | None
    waiting_for_food_reply: bool
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
    health: int
    danger: DangerCue | None
    distress: DistressCue | None
    accusation_view: AccusationView


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


def respond_to_distress(view: DecisionView) -> Decision | None:
    cue = view.distress
    if cue is None or cue.tick != view.tick or view.health <= 30:
        return None
    if view.fatigue >= view.rest_threshold or view.disposition.cooperativeness < view.disposition.caution:
        return None
    room = next(room for room in view.map_rooms if room.name == view.room)
    if cue.room not in room.neighbors:
        return None
    intent = Intent("answer_distress", destination=cue.room)
    return Decision(intent, view.goal, (Evaluation(
        "answer distress", "A nearby call was heard, and capacity and disposition favor helping.",
        intent, (cue.event_id,),
    ),))


def defensive_decision(view: DecisionView, exits: tuple[str, ...]) -> Decision:
    cue = view.danger
    assert cue is not None
    escape = Intent("escape_danger", destination=exits[0]) if exits else None
    resistance = Intent("resist_danger") if view.health > 30 else None
    call = Intent("call_for_help")
    mobile = view.health > 30 or view.tick % 2 == 0
    if escape and mobile and (view.disposition.caution >= 0 or view.fatigue < VISIBLE_EXHAUSTION):
        selected = escape
        reason = "A known exit and current mobility favor leaving."
    elif resistance and (not exits or view.disposition.cooperativeness < 0):
        selected = resistance
        reason = "Limited escape options and current capacity favor resisting."
    else:
        selected = call
        reason = "Current mobility, fatigue or disposition favors calling for help."
    evidence = (cue.event_id,)
    options = (
        Evaluation("escape", "A neighboring exit is known." if escape else "No known exit.", escape, evidence),
        Evaluation("resist", "Current health permits an attempt." if resistance else "Health limits resistance.",
                   resistance, evidence),
        Evaluation("call for help", "A call may reach someone nearby.", call, evidence),
        Evaluation("defensive response", reason, selected, evidence),
    )
    return Decision(selected, view.goal, options)


def accusation_action(view: DecisionView, evaluations: list[Evaluation]) -> Intent | None:
    social = view.accusation_view
    if social.examination_request:
        request = social.examination_request
        cooperation = 2 * view.disposition.cooperativeness
        score = social.examiner_trust + cooperation - max(0, view.disposition.caution)
        willing = score >= 60 and view.fatigue < view.rest_threshold
        reason = (
            f"Consent score {score}. Trust {social.examiner_trust}, cooperation {cooperation}, "
            f"caution {view.disposition.caution}. Fatigue {view.fatigue} must be below "
            f"{view.rest_threshold}."
        )
        action = "consent_examination" if willing else "refuse_examination"
        return record(evaluations, "answer examination request", reason,
                      Intent(action, recipient=request.examiner), (request.event_id,))
    if social.accusation:
        accusation = social.accusation
        willing = social.accuser_trust + view.disposition.cooperativeness >= 50
        explain = social.can_explain_cold and willing and view.fatigue < view.rest_threshold
        reason = (
            f"Own cold-distress evidence: {social.can_explain_cold}. "
            f"Trust {social.accuser_trust}, cooperativeness {view.disposition.cooperativeness}, "
            f"fatigue {view.fatigue}, rest threshold {view.rest_threshold}."
        )
        action = "explain_accusation" if explain else "question_accusation"
        return record(evaluations, "respond to accusation", reason,
                      Intent(action, recipient=accusation.accuser), (accusation.event_id,))
    if social.consent:
        peer, consent = social.consent
        return record(evaluations, "cooperative examination", "The local inhabitant consented.",
                      Intent("cooperative_exam", subject=peer), (consent,))
    if social.confrontation:
        peer, evidence, concern = social.confrontation
        return record(evaluations, "confront", f"Firsthand concern reached {concern}.",
                      Intent("accuse", subject=peer), (evidence,))
    if social.invitation:
        peer, evidence = social.invitation
        return record(evaluations, "request examination", "Concern remains after the confrontation.",
                      Intent("request_examination", subject=peer), (evidence,))
    return None


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
                and peer.visibly_exhausted and view.fatigue < VISIBLE_EXHAUSTION
                and view.disposition.cooperativeness >= -2):
            return record(evaluations, "contain", "The anomaly, physical conditions and willingness permit restraint.",
                          Intent("contain", subject=peer.name))
    record(evaluations, "contain", "The evidence, physical conditions or willingness did not support restraint.")
    exits = rooms[view.room].neighbors
    caution = view.disposition.caution
    threshold = 32 - (caution + 5) * 4 // 10
    concern = max((peer.concern for peer in view.peers if not peer.contained), default=0)
    evidence = f"Local concern {concern}. Avoidance threshold {threshold} (caution {caution})."
    if exits and concern >= threshold:
        return record(evaluations, "avoid", evidence,
                      Intent("move", exits[0]))
    record(evaluations, "avoid", evidence if exits else evidence + " No exit is known.")
    social = accusation_action(view, evaluations)
    if social:
        return social
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
    if view.danger and not view.sleeping:
        return defensive_decision(view, rooms[view.room].neighbors)
    action = immediate_action(view, rooms, evaluations)
    if action:
        return Decision(action, view.goal, tuple(evaluations))

    assessment = view.food_assessment
    plan = view.food_verification
    if plan:
        if plan.acceptance_id is None and view.verification_partner_local:
            cooperation = 2 * view.disposition.cooperativeness
            hunger_cost = 2 * max(0, view.hunger - view.meal_threshold)
            score = view.verification_trust + cooperation - hunger_cost
            reachable = toward(rooms, view.room, "eat") is not None
            willing = score >= 65 and view.fatigue < view.rest_threshold and reachable
            intent = Intent("accept_food_check" if willing else "decline_food_check",
                            recipient=plan.proposer)
            reason = (
                f"Verification score {score} (minimum 65): trust {view.verification_trust}, "
                f"cooperation {cooperation}, hunger cost {hunger_cost}. "
                f"Fatigue {view.fatigue} must be below {view.rest_threshold}. "
                f"Galley reachable: {reachable}."
            )
            record(evaluations, "respond to proposal", reason, intent, (plan.proposal_id,))
            return Decision(intent, view.goal, tuple(evaluations))
        if plan.result and view.verification_partner_local:
            intent = Intent("report_food_check", recipient=plan.proposer)
            record(evaluations, "report verification", "Share the firsthand check on reunion.",
                   intent, (plan.acceptance_id, plan.result.source_event))
            return Decision(intent, view.goal, tuple(evaluations))
        if plan.result and view.room != plan.meeting_room:
            step = first_step(rooms, view.room, lambda room: room.name == plan.meeting_room)
            if step:
                intent = Intent("move", step)
                record(evaluations, "return from verification", "Return to the proposed meeting room.",
                       intent, (plan.acceptance_id, plan.result.source_event))
                return Decision(intent, view.goal, tuple(evaluations))
        if plan.acceptance_id and plan.result is None:
            target = toward(rooms, view.room, "eat")
            if target:
                intent = Intent("check_food") if target.action == "eat" else target
                record(evaluations, "verify stock", "Follow the accepted plan to check the galley.",
                       intent, (plan.acceptance_id,))
                return Decision(intent, view.goal, tuple(evaluations))
    if view.verification_wait and view.hunger < 12 and view.fatigue < view.rest_threshold:
        intent = Intent("wait")
        record(evaluations, "await verification", "A peer accepted the plan and needs time to report.",
               intent, (view.verification_wait,))
        return Decision(intent, view.goal, tuple(evaluations))
    if view.food_reply_target:
        intent = Intent("answer_food", recipient=view.food_reply_target)
        record(evaluations, "answer", "A local peer asked about food.",
               intent, assessment.trace_ids)
        return Decision(intent, view.goal, tuple(evaluations))
    if view.waiting_for_food_reply and not assessment.belief:
        intent = Intent("wait")
        record(evaluations, "wait for answer", "The question was asked one tick ago.",
               intent, assessment.trace_ids)
        return Decision(intent, view.goal, tuple(evaluations))
    if (assessment.conflicted and view.food_question_target and not assessment.belief
            and view.hunger >= view.meal_threshold):
        intent = Intent("ask_food", recipient=view.food_question_target)
        reason = (f"Food evidence conflicts. Available support {assessment.available_score}, "
                  f"unavailable support {assessment.unavailable_score}.")
        record(evaluations, "ask", reason, intent, assessment.trace_ids)
        return Decision(intent, view.goal, tuple(evaluations))

    if view.food_objection:
        peer, delivery = view.food_objection
        intent = Intent("challenge_food" if assessment.belief else "doubt_food", recipient=peer)
        reason = (
            f"Available support {assessment.available_score}. "
            f"Unavailable support {assessment.unavailable_score}."
        )
        record(evaluations, "object to report", reason, intent, (*assessment.trace_ids, delivery))
        return Decision(intent, view.goal, tuple(evaluations))
    if view.food_proposal:
        peer, objection_id = view.food_proposal
        intent = Intent("propose_food_check", recipient=peer)
        record(evaluations, "propose verification", "The disagreement is unresolved locally.",
               intent, (objection_id,))
        return Decision(intent, view.goal, tuple(evaluations))

    belief = view.food_belief
    food_ruled_out = belief is not None and not belief.available and belief.confidence >= 60
    needs = [(view.fatigue - view.rest_threshold, "rest")]
    if not food_ruled_out:
        needs.append((view.hunger - view.meal_threshold, "eat"))
    else:
        record(evaluations, "eat", f"Food believed unavailable (confidence {belief.confidence}).",
               evidence_event_ids=assessment.trace_ids)

    ranked = sorted(needs, key=lambda need: (need[1] != view.goal, -need[0]))
    for urgency, activity in ranked:
        target = toward(rooms, view.room, activity) if urgency >= 0 else None
        reason = f"Need minus threshold is {urgency}."
        if activity == view.goal:
            reason += " Existing goal takes precedence."
        if urgency >= 0 and target is None:
            reason += " No reachable location."
        if activity == "eat" and assessment.conflicted:
            reason += (f" Conflicting food evidence: {assessment.available_score} available, "
                       f"{assessment.unavailable_score} unavailable.")
        record(evaluations, activity, reason, target,
               assessment.trace_ids if activity == "eat" else ())
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
