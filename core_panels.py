"""
Floating Qt Widgets control panels for each hardware core.

No top-level import of cores.py — each panel accepts the core instance
via constructor injection to avoid circular imports.
"""

from PySide6.QtWidgets import (
    QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QListWidget, QSlider, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont


# ── shared style helpers ────────────────────────────────────────────────────

_DISPLAY_STYLE = (
    "background:#1a1a1a; color:#ff6d00; border:1px solid #555;"
    "border-radius:3px; padding:2px 6px; font-size:20px;"
)
_LABEL_STYLE = "color:#bbf6ef; font-weight:bold;"

def _btn(text, color="#2a6fdb", text_color="white", height=28):
    b = QPushButton(text)
    b.setFixedHeight(height)
    b.setStyleSheet(
        f"QPushButton{{background:{color};color:{text_color};"
        "border-radius:5px;font-weight:600;padding:0 8px;}"
        f"QPushButton:hover{{background:{color}cc;}}"
        "QPushButton:disabled{background:#555;}"
    )
    return b

def _display(text="0.00"):
    lbl = QLabel(text)
    lbl.setStyleSheet(_DISPLAY_STYLE)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setFont(QFont("Cascadia Mono", 14))
    lbl.setMinimumWidth(80)
    return lbl


# ── XWingPanel ──────────────────────────────────────────────────────────────

class XWingPanel(QWidget):
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self._core = core
        self.setWindowTitle("XWing Stage")
        self.setWindowFlags(Qt.WindowType.Window)
        self.setMinimumWidth(320)

        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(10, 10, 10, 10)

        # ── Position display ─────────────────────────
        pos_row = QHBoxLayout()
        x_box = QGroupBox("X (mm)")
        x_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        xl = QVBoxLayout(x_box)
        self._x_lbl = _display(core.xPosString)
        xl.addWidget(self._x_lbl)
        pos_row.addWidget(x_box)

        y_box = QGroupBox("Y (mm)")
        y_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        yl = QVBoxLayout(y_box)
        self._y_lbl = _display(core.yPosString)
        yl.addWidget(self._y_lbl)
        pos_row.addWidget(y_box)
        root.addLayout(pos_row)

        core.xChanged.connect(lambda: self._x_lbl.setText(core.xPosString))
        core.yChanged.connect(lambda: self._y_lbl.setText(core.yPosString))

        # ── Jog controls ─────────────────────────────
        jog_box = QGroupBox("Jog")
        jog_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        grid = QGridLayout(jog_box)
        up   = _btn("▲ Up",    "#00bfa0")
        down = _btn("▼ Down",  "#00bfa0")
        left = _btn("◄ Left",  "#ff563e")
        right= _btn("► Right", "#ff563e")
        up.clicked.connect(core.moveUp)
        down.clicked.connect(core.moveDown)
        left.clicked.connect(core.moveLeft)
        right.clicked.connect(core.moveRight)
        grid.addWidget(up,    0, 1)
        grid.addWidget(left,  1, 0)
        grid.addWidget(down,  1, 1)
        grid.addWidget(right, 1, 2)
        root.addWidget(jog_box)

        # ── Home / Set Home ───────────────────────────
        ctrl_row = QHBoxLayout()
        home_btn     = _btn("Home",     "#d600cd")
        set_home_btn = _btn("Set Home", "#017a03")
        home_btn.clicked.connect(core.home)
        set_home_btn.clicked.connect(core.setHome)
        ctrl_row.addWidget(home_btn)
        ctrl_row.addWidget(set_home_btn)
        root.addLayout(ctrl_row)

        # ── Go To ─────────────────────────────────────
        goto_box = QGroupBox("Go To Position")
        goto_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        goto_hl = QHBoxLayout(goto_box)
        goto_hl.addWidget(QLabel("X:"))
        self._goto_x = QLineEdit("0.000")
        self._goto_x.setFixedWidth(70)
        goto_hl.addWidget(self._goto_x)
        goto_hl.addWidget(QLabel("Y:"))
        self._goto_y = QLineEdit("0.000")
        self._goto_y.setFixedWidth(70)
        goto_hl.addWidget(self._goto_y)
        go_btn = _btn("Go!", "#017a03")
        go_btn.clicked.connect(self._go_to)
        goto_hl.addWidget(go_btn)
        root.addWidget(goto_box)

        # ── Position Manager ──────────────────────────
        pm_box = QGroupBox("Position Manager")
        pm_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        pm_vl = QVBoxLayout(pm_box)

        # Reference
        ref_row = QHBoxLayout()
        self._ref_lbl = QLabel("Ref: None")
        self._ref_lbl.setStyleSheet("color:#aaa;")
        ref_store = _btn("Store Ref",  "#ff6d00", height=24)
        ref_clear = _btn("Clear Ref",  "#555",    height=24)
        ref_store.clicked.connect(core.storeReference)
        ref_clear.clicked.connect(core.clearReference)
        ref_row.addWidget(self._ref_lbl, 1)
        ref_row.addWidget(ref_store)
        ref_row.addWidget(ref_clear)
        pm_vl.addLayout(ref_row)

        # Sample store
        sample_row = QHBoxLayout()
        sample_row.addWidget(QLabel("Region:"))
        self._region_combo = QComboBox()
        self._region_combo.addItems(["A", "B", "C", "D", "Other"])
        self._region_combo.setFixedWidth(70)
        sample_row.addWidget(self._region_combo)
        store_sample = _btn("Store Sample", "#2a6fdb", height=24)
        clear_all    = _btn("Clear All",    "#555",    height=24)
        store_sample.clicked.connect(self._store_sample)
        clear_all.clicked.connect(core.clearSamples)
        sample_row.addWidget(store_sample)
        sample_row.addWidget(clear_all)
        pm_vl.addLayout(sample_row)

        # Sample list
        self._sample_list = QListWidget()
        self._sample_list.setMaximumHeight(100)
        self._sample_list.setStyleSheet(
            "background:#1a1a1a;color:#d4d4d4;border-radius:3px;"
        )
        pm_vl.addWidget(self._sample_list)
        root.addWidget(pm_box)

        core.coordinatesChanged.connect(self._update_positions)
        self._update_positions()

    def _go_to(self):
        self._core.setPosition(self._goto_x.text(), self._goto_y.text())

    def _store_sample(self):
        self._core.storeSample(self._region_combo.currentText())

    def _update_positions(self):
        ref = self._core.referencePosition
        if ref:
            self._ref_lbl.setText(f"Ref: X={ref['x']:.2f}  Y={ref['y']:.2f}")
            self._ref_lbl.setStyleSheet("color:#ff6d00;")
        else:
            self._ref_lbl.setText("Ref: None")
            self._ref_lbl.setStyleSheet("color:#aaa;")

        self._sample_list.clear()
        for s in self._core.samplesList:
            self._sample_list.addItem(
                f"[{s['region']}]  X={s['x']:.2f}  Y={s['y']:.2f}"
            )


# ── DeathStarPanel ──────────────────────────────────────────────────────────

class DeathStarPanel(QWidget):
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self._core = core
        self.setWindowTitle(f"DeathStar — {core.name}")
        self.setWindowFlags(Qt.WindowType.Window)
        self.setMinimumWidth(280)

        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(10, 10, 10, 10)

        # ── Angle displays ────────────────────────────
        disp_row = QHBoxLayout()
        p_box = QGroupBox("Polarizer (°)")
        p_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        pl = QVBoxLayout(p_box)
        self._p_lbl = _display(core.pPosString)
        pl.addWidget(self._p_lbl)
        disp_row.addWidget(p_box)

        w_box = QGroupBox("λ/4 Plate (°)")
        w_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        wl = QVBoxLayout(w_box)
        self._w_lbl = _display(core.wPosString)
        wl.addWidget(self._w_lbl)
        disp_row.addWidget(w_box)
        root.addLayout(disp_row)

        core.polarRotated.connect(lambda: self._p_lbl.setText(core.pPosString))
        core.wavePlateRotated.connect(lambda: self._w_lbl.setText(core.wPosString))

        # ── Set Position ─────────────────────────────
        set_box = QGroupBox("Set Position")
        set_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        set_hl = QHBoxLayout(set_box)
        set_hl.addWidget(QLabel("P:"))
        self._p_input = QLineEdit("0")
        self._p_input.setFixedWidth(70)
        set_hl.addWidget(self._p_input)
        set_hl.addWidget(QLabel("W:"))
        self._w_input = QLineEdit("0")
        self._w_input.setFixedWidth(70)
        set_hl.addWidget(self._w_input)
        set_btn = _btn("Set", "#017a03")
        set_btn.clicked.connect(self._set_position)
        set_hl.addWidget(set_btn)
        root.addWidget(set_box)

        # ── Home / Reset Home ─────────────────────────
        ctrl_row = QHBoxLayout()
        home_btn  = _btn("Home",       "#d600cd")
        reset_btn = _btn("Reset Home", "#8b0000")
        home_btn.clicked.connect(core.home)
        reset_btn.clicked.connect(core.resetHome)
        ctrl_row.addWidget(home_btn)
        ctrl_row.addWidget(reset_btn)
        if core.ZAxis:
            zhome_btn = _btn("Z Home", "#555")
            zhome_btn.clicked.connect(core.zHome)
            ctrl_row.addWidget(zhome_btn)
        root.addLayout(ctrl_row)

    def _set_position(self):
        self._core.setPosition(self._p_input.text(), self._w_input.text())


# ── CornerstonePanel ────────────────────────────────────────────────────────

class CornerstonePanel(QWidget):
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self._core = core
        self.setWindowTitle("Cornerstone Monochromator")
        self.setWindowFlags(Qt.WindowType.Window)
        self.setMinimumWidth(300)

        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(10, 10, 10, 10)

        # ── Wavelength display ────────────────────────
        wl_box = QGroupBox("Current Wavelength (nm)")
        wl_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        wll = QVBoxLayout(wl_box)
        self._wl_lbl = _display(str(core.currentWavelength))
        wll.addWidget(self._wl_lbl)
        root.addWidget(wl_box)

        core.waveChanged.connect(lambda: self._wl_lbl.setText(str(core.currentWavelength)))

        # ── Set wavelength ────────────────────────────
        goto_box = QGroupBox("Go To Wavelength")
        goto_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        goto_hl = QHBoxLayout(goto_box)
        self._wl_spin = QDoubleSpinBox()
        self._wl_spin.setRange(200.0, 2000.0)
        self._wl_spin.setDecimals(1)
        self._wl_spin.setValue(630.0)
        self._wl_spin.setSuffix(" nm")
        goto_hl.addWidget(self._wl_spin, 1)
        go_btn = _btn("Go", "#017a03")
        go_btn.clicked.connect(
            lambda: core.setWavelength(str(self._wl_spin.value()))
        )
        goto_hl.addWidget(go_btn)
        root.addWidget(goto_box)

        # ── Shutter controls ──────────────────────────
        shutter_box = QGroupBox("Shutter")
        shutter_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        shutter_hl = QHBoxLayout(shutter_box)
        open_btn  = _btn("Open",  "#017a03")
        close_btn = _btn("Close", "#b03030")
        open_btn.clicked.connect(core.openShutter)
        close_btn.clicked.connect(core.closeShutter)
        self._shutter_lbl = QLabel(core.shutterState)
        self._shutter_lbl.setStyleSheet("color:#aaa;")
        shutter_hl.addWidget(open_btn)
        shutter_hl.addWidget(close_btn)
        shutter_hl.addWidget(self._shutter_lbl)
        root.addWidget(shutter_box)

        core.shutterChanged.connect(
            lambda: self._shutter_lbl.setText(core.shutterState)
        )

        # ── Scan range ────────────────────────────────
        scan_box = QGroupBox("Scan Range")
        scan_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        form = QFormLayout(scan_box)

        self._start_spin = QDoubleSpinBox()
        self._start_spin.setRange(200.0, 2000.0)
        self._start_spin.setDecimals(1)
        self._start_spin.setValue(float(core.startWavelength))
        self._start_spin.setSuffix(" nm")
        self._start_spin.editingFinished.connect(
            lambda: core.setStartWavelength(str(self._start_spin.value()))
        )
        form.addRow("Start:", self._start_spin)

        self._end_spin = QDoubleSpinBox()
        self._end_spin.setRange(200.0, 2000.0)
        self._end_spin.setDecimals(1)
        self._end_spin.setValue(float(core.endWavelength))
        self._end_spin.setSuffix(" nm")
        self._end_spin.editingFinished.connect(
            lambda: core.setEndWavelength(str(self._end_spin.value()))
        )
        form.addRow("End:", self._end_spin)

        self._steps_spin = QSpinBox()
        self._steps_spin.setRange(1, 1000)
        self._steps_spin.setValue(int(core.numSteps))
        self._steps_spin.editingFinished.connect(
            lambda: core.setNumSteps(str(self._steps_spin.value()))
        )
        form.addRow("Steps:", self._steps_spin)

        root.addWidget(scan_box)


# ── PMTPanel ────────────────────────────────────────────────────────────────

class PMTPanel(QWidget):
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self._core = core
        self.setWindowTitle("PMT Gain Shield")
        self.setWindowFlags(Qt.WindowType.Window)
        self.setMinimumWidth(260)

        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(10, 10, 10, 10)

        # ── Gain display ──────────────────────────────
        gain_box = QGroupBox("Current Gain")
        gain_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        gl = QVBoxLayout(gain_box)
        self._gain_lbl = _display(f"{core.gain:.3f}")
        gl.addWidget(self._gain_lbl)
        root.addWidget(gain_box)

        core.gainChanged.connect(lambda: self._gain_lbl.setText(f"{core.gain:.3f}"))

        # ── Set gain ──────────────────────────────────
        set_box = QGroupBox("Set Gain (0 – 1)")
        set_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        set_hl = QHBoxLayout(set_box)

        self._gain_spin = QDoubleSpinBox()
        self._gain_spin.setRange(0.0, 1.0)
        self._gain_spin.setDecimals(3)
        self._gain_spin.setSingleStep(0.001)
        self._gain_spin.setValue(float(core.gain))
        set_hl.addWidget(self._gain_spin, 1)

        set_btn = _btn("Set", "#017a03")
        set_btn.clicked.connect(
            lambda: core.changeGain(str(self._gain_spin.value()))
        )
        set_hl.addWidget(set_btn)
        root.addWidget(set_box)

        # ── Slider ────────────────────────────────────
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 1000)
        self._slider.setValue(int(core.gain * 1000))
        self._slider.valueChanged.connect(
            lambda v: self._gain_spin.setValue(v / 1000.0)
        )
        self._gain_spin.valueChanged.connect(
            lambda v: self._slider.setValue(int(v * 1000))
        )
        root.addWidget(self._slider)


