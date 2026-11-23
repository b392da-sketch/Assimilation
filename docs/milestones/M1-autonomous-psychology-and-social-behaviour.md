# ASSIMILATION — Milestone 1 Development Specification

## Autonomous Psychology, Social Behaviour and Temporal Foundations

Working summary of the proposed specification dated 24 November 2026.
The engineering baseline is the merged M0 kernel.

## Mission

Develop twelve psychologically differentiated and socially autonomous
inhabitants. Enduring personal characteristics interact with changing
conditions, acquired knowledge, individual goals, and relationships.
Cooperation, distrust, accusations, disagreements, and danger responses
follow from those causes. The simulation does not choose outcomes for drama.

## Temporal model

At normal speed, a simulated minute corresponds to a real minute. Keep four
responsibilities distinct: authoritative logical time, deterministic engine
execution, a playback controller, and presentation. Given the same initial
conditions, seed, inputs, and software version, execution speed and the
size of advancement calls must leave outcomes identical. Test this with a
controllable clock.

Observer playback supports pause, normal speed, and configurable acceleration.
Batch runs advance without waiting. Eventual Character Mode defaults to 1×,
with opportunities for waiting and sleeping to accelerate time while the
world continues to run and interruptions remain possible.

Actions ultimately need durations from seconds to hours or longer, depending
on the task, participants, and conditions. Movement, doors, conversations,
meals, inspections, examinations, repairs, sleep, struggles, and assimilation
may be interruptible, cancellable, or continuable according to their rules.
The ten-minute M0 step is a prototype resolution. M1 establishes the temporal
architecture and demonstrates it headlessly through incremental changes.

## M1.1 — Agent architecture and bounded cognition

Distinguish objective conditions, perception, memory, belief, goals,
intentions, and attempted actions. Provide an explicit individual view.
The policy may use that view and the agent's own state. The authoritative
engine checks physical conditions when resolving intentions. Use a compact,
inspectable policy with persistent commitments, evaluated alternatives,
and decision explanations derived from recorded inputs and actual evaluations.

## M1.2 — Individual psychology

Give individuals configurable and persistent dispositions such as
sociability, caution, curiosity, cooperativeness, and threat sensitivity.
Dispositions act conditionally alongside constraints and competing motives.
Distinguish needs, occupational duties, personal interests, social
commitments, long-term goals, and emergencies. Model a small set of emotional
and physiological influences, such as stress and fatigue, without forcing
scripted reactions. Use personal histories and experiences to shape later
decisions without making personalities unstable.

## M1.3 — Memory, inference, and learning

Distinguish observations, testimony, inference, speculation, and contradicted
claims, with provenance and timestamps. Agents can learn routines,
recognize recurring behavior, remember cooperation and disagreement,
revise expectations after failure or contrary evidence, and retain uncertainty.
Memory and learning can be incomplete or mistaken. Bound storage through
explicit summarization and forgetting while preserving significant
commitments and interpersonal evidence.

## M1.4 — Relationships and communication

Use a small set of persistent, independently changing relationship dimensions,
such as trust, familiarity, and domain competence. Actual interactions
change them. Agents independently evaluate cooperation, disagreement, and
reconciliation. No global controller assigns alliances.

Use structured semantic acts for reporting, asking and answering questions,
requests and responses, warnings, challenges, reassurance, suggestions, and
coordination. Presentation can later express those acts in natural language.
Language generation does not supply authoritative facts or decisions.

## M1.5 — Suspicion, cooperation, and response to danger

Separate hearing a claim, considering it possible, believing it,
investigating, avoiding someone, requesting an examination, and supporting
or attempting containment. Preserve source chains so repeated accounts
remain distinguishable from independent witnesses. Characters may
misinterpret defensive behavior and may also recognize it as weak evidence.
Allow small groups to coordinate search, observation, assistance, technical
investigation, and precautions. Agreement and obedience remain individual.

Targets of assimilation should be able to perceive danger, flee, call for
help, or interrupt the encounter. Failure to react should follow from
circumstances such as surprise, incapacitation, or physical constraints.
Implement minimal target agency without detailed combat or new organism
anatomy. Do not tune probabilities to obtain a preferred number of outcomes.

