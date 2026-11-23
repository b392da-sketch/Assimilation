"""Run Observer Mode from the command line."""

import argparse
from collections import Counter
from dataclasses import asdict, replace
import json

from .kernel import DEFAULT_STATION, PowerConfig, Simulation
from .observer import event_record, run_observer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--ticks", type=int, help="Ticks to run before output or interactive pause")
    parser.add_argument("--interactive", action="store_true", help="Open the paused terminal observer")
    parser.add_argument("--scenario", choices=("ordinary", "low-fuel", "hidden-organism"),
                        default="ordinary")
    parser.add_argument("--events", action="store_true", help="Print the event log as JSON lines")
    parser.add_argument("--observe", metavar="NAME", help="Show only events witnessed by this inhabitant")
    args = parser.parse_args()
    ticks = args.ticks if args.ticks is not None else (0 if args.interactive else 60)
    if ticks < 0:
        parser.error("--ticks must be nonnegative")
    if args.interactive and (args.observe or args.events):
        parser.error("--interactive has its own inspection and export commands")

    station = DEFAULT_STATION
    if args.scenario == "low-fuel":
        station = replace(station, power=PowerConfig("generator", 5, 3, 80, radio_room="radio"))
    simulation = Simulation(args.seed, station, hidden_organism=args.scenario == "hidden-organism")
    if args.observe and args.observe not in {agent.name for agent in simulation.inhabitants}:
        parser.error(f"unknown inhabitant {args.observe!r}")
    simulation.advance_ticks(ticks)

    if args.interactive:
        run_observer(simulation)
        return

    events = simulation.history
    if args.observe:
        events = [
            observation
            for event in simulation.history
            for name, observation in event.observations
            if name == args.observe
        ]
    if args.observe:
        for observation in events:
            print(json.dumps(asdict(observation)))
    elif args.events:
        for event_id, event in enumerate(events, start=1):
            print(json.dumps(event_record(event_id, event)))
    summary = {
        "seed": simulation.seed,
        "scenario": args.scenario,
        "ticks": simulation.tick,
        "actions": dict(sorted(Counter(event.action for event in events).items())),
    }
    if not args.observe:
        summary["food_remaining"] = simulation.food
        summary["power"] = asdict(simulation.power) if simulation.power is not None else None
        summary["organisms"] = [
            {
                "identity": organism.identity, "parent": organism.parent, "body": organism.body,
                "contained": simulation.agents_by_name[organism.body].contained,
                "alive": simulation.agents_by_name[organism.body].alive,
            }
            for organism in simulation.organisms.values()
        ]
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
