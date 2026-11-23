from dataclasses import replace
import unittest

from assimilation.communication import Evidence, FoodBelief, assess, retain
from assimilation.kernel import DEFAULT_STATION, Intent, Room, Simulation, Station
from assimilation.observer import trace_event


class StructuredCommunicationTests(unittest.TestCase):
    def test_duplicate_transmissions_and_independent_origins(self):
        ledger = []
        claim = FoodBelief(False, 1, ("Anika", "Bram"), 40, 1, (4,))
        retain(ledger, Evidence(claim))
        retain(ledger, Evidence(replace(claim, sources=("Anika", "Cleo", "Bram"),
                                       confidence=35, transmissions=(5, 6))))
        self.assertEqual(assess(ledger).unavailable_score, 40)
        self.assertEqual(assess(ledger).evidence_ids, (1,))

        retain(ledger, Evidence(FoodBelief(False, 1, ("Dev", "Bram"), 40, 2, (7,))))
        self.assertEqual(assess(ledger).unavailable_score, 80)
        retain(ledger, Evidence(FoodBelief(True, 1, ("Farid", "Bram"), 75, 3, (8,))))
        self.assertIsNone(assess(ledger).belief)
        retain(ledger, Evidence(FoodBelief(True, 2, ("Bram",), 100, 9), firsthand=True))
        self.assertTrue(assess(ledger).belief.available)

    def test_same_claim_leads_to_different_beliefs_without_truth_leakage(self):
        simulation = Simulation(1)
        speaker, trusting, skeptical, bystander, *_ = simulation.inhabitants
        speaker.room = "galley"
        simulation.food = 0
        self.assertFalse(simulation.resolve(speaker, Intent("eat")))
        simulation.food = 3
        speaker.room = "commons"
        trusting.room = skeptical.room = bystander.room = "commons"
        trusting.relationships[speaker.name].trust = 80
        skeptical.relationships[speaker.name].trust = 15
        for target in (trusting, skeptical):
            self.assertTrue(simulation.resolve(speaker, Intent("tell", recipient=target.name)))
        self.assertFalse(trusting.food_belief.available)
        self.assertIsNone(skeptical.food_belief)
        self.assertFalse(bystander.food_evidence)

        skeptical.room = "galley"
        self.assertTrue(simulation.resolve(skeptical, Intent("eat")))
        self.assertTrue(skeptical.food_belief.available)
        self.assertFalse(trusting.food_belief.available)
        trusting.room = "galley"
        self.assertTrue(simulation.resolve(trusting, Intent("eat")))
        relationship = trusting.relationships[speaker.name]
        self.assertTrue(trusting.food_belief.available)
        self.assertLess(relationship.food_report_credibility, 0)
        self.assertEqual(relationship.trust, 80)

    def test_relayed_delivery_cannot_confirm_an_origin_twice(self):
        simulation = Simulation(1)
        source, relay_a, relay_b, listener, *_ = simulation.inhabitants
        source.room = "galley"
        simulation.food = 0
        self.assertFalse(simulation.resolve(source, Intent("eat")))
        source.room = relay_a.room = relay_b.room = listener.room = "commons"
        for relay in (relay_a, relay_b):
            relay.relationships[source.name].trust = 80
            listener.relationships[relay.name].trust = 50
            self.assertTrue(simulation.resolve(source, Intent("tell", recipient=relay.name)))
            self.assertTrue(simulation.resolve(relay, Intent("tell", recipient=listener.name)))
        self.assertEqual(listener.food_assessment.unavailable_score, 40)
        self.assertEqual(len(listener.food_evidence), 1)
        self.assertEqual(len(listener.food_belief.transmissions), 2)
        report = simulation.history[-1]
        self.assertEqual(report.message.kind, "claim")
        self.assertEqual(report.message.content.source_event, 1)

    def make_conflict(self):
        station = Station(
            (Room("commons", ("galley",), ("work", "rest")),
             Room("galley", ("commons",), ("eat",))), "commons", initial_food=0,
        )
        simulation = Simulation(1, station)
        listener, empty, stocked, respondent, *_ = simulation.inhabitants
        for actor in simulation.inhabitants:
            actor.duty_room = "commons"
            actor.hunger = actor.fatigue = 0
            actor.contained = actor not in (listener, empty, stocked, respondent)
        empty.room = "galley"
        self.assertFalse(simulation.resolve(empty, Intent("eat")))
        empty.room = "commons"
        simulation.food = 4
        # Separate visits establish two genuinely different firsthand origins.
        for witness in (stocked, respondent):
            witness.room = "galley"
            self.assertTrue(simulation.resolve(witness, Intent("eat")))
            witness.room = "commons"
        for speaker in (empty, stocked, respondent):
            listener.relationships[speaker.name].trust = 70
        listener.relationships[respondent.name].trust = 85
        for speaker in (empty, stocked):
            self.assertTrue(simulation.resolve(speaker, Intent("tell", recipient=listener.name)))
            speaker.contained = True
        listener.hunger = 12
        return simulation, listener, respondent

    def test_conflict_prompts_autonomous_question_answer_and_verification(self):
        simulation, listener, respondent = self.make_conflict()
        self.assertIsNone(listener.food_belief)
        simulation.advance()
        self.assertEqual(simulation.last_intents[listener.name], Intent("ask_food", recipient=respondent.name))
        simulation.advance()
        self.assertEqual(simulation.last_intents[respondent.name], Intent("answer_food", recipient=listener.name))
        self.assertTrue(listener.food_belief.available)
        answer_id = next(index for index, event in enumerate(simulation.history, 1)
                         if event.action == "answer_food")
        traced = trace_event(simulation, answer_id)
        self.assertEqual({row["action"] for row in traced}, {"eat", "found_no_food", "tell", "ask_food", "answer_food"})
        simulation.advance()
        self.assertEqual(simulation.last_intents[listener.name], Intent("move", "galley"))
        simulation.advance()
        self.assertTrue(any(event.actor == listener.name and event.action == "eat"
                            for event in simulation.history))

        replay, _, _ = self.make_conflict()
        replay.advance_ticks(4)
        self.assertEqual(replay.history, simulation.history)

    def test_doubt_is_private_and_refers_to_the_disputed_delivery(self):
        simulation, listener, respondent = self.make_conflict()
        peer_name = next(iter(listener.pending_food_reports))
        report = listener.pending_food_reports[peer_name]
        self.assertTrue(simulation.resolve(listener, Intent("doubt_food", recipient=peer_name)))
        event = simulation.history[-1]
        self.assertEqual(event.message.kind, "doubt")
        self.assertEqual(event.message.reply_to, report.event_id)
        self.assertNotIn(respondent.name, {observer for observer, _ in event.observations})

    def test_challenge_transmits_counterevidence_and_links_original_claim(self):
        simulation, listener, respondent = self.make_conflict()
        opposing_peer = next(iter(listener.pending_food_reports))
        original = listener.pending_food_reports[opposing_peer]
        self.assertTrue(simulation.resolve(listener, Intent("ask_food", recipient=respondent.name)))
        self.assertTrue(simulation.resolve(respondent, Intent("answer_food", recipient=listener.name)))
        self.assertTrue(simulation.resolve(listener, Intent("challenge_food", recipient=opposing_peer)))
        event = simulation.history[-1]
        self.assertEqual(event.message.kind, "challenge")
        self.assertTrue(event.message.content.available)
        self.assertEqual(event.message.reply_to, original.event_id)
        self.assertIn(original.event_id, event.causes)

    def test_seeded_shortage_autonomously_prompts_question_then_firsthand_check(self):
        simulation = Simulation(1, replace(DEFAULT_STATION, initial_food=72))
        simulation.advance_ticks(373)
        question = next(event for event in simulation.history if event.action == "ask_food")
        answers = [
            event for event in simulation.history
            if event.action == "answer_food" and event.recipient == question.actor
            and event.tick > question.tick
        ]
        self.assertTrue(answers)
        self.assertIn("100 for available and 100 for unavailable", answers[0].reason)
        observer = simulation.agents_by_name[question.actor]
        self.assertTrue(any(
            event.action == "found_no_food" and event.actor == question.actor
            and event.tick > answers[0].tick
            for event in simulation.history
        ))
        self.assertFalse(observer.food_belief.available)
        self.assertEqual(observer.food_belief.confidence, 100)
