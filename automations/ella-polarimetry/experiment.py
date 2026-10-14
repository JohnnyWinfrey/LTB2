"""Polarimetry hardware: rotation stages on one daisy-chained SMC100 port."""
from hardware import SMC100, FakeSMC100

PORT = "/dev/cu.usbserial-FTE4GWPV"
ADDRESSES = [1, 2]     # one entry per controller on the chain


def retarders(sim=False):
    """One rotation axis per address on the chain, fakes when sim is true."""
    cls = FakeSMC100 if sim else SMC100
    return [cls(PORT, address=addr, units="deg") for addr in ADDRESSES]
