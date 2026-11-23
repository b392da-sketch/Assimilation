"""Read-only inspection and explicit clock control for the terminal observer."""

from dataclasses import asdict
from fractions import Fraction
import json
from pathlib import Path
from shlex import split
from time import monotonic_ns, sleep

from .kernel import Event, Simulation
from .playback import NANOSECONDS_PER_SECOND, Playback


HELP = """Commands
  step [N]       Advance N ticks, then pause (default 1).
  play SECONDS [RATE]  Run for elapsed wall seconds, then pause (default 1×).
  status         Show current time and resources.
  inspect NAME   Show one inhabitant's state, knowledge, and last intent.
  decisions NAME [N]  Show recent choices, evaluated options, and outcomes.
  events [N]     Show the most recent N objective events (default 10).
  trace ID       Follow recorded causes of an objective event.
  export PATH    Write the objective history as JSON Lines to a new file.
  help           Show these commands.
  quit           Exit the observer."""


def event_record(event_id: int, event: Event) -> dict:
    return {"id": event_id, **asdict(event)}


def recent_events(simulation: Simulation, count: int) -> list[dict]:
    start = max(0, len(simulation.history) - count)
    return [
        event_record(index + 1, simulation.history[index])
        for index in range(start, len(simulation.history))
    ]


def trace_event(simulation: Simulation, event_id: int) -> list[dict]:
    if not 1 <= event_id <= len(simulation.history):
        raise ValueError("No event with that ID.")
    pending = [event_id]
    visited = set()
    while pending:
        current = pending.pop()
        if current not in visited:
            visited.add(current)
            pending.extend(simulation.history[current - 1].causes)
    return [event_record(index, simulation.history[index - 1]) for index in sorted(visited)]


def inspect_inhabitant(simulation: Simulation, name: str) -> dict:
    if name not in simulation.agents_by_name:
        raise ValueError(f"Unknown inhabitant {name!r}.")
    agent = simulation.agents_by_name[name]
    intent = simulation.last_intents.get(name)
    organism = simulation.organisms.get(name)
    return {
        "name": name,
        "room": agent.room,
        "duty_room": agent.duty_room,
        "hunger": agent.hunger,
        "fatigue": agent.fatigue,
        "health": agent.health,
        "disposition": asdict(agent.disposition),
        "alive": agent.alive,
        "goal": agent.goal,
        "last_intent": asdict(intent) if intent else None,
        "contained": agent.contained,
        "organism": organism.identity if organism else None,
        "food_belief": asdict(agent.food_belief) if agent.food_belief else None,
        "relationships": {peer: asdict(relationship) for peer, relationship in agent.relationships.items()},
        "witnessed_concerns": [asdict(report) for report in agent.witnessed_concerns.values()],
        "heard_concerns": [asdict(report) for report in agent.heard_concerns.values()],
        "examinations": dict(agent.examinations),
        "memory": [asdict(observation) for observation in agent.memory],
    }


def status(simulation: Simulation) -> dict:
    return {
        "seed": simulation.seed,
        "tick": simulation.tick,
        "elapsed_seconds": simulation.elapsed_seconds,
        "food_remaining": simulation.food,
        "power": asdict(simulation.power) if simulation.power else None,
        "locations": {agent.name: agent.room for agent in simulation.inhabitants},
    }


def play_window(playback: Playback, duration: str, rate: str) -> None:
    try:
        wall_nanoseconds = int(Fraction(duration) * NANOSECONDS_PER_SECOND)
        speed = Fraction(rate)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError("Duration and rate must be numbers.") from error
    if wall_nanoseconds <= 0:
        raise ValueError("Playback duration must be positive.")
    playback.resume(speed)
    last = monotonic_ns()
    deadline = last + wall_nanoseconds
    try:
        while last < deadline:
            try:
                sleep(min(0.1, (deadline - last) / NANOSECONDS_PER_SECOND))
            except KeyboardInterrupt:
                playback.elapse(min(monotonic_ns(), deadline) - last)
                break
            now = min(monotonic_ns(), deadline)
            playback.elapse(now - last)
            last = now
    finally:
        playback.pause()


def observer_command(
    simulation: Simulation, words: list[str], playback: Playback | None = None,
) -> object:
    command, *args = words
    if command == "status" and not args:
        return status(simulation)
    if command == "play" and 1 <= len(args) <= 2:
        controller = playback if playback is not None else Playback(simulation)
        play_window(controller, args[0], args[1] if len(args) == 2 else "1")
        return status(simulation)
    if command == "inspect" and len(args) == 1:
        return inspect_inhabitant(simulation, args[0])
    if command == "decisions" and 1 <= len(args) <= 2:
        name = args[0]
        if name not in simulation.agents_by_name:
            raise ValueError(f"Unknown inhabitant {name!r}.")
        count = int(args[1]) if len(args) == 2 else 5
        if count < 0:
            raise ValueError("Count must be nonnegative.")
        records = list(simulation.decision_records.get(name, ()))
        return [asdict(record) for record in records[-count:]] if count else []
    if command == "trace" and len(args) == 1:
        return trace_event(simulation, int(args[0]))
    if command == "export" and len(args) == 1:
        with Path(args[0]).open("x", encoding="utf-8") as output:
            for event_id, event in enumerate(simulation.history, start=1):
                output.write(json.dumps(event_record(event_id, event)) + "\n")
        return {"path": args[0], "events": len(simulation.history)}
    if command in ("step", "events") and len(args) <= 1:
        count = int(args[0]) if args else (1 if command == "step" else 10)
        if count < 0:
            raise ValueError("Count must be nonnegative.")
        if command == "events":
            return recent_events(simulation, count)
        simulation.advance_ticks(count)
        return status(simulation)
    raise ValueError("Unknown command or invalid arguments. Enter help for usage.")


def run_observer(simulation: Simulation) -> None:
    playback = Playback(simulation)
    print("Observer paused. Enter help for commands.")
    while True:
        try:
            words = split(input("observer> "))
            if not words:
                continue
            if words == ["quit"]:
                return
            if words == ["help"]:
                print(HELP)
                continue
            print(json.dumps(observer_command(simulation, words, playback), indent=2))
        except (EOFError, KeyboardInterrupt):
            print()
            return
        except (OSError, ValueError) as error:
            print(error)
