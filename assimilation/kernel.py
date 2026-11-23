"""Station state, local perception, routine decisions and action resolution."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from random import Random
from typing import Literal

Activity = Literal["eat", "rest", "work", "wait"]
MAX_NEED = 12


@dataclass(frozen=True)
class Room:
    name: str
    neighbors: tuple[str, ...]
    activities: tuple[Activity, ...] = ()
    outdoors: bool = False


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
    initial_food: int = 240
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
    power=PowerConfig("generator", main_fuel=720, backup_fuel=4, reserve_fuel=80, radio_room="radio"),
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


@dataclass(frozen=True)
class FoodBelief:
    available: bool
    observed_at: int
    sources: tuple[str, ...]
    confidence: int


@dataclass(frozen=True)
class SuspicionReport:
    witness: str
    subject: str
    observed_at: int
    concern: int


@dataclass
class Relationship:
    trust: int
    familiarity: int = 0


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


@dataclass
class Inhabitant:
    name: str
    room: str
    duty_room: str
    hunger: int
    fatigue: int
    meal_threshold: int
    rest_threshold: int
    memory: deque[Observation] = field(default_factory=lambda: deque(maxlen=32))
    food_belief: FoodBelief | None = None
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
    requested_help_from: set[str] = field(default_factory=set)
    examinations: dict[str, bool] = field(default_factory=dict)
    contained: bool = False
    showed_cold_distress: bool = False

    def concern_about(self, subject: str) -> int:
        if self.examinations.get(subject) is False:
            return 0
        reported = (
            report.concern * self.relationships[report.witness].trust // 100
            for report in self.heard_concerns.values()
            if report.subject == subject
        )
        return max(self.suspicion.get(subject, 0), max(reported, default=0))


@dataclass(frozen=True)
class Intent:
    action: str
    destination: str | None = None
    recipient: str | None = None
    subject: str | None = None


class Simulation:
    def __init__(
        self, seed: int, station: Station = DEFAULT_STATION, *, hidden_organism: bool = False,
    ) -> None:
        self.seed = seed
        self.station = station
        self.rooms = {room.name: room for room in station.rooms}
        self.tick = 0
        self.food = station.initial_food
        self.history: list[Event] = []
        self.last_intents: dict[str, Intent] = {}
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
            )
            for name in names
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

    def advance(self) -> None:
        self.tick += 1
        self.advance_power()
        for inhabitant in self.inhabitants:
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
            exposure = cold if outdoors else inhabitant.felt_cold
            inhabitant.fatigue = min(MAX_NEED, inhabitant.fatigue + 1 + exposure)

        intents = [(agent, self.decide(agent)) for agent in self.inhabitants if not agent.contained]
        self.last_intents = {agent.name: intent for agent, intent in intents}
        self.random.shuffle(intents)
        for agent, intent in intents:
            self.resolved_actions += self.resolve(agent, intent)
        self.finish_encounters()

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

    def decide(self, agent: Inhabitant) -> Intent:
        organism = self.organisms.get(agent.name)
        if agent.name in self.encounters:
            return Intent("assimilate", recipient=self.encounters[agent.name].target)
        peers = self.others_present(agent)
        for peer in peers:
            if agent.examinations.get(peer.name) and not peer.contained:
                return Intent("contain", subject=peer.name)
        exits = self.rooms[agent.room].neighbors
        if exits and any(agent.concern_about(peer.name) >= 30
                         for peer in peers if not peer.contained):
            return Intent("move", exits[0])
        for peer in peers:
            report = agent.witnessed_concerns.get(peer.name)
            if (report and peer.name not in agent.examinations and not peer.contained
                    and self.tick >= report.observed_at + 2):
                return Intent("examine", subject=peer.name)

        if self.station.power:
            response = self.power_response(agent)
            if response:
                return response

        belief = agent.food_belief
        food_ruled_out = belief is not None and not belief.available and belief.confidence >= 60
        needs = [(agent.fatigue - agent.rest_threshold, "rest")]
        if not food_ruled_out:
            needs.append((agent.hunger - agent.meal_threshold, "eat"))

        # Finish a feasible need-driven trip before choosing another routine.
        ranked = sorted(needs, key=lambda need: (need[1] != agent.goal, -need[0]))
        for urgency, activity in ranked:
            if urgency < 0:
                continue
            target = self.toward(agent.room, activity)
            if target:
                agent.goal = activity
                return target

        agent.goal = None
        if organism and self.tick >= organism.recovery_until:
            others = self.others_present(agent)
            if len(others) == 1 and others[0].name not in organism.converted:
                return Intent("assimilate", recipient=others[0].name)

        for report in agent.witnessed_concerns.values():
            for peer in self.others_present(agent):
                if self.can_warn(agent, peer, report):
                    return Intent("warn", recipient=peer.name, subject=report.subject)

        if belief is not None and not belief.available and belief.confidence >= 60:
            for peer in self.inhabitants:
                if self.can_share(agent, peer):
                    return Intent("tell", recipient=peer.name)

        return self.toward(agent.room, "work", agent.duty_room) or Intent("wait")

    def power_response(self, agent: Inhabitant) -> Intent | None:
        generator = self.station.power.generator_room
        requester = agent.help_requested_by
        if requester:
            if not agent.help_accepted:
                willing = agent.fatigue < agent.rest_threshold and agent.relationships[requester].trust >= 65
                return Intent("accept_help" if willing else "decline_help", recipient=requester)
            if agent.room == generator:
                return Intent("refuel")
            step = self.first_step(agent.room, lambda room: room.name == generator)
            return Intent("move", step) if step else Intent("decline_help", recipient=requester)
        if not agent.felt_cold or agent.checked_generator:
            return None
        if agent.room == generator:
            return Intent("refuel")
        if agent.duty_room != generator:
            return None
        if not agent.requested_help_from:
            for peer in self.others_present(agent):
                if peer.duty_room != generator:
                    return Intent("request_help", recipient=peer.name)
        step = self.first_step(agent.room, lambda room: room.name == generator)
        return Intent("move", step) if step else None

    def can_share(self, agent: Inhabitant, peer: Inhabitant) -> bool:
        belief = agent.food_belief
        return (
            belief is not None
            and agent.room == peer.room
            and peer.name not in belief.sources
            and peer.name != agent.name
            and self.shared_reports.get((agent.name, peer.name)) != belief.available
        )

    def can_warn(self, agent: Inhabitant, peer: Inhabitant, report: SuspicionReport) -> bool:
        previous = agent.sent_concerns.get((peer.name, report.subject), -1)
        return (
            agent.room == peer.room
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

    def tell(self, agent: Inhabitant, peer: Inhabitant) -> bool:
        belief = agent.food_belief
        if belief is None or not self.can_share(agent, peer):
            return False
        self.shared_reports[agent.name, peer.name] = belief.available
        relationship = peer.relationships[agent.name]
        report = FoodBelief(
            belief.available,
            belief.observed_at,
            (*belief.sources, peer.name),
            belief.confidence * relationship.trust // 100,
        )
        current = peer.food_belief
        if current is None or (
            report.confidence >= 30
            and report.observed_at >= current.observed_at
            and (report.confidence > current.confidence or report.observed_at > current.observed_at)
        ):
            peer.food_belief = report
        self.record(agent, "tell", agent.room, recipient=peer.name, testimony=belief)
        return True

    def toward(self, start: str, activity: Activity, target: str | None = None) -> Intent | None:
        def matches(room: Room) -> bool:
            return activity in room.activities and (target is None or target == room.name)

        if matches(self.rooms[start]):
            return Intent(activity)
        step = self.first_step(start, matches)
        return Intent("move", step) if step else None

    def first_step(self, start: str, matches: Callable[[Room], bool]) -> str | None:
        queue = deque([(start, None)])
        visited = {start}
        while queue:
            name, first_step = queue.popleft()
            room = self.rooms[name]
            if matches(room):
                return first_step
            for neighbor in room.neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, first_step or neighbor))
        return None

    def resolve(self, agent: Inhabitant, intent: Intent) -> bool:
        if agent.contained:
            return False
        origin = self.rooms[agent.room]
        action = intent.action
        destination = intent.destination
        if action == "move":
            if destination not in origin.neighbors:
                return False
            agent.room = destination
        elif action == "wait":
            return True
        elif action == "tell":
            peer = self.agents_by_name.get(intent.recipient)
            return peer is not None and self.tell(agent, peer)
        elif action == "warn":
            return self.warn(agent, intent)
        elif action == "request_help":
            peer = self.agents_by_name.get(intent.recipient)
            if (peer is None or peer is agent or peer.room != agent.room
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
            agent.help_accepted = action == "accept_help"
            if not agent.help_accepted:
                agent.help_requested_by = None
            self.record(agent, action, agent.room, recipient=intent.recipient)
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
        elif action == "rest":
            agent.goal = None
            shivering = (
                agent.felt_cold and agent.fatigue == MAX_NEED and not agent.showed_cold_distress
            )
            agent.fatigue = max(0, agent.fatigue - 6)
            if shivering:
                agent.showed_cold_distress = True
                self.record(agent, action, origin.name, visible_as="uneasy_encounter")
                return True
        elif action == "work" and self.station.power and origin.name == self.station.power.radio_room:
            action = "radio_contact" if self.power.source != "off" else "radio_unpowered"

        self.record(agent, action, origin.name, destination)
        return True

    def resolve_investigation(self, agent: Inhabitant, intent: Intent) -> bool:
        subject = self.agents_by_name.get(intent.subject)
        if (subject is None or subject is agent or subject.contained or subject.room != agent.room
                or subject.name not in agent.witnessed_concerns):
            return False
        if intent.action == "examine":
            report = agent.witnessed_concerns[subject.name]
            if subject.name in agent.examinations or self.tick < report.observed_at + 2:
                return False
            abnormal = subject.name in self.organisms
            agent.examinations[subject.name] = abnormal
            if not abnormal:
                agent.suspicion.pop(subject.name, None)
                agent.witnessed_concerns.pop(subject.name, None)
            self.record(
                agent, "examination_anomaly" if abnormal else "examination_clear",
                agent.room, recipient=agent.name, subject=subject.name,
            )
            return True
        if not agent.examinations.get(subject.name):
            return False
        subject.contained = True
        self.record(agent, "contained", agent.room, subject=subject.name)
        return True

    def others_present(self, agent: Inhabitant) -> list[Inhabitant]:
        return [
            peer for peer in self.inhabitants
            if peer is not agent and peer.room == agent.room
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
                not actor.contained and not target.contained
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
                target.suspicion.clear()
                target.witnessed_concerns.clear()
                target.heard_concerns.clear()
                target.sent_concerns.clear()
                target.examinations.clear()
                target.help_requested_by = None
                target.help_accepted = False
                target.requested_help_from.clear()
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
        action = "refuel_completed" if power.refuel_worker == agent.name else "refuel_assisted"
        power.main_fuel = power.reserve_fuel
        power.reserve_fuel = 0
        power.refuel_worker = None
        agent.help_requested_by = None
        agent.help_accepted = False
        parent = self.refuel_start_event
        self.record(
            agent, action, agent.room, causes=(parent,) if parent is not None else (),
            reason="The second refueling action transferred reserve fuel to the main supply.",
        )
        self.refuel_finish_event = len(self.history)
        return True

    def record(
        self, agent: Inhabitant, action: str, room: str, destination: str | None = None,
        *, recipient: str | None = None, testimony: FoodBelief | None = None,
        subject: str | None = None, visible_as: str | None = None,
        concern: SuspicionReport | None = None,
        causes: tuple[int, ...] = (), reason: str | None = None,
    ) -> None:
        observations = []
        for observer in self.inhabitants:
            if observer.room not in (room, destination):
                continue
            if recipient is not None and observer.name not in (agent.name, recipient):
                continue
            perceived_action = visible_as or action
            if action == "move":
                perceived_action = "depart" if observer.room == room else "arrive"
            observation = Observation(
                self.tick, agent.name, perceived_action, observer.room, testimony, concern,
                subject if visible_as is None else None,
            )
            observer.memory.append(observation)
            observations.append((observer.name, observation))
            if observer is not agent:
                observer.relationships[agent.name].familiarity += 1
                if visible_as == "uneasy_encounter":
                    if observer.examinations.get(agent.name) is False:
                        del observer.examinations[agent.name]
                    strength = min(100, observer.suspicion.get(agent.name, 0) + 20)
                    observer.suspicion[agent.name] = strength
                    observer.witnessed_concerns[agent.name] = SuspicionReport(
                        observer.name, agent.name, self.tick, strength,
                    )
            if action in ("eat", "found_no_food"):
                observer.food_belief = FoodBelief(
                    action == "eat", self.tick, (observer.name,), 100,
                )
        event = Event(
            self.tick, agent.name, action, room, tuple(observations), destination,
            recipient, testimony, subject, concern, causes, reason,
        )
        self.history.append(event)
