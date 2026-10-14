"""TH260 -- TimeHarp 260 TCSPC board, driven through helpers/th260lib64.dll."""
import os
import time

import numpy as np

from ._shared import HELPERS_DIR


class TH260DLLClient:
    """
    Direct ctypes driver for the TimeHarp 260 via th260lib64.dll. Based on
    PicoQuant's TH260-Demos histomode.py.

    The board settings are not defaulted here: the caller passes every key in
    SETTING_KEYS (TCSPC_Live.py hard-codes them for its configuration). The bin
    width is the one setting meant to change at runtime -- setBinWidth().

    Also adds rates(), which reads the sync/count rates without running a
    measurement (the board refreshes them every 100 ms).
    """

    MAXDEVNUM = 4
    MODE_HIST = 0
    MAXLENCODE = 5
    MAXINPCHAN = 2
    MAXHISTLEN = 32768
    FLAG_OVERFLOW = 0x0001

    SETTING_KEYS = (
        "offset_ns",             # acquisition offset
        "sync_divider",
        "sync_cfd_zero_cross",   # mV (260 P)
        "sync_cfd_level",        # mV (260 P)
        "sync_offset_ps",
        "input_cfd_zero_cross",  # mV (260 P), all channels
        "input_cfd_level",       # mV (260 P), one value or a per-channel list
        "input_offset_ps",       # all channels
        "sync_trigger_edge",     # 260 N only
        "sync_trigger_level",    # mV, 260 N only
        "input_trigger_edge",    # 260 N only
        "input_trigger_level",   # mV, 260 N only
        "stop_overflow",         # 0/1, stop when a bin reaches stop_count
        "stop_count",
    )

    def __init__(self, settings, dll_path=HELPERS_DIR / "th260lib64.dll", bin_width_ps=200):
        import ctypes as ct
        self._ct = ct
        missing = set(self.SETTING_KEYS) - set(settings)
        unknown = set(settings) - set(self.SETTING_KEYS)
        if missing or unknown:
            raise ValueError(f"TH260 settings: missing {sorted(missing)}, "
                             f"unknown {sorted(unknown)}")
        self.settings = dict(settings)
        self.binWidthPs = bin_width_ps
        self.lib = ct.WinDLL(os.path.abspath(dll_path))
        self.dev = -1
        self.numChannels = 0
        self.histLen = 0
        self.resolution = 0.0
        self.model = ""
        self._counts = [(ct.c_uint * self.MAXHISTLEN)() for _ in range(self.MAXINPCHAN)]

    def _try(self, retcode, name):
        if retcode < 0:
            err = self._ct.create_string_buffer(40)
            self.lib.TH260_GetErrorString(err, self._ct.c_int(retcode))
            raise RuntimeError(f"TH260_{name} failed ({retcode}: "
                               f"{err.value.decode(errors='replace')})")

    def info(self):
        return {"resolution_ps": self.resolution,
                "channels": self.numChannels,
                "hist_len": self.histLen}

    def init(self):
        """Open the first board and apply self.settings. Returns resolution/channels/bins."""
        ct, lib, st = self._ct, self.lib, self.settings
        if self.dev >= 0:
            self.close()

        serial = ct.create_string_buffer(8)
        for i in range(self.MAXDEVNUM):
            if lib.TH260_OpenDevice(ct.c_int(i), serial) == 0:
                self.dev = i
                break
        else:
            raise RuntimeError("no TH260 device available")
        d = ct.c_int(self.dev)

        self._try(lib.TH260_Initialize(d, ct.c_int(self.MODE_HIST)), "Initialize")
        model = ct.create_string_buffer(16)
        partno = ct.create_string_buffer(8)
        version = ct.create_string_buffer(16)
        self._try(lib.TH260_GetHardwareInfo(d, model, partno, version), "GetHardwareInfo")
        self.model = model.value.decode()
        n = ct.c_int()
        self._try(lib.TH260_GetNumOfInputChannels(d, ct.byref(n)), "GetNumOfInputChannels")
        self.numChannels = min(n.value, self.MAXINPCHAN)

        self._try(lib.TH260_SetSyncDiv(d, ct.c_int(st["sync_divider"])), "SetSyncDiv")
        if self.model == "TimeHarp 260 P":
            self._try(lib.TH260_SetSyncCFD(d, ct.c_int(st["sync_cfd_level"]),
                                           ct.c_int(st["sync_cfd_zero_cross"])), "SetSyncCFD")
            for i in range(self.numChannels):
                level = st["input_cfd_level"]
                if isinstance(level, (list, tuple)):
                    level = level[i]
                self._try(lib.TH260_SetInputCFD(d, ct.c_int(i), ct.c_int(level),
                                                ct.c_int(st["input_cfd_zero_cross"])),
                          "SetInputCFD")
        elif self.model == "TimeHarp 260 N":
            self._try(lib.TH260_SetSyncEdgeTrg(d, ct.c_int(st["sync_trigger_level"]),
                                               ct.c_int(st["sync_trigger_edge"])),
                      "SetSyncEdgeTrg")
            for i in range(self.numChannels):
                self._try(lib.TH260_SetInputEdgeTrg(d, ct.c_int(i),
                                                    ct.c_int(st["input_trigger_level"]),
                                                    ct.c_int(st["input_trigger_edge"])),
                          "SetInputEdgeTrg")
        else:
            raise RuntimeError(f"unknown TH260 model {self.model!r}")

        self._try(lib.TH260_SetSyncChannelOffset(d, ct.c_int(st["sync_offset_ps"])),
                  "SetSyncChannelOffset")
        for i in range(self.numChannels):
            self._try(lib.TH260_SetInputChannelOffset(d, ct.c_int(i),
                                                      ct.c_int(st["input_offset_ps"])),
                      "SetInputChannelOffset")

        hl = ct.c_int()
        self._try(lib.TH260_SetHistoLen(d, ct.c_int(self.MAXLENCODE), ct.byref(hl)),
                  "SetHistoLen")
        self.histLen = hl.value
        self._try(lib.TH260_SetOffset(d, ct.c_int(st["offset_ns"])), "SetOffset")
        self.setBinWidth(self.binWidthPs)
        self._try(lib.TH260_SetStopOverflow(d, ct.c_int(st["stop_overflow"]),
                                            ct.c_uint(st["stop_count"])), "SetStopOverflow")

        time.sleep(0.15)  # rates are only valid 150 ms after Initialize/SetSyncDiv
        print(f"TH260 {self.model} (S/N {serial.value.decode()}) configured: "
              f"{self.resolution:.0f} ps, {self.numChannels} ch")
        return self.info()

    def setBinWidth(self, width_ps):
        """Set the bin width to the nearest available base * 2**n. Returns the
        actual width in ps. Not while a measurement is running."""
        ct, lib = self._ct, self.lib
        d = ct.c_int(self.dev)
        base, steps = ct.c_double(), ct.c_int()
        self._try(lib.TH260_GetBaseResolution(d, ct.byref(base), ct.byref(steps)),
                  "GetBaseResolution")
        code = int(round(np.log2(max(float(width_ps), base.value) / base.value)))
        code = min(max(code, 0), steps.value - 1)
        self._try(lib.TH260_SetBinning(d, ct.c_int(code)), "SetBinning")
        res = ct.c_double()
        self._try(lib.TH260_GetResolution(d, ct.byref(res)), "GetResolution")
        self.resolution = res.value
        self.binWidthPs = res.value
        return res.value

    def rates(self):
        """(sync_rate, [count_rate per channel]) -- no measurement needed."""
        ct = self._ct
        d = ct.c_int(self.dev)
        sync = ct.c_int()
        self._try(self.lib.TH260_GetSyncRate(d, ct.byref(sync)), "GetSyncRate")
        rates = []
        for i in range(self.numChannels):
            cr = ct.c_int()
            self._try(self.lib.TH260_GetCountRate(d, ct.c_int(i), ct.byref(cr)),
                      "GetCountRate")
            rates.append(cr.value)
        return sync.value, rates

    def measure(self, tacq_ms, bins=2000):
        """One acquisition. Returns the histogram plus the rates that go with it."""
        ct, lib = self._ct, self.lib
        d = ct.c_int(self.dev)
        if bins <= 0 or bins > self.histLen:
            bins = self.histLen  # clamp to what the board holds

        self._try(lib.TH260_ClearHistMem(d), "ClearHistMem")
        sync, rates = self.rates()
        warnings = ct.c_int()
        self._try(lib.TH260_GetWarnings(d, ct.byref(warnings)), "GetWarnings")
        if warnings.value:
            text = ct.create_string_buffer(16384)  # library requires 16384 bytes
            lib.TH260_GetWarningsText(d, text, warnings)
            print(text.value.decode(errors="replace"))

        self._try(lib.TH260_StartMeas(d, ct.c_int(int(tacq_ms))), "StartMeas")
        status = ct.c_int(0)
        while status.value == 0:
            self._try(lib.TH260_CTCStatus(d, ct.byref(status)), "CTCStatus")
            time.sleep(0.001)  # don't spin a core while the board counts
        self._try(lib.TH260_StopMeas(d), "StopMeas")

        counts = np.empty((self.numChannels, bins), dtype=np.uint32)
        for i in range(self.numChannels):
            self._try(lib.TH260_GetHistogram(d, ct.byref(self._counts[i]), ct.c_int(i),
                                             ct.c_int(0)), "GetHistogram")
            counts[i] = np.ctypeslib.as_array(self._counts[i])[:bins]

        flags = ct.c_int()
        self._try(lib.TH260_GetFlags(d, ct.byref(flags)), "GetFlags")

        result = self.info()
        result.update({
            "bins": bins,
            "sync_rate": sync,
            "count_rate": rates,
            "overflow": bool(flags.value & self.FLAG_OVERFLOW),
            "counts": counts,
        })
        return result

    def close(self):
        for i in range(self.MAXDEVNUM):  # no harm in closing all
            self.lib.TH260_CloseDevice(self._ct.c_int(i))
        self.dev = -1


