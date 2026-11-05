import time

TITLE = "Lock-in Read Test"


def main(sim=False):
    from . import experiment

    lockin = experiment.lockin(sim)
    start = time.monotonic()
    while time.monotonic() - start < 10:
        print(f"{time.monotonic() - start:5.2f} s  X = {lockin.measure()} V")
        time.sleep(0.1)
    lockin.close()


if __name__ == "__main__":
    import sys
    main(sim="--sim" in sys.argv)
