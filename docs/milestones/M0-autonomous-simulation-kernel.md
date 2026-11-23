# ASSIMILATION — Milestone 0 Specification
## M0: Autonomous Simulation Kernel

**Status:** Proposed implementation specification\
**Date:** 23 November 2026\
**Repository:** https://github.com/b392da-sketch/Assimilation\
**Implementation agent:** Codex\
**Intended repository document:** `docs/milestones/M0-autonomous-simulation-kernel.md`

---

## 1. Purpose

Build the first executable version of ASSIMILATION: a deterministic, autonomous, causally driven simulation of a small Antarctic research station inhabited by independent human agents and, optionally, an assimilating extraterrestrial organism.

M0 is a **proof of the project's underlying simulation philosophy**, not an attempt to produce a finished game.

The simulation must demonstrate that agents with different goals, knowledge and capabilities can interact with a persistent physical environment and generate distinct histories without predetermined story events.

Its success will be judged by the coherence of its mechanisms, not by the frequency of dramatic outcomes.

### Foundational principle

> Events follow from causes. The simulation does not choose events because they would make an interesting story.

This requirement applies to the organism, the human characters, environmental processes, social interactions and ultimately the player.

---

## 2. Existing project context

The repository currently contains a minimal README and no established implementation.

Codex should establish the initial project structure rather than assume that a simulation engine already exists.

The broader research is contained in nine ASSIMILATION research dossiers in Notion. Relevant dossiers include:

