"""Thorlabs KDC101 K-Cube DC servo stage (Kinesis DLL).

  KDC101Stage       what automations and the GUI use: a few simple methods
                    (stage.gotoMm(mm), stage.getPosition(), ...) plus the
                    scan range the GUI fills in (startMm, endMm, numSteps).
  KDC101Client      all the hardware code: every Kinesis CC command as a
                    method, over the Kinesis Thorlabs.MotionControl.KCube.
                    DCServo.dll.
  FakeKDC101Stage   KDC101Stage on a simulated stage (--sim).

The KDC101 is a motorized DC servo positioner, not a piezo: it slews to a
position at the move velocity instead of jumping, so gotoMm() waits for the
stage to arrive (and the scan's settleTime only covers the last bit of
mechanical settling). The position zero is set by homing (home()), which
must be done before moving.

Positions are millimeters, the device's real units; the raw device units
are motor steps. The motor setup applied on connect (STEPS_PER_REV,
GBOX_RATIO, PITCH) is the one from Thorlabs' official KDC101 example
(KDC101 + PRM1-Z8) -- use setMotorParams if yours differs.

The DLL is searched in the standard Kinesis install folders first (C:\\Program
Files (x86) or C:\\Program Files, then the Thorlabs\\Kinesis subfolder) because
its companion DLLs (the DeviceManager family) must sit next to it; a copy in
helpers/ is the fallback. Either way only the DLLs are needed, not the
Kinesis app. The Kinesis set in helpers/ must be from one release: mixing,
e.g., a new DCServo.dll with an old DeviceManager.dll fails to load.
"""
import os
import time

from ._shared import HELPERS_DIR


