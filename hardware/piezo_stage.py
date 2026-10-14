"""Thorlabs KPZ101 K-Cube piezo stage (Kinesis DLL). Not wrapped for auto_gui yet."""
import os
import time

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

    def __init__(self, dll_dir=DLL_DIR):
        import ctypes as ct
        self._ct = ct
        dll_dir = os.path.abspath(dll_dir)
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
        self._try(self.lib.PCC_SetOutputVoltage(self.sx, int(vx_code)), "PCC_SetOutputVoltage X")
        self._try(self.lib.PCC_SetOutputVoltage(self.sy, int(vy_code)), "PCC_SetOutputVoltage Y")

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
