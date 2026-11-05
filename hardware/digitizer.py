"""Digitizer -- NI scope, one averaged-voltage reading."""
import random

import numpy as np


class NIScopeClient:
    """Averages one 5 MS record from channel 1 of the NI scope (Dev1)."""

    def record(self):
        import niscope

        with niscope.Session("Dev1") as session:
            session.channels[1].configure_vertical(range=40.0, coupling=niscope.VerticalCoupling.DC)
            session.configure_horizontal_timing(
                min_sample_rate=5000000,
                min_num_pts=5000000,
                ref_position=50.0,  # percent of the record before the trigger
                num_records=1,
                enforce_realtime=True,
            )
            with session.initiate():
                waveforms = session.channels[1].fetch()
            return np.mean(waveforms[0].samples)


class Digitizer:
    """NI digitizer: one averaged-voltage reading. QML-free port of the
    NIScopeClient use in the automation clusters.

    `measure()` is named so auto_gui shows it as a read-out button + value
    label; automations also call it directly (replacing the clusters' old
    self.digi.record()).
    """

    def __init__(self):
        self._connect()
        print(f"{type(self).__name__} online")

    def _connect(self):
        self.scope = NIScopeClient()

    def measure(self):
        voltage = self.scope.record()
        print(f"Digitizer measured {voltage} V")
        return voltage


class _FakeScope:
    """No-op stand-in for NIScopeClient: a random voltage in a plausible range."""

    def record(self):
        return random.uniform(0.0, 10.0)


class FakeDigitizer(Digitizer):
    """Headless digitizer: real logic reading a fake scope."""

    def _connect(self):
        self.scope = _FakeScope()
