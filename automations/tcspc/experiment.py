"""TCSPC hardware: TimeHarp 260 board, plus the Cornerstone for spectral scans.

Board settings stay in each automation, since they differ per measurement.
"""
from hardware import TH260, FakeTH260, Cornerstone, FakeCornerstone


def th260(settings, bin_width_ps, sim=False):
    if sim:
        return FakeTH260(bin_width_ps=bin_width_ps)
    return TH260(settings, bin_width_ps=bin_width_ps)


def cornerstone(sim=False):
    return FakeCornerstone() if sim else Cornerstone()
