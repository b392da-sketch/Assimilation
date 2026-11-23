"""Evaluate ordinary and hidden-organism scenarios across reproducible seeds."""

import argparse
from collections import Counter
import json
from time import perf_counter
import tracemalloc

from .kernel import MAX_NEED, Simulation


def evaluate(seed: int, ticks: int, hidden_organism: bool) -> dict:
    started = perf_counter()
    tracemalloc.start()
    try:
        simulation = Simulation(seed, hidden_organism=hidden_organism)
        for _ in range(ticks):
            simulation.advance()
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    runtime = perf_counter() - started

    history = simulation.history
    counts = Counter(event.action for event in history)
    names = set(simulation.agents_by_name)
    organisms = simulation.organisms
    organism_ids = {organism.identity for organism in organisms.values()}
    invalid_agents = sum(
        agent.room not in simulation.rooms
        or not 0 <= agent.hunger <= MAX_NEED
        or not 0 <= agent.fatigue <= MAX_NEED
        for agent in simulation.inhabitants
    )
    invalid_events = sum(
        event.room not in simulation.rooms
        or any(cause < 1 or cause >= event_id for cause in event.causes)
        or event.action == "move" and event.destination not in simulation.rooms[event.room].neighbors
        or any(name not in names for name, _ in event.observations)
        for event_id, event in enumerate(history, start=1)
    )
    population = {
        "human": len(names) - len(organisms),
        "organism": len(organisms),
        "contained": sum(agent.contained for agent in simulation.inhabitants),
    }
    return {
        "scenario": "hidden-organism" if hidden_organism else "ordinary",
        "seed": seed,
        "ticks": simulation.tick,
        "initial_population": {"human": len(names) - int(hidden_organism),
                               "organism": int(hidden_organism), "contained": 0},
        "final_population": population,
        "food_remaining": simulation.food,
        "initial_main_fuel": simulation.station.power.main_fuel,
        "movements": counts["move"],
        "assimilation_attempts": counts["assimilation_started"],
        "assimilation_completions": counts["assimilation_completed"],
        "assimilation_interruptions": counts["assimilation_interrupted"],
        "pending_assimilations": len(simulation.encounters),
        "knowledge_transfers": sum(counts[action] for action in ("tell", "warn", "request_help")),
        "warnings": counts["warn"],
        "blackouts": counts["power_off"],
        "resolved_actions": simulation.resolved_actions,
        "event_count": len(history),
        "event_counts": dict(sorted(counts.items())),
        "seconds_with_memory_tracing": round(runtime, 6),
        "peak_traced_python_bytes": peak_bytes,
        "invalid_state_count": (
            invalid_agents + invalid_events
            + int(simulation.food < 0 or simulation.food + counts["eat"] != simulation.station.initial_food)
            + int(len(organism_ids) != len(organisms) or not names.issuperset(organisms))
            + sum(organism.body != body or (
                organism.parent is not None and organism.parent not in organism_ids
            ) for body, organism in organisms.items())
            + int(counts["assimilation_started"] != counts["assimilation_completed"]
                  + counts["assimilation_interrupted"] + len(simulation.encounters))
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=50, help="Number of seeds per scenario, starting at 1")
    parser.add_argument("--ticks", type=int, default=240)
    args = parser.parse_args()
    if args.seeds < 1 or args.ticks < 0:
        parser.error("--seeds must be positive and --ticks must be nonnegative")
    invalid = False
    for hidden_organism in (False, True):
        for seed in range(1, args.seeds + 1):
            row = evaluate(seed, args.ticks, hidden_organism)
            invalid |= bool(row["invalid_state_count"])
            print(json.dumps(row), flush=True)
    if invalid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
