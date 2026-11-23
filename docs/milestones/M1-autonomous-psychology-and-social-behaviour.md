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

### Decision traces

The terminal observer's `decisions NAME [N]` command displays evaluated
options in order, the conditions that informed the selected intent, and
whether that intent resolved. Each record links events emitted during
resolution by ID. Later end-of-tick encounter outcomes still use the
objective event history. The observer retains 32 decisions per inhabitant.
The policy records only alternatives it reached before short-circuiting.
It still uses the existing priorities.

### Dispositions slice

Each inhabitant now has seeded cooperativeness and caution. A scenario can
override either trait by passing named `Disposition` profiles to
`Simulation`. Profiles remain stable during the run. The observer shows
them with `inspect NAME` and shows the actual calculation with
`decisions NAME`.

Cooperativeness biases a help decision alongside trust, hunger and fatigue.
Exhaustion can still override a strong willingness to help. Caution adjusts
the level of local concern at which an inhabitant leaves a room. Neither
trait adds evidence or gives access to another agent's private state.
Trait effects are intentionally limited to these two decision rules.

M1-D03 uses two recipients with the same trust, fatigue, hunger and request.
Their different cooperation profiles yield opposite responses. High trust
can overcome a low cooperation bias, and fatigue can override a high one.
The caution fixture similarly keeps concern fixed while varying disposition.

Three ordinary ten-day histories matched the preceding slice exactly.
Across 50 hidden-organism runs at 240 ticks, three histories changed,
completed assimilations rose from 95 to 96, and completed containments
remained at 14. Across 50 low-fuel runs at 60 ticks, histories matched
exactly. Those runs did not generate help responses, so the controlled
request comparison supplies the evidence for that mechanism.

### Learning from cooperation

When someone finishes another inhabitant's refueling work, the original
worker learns from the assistance if present and awake. The relationship
retains a count and the most recent supporting event ID after raw memories
age out. The count adds up to 15 points to future generator help scores.
General trust and suspicion testimony continue to use their existing rules.
Bystanders and absent initiators do not acquire this participant experience.

The M1-D08 fixture follows a witnessed refuel completion to a later request.
The original worker changes from declining at a score of 62 to accepting
at 67. A departed worker gains no trust from the same completion. Nine
seeded event histories matched the preceding slice. They do not exercise a
later request influenced by prior assistance, so that effect is verified
with the controlled fixture.

### Evidence-based interpersonal memory

Each relationship keeps twelve recent significant evidence records alongside
its accumulated expectations. The record distinguishes firsthand experience
from a report checked against a later observation. It points to the original
event and, when relevant, to the promise or report it evaluates. Category
watermarks and the last verified food origin prevent duplicate credit after
details roll off. Older out-of-order evidence can be dropped by those
watermarks. Familiarity still counts observed contact separately and stores
the most recent contact event.

| Dimension | Evidence | Decision effect |
| --- | --- | --- |
| Generator competence | Witness a colleague complete one's refueling work | Adds up to 15 to generator help decisions |
| Commitment reliability | Witness a promise and its later fulfillment or explicit withdrawal | Adjusts later generator help scores |
| Willingness to help | Receive observable assistance or a decline | Ranks eligible local helpers |
| Food-report credibility | Check a report against a subsequent firsthand stock observation | Adjusts confidence in future food reports only |

A refusal affects willingness without counting as a broken promise.
A later empty store leaves a positive report unresolved because supplies may
have run out since delivery. A pending report can be
replaced by a newer report. The model treats a corroborating observation as
support for the report, with no guarantee about past stock or the speaker's
honesty. Caution increases the weight of contradiction and withdrawal.
Objective history supplies evidence only after an agent witnesses the
relevant event or receives the report. Conversion clears learned
relationship state and pending testimony for the new controller, while
others retain their experiences with that body.

The observer's `inspect NAME` output contains relationship dimensions and
provenance. `decisions NAME` shows learned terms in help scores and the
event IDs still retained for those terms. The food-report event explanation
records the confidence adjustment when applicable.

