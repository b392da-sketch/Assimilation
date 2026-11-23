# M0 architecture

M0 uses Python 3.12 and the standard library. A fixed tick keeps movement,
resource consumption, and concurrent encounters reproducible. Each tick represents ten simulated minutes. Survival thresholds are
prototype parameters.

| Component | Responsibility |
| --- | --- |
| Station configuration | Room graph, duty locations, outdoor exposure, fuel budgets and radio location |
| Simulation state | Clock, body locations, needs, food, power, organisms and pending encounters |
| Inhabitant state | Local observations, beliefs, relationships, requests, goals and examination results |
| Decision policy | Picks an intent using needs, private knowledge and local opportunities |
| Resolution | Checks actual location and resources before applying an intent |
| Event history | Stores an objective history and the observation each actor could access |
| Observer and batch runner | Control clock advancement, inspect state, and export outcomes |

Each tick advances power and exposure, collects intentions, then resolves them in
a seeded order. The engine rechecks preconditions during resolution. Encounters
finish after ordinary actions so a late arrival can still interrupt conversion.
Individual names identify bodies across state transitions. An organism controller
has its own lineage identity and occupies a body; the original human's memories
are cleared on conversion while the body and assignment persist.

This prototype models human perception by room, with separate arrival and
departure observations and private messages between named participants. The
decision policy receives local opportunities through the engine's room query.
Resolution reads objective state to enforce physical preconditions. These
boundaries are currently enforced by simulation code and tests in one module.

The observer renders data from the kernel. Its inspection, trace and export
commands do not execute decision logic. Later camera presentation can render
the appropriate view of the same simulation, with character views respecting
the character's knowledge limits. The current room graph has no rendering
geometry or camera implementation.
