"""Thorlabs KPZ101 K-Cube piezo stage (Kinesis DLL).

  PiezoStage        what automations and the GUI use: a few simple methods
                    (stage.goto(vx, vy), stage.position(), ...) plus the
                    scan range the GUI fills in (axis, startDac, endDac,
                    numSteps, fixedDac).
  StageClient       all the hardware code: every Kinesis Piezo command as a
                    method, over the Kinesis Thorlabs.MotionControl.KCube.Piezo.dll.
  FakePiezoStage    PiezoStage on a simulated stage pair (--sim).

A piezo jumps, it doesn't slew: setdac() is a step and the move is visible
right away; the settleTime in a scan covers the ringing. Output voltages are
raw DAC codes, 0..32767 = 0..max output voltage.
"""
import os
import time
from typing import Literal

from ._shared import HELPERS_DIR


class StageClient:
    """
    Direct ctypes driver for the two Thorlabs KPZ101 K-Cube piezo controllers
    (X and Y) via the Kinesis Thorlabs.MotionControl.KCube.Piezo.dll -- the same
    approach as Thorlabs' Kinesis Python examples. Replaces the old
    stage_helper_ultra.exe; the DLLs it needs ship in helpers/.

    Output voltages are raw DAC codes, 0..32767 = 0..max output voltage.
    """

    DLL_DIR = HELPERS_DIR
    DLL_NAME = "Thorlabs.MotionControl.KCube.Piezo.dll"
    SERIAL_X = "29503259"
    SERIAL_Y = "29500307"
    POLL_MS = 200
    DAC_MAX = 32767

    def __init__(self, dll_dir=None):
        import ctypes as ct
        self._ct = ct
        dll_dir = os.path.abspath(dll_dir or self.DLL_DIR)
        # The piezo DLL loads DeviceManager.dll from its own folder.
        self._dll_dir_handle = os.add_dll_directory(dll_dir)
        self.lib = ct.CDLL(os.path.join(dll_dir, self.DLL_NAME))
        for fn in ("PCC_Open", "PCC_Close", "PCC_StopPolling", "PCC_Enable",
                   "PCC_Disable", "PCC_CheckConnection"):
            getattr(self.lib, fn).argtypes = [ct.c_char_p]
        self.lib.PCC_StartPolling.argtypes = [ct.c_char_p, ct.c_int]
        self.lib.PCC_SetMaxOutputVoltage.argtypes = [ct.c_char_p, ct.c_short]
        self.lib.PCC_SetOutputVoltage.argtypes = [ct.c_char_p, ct.c_short]
        self.lib.PCC_CheckConnection.restype = ct.c_bool
        self.lib.PCC_StartPolling.restype = ct.c_bool
        self.sx = self.sy = None
        self.vx = self.vy = 0

    def _try(self, retcode, name):
        if retcode != 0:
            raise RuntimeError(f"{name} failed (Kinesis error {retcode})")

    def open(self, serial_x=None, serial_y=None, vmax_tenths=750):
        """Open, enable and zero both axes. vmax_tenths is the max output
        voltage in tenths of a volt (750 = 75.0 V)."""
        self.sx = (serial_x or self.SERIAL_X).encode()
        self.sy = (serial_y or self.SERIAL_Y).encode()
        self._try(self.lib.TLI_BuildDeviceList(), "TLI_BuildDeviceList")
        for s in (self.sx, self.sy):
            self._try(self.lib.PCC_Open(s), f"PCC_Open({s.decode()})")
            self.lib.PCC_StartPolling(s, self.POLL_MS)
            time.sleep(0.5)  # let polling fill in the device state
            self._try(self.lib.PCC_Enable(s), f"PCC_Enable({s.decode()})")
            self._try(self.lib.PCC_SetMaxOutputVoltage(s, int(vmax_tenths)),
                      f"PCC_SetMaxOutputVoltage({s.decode()})")
        self.setdac(0, 0)

    def setdac(self, vx_code, vy_code):
        self.vx = int(vx_code)
        self.vy = int(vy_code)
        self._try(self.lib.PCC_SetOutputVoltage(self.sx, int(vx_code)), "PCC_SetOutputVoltage X")
        self._try(self.lib.PCC_SetOutputVoltage(self.sy, int(vy_code)), "PCC_SetOutputVoltage Y")

    def position(self):
        """(vx, vy) -- the DAC codes last commanded to each axis."""
        return (self.vx, self.vy)

    def move_ix(self, ix, iy, width, height):
        """Map pixel index (0..width-1, 0..height-1) to DAC codes."""
        vx = ix * self.DAC_MAX // width if width > 0 else 0
        vy = iy * self.DAC_MAX // height if height > 0 else 0
        self.setdac(vx, vy)

    def reset(self, ix, width):
        """Step the X axis back from pixel ix to 0 one pixel at a time."""
        for i in range(ix, -1, -1):
            vx = i * self.DAC_MAX // width if width > 0 else 0
            self.lib.PCC_SetOutputVoltage(self.sx, vx)

    def status(self):
        """{'X': '0'|'1', 'Y': '0'|'1'} -- 1 = connected."""
        return {"X": str(int(self.lib.PCC_CheckConnection(self.sx))),
                "Y": str(int(self.lib.PCC_CheckConnection(self.sy)))}

    def disable(self):
        for s in (self.sx, self.sy):
            if s:
                try:
                    self.lib.PCC_Disable(s)
                except Exception:
                    pass

    def close(self):
        try:
            self.disable()
        finally:
            for s in (self.sx, self.sy):
                if s:
                    self.lib.PCC_StopPolling(s)
                    self.lib.PCC_Close(s)
            self.sx = self.sy = None


