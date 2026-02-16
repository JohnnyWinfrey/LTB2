import sys, time
import clr  # from pythonnet
clr.AddReference("Cornerstone")  # Cornerstone.dll must be next to the EXE
import CornerstoneDll

class Mono:
    def __init__(self):
        self.m = None
        self.connected = False
    def open(self):
        if self.m:
            try: self.m.disconnect()
            except: pass
        self.m = CornerstoneDll.Cornerstone(True)
        if not self.m.connect():
            raise RuntimeError("connect failed")
        self.connected = True
    def ensure(self):
        if not self.connected:
            raise RuntimeError("not open")
    def goto(self, nm):
        self.ensure()
        self.m.getStringResponseFromCommand(f"GOWAVE {float(nm):.3f}")
    def position(self):
        self.ensure()
        return float(self.m.getWavelength())
    def shutter(self, open_):
        self.ensure()
        self.m.setShutter(True if open_ else False)
    def close(self):
        if self.m:
            try: self.m.disconnect()
            except: pass
        self.connected = False

def main():
    mono = Mono()
    print("OK ready", flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()
        try:
            if cmd in ("exit","quit"):
                print("OK bye", flush=True)
                break
            elif cmd == "open":
                mono.open(); print("OK", flush=True)
            elif cmd == "goto":
                mono.goto(parts[1]); print("OK", flush=True)
            elif cmd == "position":
                pos = mono.position(); print(f"OK POS={pos:.3f}", flush=True)
            elif cmd == "open_shutter":
                mono.shutter(True); print("OK", flush=True)
            elif cmd == "close_shutter":
                mono.shutter(False); print("OK", flush=True)
            else:
                print("ERR unknown_cmd", flush=True)
        except Exception as e:
            print("ERR " + str(e), flush=True)
    mono.close()

if __name__ == "__main__":
    main()

