"""
State containers for LTB2 automation.
Plain data holders — no hardware, no signals, no IO.
"""

import time
import numpy as np


class Motors:
    __slots__ = ('x', 'y', 'feed_rate')

    def __init__(self, x=0.0, y=0.0, feed_rate=0.0):
        self.x = x
        self.y = y
        self.feed_rate = feed_rate

    def snapshot(self):
        return Motors(self.x, self.y, self.feed_rate)


class Optics:
    __slots__ = ('polarizers', 'retarders')

    def __init__(self, polarizers=(), retarders=()):
        self.polarizers = tuple(polarizers)
        self.retarders = tuple(retarders)

    def snapshot(self):
        return Optics(
            polarizers=tuple(p.snapshot() for p in self.polarizers),
            retarders=tuple(r.snapshot() for r in self.retarders),
        )


class Specimen:
    __slots__ = ('name', 'region')

    def __init__(self, name='', region=''):
        self.name = name
        self.region = region

    def snapshot(self):
        return Specimen(self.name, self.region)


class Measurement:
    __slots__ = ('wavelength', 'intensity', 'voltage',
                 'integration_time', 'timestamp')

    def __init__(self):
        self.wavelength = None
        self.intensity = None
        self.voltage = None
        self.integration_time = 0
        self.timestamp = time.time()


class System:
    __slots__ = ('gain', 'gain_map')

    def __init__(self):
        self.gain = 0.0
        self.gain_map = {}

    def snapshot(self):
        s = System()
        s.gain = self.gain
        s.gain_map = dict(self.gain_map)
        return s


class ScanConfig:
    __slots__ = ('nx', 'ny', 'spacing')

    def __init__(self, nx=5, ny=5, spacing=0.5):
        self.nx = nx
        self.ny = ny
        self.spacing = spacing


class State:
    __slots__ = ('motors', 'optics', 'specimen', 'measurement',
                 'system', 'scan_config', 'history')

    def __init__(self, optics=None):
        self.motors = Motors()
        self.optics = optics or Optics()
        self.specimen = Specimen()
        self.measurement = Measurement()
        self.system = System()
        self.scan_config = ScanConfig()
        self.history = []

    def record(self):
        snap = State(optics=self.optics.snapshot())
        snap.motors = self.motors.snapshot()
        snap.specimen = self.specimen.snapshot()
        snap.measurement = self.measurement
        snap.system = self.system.snapshot()
        snap.scan_config = self.scan_config
        snap.history = []
        self.history.append(snap)
        self.measurement = Measurement()
        return snap

    def to_dict(self):
        d = {
            'timestamp': self.measurement.timestamp,
            'x': self.motors.x,
            'y': self.motors.y,
            'specimen': self.specimen.name,
            'region': self.specimen.region,
            'gain': self.system.gain,
            'integration_time': self.measurement.integration_time,
        }
        for p in self.optics.polarizers:
            d[p.name or 'polarizer'] = p.angle
        for r in self.optics.retarders:
            d[r.name or 'retarder'] = r.angle
        if isinstance(self.measurement.wavelength, np.ndarray):
            d['spectrum_wavelengths'] = self.measurement.wavelength
            d['spectrum_intensities'] = self.measurement.intensity
        else:
            d['wavelength'] = self.measurement.wavelength
            d['voltage'] = self.measurement.voltage
        return d
