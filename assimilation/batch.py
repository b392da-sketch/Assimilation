"""Evaluate ordinary and hidden-organism scenarios across reproducible seeds."""

import argparse
from collections import Counter
from dataclasses import replace
import json
from time import perf_counter
import tracemalloc

from .kernel import DEFAULT_STATION, MAX_NEED, PowerConfig, Simulation, Station


def evaluate(seed: int, ticks: int, scenario: str, station: Station) -> dict:
    hidden_organism = scenario == "hidden-organism"
    started = perf_counter()
    tracemalloc.start()
    try:
        simulation = Simulation(seed, station, hidden_organism=hidden_organism)
        simulation.advance_ticks(ticks)
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
        or not 0 <= agent.health <= 100
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
        "human_alive": sum(agent.alive and agent.name not in organisms for agent in simulation.inhabitants),
        "organism_alive": sum(simulation.agents_by_name[body].alive for body in organisms),
    }
    return {
        "scenario": scenario,
        "seed": seed,
        "ticks": simulation.tick,
        "initial_population": {"human": len(names) - int(hidden_organism),
                               "organism": int(hidden_organism), "contained": 0},
        "final_population": population,
        "food_remaining": simulation.food,
        "initial_food": station.initial_food,
        "initial_main_fuel": simulation.station.power.main_fuel,
        "minimum_final_health": min(agent.health for agent in simulation.inhabitants),
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
    parser.add_argument("--seeds", type=int, help="Number of seeds per scenario, starting at 1")
    parser.add_argument("--ticks", type=int)
    parser.add_argument("--multiday", action="store_true", help="Run ten-day baseline and adverse scenarios")
    args = parser.parse_args()
    seeds = args.seeds if args.seeds is not None else (3 if args.multiday else 50)
    ticks = args.ticks if args.ticks is not None else (1440 if args.multiday else 240)
    if seeds < 1 or ticks < 0:
        parser.error("--seeds must be positive and --ticks must be nonnegative")
    scenarios = [("ordinary", DEFAULT_STATION)]
    if args.multiday:
        scenarios.extend((
            ("ration-shortage", replace(DEFAULT_STATION, initial_food=72)),
            ("fuel-shortage", replace(DEFAULT_STATION, power=PowerConfig("generator", 5, 3, 0, "radio"))),
        ))
    else:
        scenarios.append(("hidden-organism", DEFAULT_STATION))
    invalid = False
    for scenario, station in scenarios:
        for seed in range(1, seeds + 1):
            row = evaluate(seed, ticks, scenario, station)
            invalid |= bool(row["invalid_state_count"])
            print(json.dumps(row), flush=True)
    if invalid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
