# Assimilation

Assimilation is an original Antarctic station simulation. The first slice of
M0 models everyday station activity in a headless Observer Mode.

Run from the repository root with Python 3.12 and the standard library.

```bash
python3 -m assimilation --seed 1 --ticks 60
python3 -m assimilation --seed 1 --ticks 60 --events
python3 -m assimilation --scenario low-fuel --seed 1 --ticks 60 --events
python3 -m assimilation --scenario hidden-organism --seed 19 --ticks 240 --events
python3 -m assimilation --seed 1 --ticks 60 --observe Anika
python3 -m unittest discover -s tests -v
```

## Interactive observer

```bash
python3 -m assimilation --scenario low-fuel --seed 1 --interactive
```

The prompt starts paused at tick zero, or at the tick supplied with
`--ticks`. Use `step` for one tick or `step 20` for a batch. The simulator
pauses again at the prompt. Use `status` to see the clock and locations,
`inspect Anika` for private beliefs and the last selected intent, and
`events 20` for event IDs. Use `trace ID` to follow recorded causes for
power transitions, refueling, and assimilation outcomes. Other events
remain inspectable with their timestamps and participants. `export "run.jsonl"`
writes an objective event history to a new file. Use `help` for the command
list and `quit` to exit.

## Simulation rules

A configurable graph represents the station. Each tick increases needs,
collects one intent per inhabitant, and resolves those intents in seeded
order. Movement takes one tick per edge. Inhabitants choose where to eat,
rest, or report for duty using their own needs and a known station layout.
Outdoor exposure below freezing accelerates fatigue. Food is finite and the
resolver checks availability when each meal is attempted.

The observer can read the full event history or view one inhabitant's local
observations. A movement records a departure at its origin and an arrival
at its destination. Each inhabitant remembers up to 32 observations. The
observer's historical view includes earlier observations for inspection.

## M0 progress

The current headless slices cover routines, local observation, deterministic
replay, and food-shortage communication. Inhabitants continue a feasible trip
for a need until they satisfy it or receive credible evidence that food has
run out. A witnessed meal or failed meal attempt establishes a private
belief about stock. Inhabitants can share a shortage report during a
co-located encounter. Relayed reports preserve their source chain and lose
confidence according to each listener's trust in the speaker. A listener
may still check the galley after hearing a low-confidence report.

Trust is seeded and fixed for this slice. Familiarity grows through witnessed
actions. The current food supply never replenishes, and familiarity does not
yet influence decisions. Broader cooperation remains open M0 work.

In 500-tick runs with seeds 1–3, the station consumed all 240 meals per run,
generated 10–19 failed meal attempts and 128–130 shortage reports, and
continued ordinary work after the reports began.

## Station power

The main and backup supplies each burn one unit of fuel per operating tick.
Backup power supplies heat until its fuel runs out. Below-freezing outdoor
conditions then also cause indoor cold exposure, which accelerates fatigue.
The model applies that change at the next exposure update, without simulating
thermal inertia.

In the low-fuel scenario, main fuel supports five ticks and backup fuel
supports three more. Generator duty staff who feel indoor cold can walk to
the generator. Refueling takes two work actions and a finite reserve. A
co-located inhabitant can supply the second action, and the main supply
returns on the following tick. The ordinary scenario starts with 720 main
fuel units. Both scenarios use the same rules.

Radio duty makes an abstract contact with the outside while either power
supply is active. A check made at the radio during a blackout records an
unpowered set. The radio models power-dependent availability only.

Before heading to the generator, cold generator staff can privately tell
a nearby inhabitant about the problem and ask for help. The listener
evaluates the request on their next action based on fatigue and trust.
Accepting commits them to travel to the generator and help with refueling
while the outage persists. An unsolicited helper already at the generator
can still contribute. Across five low-fuel runs, all recovered main power.
The runs included declined requests, a voluntary acceptance, and both
solo and assisted refueling.

## Hidden organism

This optional scenario starts with one seeded resident under an organism's
control. It keeps up ordinary routines and can try an abstract conversion
when its needs permit and exactly one other inhabitant is present. An attempt
must continue on the next tick with the same pair alone in the same room.
Movement, a third person's arrival, or loss of that opportunity interrupts
the attempt. Resolution takes place after ordinary actions so a same-tick
arrival can still interrupt it.

The body retains its identity and location. A successful conversion
assigns a distinct organism with a parent reference and begins with fresh
private memory and beliefs. Physical needs, work assignment and relationship
state remain attached to the body as a prototype simplification. A witness
can perceive an uneasy encounter and grow suspicious. Objective outcomes and
lineage appear in the omniscient observer output only. Recovery delays the
next attempt. These experimental rules cover conversion and interruption.
An organism depends on its body's health and can die from prolonged exposure or deprivation.

A witness can privately warn another inhabitant in the same room. The report
preserves who witnessed the encounter and when. The listener weighs it by
trust and can leave a shared room if concern is high enough. Reports never
grant access to objective assimilation status. This slice allows firsthand
reports only.

Severe cold distress can raise suspicion. After two ticks, a firsthand
witness can examine the subject if they meet again. Cold and exhaustion can
mask a result. A recovering organism can show an anomaly, and a quiescent
organism can pass the examination. The prototype uses an abstract signal
with no real-world diagnostic analogue.

An anomaly allows a less fatigued examiner to start containing a visibly
exhausted subject. Both must stay in the same room and remain eligible for a
second action on the next tick. Departure cancels the attempt. Containment
prevents action but does not itself cause death. There is no release
procedure.

## Survival clock

Each tick represents ten simulated minutes. The prototype applies cold
injury after three continuous hours of exposure and deprivation damage
after a full day at maximum hunger. Severe impairment slows movement.
Warmth and food permit gradual recovery. A body at zero health stops acting.
An organism dies with its body, and the station clock keeps advancing.
These are gameplay thresholds. Work, hunger and resupply still need tuning
before long runs can represent realistic station life.

## Camera modes

| Mode | Switchable camera views | Information available |
| --- | --- | --- |
| Character | First person, third person, bird’s-eye | The controlled character’s perception and knowledge in every view |
| Observer | Third person, omniscient bird’s-eye | Read-only observation, with full world visibility in the omniscient view |

Camera selection belongs to the presentation layer. Switching views preserves
the same simulation state and does not change what an inhabitant can perceive
or how they decide and act. The Character bird’s-eye view has the same
information limits as its first- and third-person views.

The [M0 specification](docs/milestones/M0-autonomous-simulation-kernel.md) calls for a headless observer.
Graphical cameras and direct character control are planned beyond M0.

## Validation

Run `python3 -m assimilation.batch --seeds 50 --ticks 240` for the 100-run
evaluation. See the [architecture](docs/architecture.md)
and [M0 evaluation](docs/m0-evaluation.md) for the model boundaries,
reproduction commands and remaining gaps.
