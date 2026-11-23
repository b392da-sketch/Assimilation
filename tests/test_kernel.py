from dataclasses import replace
import unittest

from assimilation.kernel import DEFAULT_STATION, Intent, PowerConfig, Room, Simulation, Station


class KernelTests(unittest.TestCase):
    def run_seed(self, seed, ticks=60):
        simulation = Simulation(seed)
        for _ in range(ticks):
            simulation.advance()
        return simulation

    def test_seed_reproduces_history_and_final_state(self):
        first = self.run_seed(7)
        replay = self.run_seed(7)
        self.assertEqual(first.history, replay.history)
        self.assertEqual(first.inhabitants, replay.inhabitants)
        self.assertEqual(first.food, replay.food)
        self.assertNotEqual(first.history, self.run_seed(8).history)

    def test_inhabitants_move_and_meet_needs(self):
        simulation = self.run_seed(1)
        self.assertEqual(len(simulation.inhabitants), 12)
        self.assertEqual({event.action for event in simulation.history}, {"move", "work", "eat", "rest", "radio_contact"})
        for event in simulation.history:
            if event.action == "move":
                self.assertIn(event.destination, simulation.rooms[event.room].neighbors)

    def test_movement_is_local_and_observations_show_one_endpoint(self):
        simulation = Simulation(1)
        actor, departure_witness, arrival_witness, absent, *_ = simulation.inhabitants
        arrival_witness.room = "commons"
        absent.room = "lab"
        self.assertFalse(simulation.resolve(actor, Intent("move", "lab")))
        self.assertEqual(actor.room, "quarters")
        self.assertFalse(simulation.history)
        self.assertTrue(simulation.resolve(actor, Intent("move", "commons")))
        self.assertEqual(departure_witness.memory[-1].action, "depart")
        self.assertEqual(departure_witness.memory[-1].room, "quarters")
        self.assertEqual(arrival_witness.memory[-1].action, "arrive")
        self.assertEqual(arrival_witness.memory[-1].room, "commons")
        self.assertFalse(absent.memory)

    def test_competing_meals_cannot_consume_the_same_food(self):
        station = Station(DEFAULT_STATION.rooms, DEFAULT_STATION.quarters, initial_food=1)
        simulation = Simulation(1, station)
        first, second, *_ = simulation.inhabitants
        first.room = second.room = "galley"
        first.hunger = second.hunger = 7
        self.assertTrue(simulation.resolve(first, Intent("eat")))
        self.assertFalse(simulation.resolve(second, Intent("eat")))
        self.assertEqual(simulation.food, 0)
        self.assertEqual(second.hunger, 7)

    def test_food_testimony_requires_contact_and_retains_provenance(self):
        station = Station(DEFAULT_STATION.rooms, DEFAULT_STATION.quarters, initial_food=0)
        simulation = Simulation(1, station)
        source, relay, listener, bystander, *_ = simulation.inhabitants
        source.room = "galley"
        self.assertFalse(simulation.resolve(source, Intent("eat")))
        self.assertIsNone(relay.food_belief)
        self.assertFalse(simulation.resolve(source, Intent("tell", recipient=relay.name)))
        source.room = relay.room = listener.room = bystander.room = "commons"
        relay.relationships[source.name].trust = 80
        listener.relationships[relay.name].trust = 50

        self.assertTrue(simulation.resolve(source, Intent("tell", recipient=relay.name)))
        self.assertEqual(relay.food_belief.confidence, 80)
        self.assertIsNone(listener.food_belief)
        self.assertTrue(simulation.resolve(relay, Intent("tell", recipient=listener.name)))
        self.assertEqual(listener.food_belief.sources, (source.name, relay.name, listener.name))
        self.assertEqual(listener.food_belief.confidence, 40)
        self.assertEqual(listener.memory[-1].testimony, relay.food_belief)
        self.assertFalse(bystander.memory)
        self.assertFalse(simulation.resolve(source, Intent("tell", recipient=relay.name)))

        relay.hunger = listener.hunger = 12
        relay.fatigue = listener.fatigue = 0
        self.assertEqual(simulation.decide(listener), Intent("move", "galley"))
        self.assertNotEqual(simulation.decide(relay), Intent("move", "galley"))
        self.assertEqual(relay.relationships[source.name].familiarity, 1)

    def test_autonomous_reports_follow_a_local_food_shortage(self):
        simulation = Simulation(1, replace(DEFAULT_STATION, initial_food=30))
        for _ in range(500):
            simulation.advance()
        first_report = next(event for event in simulation.history if event.action == "tell")
        self.assertFalse(first_report.testimony.available)
        self.assertTrue(any(
            event.action == "found_no_food" and event.tick == first_report.testimony.observed_at
            for event in simulation.history
        ))
        self.assertTrue(any(event.action == "work" and event.tick > first_report.tick
                            for event in simulation.history))

    def test_agent_keeps_feasible_need_driven_trip(self):
        simulation = Simulation(1)
        agent = simulation.inhabitants[0]
        agent.room = "lab"
        agent.hunger = agent.meal_threshold
        agent.fatigue = 0
        move = simulation.decide(agent)
        self.assertEqual(move, Intent("move", "commons"))
        self.assertTrue(simulation.resolve(agent, move))
        agent.fatigue = 12
        self.assertEqual(simulation.decide(agent), Intent("move", "galley"))

    def test_custom_station_and_cold_exposure(self):
        station = Station((Room("yard", (), outdoors=True),), "yard")
        simulation = Simulation(1, station)
        first = simulation.inhabitants[0]
        fatigue = first.fatigue
        for _ in range(6):
            simulation.advance()
        self.assertEqual(first.room, "yard")
        self.assertEqual(first.fatigue, fatigue + 1)

    def test_backup_prevents_indoor_exposure_until_it_runs_out(self):
        station = Station((Room("shelter", ()),), "shelter", power=PowerConfig("shelter", 1, 1, 0))
        simulation = Simulation(1, station)
        agent = simulation.inhabitants[0]
        for source in ("main", "backup", "off"):
            simulation.advance()
            self.assertEqual(simulation.power.source, source)
            self.assertEqual(agent.felt_cold, source == "off")
        self.assertEqual(
            [event.action for event in simulation.history if event.actor == "station"],
            ["power_backup", "power_off"],
        )

    def test_radio_contact_depends_on_power_and_location(self):
        station = replace(DEFAULT_STATION, power=PowerConfig("generator", 6, 6, 0, "radio"))
        simulation = Simulation(1, station)
        operator = simulation.inhabitants[0]
        self.assertFalse(simulation.resolve(operator, Intent("work")))
        operator.room = "radio"
        for tick in range(1, 14):
            simulation.tick = tick
            simulation.advance_power()
            if tick not in (1, 7, 13):
                self.assertFalse(simulation.resolve(operator, Intent("work")))
                continue
            self.assertTrue(simulation.resolve(operator, Intent("work")))
            expected = "radio_unpowered" if tick == 13 else "radio_contact"
            self.assertEqual(simulation.history[-1].action, expected)

    def test_help_requires_contact_and_is_evaluated_independently(self):
        simulation = Simulation(1)
        requester, willing, reluctant, bystander, *_ = simulation.inhabitants
        requester.room = reluctant.room = bystander.room = "commons"
        requester.felt_cold = True
        request = Intent("request_help", recipient=willing.name)
        self.assertFalse(simulation.resolve(requester, request))
        willing.room = "commons"
        willing.fatigue = reluctant.fatigue = 0
        willing.relationships[requester.name].trust = 80
        reluctant.relationships[requester.name].trust = 50
        self.assertTrue(simulation.resolve(requester, request))
        self.assertTrue(simulation.resolve(requester, Intent("request_help", recipient=reluctant.name)))
        self.assertFalse(bystander.memory)
        self.assertEqual(simulation.decide(willing), Intent("accept_help", recipient=requester.name))
        self.assertTrue(simulation.resolve(willing, simulation.decide(willing)))
        self.assertEqual(simulation.decide(willing), Intent("move", "airlock"))
        self.assertEqual(simulation.decide(reluctant), Intent("decline_help", recipient=requester.name))
        self.assertTrue(simulation.resolve(reluctant, simulation.decide(reluctant)))
        self.assertIsNone(reluctant.help_requested_by)

    def test_refueling_requires_presence_and_conserves_fuel(self):
        station = replace(DEFAULT_STATION, power=PowerConfig("generator", 0, 0, 5))
        simulation = Simulation(1, station)
        worker, helper, *_ = simulation.inhabitants
        action = Intent("refuel")
        self.assertFalse(simulation.resolve(worker, action))
        worker.room = helper.room = "generator"
        self.assertTrue(simulation.resolve(worker, action))
        self.assertEqual(simulation.power.reserve_fuel, 5)
        self.assertTrue(simulation.resolve(helper, action))
        self.assertEqual(simulation.history[-1].action, "refuel_assisted")
        self.assertEqual(simulation.power.reserve_fuel, 0)
        self.assertEqual(simulation.power.main_fuel, 5)
        self.assertFalse(simulation.resolve(helper, action))

    def test_low_fuel_scenario_recovers_without_external_actions(self):
        station = replace(DEFAULT_STATION, power=PowerConfig("generator", 5, 3, 80))
        for seed in (1, 2, 3):
            with self.subTest(seed=seed):
                simulation = Simulation(seed, station)
                for _ in range(60):
                    simulation.advance()
                self.assertEqual(
                    [event.action for event in simulation.history if event.actor == "station"],
                    ["power_backup", "power_off", "power_main"],
                )
                self.assertEqual(simulation.power.source, "main")
                self.assertFalse(any(agent.felt_cold for agent in simulation.inhabitants))
                self.assertEqual(simulation.power.reserve_fuel, 0)

    def test_arrival_interrupts_encounter_even_after_continuation(self):
        simulation = Simulation(1, hidden_organism=True)
        host_name = next(iter(simulation.organisms))
        host = simulation.agents_by_name[host_name]
        target, bystander, *_ = [agent for agent in simulation.inhabitants if agent is not host]
        host.room = target.room = "lab"
        bystander.room = "commons"
        intent = Intent("assimilate", recipient=target.name)
        self.assertFalse(simulation.resolve(bystander, intent))
        self.assertTrue(simulation.resolve(host, intent))
        simulation.finish_encounters()
        self.assertEqual(target.suspicion[host.name], 20)
        self.assertEqual(target.memory[-1].action, "uneasy_encounter")
        self.assertFalse(bystander.memory)

        simulation.tick += 1
        self.assertTrue(simulation.resolve(host, intent))
        self.assertTrue(simulation.resolve(bystander, Intent("move", "lab")))
        simulation.finish_encounters()
        self.assertNotIn(target.name, simulation.organisms)
        self.assertFalse(simulation.encounters)
        self.assertEqual(simulation.history[-1].action, "assimilation_interrupted")
        self.assertFalse(simulation.history[-1].observations)
        self.assertFalse(simulation.resolve(host, intent))

    def test_suspicion_report_is_local_and_trust_changes_avoidance(self):
        simulation = Simulation(1, hidden_organism=True)
        subject = simulation.agents_by_name[next(iter(simulation.organisms))]
        witness, listener, bystander, *_ = [
            agent for agent in simulation.inhabitants if agent is not subject
        ]
        subject.room = witness.room = "lab"
        for tick in (1, 4):
            simulation.tick = tick
            simulation.record(subject, "assimilation_started", "lab", visible_as="uneasy_encounter")
        action = Intent("warn", recipient=listener.name, subject=subject.name)
        self.assertFalse(simulation.resolve(witness, action))
        witness.room = listener.room = bystander.room = "commons"
        self.assertEqual(simulation.decide(witness), action)
        self.assertTrue(simulation.resolve(witness, action))
        self.assertFalse(simulation.resolve(witness, action))
        self.assertFalse(simulation.resolve(
            listener, Intent("warn", recipient=bystander.name, subject=subject.name)
        ))
        self.assertFalse(bystander.memory)
        self.assertFalse(listener.suspicion)
        self.assertEqual(listener.memory[-1].concern.witness, witness.name)
        self.assertEqual(listener.memory[-1].concern.observed_at, 4)

        subject.room = listener.room = "lab"
        listener.duty_room = "lab"
        listener.relationships[witness.name].trust = 40
        self.assertEqual(simulation.decide(listener), Intent("work"))
        listener.relationships[witness.name].trust = 80
        self.assertEqual(simulation.decide(listener), Intent("move", "commons"))

    def test_autonomous_assimilation_preserves_body_and_lineage_on_replay(self):
        def run():
            simulation = Simulation(19, hidden_organism=True)
            for _ in range(240):
                simulation.advance()
            return simulation

        simulation = run()
        self.assertEqual(simulation.history, run().history)
        completed = next(event for event in simulation.history if event.action == "assimilation_completed")
        parent = simulation.organisms[completed.actor]
        offspring = simulation.organisms[completed.subject]
        self.assertEqual(offspring.parent, parent.identity)
        self.assertNotEqual(offspring.identity, parent.identity)
        self.assertEqual(offspring.body, completed.subject)
        self.assertEqual(len(simulation.inhabitants), 12)
        self.assertFalse(completed.observations)
        self.assertFalse(self.run_seed(19).organisms)

    def test_cold_distress_can_raise_and_clear_false_suspicion(self):
        simulation = Simulation(1)
        subject, examiner, absent, *_ = simulation.inhabitants
        absent.room = "lab"
        subject.fatigue = 12
        subject.felt_cold = True
        self.assertTrue(simulation.resolve(subject, Intent("rest")))
        self.assertEqual(examiner.concern_about(subject.name), 20)
        self.assertEqual(absent.concern_about(subject.name), 0)
        examination = Intent("examine", subject=subject.name)
        self.assertFalse(simulation.resolve(examiner, examination))
        simulation.tick = 2
        self.assertFalse(simulation.resolve(absent, examination))
        subject.felt_cold = False
        subject.fatigue = 8
        self.assertTrue(simulation.resolve(examiner, examination))
        self.assertEqual(simulation.history[-1].action, "examination_clear")
        self.assertEqual(examiner.concern_about(subject.name), 0)
        self.assertFalse(simulation.resolve(examiner, Intent("contain", subject=subject.name)))

    def test_examination_is_inconclusive_during_cold_stress(self):
        simulation = Simulation(1)
        subject, examiner, *_ = simulation.inhabitants
        subject.felt_cold = True
        subject.fatigue = 12
        self.assertTrue(simulation.resolve(subject, Intent("rest")))
        simulation.tick = 2
        self.assertTrue(simulation.resolve(examiner, Intent("examine", subject=subject.name)))
        self.assertEqual(examiner.examinations[subject.name], "inconclusive")
        self.assertGreater(examiner.concern_about(subject.name), 0)
        self.assertFalse(simulation.resolve(examiner, Intent("contain", subject=subject.name)))

    def test_examination_can_miss_a_quiescent_organism(self):
        simulation = Simulation(2, hidden_organism=True)
        target = simulation.agents_by_name[next(iter(simulation.organisms))]
        examiner = next(agent for agent in simulation.inhabitants if agent is not target)
        simulation.record(target, "assimilation_started", target.room, visible_as="uneasy_encounter")
        simulation.tick = 2
        self.assertTrue(simulation.resolve(examiner, Intent("examine", subject=target.name)))
        self.assertEqual(examiner.examinations[target.name], "clear")
        self.assertIn(target.name, simulation.organisms)

    def test_containment_requires_two_consecutive_actions_and_can_be_interrupted(self):
        simulation = Simulation(2, hidden_organism=True)
        target = simulation.agents_by_name[next(iter(simulation.organisms))]
        examiner = next(agent for agent in simulation.inhabitants if agent is not target)
        simulation.record(target, "assimilation_started", target.room, visible_as="uneasy_encounter")
        simulation.tick = 2
        simulation.organisms[target.name].recovery_until = 5
        target.fatigue, examiner.fatigue = 10, 0
        self.assertTrue(simulation.resolve(examiner, Intent("examine", subject=target.name)))
        self.assertEqual(examiner.examinations[target.name], "anomaly")
        restraint = Intent("contain", subject=target.name)
        self.assertTrue(simulation.resolve(examiner, restraint))
        self.assertFalse(target.contained)
        self.assertTrue(simulation.resolve(target, Intent("move", "commons")))
        self.assertIsNone(examiner.containment_attempt)
        simulation.tick = 3
        self.assertTrue(simulation.resolve(target, Intent("move", "quarters")))
        self.assertTrue(simulation.resolve(examiner, restraint))
        self.assertFalse(target.contained)
        simulation.tick = 4
        self.assertTrue(simulation.resolve(examiner, restraint))
        self.assertTrue(target.contained)
        self.assertTrue(target.alive)
        self.assertFalse(simulation.resolve(target, Intent("wait")))
        simulation.advance()
        self.assertEqual(simulation.tick, 5)

    def test_prolonged_deprivation_can_kill_a_contained_organism(self):
        station = replace(DEFAULT_STATION, initial_food=0, power=None)
        simulation = Simulation(2, station, hidden_organism=True)
        target = simulation.agents_by_name[next(iter(simulation.organisms))]
        target.contained = True
        for _ in range(1440):
            simulation.advance()
        self.assertTrue(target.alive)
        self.assertLess(target.health, 100)
        for _ in range(360):
            simulation.advance()
        self.assertFalse(target.alive)
        self.assertTrue(target.contained)
        self.assertFalse(simulation.resolve(target, Intent("wait")))
        deaths = [event for event in simulation.history if event.action == "organism_died"]
        self.assertEqual([event.actor for event in deaths], [target.name])
        self.assertEqual(simulation.tick, 1800)

    def test_cold_damage_requires_sustained_exposure(self):
        station = Station((Room("yard", (), outdoors=True),), "yard")
        simulation = Simulation(1, station)
        agent = simulation.inhabitants[0]
        for _ in range(17):
            simulation.advance()
        self.assertEqual(agent.health, 100)
        simulation.advance()
        self.assertEqual(agent.health, 98)

    def test_supplied_station_sustains_ten_days_of_routines(self):
        simulation = self.run_seed(1, 1440)
        self.assertTrue(all(agent.health == 100 for agent in simulation.inhabitants))
        self.assertGreater(simulation.food, 0)
        self.assertEqual(simulation.power.source, "main")
        for agent in simulation.inhabitants:
            meals = [event.tick for event in simulation.history
                     if event.actor == agent.name and event.action == "eat"]
            nights = [event.tick for event in simulation.history
                      if event.actor == agent.name and event.action == "sleep_completed"]
            self.assertTrue(20 <= len(meals) <= 36)
            self.assertTrue(8 <= len(nights) <= 11)
            self.assertTrue(all(b - a >= 36 for a, b in zip(meals, meals[1:])))

    def test_long_run_preserves_resource_and_state_bounds(self):
        simulation = self.run_seed(42, 500)
        meals = sum(event.action == "eat" for event in simulation.history)
        self.assertEqual(simulation.food + meals, simulation.station.initial_food)
        self.assertGreaterEqual(simulation.food, 0)
        for agent in simulation.inhabitants:
            self.assertIn(agent.room, simulation.rooms)
            self.assertIn(agent.hunger, range(13))
            self.assertIn(agent.fatigue, range(13))
            self.assertLessEqual(len(agent.memory), 32)


if __name__ == "__main__":
    unittest.main()
