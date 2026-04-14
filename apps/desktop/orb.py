#!/usr/bin/env python3
"""Jarvis desktop orb widget — frameless, always-on-top, live voice state."""
import sys
import os
import json
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl, QTimer, QPoint
from PyQt5.QtGui import QCursor

HTML = os.path.abspath(os.path.join(os.path.dirname(__file__), "orb.html"))
PHASE_FILE = Path("/tmp/jarvis-voice-phase.json")

_last_phase = "idle"


def read_phase() -> str:
    try:
        data = json.loads(PHASE_FILE.read_text())
        return data.get("phase", "idle")
    except Exception:
        return "idle"


class DragHandle(QLabel):
    """Thin strip at top that lets user drag the frameless window."""

    def __init__(self, window: QMainWindow):
        super().__init__("· · ·")
        self._win = window
        self._drag_pos: QPoint | None = None
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(18)
        self.setStyleSheet("""
            color: #2a3040;
            font-size: 9px;
            letter-spacing: 4px;
            background: #0d1117;
        """)
        self.setCursor(QCursor(Qt.SizeAllCursor))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self._win.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self._win.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


app = QApplication(sys.argv)

win = QMainWindow()
win.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
win.setFixedSize(180, 238)  # 18px drag handle + 220px orb

container = QWidget()
layout = QVBoxLayout(container)
layout.setContentsMargins(0, 0, 0, 0)
layout.setSpacing(0)

handle = DragHandle(win)
layout.addWidget(handle)

view = QWebEngineView()
view.setUrl(QUrl.fromLocalFile(HTML))
layout.addWidget(view)

win.setCentralWidget(container)

# Position bottom-right of primary screen
screen = app.primaryScreen().geometry()
win.move(screen.width() - 200, screen.height() - 278)

win.show()


def poll_phase():
    global _last_phase
    phase = read_phase()
    if phase != _last_phase:
        _last_phase = phase
        view.page().runJavaScript(f"set('{phase}')")


def on_load_finished(ok):
    if ok:
        view.page().runJavaScript(
            "if(window._demoCycle) clearInterval(window._demoCycle); set('idle');"
        )
        timer = QTimer()
        timer.timeout.connect(poll_phase)
        timer.start(800)
        win._timer = timer


view.loadFinished.connect(on_load_finished)

sys.exit(app.exec_())
