from dataclasses import replace
import unittest

from assimilation.communication import QUESTION_COOLDOWN, QUESTION_TIMEOUT
from assimilation.kernel import DEFAULT_STATION, Intent, Simulation
from assimilation.observer import trace_event
from assimilation.policy import Disposition, choose


class SocialCoordinationTests(unittest.TestCase):
    def test_a_follow_up_question_requires_new_evidence_and_a_cooldown(self):
        simulation = Simulation(1)
        asker, respondent, *_ = simulation.inhabitants
        question = Intent("ask_food", recipient=respondent.name)
        self.assertTrue(simulation.resolve(asker, question))
        simulation.tick = QUESTION_TIMEOUT
        self.assertFalse(simulation.resolve(respondent, Intent("answer_food", recipient=asker.name)))
        simulation.tick = QUESTION_COOLDOWN
        self.assertFalse(simulation.resolve(asker, question))

        source = simulation.inhabitants[2]
        source.room = "galley"
        self.assertTrue(simulation.resolve(source, Intent("eat")))
        source.room = "quarters"
        self.assertTrue(simulation.resolve(source, Intent("tell", recipient=asker.name)))
        self.assertTrue(simulation.resolve(asker, question))

    def test_autonomous_coordination_links_objection_proposal_consent_and_result(self):
        simulation = Simulation(2, replace(DEFAULT_STATION, initial_food=72))
        simulation.advance_ticks(420)
        event_id, result = next(
            (index, event) for index, event in enumerate(simulation.history, 1)
            if event.action == "report_food_check"
        )
        chain = trace_event(simulation, event_id)
        actions = {event["action"] for event in chain}
        self.assertTrue({"propose_food_check", "accept_food_check", "check_food",
                         "report_food_check"} <= actions)
        self.assertTrue({"doubt_food", "challenge_food"} & actions)
        self.assertEqual(result.message.kind, "verification report")
        self.assertIsInstance(result.message.content.available, bool)
        self.assertEqual(simulation.food + sum(
            event.action == "eat" for event in simulation.history), 72)
        self.assertTrue(any(event.action == "decline_food_check" for event in simulation.history))

        replay = Simulation(2, replace(DEFAULT_STATION, initial_food=72))
        replay.advance_ticks(420)
        self.assertEqual(simulation.history, replay.history)

    def test_same_proposal_can_be_accepted_or_declined_from_local_context(self):
        simulation = Simulation(2, replace(DEFAULT_STATION, initial_food=72))
        while simulation.tick < 420:
            simulation.advance()
            proposals = [agent for agent in simulation.inhabitants if agent.food_verification
                         and agent.food_verification.acceptance_id is None]
            if proposals:
                break
        recipient = proposals[0]
        ready = replace(
            simulation.perceive(recipient), verification_trust=85, disposition=Disposition(),
            hunger=0, fatigue=0, sleeping=False,
        )
        self.assertEqual(choose(ready).intent.action, "accept_food_check")
        tired = replace(ready, fatigue=ready.rest_threshold)
        self.assertEqual(choose(tired).intent.action, "decline_food_check")
        self.assertEqual(choose(replace(ready, verification_trust=35)).intent.action,
                         "decline_food_check")

    def test_busy_recipient_does_not_consume_a_proposal_or_prevent_retry(self):
        simulation = Simulation(1, replace(DEFAULT_STATION, initial_food=0))
        first, second, recipient, witness, *_ = simulation.inhabitants
        recipient.room = "galley"
        self.assertFalse(simulation.resolve(recipient, Intent("eat")))
        recipient.room = "quarters"
        simulation.food = 2
        witness.room = "galley"
        self.assertTrue(simulation.resolve(witness, Intent("eat")))
        witness.room = "quarters"
        for proposer in (first, second):
            proposer.relationships[recipient.name].trust = 70
            proposer.relationships[witness.name].trust = 70
            self.assertTrue(simulation.resolve(recipient, Intent("tell", recipient=proposer.name)))
            self.assertTrue(simulation.resolve(witness, Intent("tell", recipient=proposer.name)))
            self.assertTrue(simulation.resolve(proposer, Intent("doubt_food", recipient=recipient.name)))

        proposal = Intent("propose_food_check", recipient=recipient.name)
        self.assertTrue(simulation.resolve(first, proposal))
        busy_plan = recipient.food_verification
        self.assertTrue(simulation.resolve(recipient, Intent("accept_food_check", recipient=first.name)))
        existing_plan = recipient.food_verification
        before = len(simulation.history)
        existing_objection = second.food_objections[recipient.name]
        self.assertFalse(simulation.resolve(second, proposal))
        self.assertEqual(len(simulation.history), before)
        self.assertEqual(recipient.food_verification, existing_plan)
        self.assertEqual(second.proposed_food_checks, {})
        self.assertIsNone(second.offered_verification)

        simulation.tick = busy_plan.expires_at
        self.assertTrue(simulation.resolve(second, proposal))
        self.assertEqual(recipient.food_verification.proposer, second.name)
        self.assertEqual(second.food_objections[recipient.name], existing_objection)
        self.assertEqual(simulation.history[-1].message.reply_to, existing_objection[1])
