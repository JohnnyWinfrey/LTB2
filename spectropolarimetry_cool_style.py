"""SMC100 rotation-stage bring-up -- standalone auto_gui launcher.

Run: python spectropolarimetry_cool_style.py
For every axis on the daisy chain:

  1. comms  -- the address answers (wrong address or cabling fails here)
  2. home   -- references (OR) and lands at 0
  3. moves  -- each of TARGETS within TOL; after every move the other axes
               must not have moved (catches two controllers sharing an address)
  4. park   -- back to 0, even after Stop

Results go to data/<timestamp>/smc100_test.csv and a PASS/FAIL summary is
printed. Axes (port, addresses) are set in __main__. Set sim = 0 for real
hardware -- and make sure nothing is in the stages' way before Start.
"""
import os
import csv
from datetime import datetime

TOL = 0.01                                   # deg, allowed |target - position|
TARGETS = [45.0, 90.0, 180.0, 270.0, -90.0, 0.0]


class SMC100ChainTest():

    def __init__(self, axes):
        self.axes = axes
        self.results = []
        self._stop = False     # auto_gui's Stop button sets this
        print(f"SMC100ChainTest Ready ({len(axes)} axes)")

    def _log(self, test, axis, ok, detail=""):
        result = "PASS" if ok else "FAIL"
        self.results.append({'test': test, 'axis': axis.name, 'result': result, 'detail': detail})
        print(f"  [{result}] {test:<9} {axis.name}  {detail}")

    def _at(self, test, axis, target):
        pos = axis._position()
        self._log(test, axis, abs(pos - target) <= TOL, f"target {target:.3f}  at {pos:.4f} deg")

    def _testMoves(self, axis):
        others = [a for a in self.axes if a is not axis]
        for target in TARGETS:
            if self._stop:
                return
            before = [a._position() for a in others]
            axis.moveAbsolute(target)
            self._at("move", axis, target)
            if others:
                drift = max(abs(a._position() - b) for a, b in zip(others, before))
                self._log("crosstalk", axis, drift <= TOL, f"others moved {drift:.4f} deg")

    def _runTests(self):
        self.results = []
        for phase in ("comms", "home", "moves", "park"):
            print("\n" + "=" * 50 + f"\n{phase.upper()}\n" + "=" * 50)
            for axis in self.axes:
                if self._stop and phase != "park":   # park even after Stop
                    break
                try:
                    if phase == "comms":
                        self._log("comms", axis, True, f"{axis.getStatus()}, {axis.getPosition()}")
                    elif phase == "home":
                        axis.home()
                        self._at("home", axis, 0.0)
                    elif phase == "moves":
                        self._testMoves(axis)
                    else:
                        axis.moveAbsolute(0.0)
                        self._at("park", axis, 0.0)
                except Exception as exc:
                    self._log(phase, axis, False, f"{type(exc).__name__}: {exc}")

        output_dir = os.path.join("data", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        os.makedirs(output_dir, exist_ok=True)
        csv_filename = os.path.join(output_dir, 'smc100_test.csv')
        with open(csv_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['test', 'axis', 'result', 'detail'])
            writer.writeheader()
            writer.writerows(self.results)

        failed = [r for r in self.results if r['result'] == "FAIL"]
        print("\n" + "=" * 50)
        print(f"{len(self.results) - len(failed)}/{len(self.results)} checks passed"
              + (" -- stopped early" if self._stop else ""))
        for r in failed:
            print(f"  FAIL {r['test']:<9} {r['axis']}  {r['detail']}")
        print(f"Results saved to: {csv_filename}")
        return self.results


if __name__ == "__main__":
    from auto_gui import run_gui

    sim = 0
    port = "/dev/cu.usbserial-FTE4GWPV"
    addresses = [1, 2]     # one entry per controller on the chain
    if sim:
        from hardware import FakeSMC100 as SMC100
    else:
        from hardware import SMC100
    axes = [SMC100(port, address=addr, units="deg") for addr in addresses]

    tester = SMC100ChainTest(axes)

    run_gui(
        automation=tester,
        run=tester._runTests,
        hardware=axes,
        title="SMC100 Chain Test",
    )
