from dataclasses import replace
import unittest

from assimilation.allegations import Accusation, SuspicionReport
from assimilation.kernel import Intent, Organism, PowerConfig, Room, Simulation, Station
from assimilation.observer import trace_event
from assimilation.policy import Disposition, choose


class AccusationTests(unittest.TestCase):
    def scenario(self):
        station = Station(
            (Room("commons", (), ("rest", "work")), Room("generator", ()), Room("remote", ())),
            "commons", power=PowerConfig("generator", 0, 0, 10_000),
        )
        simulation = Simulation(1, station)
        technician, suspect, accuser, skeptic, distant, *_ = simulation.inhabitants
        for inhabitant in simulation.inhabitants:
            inhabitant.room = inhabitant.duty_room = "remote"
            inhabitant.hunger = inhabitant.fatigue = 0
            inhabitant.disposition = Disposition()
        technician.room = technician.duty_room = "generator"
        for inhabitant in (suspect, accuser, skeptic):
            inhabitant.room = inhabitant.duty_room = "commons"
        suspect.fatigue = 12
        for observer, trust in ((accuser, 85), (skeptic, 35)):
            observer.relationships[suspect.name].trust = trust
            suspect.relationships[observer.name].trust = 85
        return simulation, suspect, accuser, skeptic, distant

    def test_false_suspicion_becomes_known_through_local_accusation(self):
        simulation, suspect, accuser, skeptic, distant = self.scenario()
        simulation.advance()
        incident = suspect.last_cold_distress_event
        self.assertIsNotNone(incident)
        self.assertEqual(simulation.history[incident - 1].action, "rest")
        self.assertEqual(accuser.witnessed_concerns[suspect.name].origin_event, incident)
        self.assertFalse(suspect.accusations_received)
        self.assertFalse(distant.accusations_received)
        self.assertNotIn(suspect.name, simulation.organisms)
        self.assertFalse(simulation.resolve(distant, Intent("accuse", subject=suspect.name)))

        simulation.advance_ticks(42)
        allegation = next(event for event in simulation.history if event.action == "accuse")
        self.assertIn(suspect.name, {name for name, _ in allegation.observations})
        self.assertNotIn(distant.name, {name for name, _ in allegation.observations})
        self.assertEqual(allegation.message.suspicion.origin_event, incident)

    def test_autonomous_explanation_changes_one_judgment_and_leaves_another(self):
        simulation, suspect, accuser, skeptic, _ = self.scenario()
        simulation.advance_ticks(50)
        adjudications = {
            event.actor: (index, event)
            for index, event in enumerate(simulation.history, 1)
            if event.action in ("concern_reconsidered", "concern_maintained")
        }
        index, changed = adjudications[accuser.name]
        _, maintained = adjudications[skeptic.name]
        self.assertEqual(changed.action, "concern_reconsidered")
        self.assertEqual(maintained.action, "concern_maintained")
        self.assertIn("from 20 to 10", changed.reason)
        self.assertIn("from 20 to 20", maintained.reason)
        self.assertEqual(
            [event["action"] for event in trace_event(simulation, index)],
            ["rest", "accuse", "explain_accusation", "concern_reconsidered"],
        )
        self.assertTrue(any(
            record.decision.intent.action == "explain_accusation" and record.resolved
            for record in simulation.decision_records[suspect.name]
        ))
        replay, *_ = self.scenario()
        replay.advance_ticks(50)
        self.assertEqual(replay.history, simulation.history)
        self.assertEqual(replay.decision_records, simulation.decision_records)
        self.assertEqual(replay.random.getstate(), simulation.random.getstate())

    def test_consent_and_refusal_do_not_imply_a_belief_about_infection(self):
        simulation, suspect, accuser, _, _ = self.scenario()
        while simulation.tick < 55 and not suspect.examination_requests:
            simulation.advance()
        self.assertTrue(suspect.examination_requests)
        view = simulation.perceive(suspect)
        social = view.accusation_view
        ready = replace(view, accusation_view=replace(social, examiner_trust=90),
                        fatigue=0, sleeping=False)
        consent = choose(ready)
        refusal = choose(replace(ready, fatigue=ready.rest_threshold))
        self.assertEqual(consent.intent.action, "consent_examination")
        self.assertEqual(refusal.intent.action, "refuse_examination")
        examiner = simulation.agents_by_name[refusal.intent.recipient]
        before = examiner.concern_about(suspect.name)
        self.assertFalse(simulation.resolve(examiner, Intent("cooperative_exam", subject=suspect.name)))
        self.assertTrue(simulation.resolve(suspect, refusal.intent))
        self.assertEqual(examiner.concern_about(suspect.name), before)
        self.assertNotIn(suspect.name, examiner.examination_consents)
        self.assertNotIn(suspect.name, examiner.examinations)

    def test_one_original_incident_does_not_become_multiple_observations(self):
        simulation, suspect, accuser, skeptic, distant = self.scenario()
        simulation.advance()
        distant.room = "commons"
        for witness in (accuser, skeptic):
            distant.relationships[witness.name].trust = 80
            self.assertTrue(simulation.resolve(witness, Intent("warn", recipient=distant.name,
                                                               subject=suspect.name)))
        reports = list(distant.heard_concerns.values())
        self.assertEqual(len(reports), 2)
        self.assertEqual({report.origin_event for report in reports}, {suspect.last_cold_distress_event})
        self.assertEqual(distant.concern_about(suspect.name), 16)

        simulation.record(suspect, "rest", suspect.room, visible_as="uneasy_encounter")
        self.assertTrue(simulation.resolve(skeptic, Intent("warn", recipient=distant.name,
                                                          subject=suspect.name)))
        self.assertEqual(len({report.origin_event for report in distant.heard_concerns.values()}), 2)

    def test_hidden_identity_does_not_change_observers_or_survive_as_private_memories(self):
        simulation, suspect, accuser, _, _ = self.scenario()
        simulation.advance_ticks(50)
        before = simulation.perceive(accuser)
        simulation.organisms[suspect.name] = Organism(1, None, suspect.name)
        self.assertEqual(before, simulation.perceive(accuser))
        self.assertEqual(choose(before), choose(simulation.perceive(accuser)))

        # Convert a different body that held an accusation and a firsthand account.
        victim = accuser
        suspect.room = victim.room = "generator"
        for inhabitant in simulation.inhabitants:
            if inhabitant not in (suspect, victim):
                inhabitant.room = "remote"
        victim.accusations_received[suspect.name] = Accusation(
            suspect.name, SuspicionReport(suspect.name, victim.name, simulation.tick, 20),
            1, simulation.tick + 4,
        )
        self.assertTrue(simulation.resolve(suspect, Intent("assimilate", recipient=victim.name)))
        simulation.tick += 1
        self.assertTrue(simulation.resolve(suspect, Intent("assimilate", recipient=victim.name)))
        simulation.finish_encounters()
        self.assertIn(victim.name, simulation.organisms)
        self.assertFalse(victim.accusations_received)
        self.assertFalse(victim.accusations_made)
        self.assertFalse(victim.reconsiderations)
        self.assertIsNone(victim.last_cold_distress_event)

    def test_same_cue_explanation_or_question_depends_on_accused_context(self):
        simulation, suspect, _, _, _ = self.scenario()
        simulation.advance_ticks(43)
        view = simulation.perceive(suspect)
        explanation = choose(view)
        self.assertEqual(explanation.intent.action, "explain_accusation")
        skeptical = replace(view, accusation_view=replace(view.accusation_view, accuser_trust=30))
        question = choose(skeptical)
        self.assertEqual(question.intent.action, "question_accusation")
        self.assertTrue(simulation.resolve(suspect, question.intent))
        self.assertEqual(simulation.history[-1].message.kind, "question evidence")

    def test_coercive_action_depends_on_willingness_separately_from_evidence(self):
        simulation, suspect, accuser, _, _ = self.scenario()
        accuser.examinations[suspect.name] = "anomaly"
        view = simulation.perceive(accuser)
        self.assertEqual(choose(view).intent.action, "contain")
        reluctant = replace(view, disposition=Disposition(cooperativeness=-5))
        self.assertNotEqual(choose(reluctant).intent.action, "contain")
        self.assertEqual(reluctant.peers, view.peers)
