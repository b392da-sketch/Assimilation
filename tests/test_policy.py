from dataclasses import FrozenInstanceError
import unittest

from assimilation.kernel import FoodBelief, Organism, Simulation
from assimilation.policy import choose


class PolicyBoundaryTests(unittest.TestCase):
    def test_hidden_conditions_and_private_peer_state_do_not_change_choice(self):
        simulation = Simulation(7)
        actor, peer, distant, *_ = simulation.inhabitants
        distant.room = "lab"
        before = simulation.perceive(actor)

        simulation.food = 0
        simulation.power.source = "off"
        simulation.organisms[peer.name] = Organism(1, None, peer.name)
        simulation.organisms[distant.name] = Organism(2, None, distant.name)
        peer.food_belief = FoodBelief(False, 0, (peer.name,), 100)
        peer.suspicion[actor.name] = 100
        distant.room = "radio"

        after = simulation.perceive(actor)
        self.assertEqual(before, after)
        self.assertEqual(choose(before), choose(after))
        self.assertNotIn(distant.name, {other.name for other in after.peers})

    def test_view_captures_visible_cues_and_private_beliefs_as_values(self):
        simulation = Simulation(7)
        actor, peer, *_ = simulation.inhabitants
        actor.fatigue = 0
        actor.hunger = 12
        actor.examinations[peer.name] = "anomaly"
        peer.fatigue = 8
        before = simulation.perceive(actor)

        peer.fatigue = 9
        actor.food_belief = FoodBelief(False, 0, (actor.name,), 100)
        after = simulation.perceive(actor)
        self.assertFalse(before.peers[0].visibly_exhausted)
        self.assertIsNone(before.food_belief)
        self.assertTrue(after.peers[0].visibly_exhausted)
        decision = choose(after)
        self.assertEqual(decision.intent.action, "contain")
        peer.room = "lab"
        self.assertFalse(simulation.resolve(actor, decision.intent))
        with self.assertRaises(FrozenInstanceError):
            after.peers[0].contained = True
