from __future__ import annotations
import time
import os
import subprocess
import numpy as np

# serial and niscope are imported lazily inside the classes that need them, so
# that a machine without the Arduino or NI drivers can still drive the helper
# subprocesses (this is the same reason hardware.py imports this module lazily).

class _LineProcess:
    """
    Minimal line-oriented subprocess wrapper (stdin/stdout).
    Used for th260_helper.exe and stage_helper.exe.
    """
    def __init__(self, exe_path, capture_stderr=True):
        # capture_stderr=False keeps the helper's diagnostics off the pipe we
        # read responses from. Helpers that print to stderr (th260) need it;
        # the others fold stderr into stdout as they always have.
        self.exe_path = exe_path
        self.p = subprocess.Popen(
            [exe_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if capture_stderr else subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1
        )
        greet = self.p.stdout.readline()
        if not greet.startswith("OK"):
            raise RuntimeError(f"{os.path.basename(exe_path)} not ready: {greet}")

    def send(self, line, timeout=10.0):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()
        resp = self.p.stdout.readline()
        if not resp.startswith("OK"):
            raise RuntimeError(f"{os.path.basename(self.exe_path)}: {resp.strip()}")
        return resp

    def close(self):
        try:
            self.send("exit")
        except Exception:
            pass
        try:
            self.p.terminate()
        except Exception:
            pass

class ArduinoClient:
    def __init__(self, serPort, baud_rate):
        import serial

        self.devPort = serial.Serial(serPort, baud_rate)
        time.sleep(2)

    def serialRead(self):

        out = self.devPort.readline().decode('utf-8').strip()
    
        return out

    def commandSend(self, command):

        self.devPort.write(command.encode())
        self.devPort.write(b'\n')
        time.sleep(0.5)
        out = self.devPort.readline().decode('utf-8').strip()
    
        return out



    def serialClose(self):
    
        self.devPort.close()
    
        return 0

class CornerstoneClient:
    def __init__(self, exe_path: str):
        self.proc = _LineProcess(exe_path)

    def open(self):
        self.proc.send("open")

    def goto(self, nm: float):
        self.proc.send(f"goto {float(nm)}")

    def position(self) -> float:
        r = self.proc.send("position")  # "OK POS=###.###"
        for tok in r.split():
            if tok.startswith("POS="):
                return float(tok.split("=")[1])
        raise RuntimeError(f"bad position line: {r}")

    def open_shutter(self):
        self.proc.send("open_shutter")

    def close_shutter(self):
        self.proc.send("close_shutter")

    def close(self):
        self.proc.close()

class StageClient:
    """Wrapper for stage_helper.exe (dynamic-loaded Kinesis, serials hardcoded in the EXE)"""
    def __init__(self):
        self.proc = _LineProcess("helpers/stage_helper_ultra.exe")

    def open(self, serial_x=None, serial_y=None, vmax_tenths=750):
        # If no serials given, the helper uses its hardcoded defaults
        if serial_x and serial_y:
            self.proc.send(f"open {serial_x} {serial_y} {vmax_tenths}")
        else:
            self.proc.send(f"open {vmax_tenths}")

    def move_ix(self, ix, iy, width, height):
        self.proc.send(f"move_ix {ix} {iy} {width} {height}")

    def reset(self, ix, width):
        self.proc.send(f"stage_reset {ix} {width}")

    def setdac(self, vx_code, vy_code):
        self.proc.send(f"setdac {vx_code} {vy_code}")

    def status(self):
        r = self.proc.send("status")
        # r: "OK X=<0|1> Y=<0|1>"
        return dict(kv.split("=") for kv in r[3:].split())

    def disable(self):
        try:
            self.proc.send("disable")
        except Exception:
            pass

    def close(self):
        try:
            self.disable()
        finally:
            self.proc.close()

class TH260Client:
    """
    Wrapper for th260_helper_ultra.exe. The helper returns the histogram on its
    response line and writes no files -- saving is Python's job (see
    th260_helpers.saveTCSPCHDF5).

    Protocol:
      - init                     -> OK RES=<ps> CH=<n> LEN=<histlen>
      - info                     -> OK RES=<ps> CH=<n> LEN=<histlen>
      - measure <tacq_ms> <bins> -> OK RES=... CH=... LEN=... SYNC=... CR=...
                                       OVF=... DATA=<ch0>;<ch1>
      - exit
    """

    def __init__(self, exe_path="helpers/th260_helper_ultra.exe"):
        # The helper puts diagnostics on stderr; folding them into stdout would
        # desync the line protocol.
        self.proc = _LineProcess(exe_path, capture_stderr=False)

    @staticmethod
    def _fields(resp):
        """'OK A=1 B=2 DATA=...' -> {'A': '1', 'B': '2', 'DATA': '...'}"""
        out = {}
        for tok in resp.split():
            if "=" in tok:
                key, _, value = tok.partition("=")
                out[key] = value
        return out

    def _info_from(self, resp):
        # LEN is the board's full histogram length, which is not the same as
        # the number of bins a given measure() asks to have returned.
        f = self._fields(resp)
        return {
            "resolution_ps": float(f.get("RES", 0.0)),
            "channels": int(f.get("CH", 0)),
            "hist_len": int(f.get("LEN", 0)),
        }

    def init(self):
        """Open and configure the board. Returns resolution/channels/bins."""
        return self._info_from(self.proc.send("init", timeout=20.0))

    def info(self):
        return self._info_from(self.proc.send("info"))

    def measure(self, tacq_ms, bins=2000):
        """One acquisition. Returns the histogram plus the rates that go with it."""
        timeout = max(10.0, tacq_ms / 1000.0 + 10.0)
        resp = self.proc.send(f"measure {int(tacq_ms)} {int(bins)}", timeout=timeout)
        f = self._fields(resp)

        data = f.get("DATA", "")
        counts = np.array(
            [[int(v) for v in ch.split(",") if v] for ch in data.split(";") if ch],
            dtype=np.uint32,
        )

        result = self._info_from(resp)
        result.update({
            "bins": int(counts.shape[1]) if counts.size else 0,
            "sync_rate": int(f.get("SYNC", 0)),
            "count_rate": [int(v) for v in f.get("CR", "").split(",") if v],
            "overflow": f.get("OVF", "0") == "1",
            "counts": counts,
        })
        return result

    def close(self):
        self.proc.close()


class TH260DLLClient:
    """
    Direct ctypes driver for the TimeHarp 260 via th260lib64.dll -- a drop-in
    for TH260Client (same init/info/measure/close) with no helper exe. Based on
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

    def __init__(self, settings, dll_path="helpers/th260lib64.dll", bin_width_ps=200):
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

    def _info(self):
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
        return self._info()

    def info(self):
        return self._info()

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
        """One acquisition. Same return dict as TH260Client.measure."""
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

        result = self._info()
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


class NIScopeClient:
    def record(self):
        import niscope

        with niscope.Session("Dev1") as session:
            session.channels[1].configure_vertical(range=40.0, coupling=niscope.VerticalCoupling.DC)

            session.configure_horizontal_timing(
                min_sample_rate=5000000,
                min_num_pts=5000000,
                ref_position=50.0,  # Might comment later. This is a percentage.
                num_records=1,      # This gets used later in session initiate. Might make this global.
                enforce_realtime=True
                )
        
            with session.initiate():
                waveforms = session.channels[1].fetch()  # Really only concerned with channel 1. This was [0,1]
            #for wfm in waveforms:
            #    print('Channel {}, record {} samples acquired: {:,}\n'.format(wfm.channel, wfm.record, len(wfm.samples)))

            wfm = waveforms[0]

            data_store = []
            for i in range(len(wfm.samples)):
                data_store.append(wfm.samples[i])

            data_point = np.average(data_store)

            return data_point

