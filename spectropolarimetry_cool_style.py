"""SMC100 daisy-chain bring-up test -- standalone auto_gui launcher.

Run: python spectropolarimetry_cool_style.py
Checks every Newport SMC100 axis on the chain (rotation or linear), one step
at a time:

  1. comms      -- each address answers TS / TP (wrong address or cabling fails here)
  2. home       -- each axis references (OR) and lands at 0
  3. absolute   -- moves to the TARGETS for its units, position within TOL
  4. relative   -- +STEP then -STEP, back where it started
  5. crosstalk  -- moving one axis leaves every other axis where it was
                   (catches two controllers sharing an address)
  6. limits     -- a target past the software limit is refused, axis doesn't move
  7. wrap       -- rotation stages: shortest / positive / negative wrap modes
                   go the expected way round
  8. together   -- all axes started at once, then waited on
  9. park       -- every axis back to 0

Targets outside an axis's software limits are skipped (SKIP), not failed.
Results go to data/<timestamp>/smc100_test.csv and a PASS/FAIL summary is
printed. Axes (port, addresses, units) are set in __main__. Set sim = 0 for
real hardware -- and make sure nothing is in the stages' way before Start.
"""
import os
import csv
import time
from datetime import datetime

# Per-unit settings. Set TOL from the stages' spec sheets once the models are known.
TOL = {"mm": 0.002, "deg": 0.01}        # allowed |target - position|
STEP = {"mm": 0.5, "deg": 5.0}          # relative-move test step
TARGETS = {"mm": [-5.0, 5.0, 0.0],
           "deg": [45.0, 90.0, 180.0, 270.0, -90.0, 0.0]}
TOGETHER = {"mm": -3.0, "deg": 30.0}    # where every axis goes in the "together" test