## Evidence and acceptance

| ID | Demonstration |
| --- | --- |
| M1-D01 | Different playback rates reproduce events and state. |
| M1-D02 | Interrupting a long action preserves its actual duration and consequences. |
| M1-D03 | Differently disposed agents respond independently to the same request. |
| M1-D04 | False testimony can produce an incorrect belief without objective truth leakage. |
| M1-D05 | Multiple recipients of a rumour retain traceable sources. |
| M1-D06 | Two agents maintain different interpretations of an event. |
| M1-D07 | Correct evidence can conflict with low trust in the source. |
| M1-D08 | Reliable assistance can improve relevant trust. |
| M1-D09 | A wrongly accused person can respond defensively and prompt reconsideration. |
| M1-D10 | Independent witnesses remain distinguishable. |
| M1-D11 | Assimilation target perception and response have causal resolution. |
| M1-D12 | Ordinary multi-day routines and relationships remain viable without an organism. |
| M1-D13 | Contradictory information permits belief revision without consensus. |
| M1-D14 | A recipient independently weighs a trusted colleague's risky request. |
| M1-D15 | A significant social incident can be traced from observation to decisions and consequences. |

Use automated tests and comparative seed batches. Record limitations,
including what remains abstract, arbitrary, or unrealistic. Success does
not depend on producing particular numbers of accusations or assimilations.

## Research and scope

Use the engineering baseline and ASSIMILATION dossiers on [organism
reasoning](https://app.notion.com/p/421d0e0c758e81dab311f3534b3a33fa),
[suspicion and social reasoning](https://app.notion.com/p/421d0e0c758e811a876af8f678236633),
and [station operations and temporal design](https://app.notion.com/p/421d0e0c758e8151bf09f7ad6eb08fb8).
Treat unresolved research hypotheses as provisional.

Defer graphical gameplay, direct Character Mode controls, unrestricted
dialogue, LLM policy, high-fidelity animation, detailed combat, cellular
biology, fragments and fusion, epidemiology, complex factions, engineering
simulation, and scripted narrative.

## Incremental architecture and review

1. Keep the M0 deterministic step as a compatibility boundary and expose
   logical seconds independently. Pace those steps in a separate
   controller. Begin with headless evidence.
2. Introduce immutable local perception views. Move the policy to consume
   views and private cognition, with the kernel retaining physical validation.
3. Capture commitments and evaluation inputs as decision data. Introduce
   configurable profiles, experience, beliefs, and structured communication
   through those interfaces.
4. Expand durations and interruption where the evidence warrants it. Add
   target agency and social experiments using the same engine.
5. Run focused tests with each slice, compare seeded simulations with M0,
   report assumptions and gaps, and open reviewable pull requests. Merge
   decisions remain with the maintainer.

### Initial temporal slice

The engine retains ten-minute resolution and an authoritative logical
seconds projection. The controller accumulates elapsed monotonic wall time
at a selected rate and submits complete ticks in order. Sub-tick time is
retained across pauses. Batch execution advances exact ticks directly.
The terminal supports bounded real-time playback windows and explicit steps.

The mandatory deterministic-playback demonstration compares full state,
RNG state, and ordered events at 1×, 5×, 10×, and 60× with different elapsed
time sample sizes. Six archived-M0 comparisons matched the entire unpaced
event output for ordinary, low-fuel, and hidden-organism runs. An
interruption test verifies that moving cancels an existing M0 work block.
Finer action scheduling and policy perception views remain subsequent
slices. The dossier links were unavailable as a connected source for
this slice; the supplied specification governs its temporal design.

### Local perception slice

The policy takes a frozen view and returns an intent and updated routine
goal. Local peers are represented by names and observable cues. Their
private beliefs, remote locations and objective organism status stay
outside the input. The kernel constructs the view and rechecks physical
conditions when applying the intent.

Tests vary hidden facts without changing the view, exercise a visible cue,
and reject an intent after it becomes physically stale. Nine seeded event
exports match the previous slice byte for byte. Existing priorities are
preserved. Evaluating alternatives and recording decision reasons remain
open work.