# ── SpectrePanel ────────────────────────────────────────────────────────────

class _BgThread(QThread):
    done = Signal()

    def __init__(self, core):
        super().__init__()
        self._core = core

    def run(self):
        self._core.takeBackground()
        self.done.emit()


class SpectrePanel(QWidget):
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self._core = core
        self._bg_thread = None
        self.setWindowTitle("Spectrometer")
        self.setWindowFlags(Qt.WindowType.Window)
        self.setMinimumWidth(280)

        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(10, 10, 10, 10)

        # Device info
        info_lbl = QLabel(str(core.specInfo))
        info_lbl.setStyleSheet("color:#888;font-style:italic;")
        info_lbl.setWordWrap(True)
        root.addWidget(info_lbl)

        # ── Integration time ──────────────────────────
        int_box = QGroupBox("Integration Time")
        int_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        int_hl = QHBoxLayout(int_box)
        self._int_spin = QSpinBox()
        self._int_spin.setRange(core.intMin, core.intMax)
        self._int_spin.setValue(int(core.intTime))
        self._int_spin.setSuffix(" μs")
        self._int_spin.editingFinished.connect(
            lambda: core.setIntegration(str(self._int_spin.value()))
        )
        int_hl.addWidget(self._int_spin)
        root.addWidget(int_box)

        # ── Scans to average ──────────────────────────
        avg_box = QGroupBox("Scans to Average")
        avg_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        avg_hl = QHBoxLayout(avg_box)
        self._avg_spin = QSpinBox()
        self._avg_spin.setRange(1, 200)
        self._avg_spin.setValue(int(core.scansToAvg))
        self._avg_spin.editingFinished.connect(
            lambda: core.setScansToAvg(str(self._avg_spin.value()))
        )
        avg_hl.addWidget(self._avg_spin)
        root.addWidget(avg_box)

        # ── Background ────────────────────────────────
        bg_box = QGroupBox("Background")
        bg_box.setStyleSheet("QGroupBox{color:#bbf6ef;font-weight:bold;}")
        bg_vl = QVBoxLayout(bg_box)

        self._bg_btn = _btn("Take Background", "#2a6fdb")
        self._bg_btn.clicked.connect(self._take_background)
        bg_vl.addWidget(self._bg_btn)

        bg_count_row = QHBoxLayout()
        bg_count_row.addWidget(QLabel("Peak Avg:"))
        self._bg_lbl = QLabel(core.bgCounts)
        self._bg_lbl.setStyleSheet("color:#ff6d00;font-family:monospace;")
        bg_count_row.addWidget(self._bg_lbl)
        bg_vl.addLayout(bg_count_row)

        root.addWidget(bg_box)

        core.backgroundChanged.connect(lambda: self._bg_lbl.setText(core.bgCounts))

    def _take_background(self):
        if self._bg_thread is not None and self._bg_thread.isRunning():
            return
        self._bg_btn.setEnabled(False)
        self._bg_btn.setText("Taking Background…")
        self._bg_thread = _BgThread(self._core)
        self._bg_thread.done.connect(self._bg_done)
        self._bg_thread.start()

    def _bg_done(self):
        self._bg_btn.setEnabled(True)
        self._bg_btn.setText("Take Background")