class KDC101Client:
    """
    Direct ctypes driver for the Thorlabs KDC101 K-Cube DC servo positioner
    via the Kinesis Thorlabs.MotionControl.KCube.DCServo.dll -- the same
    approach as Thorlabs' official KDC101 example.

    Positions are motor steps (signed ints); the unit converters below
    translate to/from real units (mm for a linear stage).
    """

    DLL_DIR = HELPERS_DIR
    DLL_NAME = "Thorlabs.MotionControl.KCube.DCServo.dll"
    DEFAULT_SERIAL = "27600928"   # the lab KDC101 (getDevices lists all of them)
    DEVICE_TYPE = 27      # KDC101 serials start with 27 (KPZ101s are 295)
    POLL_MS = 200
    # The KDC101 is a controller; the scale depends on the stage it drives.
    # steps/mm = STEPS_PER_REV * GBOX_RATIO / PITCH (per the DCServo header).
    # The lab stage (Kinesis reference) moves 18.0 motor revs per mm, i.e.
    # 34553.55 steps/mm -- 18x the stock example params (measured: 0.1461 mm
    # real vs 2.6302 mm reported). If you know the true gearbox/screw values
    # (Kinesis -> Motor Parameters), set them here or via setMotorParams.
    STEPS_PER_REV = 1919.64186   # PRM1-Z8 motor (per Thorlabs' example)
    GBOX_RATIO = 18.0            # 18 motor revs per output rev
    PITCH = 1.0                  # mm per output rev

    # CC_GetDeviceUnitFromRealValue unit types
    UNIT_DISTANCE = 0
    UNIT_VELOCITY = 1
    UNIT_ACCEL = 2

    # The DC servo DLL's companions (the DeviceManager family) must be found
    # next to it, so the Kinesis install folder is preferred over helpers/.
    KINESIS_DIRS = (
        r"C:\Program Files (x86)\Thorlabs\Kinesis",
        r"C:\Program Files\Thorlabs\Kinesis",
    )

    def _find_dll(self, dll_dir=None):
        dirs = []
        if dll_dir:
            dirs.append(os.path.abspath(dll_dir))
        dirs.extend(self.KINESIS_DIRS)
        dirs.append(self.DLL_DIR)
        for d in dirs:
            path = os.path.join(d, self.DLL_NAME)
            if os.path.exists(path):
                return path
        raise FileNotFoundError(
            f"{self.DLL_NAME} not found in helpers/ or the Kinesis install "
            "folders -- install Kinesis or copy the DLL (and its companions) "
            "into helpers/")

    def __init__(self, dll_dir=None):
        import ctypes as ct
        self._ct = ct
        dll_path = self._find_dll(dll_dir)
        # The DC servo DLL loads its companion DLLs from its own folder.
        if hasattr(os, "add_dll_directory"):
            self._dll_dir_handle = os.add_dll_directory(os.path.dirname(dll_path))
        self.lib = ct.CDLL(dll_path)
        for fn in ("CC_Open", "CC_Close", "CC_StopPolling", "CC_EnableChannel",
                   "CC_DisableChannel", "CC_CheckConnection", "CC_Home",
                   "CC_ClearMessageQueue", "CC_MoveAbsolute",
                   "CC_StopImmediate", "CC_RequestPosition"):
            getattr(self.lib, fn).argtypes = [ct.c_char_p]
        self.lib.CC_StartPolling.argtypes = [ct.c_char_p, ct.c_int]
        self.lib.CC_SetVelParams.argtypes = [ct.c_char_p, ct.c_int, ct.c_int]
        self.lib.CC_GetVelParams.argtypes = [ct.c_char_p, ct.POINTER(ct.c_int),
                                             ct.POINTER(ct.c_int)]
        self.lib.CC_SetMoveAbsolutePosition.argtypes = [ct.c_char_p, ct.c_int]
        self.lib.CC_SetMotorParamsExt.argtypes = [ct.c_char_p, ct.c_double,
                                                  ct.c_double, ct.c_double]
        self.lib.CC_GetMotorParamsExt.argtypes = [ct.c_char_p, ct.POINTER(ct.c_double),
                                                  ct.POINTER(ct.c_double),
                                                  ct.POINTER(ct.c_double)]
        self.lib.CC_GetRealValueFromDeviceUnit.argtypes = [ct.c_char_p, ct.c_int,
                                                           ct.POINTER(ct.c_double), ct.c_int]
        self.lib.CC_GetDeviceUnitFromRealValue.argtypes = [ct.c_char_p, ct.c_double,
                                                           ct.POINTER(ct.c_int), ct.c_int]
        self.lib.CC_GetMotorTravelLimits.argtypes = [ct.c_char_p, ct.POINTER(ct.c_double),
                                                     ct.POINTER(ct.c_double)]
        self.lib.CC_GetNextMessage.argtypes = [ct.c_char_p, ct.POINTER(ct.c_ushort),
                                               ct.POINTER(ct.c_ushort),
                                               ct.POINTER(ct.c_uint32)]
        self.lib.TLI_GetDeviceListByTypeExt.argtypes = [ct.c_char_p, ct.c_uint32, ct.c_int]
        self.lib.CC_CheckConnection.restype = ct.c_bool
        self.lib.CC_StartPolling.restype = ct.c_bool
        self.lib.CC_NeedsHoming.restype = ct.c_bool
        self.lib.CC_GetPosition.restype = ct.c_int
        self.lib.CC_GetBacklash.restype = ct.c_long
        self.lib.CC_MessageQueueSize.restype = ct.c_int
        self.lib.CC_GetNextMessage.restype = ct.c_bool
        self.s = None
        self._travel = (0.0, 0.0)
        self._backlash_mm = 0.01

    def _try(self, retcode, name):
        if retcode != 0:
            raise RuntimeError(f"{name} failed (Kinesis error {retcode})")

    def open(self, serial=None):
        """Open, enable, and set up the motor (real units become mm)."""
        serial = (serial or "").strip()
        if not serial:
            raise ValueError("no serial number -- set it in the 'KDC101 stage' "
                             "window first (getDevices lists the KDC101s)")
        self.s = serial.encode()
        self._try(self.lib.TLI_BuildDeviceList(), "TLI_BuildDeviceList")
        self._try(self.lib.CC_Open(self.s), f"CC_Open({serial})")
        self.lib.CC_StartPolling(self.s, self.POLL_MS)
        time.sleep(0.5)  # let polling fill in the device state
        self._try(self.lib.CC_EnableChannel(self.s), f"CC_EnableChannel({serial})")
        self._try(self.lib.CC_SetMotorParamsExt(self.s, self.STEPS_PER_REV,
                                                self.GBOX_RATIO, self.PITCH),
                  f"CC_SetMotorParamsExt({serial})")
        lo = self._ct.c_double()
        hi = self._ct.c_double()
        self._try(self.lib.CC_GetMotorTravelLimits(self.s, self._ct.byref(lo),
                                                   self._ct.byref(hi)),
                  f"CC_GetMotorTravelLimits({serial})")
        self._travel = (float(lo.value), float(hi.value))
        self._backlash_mm = max(self.dev_to_mm(self.lib.CC_GetBacklash(self.s)), 0.01)

    def connected(self):
        return bool(self.s) and bool(self.lib.CC_CheckConnection(self.s))

    def devices(self):
        """Serial numbers of the KDC101s on the USB bus, as one string."""
        buf = self._ct.create_string_buffer(100)
        self._try(self.lib.TLI_BuildDeviceList(), "TLI_BuildDeviceList")
        self._try(self.lib.TLI_GetDeviceListByTypeExt(buf, 100, self.DEVICE_TYPE),
                  "TLI_GetDeviceListByTypeExt")
        return buf.value.decode().strip()

    # --- unit conversion ----------------------------------------------------
    def real_to_dev(self, value, unit_type):
        dev = self._ct.c_int()
        self._try(self.lib.CC_GetDeviceUnitFromRealValue(self.s, float(value),
                                                         self._ct.byref(dev), int(unit_type)),
                  "CC_GetDeviceUnitFromRealValue")
        return dev.value

    def dev_to_real(self, dev, unit_type):
        real = self._ct.c_double()
        self._try(self.lib.CC_GetRealValueFromDeviceUnit(self.s, int(dev),
                                                         self._ct.byref(real), int(unit_type)),
                  "CC_GetRealValueFromDeviceUnit")
        return real.value

    def mm_to_dev(self, mm):
        return self.real_to_dev(mm, self.UNIT_DISTANCE)

    def dev_to_mm(self, dev):
        return self.dev_to_real(dev, self.UNIT_DISTANCE)

    # --- position (mm) -------------------------------------------------------
    def position_dev(self):
        """The position the stage reports, in motor steps."""
        self.lib.CC_RequestPosition(self.s)
        return int(self.lib.CC_GetPosition(self.s))

    def position_mm(self):
        return self.dev_to_mm(self.position_dev())

    def travel_mm(self):
        return self._travel

    def needs_homing(self):
        return bool(self.lib.CC_NeedsHoming(self.s))

    # --- motion ---------------------------------------------------------------
    def home(self, timeout_s=120.0):
        """Home the stage (position becomes 0). Waits for the 'done' message
        the same way Thorlabs' official example does (type 2, id 0)."""
        self.lib.CC_ClearMessageQueue(self.s)
        self._try(self.lib.CC_Home(self.s), "CC_Home")
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if self.lib.CC_MessageQueueSize(self.s) > 0:
                mtype = self._ct.c_ushort()
                mid = self._ct.c_ushort()
                mdata = self._ct.c_uint32()
                if self.lib.CC_GetNextMessage(self.s, self._ct.byref(mtype),
                                              self._ct.byref(mid), self._ct.byref(mdata)) \
                        and mtype.value == 2 and mid.value == 0:
                    return
            time.sleep(0.05)
        raise RuntimeError(f"KDC101 homing did not finish within {timeout_s:.0f} s")

    def move_absolute_mm(self, mm, timeout_s=120.0):
        """Move to mm and wait until the stage is there. Returns the achieved
        position in mm."""
        dev = self.mm_to_dev(mm)
        self._try(self.lib.CC_SetMoveAbsolutePosition(self.s, int(dev)),
                  "CC_SetMoveAbsolutePosition")
        self._try(self.lib.CC_MoveAbsolute(self.s), "CC_MoveAbsolute")
        return self.wait_arrival(mm, timeout_s)

    def wait_arrival(self, mm, timeout_s=120.0):
        """Poll the reported position until it is at mm (within backlash) or
        the deadline passes. Returns the achieved position in mm."""
        tol = max(self._backlash_mm, 0.05)
        actual = self.position_mm()
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if abs(actual - mm) <= tol:
                return actual
            time.sleep(0.2)
            actual = self.position_mm()
        raise RuntimeError(f"KDC101 did not reach {mm} mm "
                           f"(position {actual:.3f} mm after {timeout_s:.0f} s)")

    def stop(self):
        self._try(self.lib.CC_StopImmediate(self.s), "CC_StopImmediate")

    # --- velocity / acceleration (mm/s, mm/s^2) --------------------------------
    def _vel_dev_units(self):
        a, v = self._ct.c_int(), self._ct.c_int()
        self._try(self.lib.CC_GetVelParams(self.s, self._ct.byref(a), self._ct.byref(v)),
                  "CC_GetVelParams")
        return a.value, v.value

    def velocity_mm(self):
        """(acceleration mm/s^2, velocity mm/s)."""
        a, v = self._vel_dev_units()
        return self.dev_to_real(a, self.UNIT_ACCEL), self.dev_to_real(v, self.UNIT_VELOCITY)

    def setvelocity_mm(self, v_mm_s, a_mm_s2=None):
        """Set the move velocity (mm/s) and, if given, the acceleration."""
        a_dev, v_dev = self._vel_dev_units()
        v_dev = self.real_to_dev(v_mm_s, self.UNIT_VELOCITY)
        if a_mm_s2 is not None:
            a_dev = self.real_to_dev(a_mm_s2, self.UNIT_ACCEL)
        self._try(self.lib.CC_SetVelParams(self.s, int(a_dev), int(v_dev)),
                  "CC_SetVelParams")

    def disable(self):
        if self.s:
            try:
                self.lib.CC_DisableChannel(self.s)
            except Exception:
                pass

    def close(self):
        try:
            self.disable()
        finally:
            if self.s:
                self.lib.CC_StopPolling(self.s)
                self.lib.CC_Close(self.s)
                self.s = None


