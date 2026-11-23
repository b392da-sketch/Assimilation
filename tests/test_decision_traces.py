from dataclasses import replace
import unittest

from assimilation.kernel import DEFAULT_STATION, Simulation
from assimilation.observer import observer_command


class DecisionTraceTests(unittest.TestCase):
    def test_trace_separates_policy_choice_from_failed_resolution(self):
        simulation = Simulation(1, replace(DEFAULT_STATION, initial_food=1))
        for agent in simulation.inhabitants:
            agent.room = "galley"
            agent.hunger = 12
            agent.fatigue = 0
        simulation.advance()
        records = [history[-1] for history in simulation.decision_records.values()]
        self.assertEqual(sum(record.resolved for record in records), 1)
        self.assertTrue(all(record.decision.intent.action == "eat" for record in records))
        for record in records:
            evaluations = record.decision.evaluations
            self.assertEqual(evaluations[-1].intent, record.decision.intent)
            self.assertTrue(all(option.intent is None for option in evaluations[:-1]))
            self.assertEqual(len(record.event_ids), 1)
            event = simulation.history[record.event_ids[0] - 1]
            self.assertEqual(event.action, "eat" if record.resolved else "found_no_food")

    def test_observer_reads_bounded_decision_history_without_advancing_time(self):
        simulation = Simulation(1)
        self.assertEqual(observer_command(simulation, ["decisions", "Anika"]), [])
        simulation.advance_ticks(40)
        records = observer_command(simulation, ["decisions", "Anika", "100"])
        self.assertEqual([record["tick"] for record in records], list(range(9, 41)))
        self.assertEqual(simulation.tick, 40)
        self.assertEqual(observer_command(simulation, ["decisions", "Anika", "0"]), [])
