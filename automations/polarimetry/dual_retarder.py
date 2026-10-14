
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



TITLE = "Dual Rotating Waveplate Polarimeter"


def main(sim=False):
    from auto_gui import run_gui
    from . import experiment

    retarder1, retarder2 = experiment.retarders(sim)
    dual_retarder = DualRotatingRetarder(retarder1, retarder2)

    run_gui(
        automation=dual_retarder,
        run=dual_retarder.mueller,
        hardware=[retarder1, retarder2],
        title=TITLE,
    )


if __name__ == "__main__":
    import sys
    main(sim="--sim" in sys.argv)