- [02 — Biological Models and Assimilation Mechanics](https://app.notion.com/p/421d0e0c758e81bdab02e49cd44d6cc7)
- [03 — Consciousness, Memory and Organism Intelligence](https://app.notion.com/p/421d0e0c758e813597dddcedd7cec01c)
- [04 — Detection, Evidence and Containment](https://app.notion.com/p/421d0e0c758e815aa8dc2faf77b2)
- [06 — Distributed Intelligence, Fission and Fusion](https://app.notion.com/p/421d0e0c758e815795ccee7c665bfb65)
- [07 — Organism Motives, Learning and Strategic Reasoning](https://app.notion.com/p/421d0e0c758e81dab311f3534b3a33fa)
- [08 — Suspicion, Social Contagion and Collective Reasoning](https://app.notion.com/p/421d0e0c758e811a876af8f678236633)
- [09 — Antarctic Station Operations, Layout and Infrastructure](https://app.notion.com/p/421d0e0c758e8151bf09f7ad6eb08fb8)

These research documents contain hypotheses and competing models, not merely final project decisions. Treat their provisional recommendations as experimental assumptions unless separately approved.

If Codex cannot access Notion, this M0 document must remain sufficient for initial implementation.

---

## 3. Exact scope of M0

The first implementation should contain seven integrated subsystems.

### 3.1 Time and world state

Implement a central simulation clock and persistent world state.

Requirements:

- Configurable time advancement.
- Actions occupying simulation time.
- Reproducible seeded randomness.
- Explicit ordering of simultaneous events.
- No dependence on real-world elapsed time for simulation outcomes.
- Persistent records of entities, locations, resources and ongoing actions.
- One authoritative state transition pathway.
- Ability to terminate and inspect a completed simulation run.

A simple fixed-step or deterministic event-driven architecture is acceptable. Codex should justify the approach selected.

### 3.2 Station environment

Implement one fictional Antarctic research station.

For the first version, use a compact connected graph containing approximately 12–20 meaningful locations, including:

- Living quarters.
- Kitchen and mess.
- Common room.
- Medical room.
- Laboratory.
- Communications room.
- Stores.
- Workshop.
- Generator room or powerhouse.
- Exterior routes between selected structures.

Exact room counts and layout should be configurable.

Represent:

- Location and connectivity.
- Travel time.
- Access restrictions.
- Capacity where relevant.
- Basic visibility and audibility.
- Indoor versus exterior routes.
- Simplified temperature and weather exposure.

Include a minimal infrastructure model:

- Main electrical supply.
- Backup electrical supply.
- Finite fuel.
- Basic heating dependency.
- One functioning communications system.
- A small number of condition-dependent maintenance tasks.

Failures must be consequences of actual system conditions, not scheduled dramatic events.

Do not attempt detailed engineering or thermodynamic simulation in M0.

### 3.3 Human agents

Implement twelve autonomous human agents by default.

Each must possess:

- Stable individual identity.
- Primary occupation.
- A few differentiated skills.
- Basic physiological needs.
- Current location.
- Personal goals.
- Routine responsibilities.
- Memory of relevant events.
- Individual beliefs.
- Social relationships.
- An autonomous action-selection process.

Use a heterogeneous fictional crew inspired by Dossier 09.

The first implementation must allow agents to:

1. Move between locations.
2. Work on assigned or self-selected tasks.
3. Eat.
4. Rest.
5. Communicate.
6. Observe nearby events.
7. Investigate something unusual.
8. Respond to immediate physical threats.
9. Request assistance.
10. Cooperate with or refuse another agent.

Ordinary work, sleep and meals should provide the behavioural baseline.

Agents must not spend all their time investigating alien activity.

Their activities should continue plausibly even in simulations where no organism exists.

### 3.4 Autonomous decision-making

Use a compact, explainable decision architecture.

A utility-based approach with persistent goals and intentions is a reasonable starting point, although Codex may propose an alternative.

An agent's action choice must depend on:

- Available knowledge.
- Current needs.
- Goals.
- Skills and physical capabilities.
- Expected consequences.
- Relationships.
- Feasible opportunities.
- Relevant uncertainty.

Implement a mechanism that allows agents to continue pursuing a reasonable intention without reconsidering every possible action at every simulation instant.

Agents should reconsider plans when important circumstances change.

Different personalities should have mechanically meaningful consequences, but avoid arbitrary character classes.

There must be a feasible *do nothing*, *wait*, *rest* or *continue current task* option.

A character must not be forced to perform an extraordinary action merely because a sufficiently long period has passed.

### 3.5 Perception, knowledge and communication

This subsystem is a strict requirement, not an optional enhancement.

Separate:

**Objective world state:** What is actually happening.

**Observation:** What a character legitimately perceives.

**Belief:** What that character concludes.

**Testimony:** What another character communicates.

**Action:** What the character decides to do.

Every character must possess a private knowledge state.

Agents must not directly access objective infection status, inaccessible locations, unseen actions or another agent's internal beliefs.

Information may be acquired through:

- Direct observation.
- Explicit communication.
- Inspection of accessible evidence.
- Valid inference from previously acquired information.

Messages should retain at least basic source provenance.

If A observes an event and tells B, and B tells C, C has received second-hand testimony, not witnessed the original event.

A character may reject credible information, accept false information or remain uncertain.

Implement an elementary belief-revision mechanism without attempting a fully developed cognitive science model.

### 3.6 Social interaction

Implement a small but persistent interpersonal relationship model.

At minimum, distinguish:

- Trust.
- Familiarity.
- Perceived competence.
- Willingness to cooperate.

Agents must have different initial relationships.

Their relationships should change because of actual encounters, communications and observed conduct.

Social interaction must not guarantee compliance.

A request for assistance should be evaluated by the recipient independently.

Basic suspicion may arise from observations and testimony, but M0 does not require complex faction formation or sophisticated collective politics.

Do not implement a global paranoia variable.

### 3.7 Minimal organism

Implement one autonomous organism, configurable as present or absent at simulation initialization.

The initial organism should inhabit or imitate one station resident, using the same spatial and action-resolution systems as human agents.

It must have:

- An individual identity and lineage reference.
- Physical viability and condition.
- Goals associated with survival and propagation.
- Limited access to information.
- An autonomous decision policy.
- The ability to maintain an ordinary disguise.
- One abstract, constrained assimilation mechanism.
- The ability to fail, be interrupted or die.

For M0, the assimilation process may be simplified, but it must have explicit preconditions and time or resource costs.

Use a documented experimental biological model. Do not treat it as the project's permanently selected biology.

When a human becomes assimilated, the world state must preserve the distinction between the original human identity, physical body and organism now controlling that body.

An organism may attempt assimilation when a feasible opportunity exists; it must not be forced to attack at predetermined intervals.

Different organism decisions should arise from differences in perception, risk, opportunity and goals.

The organism must not receive universal knowledge of the human population's movements or hidden information.

Detailed transformation, fragmentation, distributed intelligence and memory-copying systems are outside M0.

---

## 4. Observer mode

Implement the foundation of Observer Mode as a read-only interface.

A terminal-based or lightweight local interface is sufficient.

The observer should be able to:

- Start a simulation with a chosen seed and configuration.
- Pause and advance the simulation.
- Inspect current simulated time.
- Examine agent locations and activities.
- Inspect individual needs, goals and intentions.
- Inspect objective infection status.
- Examine an agent's private knowledge.
- Review recent significant events.
- Inspect an event's basic causal explanation.
- Export event histories for later analysis.

The observer may access omniscient information, but this must never influence the behaviour of simulated agents.

No graphical rendering is required.

The interface should be designed so that a graphical observer can eventually replace or supplement it without changing the simulation engine.

---

## 5. Required initial scenarios

M0 must support two baseline configurations.

### Scenario A — Ordinary Antarctic operations

Twelve uninfected human agents occupy a functioning station.

There is no extraterrestrial organism.

The simulation should demonstrate ordinary activity, interpersonal contact, routine technical work and responses to environmental conditions.

The absence of an organism must not cause agents to behave inexplicably or produce artificial horror events.

### Scenario B — Hidden organism

The same station and population structure exist, but one inhabitant is initially assimilated.

The organism is autonomous.

Other inhabitants do not automatically know that it exists.

The simulation should permit concealment, encounters, investigation, assimilation attempts, incorrect judgments and possible containment.

It does not need to produce all these outcomes in every run.

Both scenarios must use the same engine.

---

## 6. Architectural requirements

Codex should establish clear boundaries between:

- Simulation clock and event scheduling.
- Objective world state.
- Station environment and infrastructure.
- Agent physical state.
- Cognition, memory and beliefs.
- Goals, intentions and action selection.
- Communication and social relationships.
- Organism biology.
- Action resolution.
- Event logging.
- Observer interface.

Avoid tightly coupling presentation to simulation mechanics.

### Important invariants

- Every entity has a persistent identifier.
- Every agent occupies a valid location.
- Resources cannot be consumed without existing.
- Actions require appropriate preconditions.
- Information cannot appear in an agent's beliefs without a legitimate information pathway.
- Biological transformations cannot create contradictory agent identities.
- The observer does not mutate simulation state.
- No subsystem may silently modify the world outside the authorized transition mechanism.
- Identical starting conditions, seeds, configurations and inputs must reproduce identical event histories within a given implementation version.

Use explicit, documented data structures.

Avoid excessive abstraction before the simulation demonstrates a need for it.

---

## 7. Causal event logging

Every consequential event should be recorded with enough information to reconstruct what happened.

Suggested fields:

- Event ID.
- Simulation timestamp.
- Event type.
- Involved entities.
- Location.
- Preconditions.
- Initiating action or environmental cause.
- Resulting state changes.
- Observers or information recipients.
- Relevant parent or contributing event IDs.

For autonomous decisions, include the relevant goal, observed beliefs, considered alternatives and actual evaluation where reasonably practical.

Do not generate plausible-sounding explanations after the fact that differ from the actual decision logic.

The event system should distinguish:

- What happened.
- What agents observed.
- What agents believed.
- Why an action was chosen.
- What consequences followed.

Store events in a machine-readable format such as JSON Lines.

The logs should support both automated testing and human inspection.

---

## 8. Demonstrations Codex must produce

### D1 — Ordinary continuity

Run Scenario A for multiple simulated days.

Agents should carry out ordinary duties, move, rest, communicate and respond to needs without requiring scripted emergencies.

### D2 — Independent action

Two agents with different goals, skills or knowledge face the same situation.

Their choices should differ for understandable reasons.

### D3 — Information isolation

One agent witnesses an unusual event in a secluded location.

An agent elsewhere must remain unaware until a legitimate communication or observation pathway supplies information.

### D4 — Testimony and uncertainty

An agent communicates a claim.

The recipient must evaluate the message as testimony, not receive the originating observer's private state.

### D5 — Environmental consequence

A generator fails because of a test-injected physical condition or a legitimate equipment process.

Backup supply and repair options influence the actual outcome.

No mandatory blackout or dramatic escalation.

### D6 — Autonomous organism

An organism may conceal itself, move, pursue routine tasks and identify possible opportunities for assimilation.

Its actions must depend on its information and circumstances.

### D7 — Interrupted assimilation

A conversion attempt can fail or be interrupted when its physical conditions cease to be satisfied.

The result must be internally consistent.

### D8 — Reproducibility

Run the same scenario twice with identical inputs.

World states and ordered events must match.

### D9 — Variation

Change initial conditions, environmental parameters or random seeds.

Different interactions and event sequences should become possible.

### D10 — Causal inspection

Select a significant event from an actual run and reconstruct its contributing conditions and decisions from the recorded data.

Do not substitute a scripted demonstration for an actual engine-generated history.

---

## 9. Automated testing

Implement automated tests covering:

1. Seed determinism.
2. Valid location movement.
3. Resource accounting.
4. Action preconditions.
5. Physical state consistency.
6. Agent needs and task progression.
7. Private knowledge isolation.
8. Legitimate communication.
9. Message provenance.
10. Independent responses to requests.
11. Infection-state consistency.
12. Assimilation failure and interruption.
13. Observer nonintervention.
14. Event-history consistency.
15. Long-running simulation stability.

Tests should include both unit-level invariants and integrated simulations.

Use controlled scenario fixtures to test mechanics. A deterministic fixture is not equivalent to scripting the production narrative.

---

## 10. Batch experimentation

Build an automated runner for multiple seeded simulations.

For the initial evaluation, attempt **100 runs** across baseline and organism-present configurations, using documented scenario parameters.

Record:

- Seed and configuration.
- Simulated duration.
- Initial and final population states.
- Number of assimilation attempts and outcomes.
- Human and organism survival.
- Significant equipment failures.
- Agent movements and encounters.
- Knowledge transfers.
- Suspicion or accusation events, if implemented.
- Total executed actions.
- Event counts.
- Runtime and memory usage.
- Invalid or contradictory state counts.

Do not require a particular proportion of infected survivors or dramatic endings.

If the simulator produces repetitive or implausible behaviour, investigate the underlying mechanisms rather than manually forcing variety.

If the computational cost of 100 runs is excessive, report the completed number and observed performance limitations instead of fabricating results.

---

## 11. Explicitly excluded from M0

The following features are important to the eventual game but should not be implemented in this milestone unless a strictly necessary foundational interface requires them.

- Graphical 3D or 2D game world.
- Direct player-controlled Character Mode.
- Full gameplay transformation from human to organism.
- Final game-over screen and post-death UI.
- Detailed dialogue generation using language models.
- Sophisticated social factions or political structures.
- Comprehensive human psychological simulation.
- Complex alien transformation animations.
- Individual cellular simulation.
- Autonomous microscopic fragments.
- Full organism fission and fusion.
- Complex organism communication networks.
- Detailed epidemiological modelling.
- Realistic industrial power-system engineering.
- Elaborate medical diagnosis or blood-testing systems.
- Exterior rescue expeditions.
- Complete outside-world simulation.
- Multiplayer.
- A fixed campaign narrative.
- Scripted suspense, jump scares or dramatic pacing.

Future requirements must be accommodated where reasonably possible without implementing them prematurely.

---

## 12. Technical approach

Codex should evaluate and select an appropriate implementation language and architecture.

**Python 3.12 or later is a reasonable default candidate** for the first headless version because it facilitates deterministic simulation, debugging, automated testing, batch experiments and scientific analysis.

A different language is acceptable if Codex can justify its advantages.

Prefer:

- Minimal runtime dependencies.
- Readable and modular code.
- Declarative scenario configuration.
- Explicit state transitions.
- Standardized event serialization.
- A simple command-line interface.
- Automated tests and continuous integration.
- Documented reproduction commands.

Avoid premature graphical-engine dependencies.

Do not use an LLM as the fundamental action-selection mechanism.

Do not modify Origins or other projects.

---

## 13. Repository deliverables

Codex should create the project structure appropriate to its selected architecture.

Expected deliverables:

1. `README.md` — project description, setup, execution and current scope.
2. `docs/milestones/M0-autonomous-simulation-kernel.md` — the formal specification.
3. Architecture documentation explaining components and state boundaries.
4. Executable simulation engine.
5. Baseline scenario configurations.
6. Autonomous human and organism agents.
7. Read-only observer interface.
8. Structured event logging.
9. Automated test suite.
10. Batch evaluation utility.
11. Reproducible example runs.
12. M0 evaluation report discussing successes, weaknesses and limitations.
13. Suggested next technical and research priorities.

An implementation report must distinguish completed features from stubs and future intentions.

---

## 14. Acceptance criteria and definition of done

M0 is complete only when:

- A clean checkout can be installed and run using documented instructions.
- Both baseline scenarios execute.
- Twelve autonomous agents perform coherent activities over multiple simulated days.
- Agents possess genuinely separate information states.
- Communications transmit information only through valid mechanisms.
- The organism follows the same world and action rules as humans.
- Assimilation can succeed, fail or be interrupted according to explicit conditions.
- Environmental changes have persistent consequences.
- No prewritten narrative is required for simulation progression.
- Deterministic replay succeeds.
- The observer can inspect world and agent states without affecting them.
- Integrated tests pass.
- Batch evaluation produces usable quantitative and qualitative reports.
- Significant limitations are documented rather than concealed.

### Required independent review questions

Codex must explicitly answer:

1. Which behaviours emerged from interactions rather than being directly prescribed?
2. Which behaviours remain artificially rigid or repetitive?
3. Are agents making decisions using information they could not possess?
4. Are organism decisions causally intelligible?
5. Are ordinary station routines believable?
6. Can the simulation proceed meaningfully without an outbreak?
7. Can the environment recover from minor failures?
8. How sensitive are outcomes to initial conditions?
9. Are any mechanics producing implausible or pathological behaviour?
10. What must be changed before adding greater cognitive or biological sophistication?

---

## 15. Development workflow for Codex

Work in the existing GitHub repository:

https://github.com/b392da-sketch/Assimilation

1. Inspect the default branch and repository contents.
2. Place this specification in the repository.
3. Propose the initial architecture and identify assumptions.
4. Create a dedicated M0 development branch.
5. Implement the smallest coherent simulation vertical slice.
6. Add automatic tests before expanding into more complex systems.
7. Demonstrate ordinary station operation without an organism.
8. Integrate one autonomous organism with limited knowledge.
9. Test information isolation and assimilation mechanics.
10. Run deterministic experiments across seeds.
11. Produce an evidence-based evaluation report.
12. Open a pull request for independent review.

Do not merge the work automatically.

Do not introduce major fictional biological rules as permanent canon merely to solve implementation problems.

Use explicit, replaceable assumptions for unresolved mechanics.

Where an experimental simplification is necessary, document it.

**Most importantly, do not confuse simulation complexity with simulation quality.**

A small world whose inhabitants behave coherently and unexpectedly is a better M0 result than an enormous system containing hundreds of superficially implemented features.

---

## 16. Final instruction

The purpose of M0 is to establish that ASSIMILATION can generate believable histories without depending on a writer to select what happens.

If we remove the extraterrestrial organism, the station must remain a functioning community.

If we introduce the organism, it must act within the same physical world and informational constraints as every other inhabitant.

If the organism is destroyed immediately, the simulation must continue.

If no one ever discovers the organism, the simulation must continue.

If humans accuse one another incorrectly, those mistakes must follow from their own experiences and reasoning.

If the inhabitants cooperate effectively and prevent a catastrophe, that must be a legitimate outcome.

**Build the world first. Then demonstrate that its events genuinely follow from its causes.**