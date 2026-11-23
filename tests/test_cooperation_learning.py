from dataclasses import replace
import unittest

from assimilation.kernel import DEFAULT_STATION, Intent, PowerConfig, Simulation
from assimilation.observer import inspect_inhabitant
from assimilation.policy import Disposition, choose


class CooperationLearningTests(unittest.TestCase):
    def make_station(self):
        station = replace(DEFAULT_STATION, power=PowerConfig("generator", 0, 0, 5))
        simulation = Simulation(1, station, dispositions={"Anika": Disposition()})
        worker, helper, observer, *_ = simulation.inhabitants
        worker.room = helper.room = observer.room = "generator"
        worker.relationships[helper.name].trust = 62
        worker.hunger = worker.fatigue = 0
        worker.help_requested_by = helper.name
        return simulation, worker, helper, observer

    def test_observed_assistance_influences_later_help_decision(self):
        simulation, worker, helper, observer = self.make_station()
        before = choose(simulation.perceive(worker))
        self.assertEqual(before.intent.action, "decline_help")
        worker.help_requested_by = None

        self.assertTrue(simulation.resolve(worker, Intent("refuel")))
        self.assertTrue(simulation.resolve(helper, Intent("refuel")))
        evidence = inspect_inhabitant(simulation, worker.name)["relationships"][helper.name]
        self.assertEqual(evidence["trust"], 62)
        self.assertEqual(evidence["generator_assists"], 1)
        event = simulation.history[evidence["last_generator_assist_event"] - 1]
        self.assertEqual(event.action, "refuel_assisted")
        self.assertEqual(event.actor, helper.name)
        self.assertEqual(observer.relationships[helper.name].generator_assists, 0)

        helper.felt_cold = True
        self.assertTrue(simulation.resolve(helper, Intent("request_help", recipient=worker.name)))
        after = choose(simulation.perceive(worker))
        self.assertEqual(after.intent.action, "accept_help")
        self.assertIn("generator experience 5", after.evaluations[-1].reason)

    def test_departed_worker_learns_nothing_from_unseen_completion(self):
        simulation, worker, helper, _ = self.make_station()
        self.assertTrue(simulation.resolve(worker, Intent("refuel")))
        self.assertTrue(simulation.resolve(worker, Intent("move", "airlock")))
        self.assertTrue(simulation.resolve(helper, Intent("refuel")))
        experience = worker.relationships[helper.name]
        self.assertEqual(experience.generator_trust_bonus, 0)
        self.assertIsNone(experience.last_generator_assist_event)
        self.assertEqual(choose(simulation.perceive(worker)).intent.action, "decline_help")
