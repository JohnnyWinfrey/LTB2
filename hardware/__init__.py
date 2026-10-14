"""Device classes for auto_gui, one module per device.

Each module holds the device's transport (serial port, DLL, VISA, ...), the
real class, and its fake. A real class opens its transport in `_connect()`;
the fake subclasses it and overrides only `_connect()` to plug in a no-op
stand-in, so every control method is shared and auto_gui builds an identical
window either way. Automations pick the fakes with --sim to run on a laptop
with nothing plugged in.

Driver imports (pyvisa, seabreeze, serial, niscope) are lazy, inside the
methods that open the device, so this package imports on any machine.

To add a device: drop a module in here and re-export its classes below.
"""
from .power_meter import PowerMeter, FakePowerMeter
from .death_star import DeathStar, FakeDeathStar
from .xwing import XWing, FakeXWing
from .smc100 import SMC100, FakeSMC100
from .spectre_core import SpectreCore, FakeSpectreCore
from .cornerstone import Cornerstone, FakeCornerstone
from .pmt_shield import PMTShield, FakePMTShield
from .digitizer import Digitizer, FakeDigitizer
from .th260 import TH260, FakeTH260
from .piezo_stage import StageClient
