# M0 evaluation

## Reproduction

From the repository root, using Python 3.12 with no additional dependencies:

```bash
python3 -m unittest discover -s tests -v
python3 -m assimilation --seed 1 --ticks 1440
python3 -m assimilation --scenario low-fuel --seed 1 --ticks 60 --events
python3 -m assimilation --scenario hidden-organism --seed 2 --ticks 240 --events
python3 -m assimilation --scenario hidden-organism --seed 19 --ticks 240 --events
python3 -m assimilation.batch --seeds 50 --ticks 240 > m0-results.jsonl
```

The batch runs seeds 1–50 for each of the ordinary and hidden-organism scenarios.
Both start with the default station, 240 meals, and 720 main fuel. Each line
records configuration, population, action and event counts, final resource
state, runtime and peak Python allocations measured by `tracemalloc`. The last
two metrics depend on the machine and include tracing overhead. The command
exits with failure if its invariants detect an invalid state.

## Results

| Measure | Ordinary | Hidden organism |
| --- | ---: | ---: |
| Runs | 50 | 50 |
| Resolved actions | 142,982 | 137,257 |
| Recorded events | 143,592 | 137,677 |
| Moves | 96,335 | 93,484 |
| Food and suspicion messages | 4,159 | 2,626 |
| Assimilation attempts / interrupted / completed | 0 / 0 / 0 | 38 / 35 / 3 |
| Runs with containment | 0 | 31 |
| Invalid states detected | 0 | 0 |
| Median traced seconds per run | 0.284 | 0.260 |
| Highest peak traced Python allocations | 4.05 MiB | 3.93 MiB |

No attempt remained pending at the batch cutoff. The three completions came
from seeds 19, 20 and 33. Neither batch scenario exhausted its main fuel before
the cutoff. Death is outside the tested model. Population counts distinguish
human-controlled, organism-controlled and contained bodies.

## Demonstrations

| Spec | Evidence |
| --- | --- |
| D1 Ordinary continuity | Ordinary seed 1 completed 1,440 ticks, with 442 work events and 410 radio contacts. It continued after running out of food and fuel. Ticks have no calibrated conversion to days. |
| D2 Independent action | The same outage request is accepted or declined by recipients with different trust in the requester. The help test exercises both paths. |
| D3 Information isolation | The interruption test confirms that someone outside the room receives no original encounter observation. |
| D4 Testimony | The food testimony test confirms that relaying a report preserves the source chain and discounts confidence. The suspicion test verifies that reports do not become firsthand knowledge. |
| D5 Environment | Low-fuel seed 1 switched to backup on tick 6, lost power on tick 9, and restored it on tick 14 after physical refueling. |
| D6 Organism autonomy | Hidden-organism seed 19 shows routine activity, an organically generated private opportunity and a completed assimilation. Seed 2 shows examination and containment. |
| D7 Interruption | The room-arrival test interrupts an encounter after continuation was submitted in the same tick. The batch registered 35 interruptions. |
| D8 Reproducibility | Tests compared same-seed histories, ordinary final states, and interactive versus batch exports. |
| D9 Variation | Identical station settings produced successful conversions only in seeds 19, 20, and 33 and containment in 31 of the 50 hidden-organism runs. |
| D10 Causality | In low-fuel seed 1, `trace 158` follows backup event 61, blackout 98, refuel start 142, refuel completion 149, and main restoration 158. |

## Independent review questions

1. **Emergent behavior.** Encounters follow routine movement and seeded
   initiative. Refueling may be completed by one inhabitant or assisted by a
   co-located peer. No story event selects these outcomes.
2. **Rigid behavior.** Work consumes one tick, the same routes are often
   repeated, and a fixed trust threshold determines cooperation.
3. **Knowledge.** No leak was found in the tested paths. Agents know their
   station map and can observe a room they occupy. Testimony and examination
   remain private. The single-module boundary still relies on disciplined
   code and tests.
4. **Organism decisions.** Attempts follow a visible one-on-one opportunity,
   current needs and recovery. The policy has no deliberate search or
   deception planning.
5. **Routine plausibility.** Movement, work and rest are visible, but shifts,
   replenishment and medical consequences remain absent. The model is too
   coarse to validate believable routines over calibrated days.
6. **Without an outbreak.** All 50 ordinary runs continued with human agents
   pursuing needs and duties.
7. **Recovery.** Backup can sustain heat temporarily. Main power returns
   after refueling when a reserve is present. Once the reserve is exhausted,
   there is no resupply.
8. **Sensitivity.** Seeds change schedules, encounters and outcomes.
   Starting fuel availability controls whether a short run sees an outage.
9. **Pathologies.** Movement dominates the event stream. Exhausted supplies
   yield saturated needs without decline or death. Cold distress can
   generate many examinations, and examination is a deterministic stand-in.
10. **Next priorities.** Calibrate time and ordinary shifts, add resource
    stewardship and consequences of deprivation, separate local perception
    from objective state at the policy boundary, and replace the simple
    examination with evidence that can remain ambiguous. Expand causal
    capture beyond the selected event chains.

The results support a working headless prototype with reproducible simulations
and usable observer tools. They leave the multi-day realism criterion open.
Organism injury, death, release from containment, broader cooperation,
full decision traces and graphical cameras remain unimplemented.
