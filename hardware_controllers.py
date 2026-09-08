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

