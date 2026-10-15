
class DualRotatingRetarder():
    def __init__(self, r1, r2, monochromator, lockin):
        self.mono = monochromator
        self.r1 = r1
        self.r2 = r2
        self.lockin=lockin
        self.r1.home()
        self.r2.home()
        print("ready fready!")

    def mueller(self):
        step_size = self.mono.numSteps
        self.mono.openShutter()
        self.mono.setWavelength(self.mono.startWavelength)
        time.sleep(4)
        data = []
        for wl in range(int((self.mono.endWavelength - self.mono.startWavelength)/step_size) + 1):
            self.mono.setWavelength(self.mono.startWavelength + wl*step_size)
            for i in range(61):
                self.r1.moveAbsolute(6*i)  
                self.r2.moveAbsolute(30*i)
                #time.sleep(1)
                d = self.lockin.measure()
                data.append(d)
                print(f"data = {d}, wavelength={self.mono.startWavelength + wl*step_size}")
            self.r1.home()
            self.r2.home()
        self.mono.closeShutter()
        print("all done fam!")
            
        with open("output2.txt", "a") as file:
            for item in data:
                # Write the variable to the file with a newline character
                file.write(f"{item}\n")

                

TITLE = "UAH Mueller Matrix Spectropolarimeter"


def main(sim=False):
    from auto_gui import run_gui
    from . import experiment
   

    retarder1, retarder2 = experiment.retarders(sim)
    monochromator = experiment.cornerstone(sim)
    lockin = experiment.lockin(sim)
    dual_retarder = DualRotatingRetarder(retarder1, retarder2, monochromator, lockin)

    run_gui(
        automation=dual_retarder,
        run=dual_retarder.mueller,
        hardware=[retarder1, retarder2, monochromator,lockin],
        title=TITLE,
    )


if __name__ == "__main__":
    import sys
    import time
    main(sim="--sim" in sys.argv)
