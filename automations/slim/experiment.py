"""SLIM hardware: two DeathStars (PSG, PSA) plus a spectrometer or power meter.

Each builder returns the fake when sim is true.
"""
from hardware import (DeathStar, FakeDeathStar, SpectreCore, FakeSpectreCore,
                      PowerMeter, FakePowerMeter)

PSG_PORT = "COM10"
PSA_PORT = "COM9"


def psg(sim=False):
    return FakeDeathStar(id="PSG") if sim else DeathStar(PSG_PORT, False, "PSG")


def psa(sim=False):
    return FakeDeathStar(ZAxis=True, id="PSA") if sim else DeathStar(PSA_PORT, True, "PSA")


def spectrometer(sim=False):
    return FakeSpectreCore() if sim else SpectreCore()


def power_meter(sim=False):
    return FakePowerMeter() if sim else PowerMeter()
