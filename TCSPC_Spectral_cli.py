"""TCSPC spectral scan -- headless command-line version.

Run: python TCSPC_Spectral_cli.py

Same scan as TCSPC_Spectral.py, but with no GUI: edit the CONFIG block below,
run the file, and it sweeps the monochromator and writes the HDF5 file. This
imports no Qt, so it works on machines where PySide6 will not load.

Ctrl+C stops the sweep cleanly -- the shutter is closed and whatever was
collected up to that point is still saved.
"""
import signal
import sys
import time

from hardware import Cornerstone, TH260, FakeCornerstone, FakeTH260
from TCSPC_Spectral import TCSPCSpectral

# ─────────────────────────────────────────────────────────────────────────
# CONFIG -- edit these, then run the file.
# ─────────────────────────────────────────────────────────────────────────
SIM = 0                 # 0 = real hardware, 1 = fakes, 2 = fake mono + stub helper

SAMPLE_NAME = "sample"  # names the output folder and file
REGION = "A"

START_WAVELENGTH = 600.0   # nm
END_WAVELENGTH = 800.0     # nm
NUM_STEPS = 50             # wavelength points
SETTLE_S = 1.0             # pause after each monochromator move, seconds

TACQ_MS = 5000          # TCSPC acquisition time per wavelength, ms
BINS = 2000             # histogram bins kept per acquisition
CHANNEL = 0             # channel written to `counts` (all are kept in counts_all)

TH260_EXE = "helpers/th260_helper_ultra.exe"
CORNERSTONE_EXE = "helpers/cornerstone_helper.exe"
# ─────────────────────────────────────────────────────────────────────────


def _progress(current, total, secondsPerStep):
    """Text stand-in for auto_gui's progress bar.

    Deliberately plain lines rather than a \r-redrawn bar: the scan loop prints
    its own line per wavelength, and carriage returns turn a redirected log file
    into one unreadable line -- which matters for a long unattended run.
    """
    done = current + 1
    remaining = (total - done) * secondsPerStep
    filled = int(20 * done / total)
    bar = "|" * filled + "-" * (20 - filled)
    print(f"[{bar}] {done}/{total}  ~{remaining / 60:.1f} min left")


def buildHardware():
    """Return (cornerstone, th260) for the configured SIM mode."""
    if SIM == 1:
        return FakeCornerstone(), FakeTH260()
    if SIM == 2:
        # Real TH260 client and helper code against the stub board (build.sh stub).
        return FakeCornerstone(), TH260(TH260_EXE)
    return Cornerstone(CORNERSTONE_EXE), TH260(TH260_EXE)


def main():
    print("=" * 60)
    print(f"TCSPC spectral scan{'  [SIMULATED]' if SIM else ''}")
    print(f"  sample      : {SAMPLE_NAME}  (region {REGION})")
    print(f"  wavelengths : {START_WAVELENGTH}-{END_WAVELENGTH} nm, {NUM_STEPS} steps")
    print(f"  acquisition : {TACQ_MS} ms x {NUM_STEPS} = "
          f"~{NUM_STEPS * (TACQ_MS / 1000 + SETTLE_S) / 60:.1f} min minimum")
    print("=" * 60)

    cornerstone, th260 = buildHardware()

    cornerstone.setStartWavelength(START_WAVELENGTH)
    cornerstone.setEndWavelength(END_WAVELENGTH)
    cornerstone.setNumSteps(NUM_STEPS)
    th260.setTacq(TACQ_MS)
    th260.setBins(BINS)
    th260.setChannel(CHANNEL)

    scan = TCSPCSpectral(cornerstone, th260)
    scan.setSampleName(SAMPLE_NAME)
    scan.setRegion(REGION)
    scan.settleTime = SETTLE_S
    scan.progress = _progress          # the same hook auto_gui injects

    # Ctrl+C sets the cooperative stop flag the scan loop already checks, so the
    # shutter still closes and the partial scan is still written.
    def onInterrupt(signum, frame):
        if getattr(scan, "_stop", False):        # second Ctrl+C: give up now
            print("\nInterrupted again -- exiting immediately.")
            sys.exit(1)
        print("\nStopping after this wavelength (Ctrl+C again to force quit)...")
        scan._stop = True
    signal.signal(signal.SIGINT, onInterrupt)

    t0 = time.time()
    try:
        data = scan._spectralScan()
    finally:
        for dev, closer in ((th260, lambda: th260.th.close()),
                            (cornerstone, lambda: cornerstone.mono.close())):
            try:
                closer()
            except Exception as e:
                print(f"warning: closing {type(dev).__name__} helper failed: {e}")

    print(f"Finished {len(data)} of {NUM_STEPS} wavelengths "
          f"in {(time.time() - t0) / 60:.1f} min")
    return 0 if data else 1


if __name__ == "__main__":
    sys.exit(main())
