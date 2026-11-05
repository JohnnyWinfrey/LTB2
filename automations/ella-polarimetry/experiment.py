"""Polarimetry hardware: rotation stages on one daisy-chained SMC100 port,
plus an SR510 lock-in."""
from hardware import SMC100, FakeSMC100, SR510, FakeSR510, Cornerstone, FakeCornerstone

PORT = "/dev/cu.usbserial-FTE4GWPV"
ADDRESSES = [1, 2]     # one entry per controller on the chain
LOCKIN_PORT = "/dev/cu.usbserial-XXXXXXXX"   # !!! set to the SR510 dongle's port


def retarders(sim=False):
    """One rotation axis per address on the chain, fakes when sim is true."""
    cls = FakeSMC100 if sim else SMC100
    return [cls(PORT, address=addr, units="deg") for addr in ADDRESSES]


def lockin(sim=False):
    return FakeSR510() if sim else SR510(LOCKIN_PORT)

def cornerstone(sim=False):
    return FakeCornerstone() if sim else Cornerstone()