class KDC101Stage:
    """The KDC101 DC servo stage, made simple. Use this in automations:

        stage.connect()       open the KDC101 (serial set via setSerial)
        stage.home()          move to the home position (0 mm)
        stage.gotoMm(5.0)     move to 5.0 mm, waiting for arrival
        stage.getPosition()   the position the stage reports, mm
        stage.getTravel()     the travel limits, mm

    The GUI fills in a scan range for automations to read: startMm, endMm,
    numSteps. Velocity and acceleration default to the device's stored
    values; setVelocity / setAcceleration change them.

    Every method here just calls KDC101Client (stage.client), which has all
    the hardware code and the less common commands.
    """

    def __init__(self, dll_dir=None):
        self.name = "KDC101 stage"
        self._connect(dll_dir)
        self.serial = KDC101Client.DEFAULT_SERIAL
        self.startMm = 0.0
        self.endMm = 0.0
        self.numSteps = 50
        self._connected = False
        print("KDC101Stage online -- set the serial and press connect")

    def _connect(self, dll_dir=None):
        # Load the DLL only; connect() opens the device once the serial is
        # known (it's a field in the window, not a hardwired constant).
        self.client = KDC101Client(dll_dir)

    # --- device ------------------------------------------------------------

    def connect(self):
        """Open the KDC101 and enable it. If it reports that it needs
        homing, press home before moving anywhere."""
        self.client.open(self.serial)
        self._connected = True
        lo, hi = self.client.travel_mm()
        self.startMm = 0.0
        self.endMm = hi if hi > lo else 100.0
        limits = (f"travel {lo:.1f}..{hi:.1f} mm" if hi > lo
                  else "travel limits unset (0..0) -- moves are not clamped, "
                       "set the scan range in this window")
        scale = self.client.STEPS_PER_REV * self.client.GBOX_RATIO / self.client.PITCH
        state = "homed" if not self.client.needs_homing() \
            else "NOT homed -- press home"
        print(f"KDC101 {self.serial} online, scale {scale:.0f} steps/mm, "
              f"{limits}, {state}")

    def getDevices(self):
        """The KDC101 serial numbers Kinesis sees."""
        return self.client.devices() or "none found"

    def setSerial(self, value_str):
        self.serial = str(value_str).strip()
        print(f"Serial: {self.serial}")

    def getStatus(self):
        if not self._connected:
            return "disconnected"
        state = "homed" if not self.client.needs_homing() else "NOT homed"
        return f"{self.serial}, {state}"

    def home(self):
        """Move to the home position (0 mm)."""
        self._requireConnected()
        self.client.home()
        print("KDC101 homed -- position is now 0 mm")

    def stopMove(self):
        """Stop the stage immediately."""
        self._requireConnected()
        self.client.stop()
        print("Move stopped")

    # --- position (millimeters) --------------------------------------------

    def _requireConnected(self):
        if not self._connected:
            raise RuntimeError("KDC101 not connected -- press connect first")

    def _checkHomed(self):
        if self.client.needs_homing():
            raise RuntimeError("KDC101 is not homed -- press home first")

    def gotoMm(self, mm):
        """Move to mm and wait until the stage is there. Returns the position
        the stage reports."""
        self._requireConnected()
        self._checkHomed()
        mm = float(mm)
        lo, hi = self.client.travel_mm()
        if hi > lo and not lo <= mm <= hi:
            raise ValueError(f"position {mm} mm out of range {lo:.1f}..{hi:.1f}")
        return self.client.move_absolute_mm(mm)

    def getPosition(self):
        """The position the stage reports, in millimeters."""
        self._requireConnected()
        return self.client.position_mm()

    def getTravel(self):
        lo, hi = self.client.travel_mm() if self._connected else (0.0, 0.0)
        return f"{lo:.1f} - {hi:.1f} mm"

    def getVelocity(self):
        if not self._connected:
            return "--"
        acc, vel = self.client.velocity_mm()
        return f"{vel:.1f} mm/s, acc {acc:.0f} mm/s^2"

    # --- GUI: scan range for automations ------------------------------------

    def setStartMm(self, value_str):
        self.startMm = self._clampMm(value_str)
        print(f"Start position: {self.startMm} mm")

    def setEndMm(self, value_str):
        self.endMm = self._clampMm(value_str)
        print(f"End position: {self.endMm} mm")

    def setNumSteps(self, value_str):
        self.numSteps = max(1, int(value_str))
        print(f"Steps: {self.numSteps}")

    def setVelocity(self, value_str):
        self._requireConnected()
        self.client.setvelocity_mm(float(value_str))
        print(f"Velocity set to {float(value_str):.1f} mm/s")

    def setAcceleration(self, value_str):
        self._requireConnected()
        vel = self.client.velocity_mm()[1]
        self.client.setvelocity_mm(vel, a_mm_s2=float(value_str))
        print(f"Acceleration set to {float(value_str):.0f} mm/s^2")

    def _clampMm(self, value_str):
        v = float(value_str)
        if not self._connected:
            return v
        lo, hi = self.client.travel_mm()
        if hi <= lo:
            return v
        return min(max(v, lo), hi)


