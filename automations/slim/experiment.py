"""SLIM hardware: Medusa (PSG + PSA optics and the xwing on one Mega) plus a
spectrometer or power meter.

Each builder returns the fake when sim is true.
"""
from hardware import (Medusa, FakeMedusa, SpectreCore, FakeSpectreCore,
                      PowerMeter, FakePowerMeter)

MEDUSA_PORT = "/dev/cu.usbmodem1301"


def medusa(sim=False):
    return FakeMedusa() if sim else Medusa(MEDUSA_PORT)


def spectrometer(sim=False):
    return FakeSpectreCore() if sim else SpectreCore()


def power_meter(sim=False):
    return FakePowerMeter() if sim else PowerMeter()
