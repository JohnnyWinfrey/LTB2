"""Auto-GUI harness for hardware + automation.

Give it an automation object, the callable that runs it, and a list of
hardware objects, and it pops up:

  * one control window per hardware object (buttons/fields built by
    introspecting each object's public methods), and
  * a Start/Stop panel that runs the automation on a background thread.

Minimal usage::

    from auto_gui import run_gui
    run_gui(automation=slim, run=slim._dualRotatingWaveplate,
            hardware=[psg, psa, meter], title="SLIM Calibration")
"""
import inspect
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Qt, QObject
from PySide6.QtGui import QMovie, QPainter
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QScrollArea,
    QProgressBar,
)


# ── Theme ────────────────────────────────────────────────────────────────────
# Pick the GUI theme by name. The stylesheet is themes/<THEME>.qss next to this
# file. Set THEME = None for the plain native look. Add your own by dropping a
# new .qss file in themes/. Bundled:
#   "dark", "light", "ltb2"        -- neutral / the old SLIM look
#   "synthwave", "matrix", "dracula", "nord", "gruvbox", "bubblegum", "hotdog"
THEME = "gruvbox"

# Optional wallpaper drawn (stretched) behind the panels: a file in themes/
# (png / jpg / gif). NOTE: GIFs show their FIRST FRAME only -- Qt stylesheets
# don't animate. Set to None for no background.
BACKGROUND = ""


def _apply_theme(app):
    """Apply themes/<THEME>.qss to the whole app (no-op if THEME is None)."""
    if not THEME:
        return
    qss_path = Path(__file__).parent / "themes" / f"{THEME}.qss"
    try:
        qss = qss_path.read_text()
    except FileNotFoundError:
        print(f"[auto_gui] theme '{THEME}' not found at {qss_path}; using native style")
        return
    app.setStyle("Fusion")      # predictable base so QSS colors apply everywhere
    app.setStyleSheet(qss)


# Method names treated as "read a value" rather than "do an action".
_READOUT_PREFIXES = ("get",)
_READOUT_NAMES = {"measure", "read"}


class _Worker(QThread):
    """Runs a callable on a background thread so the GUI stays responsive.

    Lean stand-in for cores.Worker; emits the run's return value on success
    or the traceback text on failure.
    """
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, func):
        super().__init__()
        self.func = func

    def run(self):
        try:
            result = self.func()
        except Exception:
            self.error.emit(traceback.format_exc())
        else:
            self.finished.emit(result)


def _is_readout(name):
    return name in _READOUT_NAMES or name.startswith(_READOUT_PREFIXES)


def _public_methods(device):
    """Yield (name, method, signature) for public, callable, non-dunder members."""
    for name, member in inspect.getmembers(device, callable):
        if name.startswith("_"):
            continue
        try:
            sig = inspect.signature(member)
        except (TypeError, ValueError):
            continue  # C-level builtins with no introspectable signature
        yield name, member, sig


def _params(sig):
    """Return the bound method's real parameters (self already dropped)."""
    return [
        p for p in sig.parameters.values()
        if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
    ]


def build_hardware_window(device):
    """Introspect ``device`` and build a control QWidget for it."""
    title = (getattr(device, "name", None)
             or getattr(device, "id", None)
             or type(device).__name__)

    win = QWidget()
    win.setWindowTitle(str(title))
    outer = QVBoxLayout(win)
    outer.addWidget(_title_label(str(title)))

    added = False
    for name, method, sig in _public_methods(device):
        params = _params(sig)

        if not params:
            outer.addWidget(_action_or_readout_row(name, method))
            added = True
        else:
            outer.addWidget(_setter_group(name, method, params))
            added = True

    if not added:
        outer.addWidget(QLabel("No introspectable controls found."))

    outer.addStretch(1)
    win.resize(260, win.sizeHint().height())
    return win


def _title_label(text):
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
    return lbl


def _action_or_readout_row(name, method):
    """Zero-arg method: a plain action button, or (for readouts) button + value label."""
    if _is_readout(name):
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        result = QLabel("--")
        result.setStyleSheet("font-family: monospace;")
        btn = QPushButton(name)

        def do_read():
            try:
                result.setText(str(method()))
            except Exception as exc:
                result.setText(f"error: {exc}")

        btn.clicked.connect(do_read)
        lay.addWidget(btn)
        lay.addWidget(result, 1)
        return row

    btn = QPushButton(name)

    def do_action():
        try:
            method()
        except Exception as exc:
            print(f"[auto_gui] {name}() raised: {exc}")

    btn.clicked.connect(do_action)
    return btn