class FakeKDC101Client(KDC101Client):
    """KDC101Client with the Kinesis DLL swapped for stored values, so
    automations run under --sim with nothing plugged in."""

    TRAVEL_MM = (0.0, 100.0)
    STEPS_PER_MM = 1919.64186  # the real unit mapping (steps/mm)

    def __init__(self, dll_dir=None):
        # Skip KDC101Client.__init__: it loads the Kinesis DLL.
        self.s = None
        self._dev = 0
        self._vel_dev = (1000, 5000)   # (accel, velocity) in device units
        self._homed = False
        self._travel = self.TRAVEL_MM
        self._backlash_mm = 0.01

    def open(self, serial=None):
        self.s = (serial or self.DEFAULT_SERIAL).encode()
        self._dev = 0
        self._homed = False

    def connected(self):
        return self.s is not None

    def devices(self):
        return "27000001"

    def needs_homing(self):
        return not self._homed

    def mm_to_dev(self, mm):
        return int(round(float(mm) * self.STEPS_PER_MM))

    def dev_to_mm(self, dev):
        return float(dev) / self.STEPS_PER_MM

    def position_dev(self):
        return self._dev

    def position_mm(self):
        return self.dev_to_mm(self._dev)

    def travel_mm(self):
        return self._travel

    def home(self, timeout_s=120.0):
        self._dev = 0
        self._homed = True

    def move_absolute_mm(self, mm, timeout_s=120.0):
        # The fake stage arrives instantly, then the real wait logic checks it.
        self._dev = self.mm_to_dev(mm)
        return self.wait_arrival(mm, timeout_s)

    def stop(self):
        pass

    def velocity_mm(self):
        a, v = self._vel_dev
        return self.dev_to_mm(a), self.dev_to_mm(v)

    def setvelocity_mm(self, v_mm_s, a_mm_s2=None):
        a = self._vel_dev[0] if a_mm_s2 is None else int(round(a_mm_s2 * self.STEPS_PER_MM))
        self._vel_dev = (a, int(round(v_mm_s * self.STEPS_PER_MM)))

    def disable(self):
        pass

    def close(self):
        self.s = None


class FakeKDC101Stage(KDC101Stage):
    """Headless KDC101 stage: real logic driving a simulated DC servo."""

    def _connect(self, dll_dir=None):
        self.client = FakeKDC101Client(dll_dir)
