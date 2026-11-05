"""Automations, grouped by experiment family (slim/, tcspc/, ...).

Each family has an experiment.py that builds its hardware -- the one place its
COM ports live -- and one module per automation. An automation module defines
TITLE and main(sim=False); LetThereBeBeans finds those and lists them. Run one
directly from the repo root with:

    python -m automations.slim.stokes          # real hardware
    python -m automations.slim.stokes --sim    # fakes
"""
from pathlib import Path

# Every run saves under the repo's data/, wherever it was launched from.
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
