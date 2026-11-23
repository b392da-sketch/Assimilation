"""Station state, local perception, routine decisions and action resolution."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from random import Random
from typing import Literal

from .communication import (
    QUESTION_COOLDOWN, QUESTION_TIMEOUT, VERIFICATION_COOLDOWN, VERIFICATION_TIMEOUT,
    Assessment, Evidence, Message, Verification, assess, retain,
)
from .policy import (
    Activity, Decision, DecisionView, Disposition, FoodBelief, Intent, LocalPeer, Room,
    VISIBLE_EXHAUSTION, choose,
)

from .relationships import Experience, Relationship

MAX_NEED = 12
MINUTES_PER_TICK = 10
TICKS_PER_HOUR = 60 // MINUTES_PER_TICK
STARVATION_TICKS = 3 * 24 * TICKS_PER_HOUR
COLD_INJURY_TICKS = 3 * 60 // MINUTES_PER_TICK
SLEEP_TICKS = 7 * TICKS_PER_HOUR
WORK_TICKS = TICKS_PER_HOUR


@dataclass(frozen=True)
class PowerConfig:
    generator_room: str
    main_fuel: int
    backup_fuel: int
    reserve_fuel: int
    radio_room: str | None = None

    def __post_init__(self) -> None:
        if min(self.main_fuel, self.backup_fuel, self.reserve_fuel) < 0:
            raise ValueError("Fuel quantities must be nonnegative")

    @property
    def initial_source(self) -> Literal["main", "backup", "off"]:
        if self.main_fuel:
            return "main"
        if self.backup_fuel:
            return "backup"
        return "off"


@dataclass
class PowerState:
    main_fuel: int
    backup_fuel: int
    reserve_fuel: int
    source: Literal["main", "backup", "off"] = "off"
    refuel_worker: str | None = None


@dataclass(frozen=True)
class Station:
    rooms: tuple[Room, ...]
    quarters: str
    initial_food: int = 420
    outdoor_temperature: int = -24
    power: PowerConfig | None = None

    def __post_init__(self) -> None:
        names = {room.name for room in self.rooms}
        if len(names) != len(self.rooms) or self.quarters not in names:
            raise ValueError("Station needs unique room names and a quarters room")
        if self.initial_food < 0:
            raise ValueError("Initial food must be nonnegative")
        if self.power and self.power.generator_room not in names:
            raise ValueError("The generator must occupy a station room")
        if self.power and self.power.radio_room is not None and self.power.radio_room not in names:
            raise ValueError("The radio must occupy a station room")
        for room in self.rooms:
            if room.name in room.neighbors or not names.issuperset(room.neighbors):
                raise ValueError(f"Invalid exits for {room.name}")


DEFAULT_STATION = Station(
    rooms=(
        Room("quarters", ("commons",), ("rest",)),
        Room("commons", ("quarters", "galley", "lab", "infirmary", "radio", "airlock")),
        Room("galley", ("commons", "stores"), ("eat",)),
        Room("stores", ("galley",)),
        Room("lab", ("commons",), ("work",)),
        Room("infirmary", ("commons",), ("work",)),
        Room("radio", ("commons",), ("work",)),
        Room("airlock", ("commons", "generator"), outdoors=True),
        Room("generator", ("airlock",), ("work",)),
    ),
    quarters="quarters",
    power=PowerConfig("generator", main_fuel=1600, backup_fuel=4, reserve_fuel=80, radio_room="radio"),
)


@dataclass(frozen=True)
class Observation:
    tick: int
    actor: str
    action: str
    room: str
    testimony: FoodBelief | None = None
    concern: SuspicionReport | None = None
    subject: str | None = None
    message: Message | None = None


@dataclass(frozen=True)
class SuspicionReport:
    witness: str
    subject: str
    observed_at: int
    concern: int


@dataclass(frozen=True)
class HeardFoodReport:
    event_id: int
    belief: FoodBelief


@dataclass
class Organism:
    identity: int
    parent: int | None
    body: str
    recovery_until: int = 0
    converted: set[str] = field(default_factory=set)


@dataclass
class Encounter:
    actor: str
    target: str
    room: str
    started_at: int
    start_event: int
    continued: bool = False


@dataclass(frozen=True)
class Event:
    tick: int
    actor: str
    action: str
    room: str
    observations: tuple[tuple[str, Observation], ...]
    destination: str | None = None
    recipient: str | None = None
    testimony: FoodBelief | None = None
    subject: str | None = None
    concern: SuspicionReport | None = None
    causes: tuple[int, ...] = ()
    reason: str | None = None
    message: Message | None = None


@dataclass
class Inhabitant:
    name: str
    room: str
    duty_room: str
    hunger: int
    fatigue: int
    meal_threshold: int
    rest_threshold: int
    disposition: Disposition = field(default_factory=Disposition)
    memory: deque[Observation] = field(default_factory=lambda: deque(maxlen=32))
    food_belief: FoodBelief | None = None
    food_evidence: list[Evidence] = field(default_factory=list)
    food_assessment: Assessment = field(default_factory=Assessment)
    pending_food_questions: dict[str, tuple[int, int]] = field(default_factory=dict)
    asked_food_peers: dict[str, tuple[int, tuple[int, ...]]] = field(default_factory=dict)
    food_objections: dict[str, tuple[int | tuple[str, int, bool], int]] = field(default_factory=dict)
    proposed_food_checks: dict[str, tuple[int, int]] = field(default_factory=dict)
    food_verification: Verification | None = None
    verification_wait: tuple[int, int] | None = None
    offered_verification: tuple[int, int] | None = None
    last_food_question: tuple[str, int] | None = None
    relationships: dict[str, Relationship] = field(default_factory=dict)
    goal: Activity | None = None
    felt_cold: bool = False
    checked_generator: bool = False
    suspicion: dict[str, int] = field(default_factory=dict)
    witnessed_concerns: dict[str, SuspicionReport] = field(default_factory=dict)
    heard_concerns: dict[tuple[str, str], SuspicionReport] = field(default_factory=dict)
    sent_concerns: dict[tuple[str, str], int] = field(default_factory=dict)
    help_requested_by: str | None = None
    help_accepted: bool = False
    help_commitment_event: int | None = None
    pending_food_reports: dict[str, HeardFoodReport] = field(default_factory=dict)
    requested_help_from: set[str] = field(default_factory=set)
    examinations: dict[str, Literal["clear", "inconclusive", "anomaly"]] = field(default_factory=dict)
    containment_attempt: tuple[str, int] | None = None
    contained: bool = False
    showed_cold_distress: bool = False
    health: int = 100
    hungry_ticks: int = 0
    cold_ticks: int = 0
    hunger_clock: int = 0
    awake_clock: int = 0
    sleep_until: int = 0
    work_until: int = 0

    @property
    def alive(self) -> bool:
        return self.health > 0

    def concern_about(self, subject: str) -> int:
        if self.examinations.get(subject) == "clear":
            return 0
        reported = (
            report.concern * self.relationships[report.witness].trust // 100
            for report in self.heard_concerns.values()
            if report.subject == subject
        )
        return max(self.suspicion.get(subject, 0), max(reported, default=0))


@dataclass(frozen=True)
class DecisionRecord:
    tick: int
    decision: Decision
    resolved: bool
    event_ids: tuple[int, ...]


class Simulation:
    STEP_SECONDS = MINUTES_PER_TICK * 60

    def __init__(
        self, seed: int, station: Station = DEFAULT_STATION, *, hidden_organism: bool = False,
        dispositions: Mapping[str, Disposition] | None = None,
    ) -> None:
        self.seed = seed
        self.station = station
        self.rooms = {room.name: room for room in station.rooms}
        self.tick = 0
        self.food = station.initial_food
        self.history: list[Event] = []
        self.last_intents: dict[str, Intent] = {}
        self.decision_records: dict[str, deque[DecisionRecord]] = defaultdict(lambda: deque(maxlen=32))
        self.resolved_actions = 0
        self.last_power_event: int | None = None
        self.refuel_start_event: int | None = None
        self.refuel_finish_event: int | None = None
        config = station.power
        self.power = (
            PowerState(config.main_fuel, config.backup_fuel, config.reserve_fuel, config.initial_source)
            if config else None
        )
        self.random = Random(seed)
        names = (
            "Anika", "Bram", "Cleo", "Dev", "Edda", "Farid",
            "Greta", "Hana", "Ivo", "Jules", "Kiran", "Lena",
        )
        overrides = dict(dispositions or {})
        if unknown := overrides.keys() - set(names):
            raise ValueError(f"Unknown disposition names: {', '.join(sorted(unknown))}")
        profiles = Random(seed).sample(
            [Disposition(cooperation, caution) for cooperation in range(-5, 6)
             for caution in range(-5, 6)], len(names),
        )
        duties = [room.name for room in station.rooms if "work" in room.activities]
        self.inhabitants = [
            Inhabitant(
                name=name,
                room=station.quarters,
                duty_room=self.random.choice(duties or [station.quarters]),
                hunger=self.random.randrange(7),
                fatigue=self.random.randrange(7),
                meal_threshold=self.random.randrange(6, 10),
                rest_threshold=self.random.randrange(7, 11),
                disposition=overrides.get(name, profile),
            )
            for name, profile in zip(names, profiles)
        ]
        if config:
            self.inhabitants[0].duty_room = config.generator_room
        for agent in self.inhabitants:
            agent.relationships = {
                name: Relationship(self.random.randrange(40, 86))
                for name in names if name != agent.name
            }
        self.agents_by_name = {agent.name: agent for agent in self.inhabitants}
        self.shared_reports: dict[tuple[str, str], bool] = {}
        self.organisms: dict[str, Organism] = {}
        self.encounters: dict[str, Encounter] = {}
        if hidden_organism:
            body = self.random.choice(self.inhabitants).name
            self.organisms[body] = Organism(1, None, body)

    @property
    def elapsed_seconds(self) -> int:
        return self.tick * self.STEP_SECONDS

    def advance_ticks(self, ticks: int) -> None:
        if ticks < 0:
            raise ValueError("Tick count must be nonnegative.")
        for _ in range(ticks):
            self.advance()

    def advance(self) -> None:
        self.tick += 1
        self.advance_power()
        for inhabitant in self.inhabitants:
            if not inhabitant.alive:
                continue
            for source, (_, expires) in tuple(inhabitant.pending_food_questions.items()):
                if self.tick >= expires:
                    del inhabitant.pending_food_questions[source]
            if inhabitant.food_verification and self.tick >= inhabitant.food_verification.expires_at:
                inhabitant.food_verification = None
            if inhabitant.verification_wait and self.tick >= inhabitant.verification_wait[1]:
                inhabitant.verification_wait = None
            if inhabitant.offered_verification and self.tick >= inhabitant.offered_verification[1]:
                inhabitant.offered_verification = None
            inhabitant.hunger_clock += 1
            if inhabitant.hunger_clock == TICKS_PER_HOUR:
                inhabitant.hunger_clock = 0
                inhabitant.hunger = min(MAX_NEED, inhabitant.hunger + 1)
            outdoors = self.rooms[inhabitant.room].outdoors
            cold = self.station.outdoor_temperature < 0
            if not outdoors:
                inhabitant.felt_cold = cold and self.power is not None and self.power.source == "off"
                if not inhabitant.felt_cold:
                    inhabitant.showed_cold_distress = False
                    inhabitant.checked_generator = False
                    inhabitant.requested_help_from.clear()
                    inhabitant.help_requested_by = None
                    inhabitant.help_accepted = False
                    inhabitant.help_commitment_event = None
            exposure = cold if outdoors else inhabitant.felt_cold
            if inhabitant.sleep_until and self.tick >= inhabitant.sleep_until:
                inhabitant.sleep_until = 0
                inhabitant.fatigue = 0
                inhabitant.awake_clock = 0
                self.record(inhabitant, "sleep_completed", inhabitant.room)
            elif not inhabitant.sleep_until:
                inhabitant.awake_clock += 1
                exertion = inhabitant.awake_clock % (2 * TICKS_PER_HOUR) == 0
                cold_fatigue = exposure and (inhabitant.cold_ticks + 1) % TICKS_PER_HOUR == 0
                inhabitant.fatigue = min(MAX_NEED, inhabitant.fatigue + exertion + cold_fatigue)
            self.advance_health(inhabitant, exposure)

        plans = [
            (agent, self.plan(agent)) for agent in self.inhabitants
            if agent.alive and not agent.contained
        ]
        self.last_intents = {agent.name: decision.intent for agent, decision in plans}
        self.random.shuffle(plans)
        for agent, decision in plans:
            first_event = len(self.history) + 1
            resolved = self.resolve(agent, decision.intent)
            self.resolved_actions += resolved
            self.decision_records[agent.name].append(DecisionRecord(
                self.tick, decision, resolved, tuple(range(first_event, len(self.history) + 1)),
            ))
        self.finish_encounters()

    def advance_health(self, agent: Inhabitant, exposed: bool) -> None:
        agent.hungry_ticks = agent.hungry_ticks + 1 if agent.hunger == MAX_NEED else 0
        agent.cold_ticks = agent.cold_ticks + 1 if exposed else 0
        starvation_damage = (
            agent.hungry_ticks >= STARVATION_TICKS and agent.hungry_ticks % (2 * TICKS_PER_HOUR) == 0
        )
        cold_damage = agent.cold_ticks >= COLD_INJURY_TICKS and agent.cold_ticks % 3 == 0
        damage = int(starvation_damage) + 2 * int(cold_damage)
        previous = agent.health
        if damage:
            agent.health = max(0, agent.health - damage)
        elif not exposed and agent.hunger < MAX_NEED:
            agent.health = min(100, agent.health + 1)
        if previous > 30 >= agent.health > 0:
            self.record(agent, "health_impaired", agent.room)
        elif not agent.alive:
            self.record(
                agent, "organism_died" if agent.name in self.organisms else "inhabitant_died",
                agent.room, visible_as="death",
                reason="Prolonged deprivation or cold exhausted the body's viability.",
            )

    def advance_power(self) -> None:
        power = self.power
        if power is None:
            return
        previous = power.source
        if power.main_fuel:
            power.source = "main"
            power.main_fuel -= 1
        elif power.backup_fuel:
            power.source = "backup"
            power.backup_fuel -= 1
        else:
            power.source = "off"
        if power.source != previous:
            reason = {
                "main": "The main supply has fuel again.",
                "backup": "Main fuel is exhausted and backup fuel is available.",
                "off": "Both supplies are out of fuel.",
            }[power.source]
            parent = self.refuel_finish_event if power.source == "main" else self.last_power_event
            self.history.append(Event(
                self.tick, "station", f"power_{power.source}",
                self.station.power.generator_room, (),
                causes=(parent,) if parent is not None else (), reason=reason,
            ))
            self.last_power_event = len(self.history)

    def perceive(self, agent: Inhabitant) -> DecisionView:
        generator = self.station.power.generator_room if self.station.power else None
        peers = self.others_present(agent)
        observations = []
        for peer in peers:
            witnessed = agent.witnessed_concerns.get(peer.name)
            relationship = agent.relationships[peer.name]
            observations.append(LocalPeer(
                name=peer.name,
                visibly_exhausted=peer.fatigue >= VISIBLE_EXHAUSTION,
                contained=peer.contained,
                available_for_generator_help=peer.duty_room != generator and not peer.sleep_until,
                concern=agent.concern_about(peer.name),
                help_expectation=relationship.willingness_to_help,
                help_evidence_ids=tuple(
                    item.event_id for item in relationship.evidence
                    if item.kind in ("generator_assistance", "help_declined")
                ),
                witnessed_at=witnessed.observed_at if witnessed else None,
                examination=agent.examinations.get(peer.name),
            ))
        organism = self.organisms.get(agent.name)
        encounter = self.encounters.get(agent.name)
        requester = agent.help_requested_by
        relationship = agent.relationships[requester] if requester else None
        available_peers = [peer for peer in peers if not peer.sleep_until and not peer.contained]
        available_names = {peer.name for peer in available_peers}
        objections = []
        proposals = []
        for name, report in agent.pending_food_reports.items():
            if name not in available_names or not agent.food_assessment.conflicted:
                continue
            belief = agent.food_belief
            if belief is not None and belief.available == report.belief.available:
                continue
            previous = agent.food_objections.get(name)
            if previous is None or previous[0] != Evidence(report.belief).origin:
                objections.append((name, report.event_id))
            elif self.can_propose_food_check(agent, name, previous[1]):
                proposals.append((name, previous[1]))
        verification = agent.food_verification
        if verification and self.tick >= verification.expires_at:
            verification = None
        question_target = max(
            (peer for peer in available_peers if self.can_question_food(agent, peer.name)),
            key=lambda peer: (agent.relationships[peer.name].trust
                              + agent.relationships[peer.name].food_report_credibility),
            default=None,
        ) if agent.food_assessment.conflicted else None
        reply_target = next((peer.name for peer in available_peers
                             if peer.name in agent.pending_food_questions
                             and self.tick < agent.pending_food_questions[peer.name][1]), None)
        question = agent.last_food_question
        return DecisionView(
            tick=self.tick,
            room=agent.room,
            duty_room=agent.duty_room,
            map_rooms=self.station.rooms,
            generator_room=generator,
            peers=tuple(observations),
            disposition=agent.disposition,
            hunger=agent.hunger,
            fatigue=agent.fatigue,
            meal_threshold=agent.meal_threshold,
            rest_threshold=agent.rest_threshold,
            goal=agent.goal,
            sleeping=bool(agent.sleep_until),
            working=self.tick < agent.work_until,
            food_belief=agent.food_belief,
            food_assessment=agent.food_assessment,
            food_question_target=question_target.name if question_target else None,
            food_reply_target=reply_target,
            food_objection=next(iter(objections), None),
            food_proposal=next(iter(proposals), None),
            food_verification=verification,
            verification_partner_local=bool(verification and verification.proposer in available_names),
            verification_trust=agent.relationships[verification.proposer].trust if verification else 0,
            verification_wait=(
                agent.verification_wait[0]
                if agent.verification_wait and self.tick < agent.verification_wait[1] else None
            ),
            waiting_for_food_reply=bool(
                question and question[1] == self.tick - 1
                and any(peer.name == question[0] for peer in available_peers)
            ),
            food_recipients=tuple(peer.name for peer in peers if self.can_share(agent, peer)),
            warning_options=tuple(
                (peer.name, report.subject)
                for report in agent.witnessed_concerns.values()
                for peer in peers
                if self.can_warn(agent, peer, report)
            ),
            felt_cold=agent.felt_cold,
            checked_generator=agent.checked_generator,
            already_requested_help=bool(agent.requested_help_from),
            requester=requester,
            requester_trust=relationship.trust if relationship else 0,
            generator_trust_bonus=relationship.generator_trust_bonus if relationship else 0,
            commitment_reliability=relationship.commitment_reliability if relationship else 0,
            requester_evidence_ids=tuple(
                item.event_id for item in relationship.evidence
                if item.kind in ("generator_assistance", "commitment_fulfilled", "commitment_withdrawn")
            ) if relationship else (),
            help_accepted=agent.help_accepted,
            encounter_target=encounter.target if encounter else None,
            can_start_encounter=organism is not None and self.tick >= organism.recovery_until,
            known_converts=frozenset(organism.converted) if organism else frozenset(),
        )

    def decide(self, agent: Inhabitant) -> Intent:
        return self.plan(agent).intent

    def plan(self, agent: Inhabitant) -> Decision:
        decision = choose(self.perceive(agent))
        agent.goal = decision.goal
        return decision

    def can_share(self, agent: Inhabitant, peer: Inhabitant) -> bool:
        belief = agent.food_belief
        return (
            belief is not None
            and peer.alive
            and not peer.sleep_until
            and agent.room == peer.room
            and peer.name not in belief.sources
            and peer.name != agent.name
            and self.shared_reports.get((agent.name, peer.name)) != belief.available
        )

    def can_warn(self, agent: Inhabitant, peer: Inhabitant, report: SuspicionReport) -> bool:
        previous = agent.sent_concerns.get((peer.name, report.subject), -1)
        return (
            agent.room == peer.room
            and not peer.sleep_until
            and peer.name not in (agent.name, report.subject)
            and previous < report.observed_at
        )

    def warn(self, agent: Inhabitant, intent: Intent) -> bool:
        peer = self.agents_by_name.get(intent.recipient)
        report = agent.witnessed_concerns.get(intent.subject)
        if peer is None or report is None or not self.can_warn(agent, peer, report):
            return False
        agent.sent_concerns[peer.name, report.subject] = report.observed_at
        peer.heard_concerns[agent.name, report.subject] = report
        self.record(
            agent, "warn", agent.room, recipient=peer.name, subject=report.subject,
            concern=report,
        )
        return True

    def outgoing_food_claim(self, agent: Inhabitant) -> FoodBelief | None:
        belief = agent.food_belief
        if belief is None:
            return None
        origin = Evidence(belief).origin
        return next((item.claim for item in agent.food_evidence if item.origin == origin), belief)

    def update_food_evidence(self, agent: Inhabitant, evidence: Evidence) -> None:
        retain(agent.food_evidence, evidence)
        agent.food_assessment = assess(agent.food_evidence)
        agent.food_belief = agent.food_assessment.belief

    def deliver_food_message(
        self, agent: Inhabitant, peer: Inhabitant, action: str, message: Message,
    ) -> bool:
        belief = message.content
        reason = message.reason
        event_id = len(self.history) + 1
        if belief is not None:
            relationship = peer.relationships[agent.name]
            credibility = max(0, min(100, relationship.trust + relationship.food_report_credibility))
            report = FoodBelief(
                belief.available, belief.observed_at, (*belief.sources, peer.name),
                belief.confidence * credibility // 100, belief.source_event,
                (*belief.transmissions, event_id),
            )
            self.update_food_evidence(peer, Evidence(report))
            result = peer.food_assessment
            reason = (
                f"Recipient applied credibility {credibility} to this report "
                f"for weight {report.confidence}. Support is {result.available_score} for "
                f"available and {result.unavailable_score} for unavailable."
            )
            peer.pending_food_reports[agent.name] = HeardFoodReport(event_id, belief)

        parent = (belief.transmissions[-1] if belief.transmissions else belief.source_event) if belief else None
        causes = tuple(dict.fromkeys(reference for reference in (message.reply_to, parent) if reference))
        if message.kind == "question":
            causes = agent.food_assessment.trace_ids
        self.record(agent, action, agent.room, recipient=peer.name, testimony=belief,
                    message=message, reason=reason, causes=causes)
        return True

    def tell(self, agent: Inhabitant, peer: Inhabitant) -> bool:
        belief = self.outgoing_food_claim(agent)
        if belief is None or not self.can_share(agent, peer):
            return False
        self.shared_reports[agent.name, peer.name] = belief.available
        kind = "observation" if len(belief.sources) == 1 else "claim"
        return self.deliver_food_message(agent, peer, "tell", Message(kind, "food", belief))

    def can_question_food(self, agent: Inhabitant, peer: str) -> bool:
        previous = agent.asked_food_peers.get(peer)
        return previous is None or (
            self.tick >= previous[0] + QUESTION_COOLDOWN
            and agent.food_assessment.evidence_ids != previous[1]
        )

    def communicate_about_food(self, agent: Inhabitant, intent: Intent) -> bool:
        peer = self.agents_by_name.get(intent.recipient)
        if (peer is None or peer is agent or peer.room != agent.room
                or not peer.alive or peer.sleep_until):
            return False
        if intent.action == "ask_food":
            pending = peer.pending_food_questions.get(agent.name)
            if not self.can_question_food(agent, peer.name) or pending and self.tick < pending[1]:
                return False
            agent.asked_food_peers[peer.name] = (self.tick, agent.food_assessment.evidence_ids)
            agent.last_food_question = (peer.name, self.tick)
            peer.pending_food_questions[agent.name] = (len(self.history) + 1, self.tick + QUESTION_TIMEOUT)
            message = Message("question", "food")
        elif intent.action == "answer_food":
            question = agent.pending_food_questions.pop(peer.name, None)
            if question is None or self.tick >= question[1]:
                return False
            belief = self.outgoing_food_claim(agent)
            if belief is not None and peer.name in belief.sources:
                belief = None
            message = Message("answer", "food", belief, reply_to=question[0])
        else:
            heard = agent.pending_food_reports.get(peer.name)
            if heard is None or not agent.food_assessment.conflicted:
                return False
            previous = agent.food_objections.get(peer.name)
            origin = Evidence(heard.belief).origin
            if previous and previous[0] == origin:
                return False
            belief = agent.food_belief
            explanation = (
                f"Available support {agent.food_assessment.available_score}. "
                f"Unavailable support {agent.food_assessment.unavailable_score}."
            )
            if intent.action == "challenge_food":
                if belief is None or belief.available == heard.belief.available:
                    return False
                counterclaim = self.outgoing_food_claim(agent)
                if counterclaim is not None and peer.name in counterclaim.sources:
                    counterclaim = None
                message = Message("challenge", "food", counterclaim, reply_to=heard.event_id, reason=explanation)
            else:
                if belief is not None:
                    return False
                message = Message("doubt", "food", reply_to=heard.event_id, reason=explanation)
            agent.food_objections[peer.name] = (origin, len(self.history) + 1)
        return self.deliver_food_message(agent, peer, intent.action, message)

    def coordinate_food_check(self, agent: Inhabitant, intent: Intent) -> bool:
        action = intent.action
        plan = agent.food_verification
        if action == "check_food":
            if (plan is None or plan.acceptance_id is None or plan.result is not None
                    or self.tick >= plan.expires_at or "eat" not in self.rooms[agent.room].activities):
                return False
            self.record(agent, action, agent.room, causes=(plan.acceptance_id,))
            agent.food_verification = replace(plan, result=self.history[-1].message.content)
            return True

        peer = self.agents_by_name.get(intent.recipient)
        if (peer is None or peer is agent or peer.room != agent.room
                or not peer.alive or peer.sleep_until or peer.contained):
            return False
        if action == "propose_food_check":
            objection = agent.food_objections.get(peer.name)
            report = agent.pending_food_reports.get(peer.name)
            if (objection is None or report is None or not agent.food_assessment.conflicted
                    or Evidence(report.belief).origin != objection[0]
                    or not self.can_propose_food_check(agent, peer.name, objection[1])):
                return False
            agent.proposed_food_checks[peer.name] = (objection[1], self.tick)
            if peer.food_verification and self.tick < peer.food_verification.expires_at:
                return False
            agent.offered_verification = (len(self.history) + 1, self.tick + VERIFICATION_TIMEOUT)
            peer.food_verification = Verification(
                agent.name, len(self.history) + 1, self.tick + VERIFICATION_TIMEOUT, agent.room,
            )
            return self.deliver_food_message(
                agent, peer, action, Message("proposal", "food", reply_to=objection[1],
                                             reason="Propose a firsthand stock check."),
            )
        if plan is None or plan.proposer != peer.name or self.tick >= plan.expires_at:
            return False
        if action == "report_food_check":
            if plan.result is None:
                return False
            agent.food_verification = None
            if peer.verification_wait and peer.verification_wait[0] == plan.acceptance_id:
                peer.verification_wait = None
            if peer.offered_verification and peer.offered_verification[0] == plan.proposal_id:
                peer.offered_verification = None
            return self.deliver_food_message(
                agent, peer, action, Message("verification report", "food", plan.result,
                                             reply_to=plan.acceptance_id),
            )
        if plan.acceptance_id is not None:
            return False
        accepted = action == "accept_food_check"
        agent.food_verification = replace(plan, acceptance_id=len(self.history) + 1) if accepted else None
        if accepted:
            peer.verification_wait = (len(self.history) + 1, min(plan.expires_at, self.tick + 6))
        elif peer.offered_verification and peer.offered_verification[0] == plan.proposal_id:
            peer.offered_verification = None
        return self.deliver_food_message(
            agent, peer, action, Message("acceptance" if accepted else "decline", "food",
                                         reply_to=plan.proposal_id),
        )

    def can_propose_food_check(self, agent: Inhabitant, peer: str, objection_id: int) -> bool:
        if agent.offered_verification and self.tick < agent.offered_verification[1]:
            return False
        previous = agent.proposed_food_checks.get(peer)
        return previous is None or (
            previous[0] != objection_id and self.tick >= previous[1] + VERIFICATION_COOLDOWN
        )

    def resolve(self, agent: Inhabitant, intent: Intent) -> bool:
        if agent.contained or not agent.alive:
            return False
        if agent.sleep_until:
            return intent.action == "sleep"
        origin = self.rooms[agent.room]
        action = intent.action
        destination = intent.destination
        if action == "move":
            if destination not in origin.neighbors or (agent.health <= 30 and self.tick % 2):
                return False
            agent.room = destination
            agent.work_until = 0
            agent.containment_attempt = None
            for peer in self.inhabitants:
                if peer.containment_attempt and peer.containment_attempt[0] == agent.name:
                    peer.containment_attempt = None
        elif action == "wait":
            return True
        elif action == "continue_work":
            return self.tick < agent.work_until
        elif action == "tell":
            peer = self.agents_by_name.get(intent.recipient)
            return peer is not None and self.tell(agent, peer)
        elif action in ("ask_food", "answer_food", "doubt_food", "challenge_food"):
            return self.communicate_about_food(agent, intent)
        elif action in ("propose_food_check", "accept_food_check", "decline_food_check",
                        "report_food_check", "check_food"):
            return self.coordinate_food_check(agent, intent)
        elif action == "warn":
            return self.warn(agent, intent)
        elif action == "request_help":
            peer = self.agents_by_name.get(intent.recipient)
            if (peer is None or peer is agent or not peer.alive or peer.sleep_until
                    or peer.room != agent.room
                    or not agent.felt_cold or peer.name in agent.requested_help_from):
                return False
            agent.requested_help_from.add(peer.name)
            if peer.help_requested_by is not None:
                return False
            peer.help_requested_by = agent.name
            self.record(agent, "request_help", agent.room, recipient=peer.name)
            return True
        elif action in ("accept_help", "decline_help"):
            if agent.help_requested_by is None or agent.help_requested_by != intent.recipient:
                return False
            if action == "accept_help" and agent.help_accepted:
                return False
            commitment = agent.help_commitment_event
            agent.help_accepted = action == "accept_help"
            self.record(agent, action, agent.room, recipient=intent.recipient,
                        causes=(commitment,) if commitment else ())
            event_id = len(self.history)
            if agent.help_accepted:
                agent.help_commitment_event = event_id
            else:
                requester = self.agents_by_name[intent.recipient]
                if self.observed_event(requester.name, event_id):
                    witnessed_commitment = (
                        commitment if commitment and self.observed_event(requester.name, commitment)
                        else None
                    )
                    kind = "commitment_withdrawn" if witnessed_commitment else "help_declined"
                    requester.relationships[agent.name].learn(
                        Experience(kind, event_id, related_event_id=witnessed_commitment),
                        requester.disposition.caution,
                    )
                agent.help_requested_by = None
                agent.help_commitment_event = None
            return True
        elif action == "refuel":
            return self.refuel(agent)
        elif action == "assimilate":
            return self.attempt_assimilation(agent, intent.recipient)
        elif action in ("examine", "contain"):
            return self.resolve_investigation(agent, intent)
        elif action not in origin.activities:
            return False
        elif action == "eat":
            agent.goal = None
            if self.food == 0:
                self.record(agent, "found_no_food", origin.name)
                return False
            self.food -= 1
            agent.hunger = 0
            agent.hunger_clock = 0
            agent.hungry_ticks = 0
        elif action == "rest":
            agent.goal = None
            shivering = (
                agent.felt_cold and agent.fatigue == MAX_NEED and not agent.showed_cold_distress
            )
            agent.sleep_until = self.tick + SLEEP_TICKS
            agent.work_until = 0
            if shivering:
                agent.showed_cold_distress = True
                self.record(agent, action, origin.name, visible_as="uneasy_encounter")
                return True
        elif action == "work":
            if self.tick < agent.work_until:
                return False
            agent.work_until = self.tick + WORK_TICKS
            if self.station.power and origin.name == self.station.power.radio_room:
                action = "radio_contact" if self.power.source != "off" else "radio_unpowered"

        self.record(agent, action, origin.name, destination)
        return True

    def resolve_investigation(self, agent: Inhabitant, intent: Intent) -> bool:
        subject = self.agents_by_name.get(intent.subject)
        if (subject is None or subject is agent or not subject.alive or subject.contained
                or subject.room != agent.room
                or subject.name not in agent.witnessed_concerns):
            return False
        if intent.action == "examine":
            report = agent.witnessed_concerns[subject.name]
            if subject.name in agent.examinations or self.tick < report.observed_at + 2:
                return False
            organism = self.organisms.get(subject.name)
            if subject.felt_cold or subject.fatigue == MAX_NEED:
                result = "inconclusive"
            elif organism and 0 < organism.recovery_until and self.tick <= organism.recovery_until + 4:
                result = "anomaly"
            else:
                result = "clear"
            agent.examinations[subject.name] = result
            if result == "clear":
                agent.suspicion.pop(subject.name, None)
                agent.witnessed_concerns.pop(subject.name, None)
            self.record(
                agent, f"examination_{result}",
                agent.room, recipient=agent.name, subject=subject.name,
            )
            return True
        if (agent.examinations.get(subject.name) != "anomaly"
                or not subject.fatigue >= VISIBLE_EXHAUSTION > agent.fatigue):
            return False
        attempt = agent.containment_attempt
        if attempt != (subject.name, self.tick - 1):
            agent.containment_attempt = (subject.name, self.tick)
            self.record(agent, "containment_started", agent.room, subject=subject.name)
            return True
        agent.containment_attempt = None
        subject.contained = True
        self.record(agent, "contained", agent.room, subject=subject.name)
        return True

    def others_present(self, agent: Inhabitant) -> list[Inhabitant]:
        return [
            peer for peer in self.inhabitants
            if peer is not agent and peer.alive and peer.room == agent.room
        ]

    def attempt_assimilation(self, agent: Inhabitant, target: str | None) -> bool:
        organism = self.organisms.get(agent.name)
        if organism is None or self.tick < organism.recovery_until:
            return False
        others = self.others_present(agent)
        if len(others) != 1 or others[0].name != target or others[0].contained:
            return False
        encounter = self.encounters.get(agent.name)
        if encounter:
            if target != encounter.target or self.tick != encounter.started_at + 1:
                return False
            encounter.continued = True
            return True
        self.record(
            agent, "assimilation_started", agent.room, subject=target, visible_as="uneasy_encounter",
            reason="The organism attempted conversion while alone with one inhabitant.",
        )
        self.encounters[agent.name] = Encounter(agent.name, others[0].name, agent.room, self.tick,
                                                len(self.history))
        return True

    def finish_encounters(self) -> None:
        for name, encounter in tuple(self.encounters.items()):
            actor = self.agents_by_name[name]
            target = self.agents_by_name[encounter.target]
            alone = (
                actor.alive and target.alive and not actor.contained and not target.contained
                and actor.room == encounter.room and self.others_present(actor) == [target]
            )
            if alone and encounter.started_at == self.tick:
                continue
            del self.encounters[name]
            organism = self.organisms[name]
            organism.recovery_until = self.tick + 3
            if alone and encounter.continued and target.name not in self.organisms:
                organism.converted.add(target.name)
                offspring = Organism(
                    len(self.organisms) + 1, organism.identity, target.name, self.tick + 3,
                )
                offspring.converted.add(name)
                self.organisms[target.name] = offspring
                target.memory.clear()
                target.food_belief = None
                target.food_evidence.clear()
                target.food_assessment = Assessment()
                target.pending_food_questions.clear()
                target.asked_food_peers.clear()
                target.food_objections.clear()
                target.proposed_food_checks.clear()
                target.food_verification = None
                target.verification_wait = None
                target.offered_verification = None
                target.last_food_question = None
                target.suspicion.clear()
                target.witnessed_concerns.clear()
                target.heard_concerns.clear()
                target.sent_concerns.clear()
                target.examinations.clear()
                target.containment_attempt = None
                target.help_requested_by = None
                target.help_accepted = False
                target.requested_help_from.clear()
                target.help_commitment_event = None
                target.pending_food_reports.clear()
                target.relationships = {
                    peer: Relationship(relationship.trust)
                    for peer, relationship in target.relationships.items()
                }
                target.goal = None
                self.history.append(Event(self.tick, name, "assimilation_completed", actor.room, (),
                                          subject=target.name, causes=(encounter.start_event,),
                                          reason="The pair remained alone and conversion continued."))
            else:
                if not alone:
                    reason = "The pair no longer met the location, privacy, or containment requirements."
                elif not encounter.continued:
                    reason = "The next conversion action did not resolve."
                else:
                    reason = "The target already had an organism controller."
                self.history.append(Event(self.tick, name, "assimilation_interrupted", encounter.room,
                                          (), subject=target.name, causes=(encounter.start_event,),
                                          reason=reason))

    def refuel(self, agent: Inhabitant) -> bool:
        power = self.power
        if power is None or agent.room != self.station.power.generator_room:
            return False
        if power.main_fuel or not power.reserve_fuel:
            agent.checked_generator = True
            agent.help_requested_by = None
            agent.help_accepted = False
            agent.help_commitment_event = None
            self.record(agent, "generator_checked", agent.room)
            return False
        if power.refuel_worker is None:
            power.refuel_worker = agent.name
            parent = self.last_power_event
            self.record(
                agent, "refuel_started", agent.room,
                causes=(parent,) if parent is not None else (),
                reason="The main supply was empty and reserve fuel was available.",
            )
            self.refuel_start_event = len(self.history)
            return True
        worker = self.agents_by_name[power.refuel_worker]
        action = "refuel_completed" if worker is agent else "refuel_assisted"
        power.main_fuel = power.reserve_fuel
        power.reserve_fuel = 0
        power.refuel_worker = None
        parent = self.refuel_start_event
        self.record(
            agent, action, agent.room, causes=(parent,) if parent is not None else (),
            reason="The second refueling action transferred reserve fuel to the main supply.",
        )
        self.refuel_finish_event = len(self.history)
        witnesses = {name for name, _ in self.history[-1].observations}
        if worker is not agent and worker.name in witnesses:
            worker.relationships[agent.name].learn(
                Experience("generator_assistance", self.refuel_finish_event, related_event_id=parent),
                worker.disposition.caution,
            )
        for contributor in ((worker, agent) if worker is not agent else (agent,)):
            if contributor.name not in witnesses:
                continue
            requester = contributor.help_requested_by
            commitment = contributor.help_commitment_event
            if commitment and requester in witnesses and self.observed_event(requester, commitment):
                recipient = self.agents_by_name[requester]
                recipient.relationships[contributor.name].learn(
                    Experience("commitment_fulfilled", self.refuel_finish_event,
                               related_event_id=commitment),
                    recipient.disposition.caution,
                )
            if contributor is agent or commitment:
                contributor.help_requested_by = None
                contributor.help_accepted = False
                contributor.help_commitment_event = None
        return True

    def observed_event(self, name: str, event_id: int) -> bool:
        return any(observer == name for observer, _ in self.history[event_id - 1].observations)

    def verify_food_reports(self, observer: Inhabitant, available: bool, event_id: int) -> None:
        for source, report in observer.pending_food_reports.items():
            belief = report.belief
            # Stock may run out after a truthful positive report.
            if belief.available and not available:
                continue
            relationship = observer.relationships[source]
            origin_event = belief.source_event
            if origin_event is None or origin_event <= relationship.verified_food_origin_event:
                continue
            relationship.verified_food_origin_event = origin_event
            kind = "food_report_supported" if belief.available == available else "food_report_contradicted"
            relationship.learn(
                Experience(kind, event_id, "verified testimony", report.event_id, origin_event),
                observer.disposition.caution,
            )
        observer.pending_food_reports.clear()

    def record(
        self, agent: Inhabitant, action: str, room: str, destination: str | None = None,
        *, recipient: str | None = None, testimony: FoodBelief | None = None,
        subject: str | None = None, visible_as: str | None = None,
        concern: SuspicionReport | None = None,
        causes: tuple[int, ...] = (), reason: str | None = None, message: Message | None = None,
    ) -> None:
        observations = []
        event_id = len(self.history) + 1
        stock_observed = action in ("eat", "found_no_food", "check_food")
        if stock_observed:
            message = Message("observation", "food", FoodBelief(
                action == "eat" or action == "check_food" and self.food > 0,
                self.tick, (agent.name,), 100, event_id,
            ))
        for observer in self.inhabitants:
            if not observer.alive or (observer.sleep_until and observer is not agent):
                continue
            if observer.room not in (room, destination):
                continue
            if recipient is not None and observer.name not in (agent.name, recipient):
                continue
            perceived_action = visible_as or action
            if action == "move":
                perceived_action = "depart" if observer.room == room else "arrive"
            observation = Observation(
                self.tick, agent.name, perceived_action, observer.room, testimony, concern,
                subject if visible_as is None else None, message,
            )
            observer.memory.append(observation)
            observations.append((observer.name, observation))
            if observer is not agent:
                relationship = observer.relationships[agent.name]
                relationship.familiarity += 1
                relationship.last_contact_event = event_id
                if visible_as == "uneasy_encounter":
                    if observer.examinations.get(agent.name) != "anomaly":
                        observer.examinations.pop(agent.name, None)
                    strength = min(100, observer.suspicion.get(agent.name, 0) + 20)
                    observer.suspicion[agent.name] = strength
                    observer.witnessed_concerns[agent.name] = SuspicionReport(
                        observer.name, agent.name, self.tick, strength,
                    )
            if stock_observed:
                available = message.content.available
                self.verify_food_reports(observer, available, event_id)
                self.update_food_evidence(observer, Evidence(
                    FoodBelief(available, self.tick, (observer.name,), 100, event_id), firsthand=True,
                ))
                observer.asked_food_peers.clear()
        event = Event(
            self.tick, agent.name, action, room, tuple(observations), destination,
            recipient, testimony, subject, concern, causes, reason, message,
        )
        self.history.append(event)
