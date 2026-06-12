import inspect
import sys
import traceback
from contextlib import redirect_stdout

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QDoubleSpinBox, QSpinBox, QLineEdit,
    QGroupBox, QScrollArea, QTextEdit,
)
from PySide6.QtCore import Qt, QObject, QThread, Signal
from PySide6.QtGui import QFont

# Create QApplication at import time so cores can safely create QWidgets
# in their __init__ before run() is called.
if not QApplication.instance():
    _bootstrap_app = QApplication(sys.argv)


class _LiveStream(QObject):
    text_written = Signal(str)

    def write(self, text):
        self.text_written.emit(text)

    def flush(self):
        pass


class _Worker(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, func, kwargs, stream):
        super().__init__()
        self._func = func
        self._kwargs = kwargs
        self._stream = stream
        self._stop_func = None

    def run(self):
        try:
            with redirect_stdout(self._stream):
                result = self._func(**self._kwargs)
            self.finished.emit(result)
        except Exception:
            self.error.emit(traceback.format_exc())


# Registry populated by @core
_cores: list = []


def core(func=None, *, stop=None):
    """Decorator that registers a function as a runnable node card.

    Usage:
        @core
        def my_scan(param: float = 1.0): ...

        @core(stop=automation.cancel)
        def my_scan(): ...
    """
    if func is None:
        # Called as @core(stop=...) — return the actual decorator
        def decorator(f):
            _cores.append((f, stop))
            return f
        return decorator
    # Called as @core with no arguments
    _cores.append((func, None))
    return func


def _make_widget(param: inspect.Parameter):
    ann = param.annotation
    default = param.default if param.default is not inspect.Parameter.empty else None

    if ann is float:
        w = QDoubleSpinBox()
        w.setRange(-1e9, 1e9)
        w.setDecimals(4)
        w.setSingleStep(0.1)
        if default is not None:
            w.setValue(float(default))
        return w, w.value

    if ann is int:
        w = QSpinBox()
        w.setRange(-1_000_000, 1_000_000)
        if default is not None:
            w.setValue(int(default))
        return w, w.value

    w = QLineEdit()
    if default is not None:
        w.setText(str(default))
    return w, w.text


class NodeCard(QGroupBox):
    def __init__(self, func, stop_func=None):
        super().__init__(func.__name__.replace("_", " ").title())
        self._func = func
        self._stop_func = stop_func
        self._getters: dict[str, callable] = {}
        self._worker = None

        vl = QVBoxLayout(self)
        vl.setSpacing(8)

        doc = inspect.getdoc(func)
        if doc:
            lbl = QLabel(doc)
            lbl.setStyleSheet("color:#888; font-style:italic;")
            lbl.setWordWrap(True)
            vl.addWidget(lbl)

        for pname, param in inspect.signature(func).parameters.items():
            if param.annotation is inspect.Parameter.empty:
                continue
            w, getter = _make_widget(param)
            self._getters[pname] = getter
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{pname}:"), 1)
            row.addWidget(w, 2)
            vl.addLayout(row)

        btn_row = QHBoxLayout()

        self._btn_run = QPushButton("▶  Run")
        self._btn_run.setFixedHeight(32)
        self._btn_run.setStyleSheet(
            "QPushButton{background:#2a6fdb;color:white;border-radius:5px;font-weight:600;}"
            "QPushButton:hover{background:#3a7fef;}"
            "QPushButton:disabled{background:#555;}"
        )
        self._btn_run.clicked.connect(self._run)
        btn_row.addWidget(self._btn_run)

        self._btn_stop = QPushButton("■  Stop")
        self._btn_stop.setFixedHeight(32)
        self._btn_stop.setEnabled(False)
        self._btn_stop.setStyleSheet(
            "QPushButton{background:#b03030;color:white;border-radius:5px;font-weight:600;}"
            "QPushButton:hover{background:#c04040;}"
            "QPushButton:disabled{background:#555;}"
        )
        self._btn_stop.clicked.connect(self._stop)
        btn_row.addWidget(self._btn_stop)

        vl.addLayout(btn_row)

        self._out = QTextEdit()
        self._out.setReadOnly(True)
        self._out.setFixedHeight(160)
        self._out.setFont(QFont("Courier New", 10))
        self._out.setStyleSheet(
            "background:#1e1e1e;color:#d4d4d4;border-radius:4px;padding:4px;"
        )
        vl.addWidget(self._out)

    def _run(self):
        self._out.clear()
        self._btn_run.setEnabled(False)
        self._btn_stop.setEnabled(True)

        stream = _LiveStream()
        stream.text_written.connect(self._out.insertPlainText)

        self._worker = _Worker(self._func, {n: g() for n, g in self._getters.items()}, stream)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _stop(self):
        if self._stop_func is not None:
            self._stop_func()
        elif self._worker is not None:
            self._worker.requestInterruption()
        self._btn_stop.setEnabled(False)
        self._out.insertPlainText("\n[Stop requested]")

    def _on_finished(self, result):
        if result is not None:
            self._out.insertPlainText(f"\n✓ {result}")
        self._btn_run.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def _on_error(self, text):
        self._out.setPlainText(text)
        self._btn_run.setEnabled(True)
        self._btn_stop.setEnabled(False)


class _App(QMainWindow):
    def __init__(self, nodes: list, title: str = "LTB2"):
        super().__init__()
        self.setWindowTitle(title)
        self.setMinimumSize(660, 420)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        vl = QVBoxLayout(container)
        vl.setContentsMargins(16, 16, 16, 16)
        vl.setSpacing(12)
        vl.setAlignment(Qt.AlignmentFlag.AlignTop)
        for func, stop_func in nodes:
            vl.addWidget(NodeCard(func, stop_func))
        scroll.setWidget(container)
        self.setCentralWidget(scroll)


def run(title: str = "LTB2 Automation"):
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = _App(_cores, title=title)
    window.show()
    window.raise_()
    sys.exit(app.exec())
