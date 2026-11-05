"""TCSPC hardware: TimeHarp 260 board, the Cornerstone for spectral scans,
the KPZ101 piezo stage pair, and the KDC101 DC servo stage.

Board settings stay in each automation, since they differ per measurement.
"""
from hardware import (
    TH260, FakeTH260,
    Cornerstone, FakeCornerstone,
    PiezoStage, FakePiezoStage,
    KDC101Stage, FakeKDC101Stage,
)


def th260(settings, bin_width_ps, sim=False):
    if sim:
        return FakeTH260(bin_width_ps=bin_width_ps)
    return TH260(settings, bin_width_ps=bin_width_ps)


def cornerstone(sim=False):
    return FakeCornerstone() if sim else Cornerstone()


def stage(sim=False):
    """The KPZ101 piezo stage pair (open loop, DAC codes on X and Y)."""
    return FakePiezoStage() if sim else PiezoStage()


def kdc101(sim=False):
    """The KDC101 DC servo stage (motorized, millimeters)."""
    return FakeKDC101Stage() if sim else KDC101Stage()
