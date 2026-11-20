"""
===================================================
  ______   __                       _
 | __ ) \ / /  ___ _ __   ___ _ __ | |_   _ ____
 |  _ \\ V /  / __| '_ \ / _ \ '_ \| | | | |_  /
 | |_) || |   \__ \ | | |  __/ |_) | | |_| |/ /
 |____/ |_|   |___/_| |_|\___| .__/|_|\__, /___|
                             |_|      |___/

===================================================
Telegram - https://t.me/resourcessneplyz
"""

import time
import ctypes
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QLabel, QFrame

KEY_MAP = {
    0x08: "Backspace", 0x09: "Tab", 0x0D: "Enter", 0x1B: "Esc",
    0x20: "Space", 0x25: "←", 0x26: "↑", 0x27: "→", 0x28: "↓",
    0x2E: "Del", 0x2D: "Ins", 0x24: "Home", 0x23: "End",
    0x70: "F1", 0x71: "F2", 0x72: "F3", 0x73: "F4",
    0x74: "F5", 0x75: "F6", 0x76: "F7", 0x77: "F8",
    0x78: "F9", 0x79: "F10", 0x7A: "F11", 0x7B: "F12",
}
for _c in range(0x30, 0x3A):  # 0-9
    KEY_MAP[_c] = chr(_c)
for _c in range(0x41, 0x5B):  # A-Z
    KEY_MAP[_c] = chr(_c)


class KeystrokeOSD(QWidget):
    """Глобальный оверлей отображения нажатий клавиш."""
    def __init__(self):
        super().__init__()
        self._enabled = False
        self._was_down = {}
        self._last_press_time = 0.0
        self._accent = "#ff2e5b"

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.pill = QFrame()
        self.pill.setObjectName("KeyPill")
        lay = QHBoxLayout(self.pill)
        lay.setContentsMargins(18, 10, 18, 10)

        self.lbl = QLabel("")
        self.lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl)
        root.addWidget(self.pill)

        self._apply_style()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_keys)

    def _apply_style(self):
        self.pill.setStyleSheet(f"""
            QFrame#KeyPill {{
                background-color: rgba(15, 15, 22, 215);
                border: 1px solid {self._accent};
                border-radius: 14px;
            }}
        """)
        self.lbl.setStyleSheet("""
            color: #ffffff;
            font-family: "Consolas", "Segoe UI", sans-serif;
            font-size: 16px;
            font-weight: 800;
            letter-spacing: 1px;
            background: transparent;
        """)

    def set_accent(self, hex_color: str):
        self._accent = hex_color
        self._apply_style()

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        if enabled:
            self._was_down.clear()
            self._timer.start(20)
        else:
            self._timer.stop()
            self.hide()

    def _reposition(self):
        self.adjustSize()
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.center().x() - self.width() // 2
            y = geo.bottom() - self.height() - 48
            self.move(x, y)

    def _poll_keys(self):
        user32 = ctypes.windll.user32
        mods = []
        if user32.GetAsyncKeyState(0x11) & 0x8000:
            mods.append("Ctrl")
        if user32.GetAsyncKeyState(0x10) & 0x8000:
            mods.append("Shift")
        if user32.GetAsyncKeyState(0x12) & 0x8000:
            mods.append("Alt")
        if (user32.GetAsyncKeyState(0x5B) & 0x8000) or (user32.GetAsyncKeyState(0x5C) & 0x8000):
            mods.append("Win")

        triggered = None
        for vk, name in KEY_MAP.items():
            down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
            if down and not self._was_down.get(vk, False):
                triggered = name
            self._was_down[vk] = down

        now = time.perf_counter()
        if triggered:
            combo = " + ".join(mods + [triggered])
            self.lbl.setText(combo)
            self._reposition()
            self.show()
            self._last_press_time = now
        elif self.isVisible() and (now - self._last_press_time) > 1.4:
            self.hide()