class TH260:
    """TimeHarp 260 TCSPC board, driven through th260lib64.dll (TH260DLLClient).

    `settings` must hold every TH260DLLClient.SETTING_KEYS key; the automation
    file owns them (see TCSPC_Live.py). This class holds the acquisition
    settings and hands raw arrays to the automation.
    """

    def __init__(self, settings, dll_path=HELPERS_DIR / "th260lib64.dll", bin_width_ps=200):
        self._connect(settings, dll_path, bin_width_ps)
        info = self.th.init()
        self.resolutionPs = info["resolution_ps"]
        self.numChannels = info["channels"]
        self.histLen = info["hist_len"]
        self.tacq = 5000        # acquisition time, ms
        self.bins = None        # bins kept per acquisition; None => auto (sync period)
        self.channel = 0        # channel plotted / saved
        self.lastCounts = None
        self.lastCountRate = 0
        self.lastSyncRate = 0

    def _connect(self, settings, dll_path, bin_width_ps):
        self.th = TH260DLLClient(settings, dll_path, bin_width_ps)

    def setTacq(self, value_str):
        self.tacq = int(float(value_str))
        print(f"Acquisition time set to {self.tacq} ms")

    def setBins(self, value_str):
        """A number fixes the bin count; 'auto', 0 or blank goes back to sizing
        the histogram to one sync period at the start of each acquisition."""
        text = str(value_str).strip().lower()
        n = 0 if text in ("", "auto") else int(float(text))
        self.bins = n if n > 0 else None
        print(f"Bins set to {self.bins if self.bins else 'auto (one sync period)'}")

    def setChannel(self, value_str):
        self.channel = int(float(value_str))
        print(f"Channel set to {self.channel}")

    def _timeAxisNs(self, bins=None):
        """Bin centres in ns -- the x axis for a decay curve."""
        n = self.bins if bins is None else bins
        return np.arange(n) * (self.resolutionPs / 1000.0)

    def _acquire(self):
        """One acquisition. Underscored so auto_gui ignores it; automations call
        this for the array, while measure() is the GUI-facing readout."""
        result = self.th.measure(self.tacq, self.bins or 0)  # 0 => whole histogram
        self.lastCounts = result["counts"]
        self.lastSyncRate = result["sync_rate"]
        rates = result["count_rate"]
        self.lastCountRate = rates[self.channel] if self.channel < len(rates) else 0
        if result["overflow"]:
            print("WARNING: TH260 histogram overflowed")
        return result

    def measure(self):
        result = self._acquire()
        total = int(result["counts"][self.channel].sum())
        print(f"TH260 measured {total} counts on channel {self.channel}")
        return f"{total} counts"

    def getResolution(self):
        return f"{self.resolutionPs:.0f} ps"

    def getCountRate(self):
        return f"{self.lastCountRate} /s"


