import unittest

from assimilation.kernel import Intent, Room, Simulation, Station
from assimilation.observer import trace_event
from assimilation.policy import Disposition


class DefensiveAgencyTests(unittest.TestCase):
    def scenario(self, *, exit_known=True, sleeper=False, distracted=False, health=100, help_nearby=False):
        station = Station((
            Room("lab", ("hall",) if exit_known else ()),
            Room("hall", ("lab",) if exit_known else ()),
            Room("remote", ()),
        ), "remote")
        simulation = Simulation(19, station, hidden_organism=True)
        host = simulation.agents_by_name[next(iter(simulation.organisms))]
        target, helper, distant, *_ = [agent for agent in simulation.inhabitants if agent is not host]
        host.room = target.room = "lab"
        helper.room = "hall" if help_nearby else "remote"
        target.disposition = Disposition(caution=-5 if distracted else 5)
        helper.disposition = Disposition(cooperativeness=5, caution=-5)
        host.fatigue = target.fatigue = helper.fatigue = 0
        target.health = health
        if sleeper:
            target.sleep_until = 5
        if distracted:
            target.work_until = 5
        self.assertTrue(simulation.resolve(host, Intent("assimilate", recipient=target.name)))
        simulation.finish_encounters()
        return simulation, target, helper, distant

    def test_alert_target_notices_and_escapes_without_identifying_the_threat(self):
        simulation, target, _, distant = self.scenario()
        simulation.advance()
        self.assertEqual(target.room, "hall")
        record = simulation.decision_records[target.name][-1]
        self.assertTrue(record.resolved)
        self.assertEqual(record.decision.intent.action, "escape_danger")
        self.assertEqual(len(record.decision.evaluations), 4)
        interrupted = trace_event(simulation, len(simulation.history))
        self.assertEqual(
            [event["action"] for event in interrupted],
            ["assimilation_started", "danger_noticed", "escape_danger", "assimilation_interrupted"],
        )
        self.assertNotIn("assimilation", repr(record.decision))
        self.assertFalse(distant.memory)
        self.assertNotIn(target.name, simulation.organisms)

    def test_resistance_can_fail_and_conversion_can_complete(self):
        simulation, target, _, _ = self.scenario(exit_known=False, health=40)
        simulation.advance()
        record = simulation.decision_records[target.name][-1]
        self.assertEqual(record.decision.intent.action, "resist_danger")
        self.assertFalse(record.resolved)
        failed = simulation.history[record.event_ids[0] - 1]
        self.assertEqual(failed.action, "resist_danger_failed")
        self.assertIn("capacity", failed.reason)
        self.assertIn(target.name, simulation.organisms)

    def test_sleep_incapacity_and_distraction_delay_recognition(self):
        for conditions in ({"sleeper": True}, {"health": 10}, {"distracted": True}):
            with self.subTest(conditions=conditions):
                simulation, target, _, _ = self.scenario(exit_known=False, **conditions)
                simulation.advance()
                self.assertFalse(any(event.action == "danger_noticed" for event in simulation.history))
                self.assertIn(target.name, simulation.organisms)
        ordinary, target, _, _ = self.scenario(exit_known=False)
        ordinary.advance()
        self.assertTrue(any(event.action == "danger_noticed" for event in ordinary.history))
        self.assertEqual(ordinary.decision_records[target.name][-1].decision.intent.action, "resist_danger")

    def test_a_heard_call_can_prompt_intervention_within_the_tick(self):
        simulation, target, helper, distant = self.scenario(health=26, help_nearby=True)
        simulation.advance()
        self.assertEqual(helper.room, "lab")
        self.assertEqual(simulation.last_intents[helper.name].action, "answer_distress")
        self.assertNotIn(target.name, simulation.organisms)
        self.assertFalse(distant.memory)
        actions = [event["action"] for event in trace_event(simulation, len(simulation.history))]
        self.assertEqual(actions, ["assimilation_started", "danger_noticed", "call_for_help",
                                   "answer_distress", "assimilation_interrupted"])

        isolated, target, helper, _ = self.scenario(health=26)
        isolated.advance()
        self.assertEqual(helper.room, "remote")
        self.assertIsNone(helper.distress)
        self.assertIn(target.name, isolated.organisms)

    def test_defensive_scenario_replays_history_and_rng_state(self):
        first, _, _, _ = self.scenario(health=26, help_nearby=True)
        second, _, _, _ = self.scenario(health=26, help_nearby=True)
        first.advance_ticks(12)
        second.advance_ticks(12)
        self.assertEqual(first.history, second.history)
        self.assertEqual(first.random.getstate(), second.random.getstate())

    def test_reachable_exit_can_fail_once_the_encounter_is_progressing(self):
        simulation, target, _, _ = self.scenario(health=40)
        host = simulation.agents_by_name[next(iter(simulation.organisms))]
        simulation.tick += 1
        simulation.publish_danger_cues()
        intent = simulation.decide(target)
        self.assertEqual(intent, Intent("escape_danger", destination="hall"))
        self.assertTrue(simulation.resolve(host, Intent("assimilate", recipient=target.name)))
        self.assertFalse(simulation.resolve(target, intent))
        failure = simulation.history[-1]
        self.assertEqual(failure.action, "escape_danger_failed")
        self.assertIn("already progressing", failure.reason)
        simulation.finish_encounters()
        self.assertIn(target.name, simulation.organisms)
