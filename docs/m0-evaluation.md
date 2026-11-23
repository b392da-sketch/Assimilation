# M0 evaluation

## Reproduction

Use Python 3.12 from the repository root.

```bash
python3 -m unittest discover -s tests -v
python3 -m assimilation --seed 1 --ticks 1440
python3 -m assimilation --scenario low-fuel --seed 1 --ticks 60 --events
python3 -m assimilation --scenario hidden-organism --seed 19 --ticks 240 --events
python3 -m assimilation.batch --seeds 50 --ticks 240 > m0-short.jsonl
python3 -m assimilation.batch --multiday > m0-multiday.jsonl
```

The batch tool writes one row per run, including scenario, seed, elapsed
ticks, population, activity counts, runtime, and peak Python allocations.
Timings include memory tracing overhead. It exits with an error when a
checked invariant fails.

## Short batch

The batch repeats seeds 1–50 for the ordinary and hidden-organism scenarios.
Both use the same 420 meals and 1,600 units of main fuel. Each run covers
240 ticks, or 40 simulated hours.

| Measure | Ordinary | Hidden organism |
| --- | ---: | ---: |
| Runs | 50 | 50 |
| Moves | 15,037 | 17,897 |
| Meals eaten | 2,519 | 2,465 |
| Completed sleep periods | 796 | 784 |
| Warnings | 0 | 372 |
| Assimilation attempts / interrupted / completed | 0 / 0 / 0 | 336 / 241 / 95 |
| Runs with containment | 0 | 13 |
| Invalid states detected | 0 | 0 |

The prior revision produced 76 assimilation attempts and three completions.
The new routines materially change encounter opportunities. Longer periods in
one room give pairs more chances to remain together across two ticks.
These counts describe the model under the revised routines. They cannot
establish plausible assimilation or containment frequencies.

## Ten-day runs

Each row summarizes seeds 1–3 at 1,440 ticks each. All nine runs completed
with zero detected invariant failures. The shortages are separate scenarios
so food deprivation and cold injury can be observed independently.

| Scenario | Provision | Survivors per run | Lowest final health per run | Meals remaining |
| --- | --- | --- | --- | --- |
| Ordinary | 420 meals and 1,600 main fuel | 12 / 12 / 12 | 100 / 100 / 100 | 107 / 107 / 113 |
| Ration shortage | 72 meals and 1,600 main fuel | 12 / 12 / 12 | 45 / 43 / 44 | 0 / 0 / 0 |
| Fuel shortage | 420 meals, five main and three backup fuel, no reserve | 0 / 0 / 0 | 0 / 0 / 0 | 390 / 388 / 393 |

The ordinary runs consumed 307–313 meals, equivalent to about 2.6 meals per
inhabitant per day, and completed 112–116 seven-hour sleep periods per run.
They finished on main power with 160 main fuel units available. Movement took
roughly 10–11% of resolved ticks in these runs. This denominator includes
sleep, ongoing work and waits. The earlier evaluation counted resolved ticks
under a simulation with no sustained sleep or work, so the ratios describe
different behavior.

The ration-shortage runs show health decline while all inhabitants remain
alive through day ten. A separate no-food test runs beyond ten days and
checks that a contained organism can die from deprivation. The fuel-shortage
runs exhausted backup power on tick nine and all inhabitants eventually died
from sustained cold. All clocks reached day ten.

## Acceptance evidence

| Demonstration | Evidence |
| --- | --- |
| D1 Ordinary continuity | Three supplied ten-day runs sustained meals, sleep, work and all twelve inhabitants. |
| D2 Independent action | The help test shows recipients accepting or declining the same request based on their trust in the requester. |
| D3 Information isolation | In the encounter interruption test, an absent agent receives no original observation. |
| D4 Testimony | Tests check source preservation, confidence discounts, and the effect of trust on avoidance. |
| D5 Environmental consequence | Low-fuel seed 1 uses backup, loses power, and restores it after refueling. |
| D6 Autonomous organism | Hidden-organism seed 19 completes assimilation through normal simulation actions. |
| D7 Interruption | A test interrupts conversion after a continuation action when another agent enters the room. |
| D8 Replay | Tests compare same-seed histories and final states and verify that observer inspection does not alter replay. |
| D9 Variation | Seeds change movement and encounter outcomes. Independent shortages change survival outcomes. |
| D10 Causal inspection | Low-fuel seed 1 event 58 traces restoration through refueling and the blackout. |

Ordinary activities are deliberately simple. Work blocks hold one location
and do not model shifts, work products, or differences in professional skill.
The station can use its stock over ten days, but has no way to replenish it.
Health thresholds are gameplay parameters and do not validate medical realism.
Evidence and containment remain abstract and can still be repetitive.
Decision logic relies on a single kernel module with tests enforcing local
knowledge, and only selected causal chains are captured. A subsequent
iteration can improve the perception boundary, technical roles, and
resource stewardship using these baselines.
