from dataclasses import replace
import unittest

from assimilation.kernel import DEFAULT_STATION, HeardFoodReport, Intent, PowerConfig, Simulation
from assimilation.policy import Disposition, choose
from assimilation.relationships import EVIDENCE_LIMIT, Experience, Relationship


class InterpersonalEvidenceTests(unittest.TestCase):
    def test_fulfilled_and_withdrawn_commitments_revise_reliability(self):
        station = replace(DEFAULT_STATION, power=PowerConfig("generator", 0, 0, 5))
        simulation = Simulation(1, station, dispositions={"Anika": Disposition(caution=3)})
        requester, helper, bystander, *_ = simulation.inhabitants
        requester.room = helper.room = bystander.room = "generator"
        requester.felt_cold = True
        request = Intent("request_help", recipient=helper.name)
        accept = Intent("accept_help", recipient=requester.name)
        self.assertTrue(simulation.resolve(requester, request))
        self.assertTrue(simulation.resolve(helper, accept))
        acceptance_id = len(simulation.history)
        self.assertTrue(simulation.resolve(requester, Intent("refuel")))
        self.assertTrue(simulation.resolve(helper, Intent("refuel")))

        relationship = requester.relationships[helper.name]
        self.assertEqual(relationship.commitment_reliability, 5)
        self.assertEqual(relationship.generator_trust_bonus, 5)
        self.assertEqual(bystander.relationships[helper.name].evidence, [])
        fulfilled = relationship.evidence[-1]
        self.assertEqual(fulfilled.related_event_id, acceptance_id)
        self.assertEqual(simulation.history[fulfilled.event_id - 1].action, "refuel_assisted")

        requester.requested_help_from.clear()
        self.assertTrue(simulation.resolve(requester, request))
        self.assertTrue(simulation.resolve(helper, accept))
        self.assertTrue(simulation.resolve(helper, Intent("decline_help", recipient=requester.name)))
        self.assertEqual(relationship.commitment_reliability, -3)
        self.assertEqual(relationship.generator_trust_bonus, 5)
        self.assertEqual(relationship.evidence[-1].kind, "commitment_withdrawn")

    def test_refusal_changes_later_helper_selection_when_witnessed(self):
        simulation = Simulation(1)
        worker, first, second, *_ = simulation.inhabitants
        worker.room = first.room = second.room = "commons"
        first.duty_room = second.duty_room = "lab"
        worker.felt_cold = True
        initial = choose(simulation.perceive(worker))
        self.assertEqual(initial.intent.recipient, first.name)
        self.assertTrue(simulation.resolve(worker, initial.intent))
        self.assertTrue(simulation.resolve(first, Intent("decline_help", recipient=worker.name)))
        worker.requested_help_from.clear()
        after = choose(simulation.perceive(worker))
        self.assertEqual(after.intent.recipient, second.name)
        self.assertIn("Bram -2", after.evaluations[-1].reason)
        self.assertEqual(after.evaluations[-1].evidence_event_ids, (len(simulation.history),))
        self.assertEqual(worker.relationships[first.name].willingness_to_help, -2)
        self.assertEqual(worker.relationships[first.name].commitment_reliability, 0)

    def test_food_testimony_is_private_and_revised_with_firsthand_evidence(self):
        station = replace(DEFAULT_STATION, initial_food=2)
        simulation = Simulation(1, station, dispositions={"Bram": Disposition(caution=3)})
        speaker, listener, bystander, *_ = simulation.inhabitants
        speaker.room = "galley"
        listener.room = bystander.room = "commons"
        tell = Intent("tell", recipient=listener.name)
        self.assertTrue(simulation.resolve(speaker, Intent("eat")))
        speaker.room = "commons"
        self.assertTrue(simulation.resolve(speaker, tell))
        self.assertNotIn(speaker.name, bystander.pending_food_reports)
        listener.room = "galley"
        self.assertTrue(simulation.resolve(listener, Intent("eat")))
        relationship = listener.relationships[speaker.name]
        self.assertEqual(relationship.food_report_credibility, 4)

        speaker.room = "galley"
        self.assertFalse(simulation.resolve(speaker, Intent("eat")))
        speaker.room = listener.room = "commons"
        simulation.food = 1  # A controlled change unknown to the speaker.
        self.assertTrue(simulation.resolve(speaker, tell))
        self.assertEqual(relationship.food_report_credibility, 4)
        listener.room = "galley"
        self.assertTrue(simulation.resolve(listener, Intent("eat")))
        self.assertEqual(relationship.food_report_credibility, -3)
        self.assertEqual(relationship.generator_trust_bonus, 0)
        self.assertEqual(relationship.commitment_reliability, 0)
        self.assertEqual([item.kind for item in relationship.evidence],
                         ["food_report_supported", "food_report_contradicted"])
        self.assertTrue(all(item.basis == "verified testimony" for item in relationship.evidence))
        for evidence in relationship.evidence:
            self.assertEqual(simulation.history[evidence.related_event_id - 1].action, "tell")
            self.assertLess(evidence.origin_event_id, evidence.related_event_id)
            self.assertLess(evidence.related_event_id, evidence.event_id)

    def test_replayed_evidence_is_ignored_after_rollover(self):
        relationship = Relationship(60)
        for event_id in range(1, EVIDENCE_LIMIT + 4):
            relationship.learn(Experience("generator_assistance", event_id), 0)
        relationship.learn(Experience("generator_assistance", 1), 0)
        self.assertEqual(len(relationship.evidence), EVIDENCE_LIMIT)
        self.assertEqual(relationship.generator_assists, EVIDENCE_LIMIT + 3)
        self.assertEqual(relationship.generator_trust_bonus, 15)

    def test_repeated_report_from_same_origin_earns_credit_once(self):
        simulation = Simulation(1, replace(DEFAULT_STATION, initial_food=3))
        speaker, listener, *_ = simulation.inhabitants
        speaker.room = "galley"
        listener.room = "commons"
        self.assertTrue(simulation.resolve(speaker, Intent("eat")))
        speaker.room = "commons"
        self.assertTrue(simulation.resolve(speaker, Intent("tell", recipient=listener.name)))
        original = listener.pending_food_reports[speaker.name]
        listener.room = "galley"
        self.assertTrue(simulation.resolve(listener, Intent("eat")))
        relationship = listener.relationships[speaker.name]
        self.assertEqual(relationship.food_report_credibility, 4)

        # Deliver the same underlying report again with a different delivery ID.
        listener.pending_food_reports[speaker.name] = HeardFoodReport(
            len(simulation.history), original.belief,
        )
        self.assertTrue(simulation.resolve(listener, Intent("eat")))
        self.assertEqual(relationship.food_report_credibility, 4)
        self.assertEqual(len(relationship.evidence), 1)

    def test_new_controller_does_not_inherit_interpersonal_evidence(self):
        simulation = Simulation(1, hidden_organism=True)
        host_name = next(iter(simulation.organisms))
        host = simulation.agents_by_name[host_name]
        target, observer, *_ = [agent for agent in simulation.inhabitants if agent is not host]
        host.room = target.room = "lab"
        target.relationships[observer.name].learn(Experience("generator_assistance", 1), 0)
        observer.relationships[target.name].learn(Experience("help_declined", 1), 0)
        baseline_trust = target.relationships[observer.name].trust
        intent = Intent("assimilate", recipient=target.name)
        self.assertTrue(simulation.resolve(host, intent))
        simulation.tick += 1
        self.assertTrue(simulation.resolve(host, intent))
        simulation.finish_encounters()
        self.assertIn(target.name, simulation.organisms)
        self.assertEqual(target.relationships[observer.name].evidence, [])
        self.assertEqual(target.relationships[observer.name].familiarity, 0)
        self.assertEqual(target.relationships[observer.name].trust, baseline_trust)
        self.assertEqual(len(observer.relationships[target.name].evidence), 1)