class PiezoStage:
    """The piezo stage, made simple. Use this in automations:

        stage.goto(1000, 2000)  # both axes to those DAC codes (instant)
        stage.position()        # (vx, vy) current DAC codes

    The GUI fills in a scan range for automations to read: axis ("X" or "Y"),
    startDac, endDac, numSteps, and fixedDac -- where the other axis sits
    while one axis is swept.

    Every method here just calls StageClient (stage.client), which has all
    the hardware code and the less common commands.
    """

    DAC_MAX = StageClient.DAC_MAX

    def __init__(self, dll_dir=None):
        self.name = "Piezo stage"
        self._connect(dll_dir)
        self.axis = "X"
        self.startDac = 0
        self.endDac = self.DAC_MAX
        self.numSteps = 50
        self.fixedDac = 0
        print("PiezoStage online")

    def _connect(self, dll_dir=None):
        client = StageClient(dll_dir)
        try:
            client.open()   # enables both axes and zeros them
        except Exception:
            client.close()
            raise
        self.client = client

    def goto(self, vx, vy):
        """Move both axes to DAC codes 0..32767. A piezo is a step, not a
        slew: the move is done as soon as the command goes out."""
        self.client.setdac(int(vx), int(vy))

    def position(self):
        """(vx, vy) -- the DAC codes last commanded to each axis."""
        return self.client.position()

    # --- GUI: scan range for automations ------------------------------------

    def setAxis(self, axis: Literal["X", "Y"]):
        self.axis = str(axis).upper()
        print(f"Scan axis: {self.axis}")

    def setStartDac(self, value_str):
        self.startDac = self._clampDac(value_str)
        print(f"Start DAC: {self.startDac}")

    def setEndDac(self, value_str):
        self.endDac = self._clampDac(value_str)
        print(f"End DAC: {self.endDac}")

    def setNumSteps(self, value_str):
        self.numSteps = max(1, int(value_str))
        print(f"Steps: {self.numSteps}")

    def setFixedDac(self, value_str):
        self.fixedDac = self._clampDac(value_str)
        print(f"Fixed axis DAC: {self.fixedDac}")

    def _clampDac(self, value):
        return int(round(min(max(float(value), 0.0), self.DAC_MAX)))


class FakeStageClient(StageClient):
    """StageClient with the Kinesis DLL swapped for stored DAC codes, so
    automations run under --sim with nothing plugged in."""

    def __init__(self, dll_dir=None):
        # Skip StageClient.__init__: it loads the Kinesis DLL.
        self.sx = self.sy = None
        self.vx = self.vy = 0

    def open(self, serial_x=None, serial_y=None, vmax_tenths=750):
        self.sx = (serial_x or self.SERIAL_X).encode()
        self.sy = (serial_y or self.SERIAL_Y).encode()
        self.setdac(0, 0)

    def setdac(self, vx_code, vy_code):
        self.vx = int(vx_code)
        self.vy = int(vy_code)

    def status(self):
        return {"X": "1", "Y": "1"}

    def reset(self, ix, width):
        for i in range(ix, -1, -1):
            self.setdac(i * self.DAC_MAX // width if width > 0 else 0, self.vy)

    def disable(self):
        pass

    def close(self):
        self.sx = self.sy = None


class FakePiezoStage(PiezoStage):
    """Headless piezo stage: real logic driving a simulated KPZ101 pair."""

    def _connect(self, dll_dir=None):
        client = FakeStageClient(dll_dir)
        client.open()
        self.client = client
