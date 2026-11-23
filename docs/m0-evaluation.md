# M0 evaluation

## Reproduction

From the repository root, using Python 3.12 with no additional dependencies:

```bash
python3 -m unittest discover -s tests -v
python3 -m assimilation --seed 1 --ticks 1440
python3 -m assimilation --scenario low-fuel --seed 1 --ticks 60 --events
python3 -m assimilation --scenario hidden-organism --seed 10 --ticks 240 --events
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
| Resolved actions | 142,982 | 142,016 |
| Recorded events | 143,592 | 142,648 |
| Moves | 96,335 | 95,311 |
| Food and suspicion messages | 4,159 | 4,357 |
| Assimilation attempts / interrupted / completed | 0 / 0 / 0 | 76 / 73 / 3 |
| Runs with containment | 0 | 4 |
| Invalid states detected | 0 | 0 |
| Median traced seconds per run | 0.309 | 0.297 |
| Highest peak traced Python allocations | 4.05 MiB | 4.03 MiB |

No attempt remained pending at the batch cutoff. The three completions came
from seeds 19, 20 and 33. Neither batch scenario exhausted its main fuel before
the cutoff. No bodies died by the batch cutoff. The longer baseline and deprivation
fixtures exercise impairment and death.

## Independent review corrections

The original batch reported containment in 31 runs with immediate restraint
after a perfect exam. The revised batch yielded 38 anomalous, 18 clear
and six inconclusive examinations. Of 166 containment attempts, four
completed. A containment now requires two consecutive eligible actions,
and departure interrupts it. These counts measure the prototype rules
under the tested conditions.

The clock uses ten-minute ticks. Sustained maximum hunger or cold reduces
health. Severe impairment slows movement, and a controller can no longer
act when the body dies. Tests distinguish being alive and contained from
dying while contained.

## Demonstrations

| Spec | Evidence |
| --- | --- |
| D1 Ordinary continuity | Ordinary seed 1 reached ten simulated days (1,440 ticks) and produced 206 work actions. All twelve eventually died after food ran out, and the clock continued. |
| D2 Independent action | The same outage request is accepted or declined by recipients with different trust in the requester. The help test exercises both paths. |
| D3 Information isolation | The interruption test confirms that someone outside the room receives no original encounter observation. |
| D4 Testimony | The food testimony test confirms that relaying a report preserves the source chain and discounts confidence. The suspicion test verifies that reports do not become firsthand knowledge. |
| D5 Environment | Low-fuel seed 1 switched to backup on tick 6, lost power on tick 9, and restored it on tick 14 after physical refueling. |
| D6 Organism autonomy | Hidden-organism seed 19 shows routine activity, an organically generated private opportunity and a completed assimilation. Seed 10 shows examination and containment. |
| D7 Interruption | The room-arrival test interrupts an encounter after continuation was submitted in the same tick. The batch registered 73 interruptions. |
| D8 Reproducibility | Tests compared same-seed histories, ordinary final states, and interactive versus batch exports. |
| D9 Variation | Identical station settings produced successful conversions only in seeds 19, 20, and 33 and containment in four of the 50 hidden-organism runs. |
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
   replenishment remain absent. Ten-minute ticks make elapsed time measurable.
   Survival thresholds still need tuning.
6. **Without an outbreak.** All 50 ordinary runs continued with human agents
   pursuing needs and duties.
7. **Recovery.** Backup can sustain heat temporarily. Main power returns
   after refueling when a reserve is present. Once the reserve is exhausted,
   there is no resupply.
8. **Sensitivity.** Seeds change schedules, encounters and outcomes.
   Starting fuel availability controls whether a short run sees an outage.
9. **Pathologies.** Movement dominates the event stream. Stores have no resupply loop,
   so the prolonged baseline ends with all inhabitants dead. Cold distress
   can still generate many examinations.
10. **Next priorities.** Calibrate shifts and resource stewardship,
    separate local perception from objective state at the policy boundary,
    and exercise investigation across more scenarios. Expand causal
    capture beyond the selected event chains.

The results support a working headless prototype with reproducible simulations
and usable observer tools. They leave the multi-day realism criterion open.
Release from containment, broader cooperation,
full decision traces and graphical cameras remain unimplemented.