def _setter_group(name, method, params):
    """Method with args: one text field per param + a call button."""
    box = QGroupBox(name)
    form = QFormLayout(box)
    fields = {}

    for p in params:
        field = QLineEdit()
        if p.default is not inspect.Parameter.empty:
            field.setPlaceholderText(f"(default {p.default!r})")
            label = f"{p.name} (opt)"
        else:
            label = p.name
        fields[p.name] = (field, p)
        form.addRow(label, field)

    btn = QPushButton(name)

    def do_call():
        args = []
        for _, (field, p) in fields.items():
            text = field.text()
            if text == "" and p.default is not inspect.Parameter.empty:
                args.append(p.default)
            else:
                args.append(text)  # setters here accept strings
        try:
            method(*args)
        except Exception as exc:
            print(f"[auto_gui] {name}({args}) raised: {exc}")

    btn.clicked.connect(do_call)
    form.addRow(btn)
    return box


class Progress(QObject):
    """Thread-safe progress reporter backing the Start panel's bar.

    Same hand-off as LivePlot: the automation runs on a worker thread and may
    not touch widgets, so reporting a step emits a signal that Qt delivers on
    the GUI thread, where the bar is actually redrawn.

    ControlWindow attaches one to the automation as ``.progress``, so a scan
    loop just calls it::

        for i, angle in enumerate(angles):
            ...
            self.progress(i + 1, len(angles))            # bar + "12/181"
            self.progress(i + 1, len(angles), "settling")  # with a message
    """
    _tick = Signal(int, int, float)

    def __init__(self, bar, label):
        super().__init__()
        self._bar = bar
        self._label = label
        self._tick.connect(self._on_tick)

    # --- called from the automation (any thread) ---
    def __call__(self, current, total, stepTime):
        self._tick.emit(int(current), int(total), float(stepTime))

    def reset(self):
        self._tick.emit(0, 0, 0)

    # --- always runs on the GUI thread ---
    def _on_tick(self, current, total, stepTime):
        self._bar.setRange(0, total)
        self._bar.setValue(min(current, total))
        if total != 0:
            _pComplete = 1-((current+1)/total)
            text = f"~{round(_pComplete*stepTime)} min"
            self._label.setText(f"{text}")


