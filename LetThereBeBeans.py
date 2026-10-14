"""LTB2 launcher: one button per automation, grouped by family.

Automations are found automatically: any module in automations/<family>/ that
defines main() gets a button labelled with its TITLE. Modules are read, not
imported, so the menu opens fast and a broken automation can't stop it.
Each automation runs in its own process (its own window, crash-isolated).
"""
import ast
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QCheckBox, QGroupBox, QPushButton, QVBoxLayout, QWidget,
)

from auto_gui import apply_theme

ROOT = Path(__file__).resolve().parent


def discover():
    """{family: [(title, module), ...]} for every automation module."""
    found = {}
    for path in sorted((ROOT / "automations").glob("*/*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if not any(isinstance(n, ast.FunctionDef) and n.name == "main" for n in tree.body):
            continue
        title = path.stem
        for n in tree.body:
            if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                    and any(getattr(t, "id", None) == "TITLE" for t in n.targets)):
                title = n.value.value
        module = ".".join(path.relative_to(ROOT).with_suffix("").parts)
        found.setdefault(path.parent.name, []).append((title, module))
    return found


def launch(module, sim):
    # New process => its own QApplication; doesn't block this menu.
    args = [sys.executable, "-m", module] + (["--sim"] if sim else [])
    subprocess.Popen(args, cwd=ROOT)
    print(f"launched {module}" + (" (sim)" if sim else ""))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_theme(app)

    win = QWidget()
    win.setWindowTitle("LTB2")
    layout = QVBoxLayout(win)

    sim_box = QCheckBox("Simulate (fake hardware)")
    layout.addWidget(sim_box)

    for family, automations in discover().items():
        group = QGroupBox(family.upper())
        group_layout = QVBoxLayout(group)
        for title, module in sorted(automations):
            btn = QPushButton(title)
            btn.clicked.connect(lambda _=False, m=module: launch(m, sim_box.isChecked()))
            group_layout.addWidget(btn)
        layout.addWidget(group)

    win.show()
    app.exec()
