from hardware import SMC100 
import time
from auto_gui import run_gui

class DualRotatingRetarder():
    def __init__(self, r1, r2):
        self.r1 = r1
        self.r2 = r2
        self.r1.home()
        self.r2.home()
        print("ready fready!")

    def mueller(self):
        for i in range(1):
            self.r1.moveAbsolute(10)  
            self.r2.moveAbsolute(10)
            print("all done fam!")



if __name__ == "__main__":
    port = "/dev/cu.usbserial-FTE4GWPV"

    retarder1 = SMC100(port, 1, units="deg")
    retarder2 = SMC100(port, 2, units="deg")

    dual_retarder = DualRotatingRetarder(retarder1, retarder2)

    run_gui(
        automation=dual_retarder,
        run=dual_retarder.mueller, 
        hardware=[retarder1, retarder2],
        title="Dual Rotating Waveplate Polarimeter",
    )