class SMC100ChainTest():

    def __init__(self, axes):
        self.axes = axes
        self.results = []
        print(f"SMC100ChainTest Ready ({len(axes)} axes)")

    def _record(self, test, axis, result, detail=""):
        """result: True/False for PASS/FAIL, or "SKIP"."""
        if result != "SKIP":
            result = "PASS" if result else "FAIL"
        self.results.append({'time': datetime.now().strftime("%H:%M:%S"), 'test': test,
                             'axis': axis.name, 'result': result, 'detail': detail})
        print(f"  [{result}] {test:<10} {axis.name}  {detail}")
        return result == "PASS"

    def _check(self, test, axis, action):
        """Run `action`; any exception is recorded as a FAIL instead of ending the run."""
        try:
            return action()
        except Exception as exc:
            self._record(test, axis, False, f"{type(exc).__name__}: {exc}")
            return None

    def _checkAt(self, test, axis, target):
        pos = axis._position()
        err = pos - target
        u = axis.units
        return self._record(test, axis, abs(err) <= TOL[u],
                            f"target {target:.4f}  at {pos:.4f}  err {err:+.4f} {u}")

    def _reachable(self, axis, target):
        return axis.minPos <= target <= axis.maxPos

    # ── tests ───────────────────────────────────────────────────────────

    def _testComms(self, axis):
        def run():
            status, pos = axis.getStatus(), axis.getPosition()
            self._record("comms", axis, True, f"{status}, {pos}")
        self._check("comms", axis, run)

    def _testHome(self, axis):
        def run():
            axis.home()
            self._checkAt("home", axis, 0.0)
        self._check("home", axis, run)

    def _testAbsolute(self, axis):
        for target in TARGETS[axis.units]:
            if getattr(self, "_stop", False):
                return
            if not self._reachable(axis, target):
                self._record("absolute", axis, "SKIP", f"{target} outside "
                             f"[{axis.minPos}, {axis.maxPos}] {axis.units}")
                continue

            def run():
                axis.moveAbsolute(target)
                self._checkAt("absolute", axis, target)
            self._check("absolute", axis, run)

    def _testRelative(self, axis):
        step = STEP[axis.units]

        def run():
            start = axis._position()
            d = step if self._reachable(axis, start + step) else -step
            axis.moveRelative(d)
            self._checkAt("relative", axis, start + d)
            axis.moveRelative(-d)
            self._checkAt("relative", axis, start)
        self._check("relative", axis, run)

    def _testCrosstalk(self, axis):
        others = [a for a in self.axes if a is not axis]
        if not others:
            return
        step = STEP[axis.units]

        def run():
            before = {id(a): a._position() for a in others}
            start = axis._position()
            axis.moveRelative(step if self._reachable(axis, start + step) else -step)
            moved = [f"{a.name} {a._position() - before[id(a)]:+.4f}"
                     for a in others if abs(a._position() - before[id(a)]) > TOL[a.units]]
            self._record("crosstalk", axis, not moved,
                         "others moved: " + ", ".join(moved) if moved else "no other axis moved")
        self._check("crosstalk", axis, run)

    def _testLimits(self, axis):
        def run():
            before = axis._position()
            try:
                axis.moveAbsolute(axis.maxPos + 1.0)
                refused = False
            except ValueError:
                refused = True
            drift = abs(axis._position() - before)
            self._record("limits", axis, refused and drift <= TOL[axis.units],
                         f"{'refused' if refused else 'NOT refused'}, "
                         f"moved {drift:.4f} {axis.units}")
        self._check("limits", axis, run)

    def _testWrap(self, axis):
        """From 0: shortest to 350 -> -10, positive to 10 -> +10 (turning +20),
        negative to 350 -> -10 (turning -20). Needs travel to cover -10..10."""
        if axis.units != "deg":
            return
        if not (self._reachable(axis, -10.0) and self._reachable(axis, 10.0)):
            self._record("wrap", axis, "SKIP", "travel doesn't cover -10..10 deg")
            return

        def run():
            axis.moveAbsolute(0.0)
            for mode, target, expect in (("shortest", 350.0, -10.0),
                                         ("positive", 10.0, 10.0),
                                         ("negative", 350.0, -10.0)):
                axis.setWrap(mode)
                axis.moveAbsolute(target)
                self._checkAt("wrap", axis, expect)
        try:
            self._check("wrap", axis, run)
        finally:
            axis.setWrap("off")

    def _testTogether(self):
        movers = []
        for a in self.axes:
            target = TOGETHER[a.units]
            if not self._reachable(a, target):
                self._record("together", a, "SKIP", f"{target} {a.units} out of range")
            elif self._check("together", a, lambda a=a, t=target: a._startAbsolute(t) or True):
                movers.append((a, target))
        t0 = time.monotonic()
        for a, _ in movers:
            self._check("together", a, a._waitReady)
        print(f"  all axes finished {time.monotonic() - t0:.2f} s after the last start")
        for a, target in movers:
            self._check("together", a, lambda a=a, t=target: self._checkAt("together", a, t))

    def _testPark(self, axis):
        def run():
            axis.moveAbsolute(0.0)
            self._checkAt("park", axis, 0.0)
        self._check("park", axis, run)

    # ── run ─────────────────────────────────────────────────────────────

    def _runTests(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = os.path.join("data", timestamp)
        os.makedirs(output_dir, exist_ok=True)
        csv_filename = os.path.join(output_dir, 'smc100_test.csv')
        print(f"Saving results to: {output_dir}")
        self.results = []

        # Targets in these tests are literal positions; put each axis's wrap
        # mode back afterwards.
        saved_wrap = [a.wrap for a in self.axes]
        for a in self.axes:
            a.wrap = None

        per_axis = [self._testComms, self._testHome, self._testAbsolute,
                    self._testRelative, self._testCrosstalk, self._testLimits,
                    self._testWrap]
        total = len(per_axis) * len(self.axes) + 1 + len(self.axes)
        step = 0

        try:
            for test in per_axis:
                print("\n" + "=" * 50 + f"\n{test.__name__[5:].upper()}\n" + "=" * 50)
                for axis in self.axes:
                    if getattr(self, "_stop", False):
                        break
                    test(axis)
                    self.progress(step, total)
                    step += 1

            if not getattr(self, "_stop", False):
                print("\n" + "=" * 50 + "\nTOGETHER\n" + "=" * 50)
                self._testTogether()
                self.progress(step, total)
                step += 1

            print("\n" + "=" * 50 + "\nPARK\n" + "=" * 50)
            for axis in self.axes:   # park even after Stop, so stages end somewhere known
                self._testPark(axis)
                self.progress(step, total)
                step += 1
        finally:
            for a, wrap in zip(self.axes, saved_wrap):
                a.wrap = wrap

        with open(csv_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['time', 'test', 'axis', 'result', 'detail'])
            writer.writeheader()
            writer.writerows(self.results)

        failed = [r for r in self.results if r['result'] == "FAIL"]
        skipped = [r for r in self.results if r['result'] == "SKIP"]
        checked = len(self.results) - len(skipped)
        print("\n" + "=" * 50)
        print(f"{checked - len(failed)}/{checked} checks passed"
              + (f", {len(skipped)} skipped" if skipped else "")
              + (" -- stopped early" if getattr(self, "_stop", False) else ""))
        for r in failed:
            print(f"  FAIL {r['test']:<10} {r['axis']}  {r['detail']}")
        print(f"Results saved to: {csv_filename}")
        return self.results

    def progress(self, current, total, *args):
        """Replaced by auto_gui's progress bar; a no-op when run headless."""


if __name__ == "__main__":
    from auto_gui import run_gui

    sim = 1
    port = "COM5"
    addresses = [1, 2]     # one entry per controller on the chain
    units = "deg"          # rotation stages; "mm" for linear ones
    if sim:
        from hardware import FakeSMC100 as SMC100
    else:
        from hardware import SMC100
    axes = [SMC100(port, address=addr, units=units) for addr in addresses]

    tester = SMC100ChainTest(axes)

    run_gui(
        automation=tester,
        run=tester._runTests,
        hardware=axes,
        title="SMC100 Chain Test",
    )
