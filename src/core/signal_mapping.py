"""
real_time_solver.py

Provides RealTimeSolver for real-time hydraulic and quality
simulation. Handles signal input, simulation steps, and
result storage with raw output.
Settings for timing are read from a TOML config under [TIMES].
"""

from __future__ import annotations

import time
import threading
from datetime import datetime, timedelta
import toml
from epanet_solver import EpanetSimulation
from signal_mapping import SignalMapping
from data_container import DataContainer


class RealTimeSolver:
    """
    Real-time hydraulic and quality simulation service.

    Manages a background thread to:
      1. Fetch signals
      2. Update and run simulation step
      3. Store results
      4. Repeat at configured real-time interval

    Configuration:
      [TIMES]
      real_time_step = <seconds>
      initial_timestamp = "YYYY/MM/DD HH:MM:SS"

    Methods:
        start(): Begin background loop.
        pause(): Pause loop.
        resume(): Resume paused loop.
        halt(): Stop loop.
        status(): Return interval and timestamps.
        get_last(): Return last stored results as Python dict.
        get(...): Query stored results as Python dict.
    """

    def __init__(
        self,
        config_file: str,
    ):
        """
        Initialize solver from a TOML config.

        Args:
            config_file: path to TOML config file containing [TIMES].
        """
        # Load config
        cfg = toml.load(config_file)
        times = cfg.get('TIMES', {})
        try:
            step = int(times['real_time_step'])
            initial_ts = times.get('initial_timestamp')
        except KeyError as e:
            raise ValueError(f"Missing TIMES setting: {e}")

        # Parse initial timestamp if provided
        if initial_ts:
            # expect "YYYY/MM/DD HH:MM:SS"
            self.start_time = datetime.strptime(initial_ts, '%Y/%m/%d %H:%M:%S')
        else:
            self.start_time = datetime.utcnow()
        self.current_time = self.start_time

        # Interval for real-time steps
        self.interval = timedelta(seconds=step)

        # Load signal mapper and Epanet simulation
        self.signals = SignalMapping(config_file)
        self.sim = EpanetSimulation()

        # Prepare data container
        self.data = DataContainer(interval=self.interval)

        # Control flags and thread handle
        self._running = False
        self._paused = False
        self._thread: threading.Thread | None = None

    def _loop(self) -> None:
        """Internal loop: fetch, update, run, store, wait."""
        while self._running:
            if self._paused:
                time.sleep(0.1)
                continue
            now = datetime.utcnow()
            self.current_time = now
            obs = self.signals.get(now)
            self.sim.update(obs)
            self.sim.run_step()
            _ = self.sim.get_losses()
            results = self.sim.get_results()
            try:
                self.data.add(now, results)
            except ValueError as err:
                raise RuntimeError("Data add error: " + str(err))
            time.sleep(self.interval.total_seconds())

    def start(self) -> None:
        """Start the simulation loop in a daemon thread."""
        if self._running:
            return
        self._running = True
        # Reset current_time for run
        self.current_time = self.start_time
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def pause(self) -> None:
        """Pause the simulation loop."""
        self._paused = True

    def resume(self) -> None:
        """Resume a paused simulation loop."""
        self._paused = False

    def halt(self) -> None:
        """Stop the simulation and join the thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.interval.total_seconds())

    def status(self) -> dict:
        """Return interval and current status info."""
        state = 'PAUSED' if self._paused else 'RUNNING' if self._running else 'STOPPED'
        return {
            'real_time_step': int(self.interval.total_seconds()),
            'status': state,
            'start_time': self.start_time.isoformat(),
            'current_time': self.current_time.isoformat(),
        }

    def get_last(self) -> dict:
        """Return last stored results as a Python dict."""
        return self.data.get_last()

    def get(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        element_type: str | None = None,
        element_id: str | None = None,
        variable: str | None = None,
    ) -> dict:
        """Query stored data with optional filters."""
        return self.data.get(start_time, end_time, element_type, element_id, variable)
