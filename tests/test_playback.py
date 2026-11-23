from dataclasses import replace
from fractions import Fraction
import unittest

from assimilation.kernel import DEFAULT_STATION, Intent, PowerConfig, Simulation, WORK_TICKS
from assimilation.playback import NANOSECONDS_PER_SECOND, Playback


class PlaybackTests(unittest.TestCase):
    def assert_same_simulation(self, actual, expected):
        self.assertEqual(actual.random.getstate(), expected.random.getstate())
        self.assertEqual(
            {key: value for key, value in vars(actual).items() if key != "random"},
            {key: value for key, value in vars(expected).items() if key != "random"},
        )

    def test_playback_rates_and_sample_sizes_match_unpaced_engine(self):
        station = replace(DEFAULT_STATION, power=PowerConfig("generator", 5, 3, 80, "radio"))
        expected = Simulation(19, station, hidden_organism=True)
        expected.advance_ticks(60)

        for rate, samples in ((1, 1), (5, 11), (10, 73), (60, 241)):
            with self.subTest(rate=rate, samples=samples):
                actual = Simulation(19, station, hidden_organism=True)
                playback = Playback(actual)
                playback.resume(Fraction(rate))
                duration = expected.elapsed_seconds * NANOSECONDS_PER_SECOND // rate
                for sample in range(samples):
                    start = duration * sample // samples
                    end = duration * (sample + 1) // samples
                    playback.elapse(end - start)
                self.assert_same_simulation(actual, expected)

    def test_pause_retains_partial_time_and_does_not_count_wall_time(self):
        simulation = Simulation(7)
        playback = Playback(simulation)
        playback.resume()
        self.assertEqual(playback.elapse(300 * NANOSECONDS_PER_SECOND), 0)
        playback.pause()
        self.assertEqual(playback.elapse(1000 * NANOSECONDS_PER_SECOND), 0)
        playback.resume(Fraction(3, 2))
        self.assertEqual(playback.elapse(200 * NANOSECONDS_PER_SECOND), 1)
        self.assertEqual(simulation.elapsed_seconds, 600)

    def test_movement_interrupts_an_existing_work_block(self):
        simulation = Simulation(1)
        agent = simulation.inhabitants[0]
        agent.room = "lab"
        self.assertTrue(simulation.resolve(agent, Intent("work")))
        self.assertEqual(agent.work_until, WORK_TICKS)
        self.assertTrue(simulation.resolve(agent, Intent("move", "commons")))
        self.assertFalse(simulation.resolve(agent, Intent("continue_work")))


if __name__ == "__main__":
    unittest.main()