Compared with merged PR #6, 39 seeded runs kept the same ordered action
sequences and social action counts. The comparison covered three ordinary
ten-day runs, 12 low-fuel runs, 12 hidden-organism runs and 12 ration-shortage
runs. The revised system retained 11 firsthand assistance records across the
low-fuel runs, and 253 corroborated food reports across the shortage runs
with 542 messages. Hidden-organism runs still produced 74 warnings,
16 completed assimilations and three containments. The sampled histories
did not contain a naturally occurring follow-up request changed by prior
learning. Controlled tests exercise altered helper selection, promise
withdrawal, contradictory reports, and evidence rollover. The established
long-lived refueling setup and the lack of autonomous restocking remain
limitations.

### Structured communication and conflicting testimony

The first topic is galley stock. A semantic message carries a topic, an
act (observation, claim, question, answer, doubt, or challenge), optional
evidence, and a reference to the conversation event it answers or disputes.
Messages travel between co-located individuals. Observations are local.
The message ledger records the originating observation and the IDs of
each transmission. Relays preserve the strength of the individual
evidence they convey. They don't attribute a combined belief score to
one origin.

Each inhabitant keeps the twelve most recent distinct origins. Two paths
from the same observation occupy one slot, with the stronger path retained.
Direct experience makes earlier claims irrelevant to the current stock
estimate. More recent reports remain eligible. Testimony is discounted by
the recipient's trust and food-report credibility. Independent available
and unavailable weights are summed and capped at 100 per side. A gap of
less than 20 leaves the belief unresolved. These values are tuning
assumptions. A newer or more confident claim alone does not erase the
opposite evidence. With an unresolved conflict and a need to eat, an
inhabitant can question the most credible local peer they have not asked
since their last direct observation. They wait one tick if the peer stays
nearby and can then seek firsthand evidence. Replies are autonomous;
doubts and challenges are currently resolver actions exercised by tests.

Use `inspect NAME` to see retained evidence, delivery paths, and support
scores. `decisions NAME` links selected questions and food decisions to
their evidence and transmissions. `trace ID` follows observation,
delivery, and reply references. General trust is unaffected by an
incorrect food report. The separate food credibility score can recover
with later corroboration.

The test suite covers differing interpretations of the same claim,
a stale claim held as belief, independent corroboration, repeated
intermediaries, conflicting evidence, private delivery, challenge
provenance, and deterministic reply and action resolution. One controlled
scenario seeds conflicting firsthand histories. The agents then
autonomously ask, answer, reconsider, move and eat. In the natural
ration-shortage seed 1, Kiran asks Ivo at tick 368. The answer leaves the
two support scores tied. Kiran checks the galley at tick 372 and revises
the belief from firsthand evidence.

#### Comparison with PR #7

Action sequences matched in three ordinary ten-day runs, 12 low-fuel
runs, and 50 hidden-organism runs. All 12 ration-shortage runs changed.
Use `python3 -m assimilation.batch --multiday --seeds 12 --ticks 800`
to reproduce the ration-shortage configuration. The comparison checked
food accounting and event references and found identical survival counts.

| Ration-shortage outcome, seeds 1–12, 800 ticks | PR #7 | This slice |
| --- | ---: | ---: |
| Reports | 542 | 564 |
| Questions / answers | 0 / 0 | 68 / 64 |
| Moves | 7,797 | 7,639 |
| Meals | 864 | 864 |

Questions and delays are expected when evidence conflicts. Fewer moves
and more reports are secondary effects of revised decisions and group
timing. None of the naturally sampled answers turned an unresolved
conflict directly into a settled belief. The controlled scenario
demonstrates that path. No behavior was tuned to hit a target outcome.

This model covers one topic and bounded evidence. It has no general
model of deception, no temporal decay between observations, and no
sub-tick conversations. Strong support on both sides can saturate and
leave a tie. Older information can be dropped after the evidence budget
fills. Notion was unavailable as a connected source for this slice, so
the repository specification and the supplied requirements were used.
