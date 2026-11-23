import unittest

from assimilation.kernel import Simulation
from assimilation.policy import Disposition, choose


class DispositionTests(unittest.TestCase):
    def test_two_recipients_weigh_same_request_differently(self):
        simulation = Simulation(1, dispositions={
            "Bram": Disposition(cooperativeness=5),
            "Cleo": Disposition(cooperativeness=-5),
        })
        requester, willing, reluctant, *_ = simulation.inhabitants
        for recipient in (willing, reluctant):
            recipient.help_requested_by = requester.name
            recipient.hunger = recipient.fatigue = 0
            recipient.relationships[requester.name].trust = 65

        accepted = choose(simulation.perceive(willing))
        declined = choose(simulation.perceive(reluctant))
        self.assertEqual(accepted.intent.action, "accept_help")
        self.assertEqual(declined.intent.action, "decline_help")
        self.assertIn("Help score 75", accepted.evaluations[-1].reason)
        self.assertIn("Help score 55", declined.evaluations[-1].reason)

        willing.fatigue = willing.rest_threshold
        reluctant.relationships[requester.name].trust = 90
        self.assertEqual(simulation.decide(willing).action, "decline_help")
        self.assertEqual(simulation.decide(reluctant).action, "accept_help")

    def test_caution_changes_avoidance_given_the_same_concern(self):
        simulation = Simulation(1, dispositions={
            "Bram": Disposition(caution=5),
            "Cleo": Disposition(caution=-5),
        })
        subject, cautious, tolerant, *_ = simulation.inhabitants
        for actor in (cautious, tolerant):
            actor.suspicion[subject.name] = 30
            actor.room = actor.duty_room = subject.room = "lab"
            actor.hunger = actor.fatigue = 0
        self.assertEqual(simulation.decide(cautious).destination, "commons")
        self.assertEqual(simulation.decide(tolerant).action, "work")
        tolerant.suspicion[subject.name] = 40
        self.assertEqual(simulation.decide(tolerant).destination, "commons")

    def test_default_profiles_are_distinct_and_reproducible(self):
        first = Simulation(7)
        second = Simulation(7)
        profiles = [agent.disposition for agent in first.inhabitants]
        self.assertEqual(len(set(profiles)), 12)
        self.assertEqual(profiles, [agent.disposition for agent in second.inhabitants])
        first.advance_ticks(240)
        self.assertEqual(profiles, [agent.disposition for agent in first.inhabitants])
