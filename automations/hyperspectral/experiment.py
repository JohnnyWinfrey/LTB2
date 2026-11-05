"""Hyperspectral hardware: XWing stage, Cornerstone monochromator, PMT gain
shield and digitizer."""
from hardware import (XWing, FakeXWing, Cornerstone, FakeCornerstone,
                      PMTShield, FakePMTShield, Digitizer, FakeDigitizer)

XWING_PORT = "COM3"
PMT_PORT = "COM4"


def setup(sim=False):
    """(xwing, cornerstone, pmt, digitizer), fakes when sim is true."""
    if sim:
        return FakeXWing(), FakeCornerstone(), FakePMTShield(), FakeDigitizer()
    return XWing(XWING_PORT), Cornerstone(), PMTShield(PMT_PORT), Digitizer()