class ControlWindow(QWidget):
    """Start/Stop panel that runs ``run`` on a background thread."""

    def __init__(self, automation, run, title="Automation"):
        super().__init__()
        self.automation = automation
        self.run_func = run
        self.worker = None

        self.setWindowTitle(title)
        lay = QVBoxLayout(self)
        lay.addWidget(_title_label(title))

        self.status = QLabel("Idle")
        self.status.setAlignment(Qt.AlignCenter)

        self.bar = QProgressBar()
        self.bar.setRange(0, 1)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)

        self.step_label = QLabel("")
        self.step_label.setAlignment(Qt.AlignCenter)
        self.step_label.setStyleSheet("font-family: monospace;")

        # The automation reports progress through this; harmless if it never does.
        self.progress = Progress(self.bar, self.step_label)
        setattr(self.automation, "progress", self.progress)

        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self._start)
        self.stop_btn.clicked.connect(self._stop)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)

        lay.addLayout(btn_row)
        lay.addWidget(self.status)
        lay.addWidget(self.bar)
        lay.addWidget(self.step_label)
        self.resize(260, self.sizeHint().height())

    def _start(self):
        if self.worker is not None and self.worker.isRunning():
            return
        # Cooperative-stop flag; loops opt in with `if self._stop: break`.
        setattr(self.automation, "_stop", False)
        self.progress.reset()

        self.worker = _Worker(self.run_func)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status.setText("Running...")

    def _stop(self):
        setattr(self.automation, "_stop", True)
        self.status.setText("Stopping...")

    def _reset_buttons(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_finished(self, result):
        setattr(self.automation, "result", result)
        stopped = getattr(self.automation, "_stop", False)
        self.status.setText("Stopped" if stopped else "Done")
        self._reset_buttons()

    def _on_error(self, tb):
        print(tb)
        self.status.setText("Error (see console)")
        self._reset_buttons()


class LivePlot(QObject):
    """A live plot window you can push data to from anywhere -- including the
    background scan thread.

    The catch this solves: your automation runs on a worker thread, but plot
    widgets may only be touched on the GUI (main) thread. So `append`/`setData`
    don't draw directly -- they emit a signal that Qt delivers on the main
    thread, where the actual redraw happens. That makes them safe to call from
    inside an automation for-loop.

    Two modes:
      * "append"  -- accumulate one (x, y) point per call (a scan curve building
                     up, e.g. intensity vs. angle).
      * "replace" -- setData(xs, ys) swaps the whole trace each call (a live
                     spectrum, e.g. counts vs. wavelength).

    Create it on the main thread *before* run_gui (the constructor makes a
    QApplication if none exists yet, so ordering is forgiving), hand it to your
    automation, and call it in the loop::

        plot = LivePlot(title="SLIM sweep", xlabel="PSG angle", ylabel="counts")
        slim.plotter = plot
        run_gui(automation=slim, run=slim._dualRotatingWaveplate, hardware=[...])

        # ...inside the loop:
        self.plotter.append(angle, intensity)
    """
    _dataReady = Signal(object, object)

    def __init__(self, title="Live", xlabel="x", ylabel="y", mode="append"):
        # Ensure a QApplication exists before making any Qt/pyqtgraph widgets.
        QApplication.instance() or QApplication(sys.argv)
        super().__init__()

        import pyqtgraph as pg  # lazy: keeps `import auto_gui` cheap
        self._win = pg.plot(title=title)
        self._win.setLabel('bottom', xlabel)
        self._win.setLabel('left', ylabel)
        self._win.showGrid(x=True, y=True)
        self._curve = self._win.plot(pen='y')

        self._mode = mode
        self._xs = []
        self._ys = []
        # AutoConnection => when emitted from the worker thread, the slot is
        # queued onto this object's (main) thread. This is the safe hand-off.
        self._dataReady.connect(self._on_data)

    # --- called from the automation (any thread) ---
    def append(self, x, y):
        """Add one point to an accumulating curve (mode='append')."""
        self._dataReady.emit(x, y)

    def setData(self, xs, ys):
        """Replace the whole trace (mode='replace')."""
        self._dataReady.emit(list(xs), list(ys))

    def clear(self):
        self._dataReady.emit(None, None)

    # --- always runs on the GUI thread ---
    def _on_data(self, x, y):
        if x is None:                      # clear()
            self._xs, self._ys = [], []
            self._curve.setData([], [])
        elif self._mode == "append":
            self._xs.append(x)
            self._ys.append(y)
            self._curve.setData(self._xs, self._ys)
        else:                              # "replace"
            self._curve.setData(x, y)


def run_gui(automation=None, run=None, hardware=(), title="Automation"):
    """Pop up a window per hardware object, plus a Start/Stop panel.

    automation : the object holding the run + a `.result` after finishing. Pass
                 None to skip the Start/Stop panel and show only the hardware
                 windows -- e.g. a launcher menu built from an object whose
                 zero-arg methods each start an experiment (see launcher.py).
    run        : the callable Start executes. Defaults to `automation.run`.
    hardware   : iterable of device objects, one window each.
    title      : control-window title.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    _apply_theme(app)

    # One parent window holds every panel side by side, so closing it closes
    # everything. (A LivePlot, if attached, stays its own pyqtgraph window.)
    row = QWidget()
    if BACKGROUND:
        bg = Path(__file__).parent / "themes" / BACKGROUND
        if bg.exists():
            # Stretch the image to fill; opaque panels sit on top as cards.
            row.setObjectName("bgRoot")
            row.setStyleSheet(
                f'#bgRoot {{ border-image: url("{bg.as_posix()}") 0 0 0 0 '
                f'stretch stretch; }}'
            )
        else:
            print(f"[auto_gui] background '{BACKGROUND}' not found in themes/; skipping")
    layout = QHBoxLayout(row)
    layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

    for device in hardware:
        layout.addWidget(build_hardware_window(device), alignment=Qt.AlignTop)

    if automation is not None:
        if run is None:
            run = getattr(automation, "run", None)
            if run is None:
                raise ValueError(
                    "Pass run=... (a callable); automation has no run() method."
                )
        layout.addWidget(ControlWindow(automation, run, title=title),
                         alignment=Qt.AlignTop)

    # Wrap in a scroll area so many panels scroll instead of overflowing screen.
    window = QScrollArea()
    window.setWindowTitle(title)
    window.setWidgetResizable(True)
    window.setWidget(row)
    hint = row.sizeHint()
    window.resize(min(hint.width() + 30, 1200), min(hint.height() + 30, 800))
    window.show()

    app.exec()
    return window
