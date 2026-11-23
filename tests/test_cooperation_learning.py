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

    def test_assistance_evidence_outlasts_observation_rollover(self):
        simulation, worker, helper, _ = self.make_station()
        self.assertTrue(simulation.resolve(worker, Intent("refuel")))
        self.assertTrue(simulation.resolve(helper, Intent("refuel")))
        event_id = worker.relationships[helper.name].last_generator_assist_event

        for _ in range(worker.memory.maxlen + 1):
            simulation.tick += 6
            self.assertTrue(simulation.resolve(helper, Intent("work")))

        self.assertFalse(any(observation.action == "refuel_assisted" for observation in worker.memory))
        relationship = worker.relationships[helper.name]
        self.assertEqual(relationship.last_generator_assist_event, event_id)
        self.assertEqual(simulation.history[event_id - 1].action, "refuel_assisted")
        self.assertEqual(choose(simulation.perceive(worker)).intent.action, "accept_help")

    def test_repeated_assistance_caps_bonus_and_duplicate_action_earns_nothing(self):
        simulation, worker, helper, _ = self.make_station()
        relationship = worker.relationships[helper.name]
        for completed in range(1, 6):
            # Reset supplies between distinct repair episodes.
            simulation.power.main_fuel = 0
            simulation.power.reserve_fuel = 5
            self.assertTrue(simulation.resolve(worker, Intent("refuel")))
            self.assertTrue(simulation.resolve(helper, Intent("refuel")))
            event_id = relationship.last_generator_assist_event
            self.assertFalse(simulation.resolve(helper, Intent("refuel")))
            self.assertEqual(relationship.generator_assists, completed)
            self.assertEqual(relationship.generator_trust_bonus, min(15, 5 * completed))
            self.assertEqual(relationship.last_generator_assist_event, event_id)
        self.assertEqual(relationship.trust, 62)

    def test_sleeping_worker_does_not_learn_about_completed_assistance(self):
        simulation, worker, helper, _ = self.make_station()
        self.assertTrue(simulation.resolve(worker, Intent("refuel")))
        worker.sleep_until = simulation.tick + 1
        self.assertTrue(simulation.resolve(helper, Intent("refuel")))
        self.assertEqual(worker.relationships[helper.name].generator_assists, 0)
        self.assertFalse(any(observation.action == "refuel_assisted" for observation in worker.memory))

    def test_autonomous_refuel_records_firsthand_cooperation(self):
        station = replace(DEFAULT_STATION, power=PowerConfig("generator", 5, 3, 80, "radio"))
        simulation = Simulation(1, station)
        simulation.advance_ticks(60)

        started = next(event for event in simulation.history if event.action == "refuel_started")
        completion_id, completion = next(
            (event_id, event) for event_id, event in enumerate(simulation.history, start=1)
            if event.action == "refuel_assisted"
        )
        worker = simulation.agents_by_name[started.actor]
        experience = worker.relationships[completion.actor]
        self.assertIn(worker.name, {observer for observer, _ in completion.observations})
        self.assertEqual(experience.generator_assists, 1)
        self.assertEqual(experience.last_generator_assist_event, completion_id)
        self.assertEqual(simulation.power.source, "main")