class _FakeTH260Client:
    """No-op stand-in for TH260DLLClient: synthetic single-exponential decay."""

    RESOLUTION_PS = 200.0
    CHANNELS = 2
    HISTLEN = 32768

    def __init__(self, *args, **kwargs):
        pass

    def init(self):
        return {"resolution_ps": self.RESOLUTION_PS,
                "channels": self.CHANNELS,
                "hist_len": self.HISTLEN}

    def info(self):
        return self.init()

    def measure(self, tacq_ms, bins=2000):
        if bins <= 0 or bins > self.HISTLEN:
            bins = self.HISTLEN  # clamp like the real client
        t0 = 40
        j = np.arange(bins)
        dt = np.clip(j - t0, 0, None)
        rows = []
        for ch in range(self.CHANNELS):
            tau = (12.0 if ch == 0 else 20.0) / (self.RESOLUTION_PS / 1000.0)
            mean = 2.0 + (1e4 * max(tacq_ms / 5000.0, 1.0)
                          * (1 - np.exp(-dt / 3.0)) * np.exp(-dt / tau)) * (j >= t0)
            rows.append(np.random.poisson(mean))
        return {"resolution_ps": self.RESOLUTION_PS,
                "channels": self.CHANNELS,
                "hist_len": self.HISTLEN,
                "bins": bins,
                "sync_rate": 40000000,
                "count_rate": [25000, 26000],
                "overflow": False,
                "counts": np.array(rows, dtype=np.uint32)}

    def rates(self):
        return 40000000, [int(np.random.normal(25000, 500)),
                          int(np.random.normal(26000, 500))]

    def setBinWidth(self, width_ps):
        # 260 P-like: 25 ps base, 2**n steps. Instance attr shadows the class one.
        code = int(round(np.log2(max(float(width_ps), 25.0) / 25.0)))
        self.RESOLUTION_PS = 25.0 * 2 ** min(max(code, 0), 21)
        return self.RESOLUTION_PS

    def close(self):
        pass


class FakeTH260(TH260):
    """Headless TCSPC board: real logic driving a synthetic-decay client."""

    def __init__(self, settings=None, dll_path="FAKE", bin_width_ps=200):
        super().__init__(settings, dll_path, bin_width_ps)
        print("FakeTH260 online")

    def _connect(self, settings, dll_path, bin_width_ps):
        self.th = _FakeTH260Client()
        self.th.setBinWidth(bin_width_ps)
