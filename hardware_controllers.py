from __future__ import annotations
import serial
import time
import os
import subprocess
import niscope
import numpy as np

class _LineProcess:
    """
    Minimal line-oriented subprocess wrapper (stdin/stdout).
    Used for th260_helper.exe and stage_helper.exe.
    """
    def __init__(self, exe_path):
        self.exe_path = exe_path
        self.p = subprocess.Popen(
            [exe_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", bufsize=1
        )
        greet = self.p.stdout.readline()
        print(greet, "\n")
        if not greet.startswith("OK"):
            raise RuntimeError(f"{os.path.basename(exe_path)} not ready: {greet}")

    def send(self, line, timeout=10.0):
        self.p.stdin.write(line + "\n")
        print(line, "\n")
        self.p.stdin.flush()
        resp = self.p.stdout.readline()
        print("resp", resp)
        if not resp.startswith("OK"):
            raise RuntimeError(resp)
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
    Thin wrapper around th260_helper.exe using the shared LineProcess.
    Protocol (as implemented by your helper):
      - init <outDir> <ix> <iy>
      - measure <outDir> <ix> <iy> <wavelength_nm> <tacq_ms>
      - info            (optional; returns OK RES=... CH=... LEN=...)
      - exit
    """

    def __init__(self):
        self.proc = _LineProcess("helpers/th260_helper_ultra.exe")

    # -- Setup / connection ----------------------------------------------------

    def init(self, output_dir: str, ix: int, iy: int) -> None:
        """Initialize helper with an output directory and starting pixel coords."""
        self.proc.send(f"init {output_dir} {int(ix)} {int(iy)}", timeout=20.0)

    def connect(self, output_dir: str = "dump", ix: int = 1, iy: int = 1) -> None:
        """
        Convenience: some code paths used a 'connect' that just called `init dump 1 1`.
        Keep that behavior for compatibility.
        """
        self.init(output_dir, ix, iy)

    # -- Acquisition -----------------------------------------------------------

    def acquire(self, tacq_ms: int, output_dir: str, wl: float, ix: int, iy: int) -> None:
        """
        Trigger a measurement. The helper writes data to disk in output_dir.
        We just ensure the call succeeds (OK) and wait long enough.
        """
        cmd = f"measure {output_dir} {int(ix)} {int(iy)} {float(wl)} {int(tacq_ms)}"
        # Acquisition time affects how long the helper runs; add a cushion.
        timeout = max(10.0, tacq_ms / 1000.0 + 10.0)
        self.proc.send(cmd, timeout=timeout)

    # -- Optional helpers ------------------------------------------------------

    def info(self) -> dict:
        """
        Ask the helper for instrument info if it supports `info`.
        Expected line: 'OK RES=<ps> CH=<n> LEN=<bins>'
        """
        resp = self.proc.send("info")
        parts = resp.split()[1:]  # drop 'OK'
        try:
            kv = dict(p.split("=", 1) for p in parts)
            return {
                "resolution_ps": float(kv.get("RES", "0")),
                "channels": int(kv.get("CH", "0")),
                "bins": int(kv.get("LEN", "0")),
            }
        except Exception:
            # If helper doesn't support info or format differs, return raw text
            return {"raw": resp}

    # -- Shutdown --------------------------------------------------------------

    def close(self) -> None:
        """Gracefully stop the helper process."""
        self.proc.close()

class NIScopeClient:
    def record(self):
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

