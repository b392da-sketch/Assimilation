"""Translate elapsed wall time into deterministic engine steps."""

from fractions import Fraction

from .kernel import Simulation

NANOSECONDS_PER_SECOND = 1_000_000_000


class Playback:
    """A paused-by-default controller driven by monotonic elapsed time samples."""

    def __init__(self, simulation: Simulation) -> None:
        self.simulation = simulation
        self.rate = Fraction(1)
        self.running = False
        self._credit = Fraction(0)

    def resume(self, rate: Fraction = Fraction(1)) -> None:
        if rate <= 0:
            raise ValueError("Playback rate must be positive.")
        self.rate = rate
        self.running = True

    def pause(self) -> None:
        self.running = False

    def elapse(self, wall_nanoseconds: int) -> int:
        if wall_nanoseconds < 0:
            raise ValueError("Elapsed wall time must be nonnegative.")
        if not self.running:
            return 0
        self._credit += wall_nanoseconds * self.rate
        quantum = self.simulation.STEP_SECONDS * NANOSECONDS_PER_SECOND
        ticks, self._credit = divmod(self._credit, quantum)
        self.simulation.advance_ticks(ticks)
        return ticks
