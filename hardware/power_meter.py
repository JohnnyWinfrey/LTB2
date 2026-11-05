"""Thorlabs power meter over pyvisa/USB."""
import random


class PowerMeter:
    """Real Thorlabs power meter over pyvisa/USB."""

    def __init__(self):
        # Handles opened once via open(), closed once via close().
        self.rm    = None
        self.instr = None

    def _connect(self):
        import pyvisa

        self.rm = pyvisa.ResourceManager()
        # !!! The serial number (P00...) and PID (0x8078) must match the
        #     connected device. Check with the Windows Device Manager.
        self.instr = self.rm.open_resource(
            'USB0::0x1313::0x8078::P0011973::INSTR'
        )

    def open(self, wl):
        """Open the resource manager + instrument and apply one-time config."""
        self._connect()
        # print(self.instr.query("SYST:SENS:IDN?"))
        self.instr.write("SENS:RANGE:AUTO ON")
        self.instr.write(f"SENS:CORR:WAV {wl}")
        self.instr.write("SENS:POW:UNIT W")
        # set averaging to 1000 points (COUN is the count subcommand)
        self.instr.write("SENS:AVER:COUN 1000")
        print("Power meter connected")

    def measure(self):
        """Read a single power value from the already-open meter."""
        # query() returns the raw text response, e.g. "1.234567E-06\n";
        # cast to float so downstream arrays are numeric.
        power = float(self.instr.query("MEAS:POW?"))
        print(f"Measured power = {power}")
        return power

    def close(self):
        """Close the instrument and resource manager if they are open."""
        for handle in (self.instr, self.rm):
            if handle is not None:
                try:
                    handle.close()
                except Exception:
                    pass
        self.instr = self.rm = None
        print("Power meter closed")


class _FakeVisaInstrument:
    """No-op stand-in for a pyvisa resource; MEAS:POW? returns a random power."""

    def write(self, command):
        pass

    def query(self, command):
        return str(random.uniform(1e-6, 1e-3))

    def close(self):
        pass


class FakePowerMeter(PowerMeter):
    """Headless power meter: real logic reading a fake VISA instrument."""

    def _connect(self):
        self.instr = _FakeVisaInstrument()
