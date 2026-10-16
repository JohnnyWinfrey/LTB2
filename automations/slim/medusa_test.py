"""Medusa bench test: just the Medusa control panel, no scan. Temporary.

    python -m automations.slim.medusa_test                         # MEDUSA_PORT
    python -m automations.slim.medusa_test /dev/cu.usbmodem1301    # e.g. on a Mac
    python -m automations.slim.medusa_test --sim
"""

TITLE = "Medusa Test"


def main(sim=False, port=None):
    from auto_gui import run_gui
    from hardware import Medusa
    from . import experiment

    medusa = experiment.medusa(sim) if sim or port is None else Medusa(port)
    run_gui(hardware=[medusa], title=TITLE)


if __name__ == "__main__":
    import sys
    ports = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(sim="--sim" in sys.argv, port=ports[0] if ports else None)
