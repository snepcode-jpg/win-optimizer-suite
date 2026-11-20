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

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFrame, QLabel, QPushButton
)


class DesktopHUD(QWidget):
    closed_by_user = Signal()

    def __init__(self):
        super().__init__()
        self._drag_pos = QPoint()
        self._always_on_top = True
        self._click_through = False

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowOpacity(0.92)
        self._apply_window_flags()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.frame = QFrame()
        self.frame.setObjectName("HudFrame")
        self.frame.setStyleSheet("""
            QFrame#HudFrame {
                background-color: rgba(14, 14, 19, 232);
                border: 1px solid rgba(255, 46, 91, 150);
                border-radius: 12px;
            }
            QLabel#HudBrand { color: #ff2e5b; font-size: 11px; font-weight: 800; letter-spacing: 1px; background: transparent; }
            QLabel#HudKey { color: #8f8fa1; font-size: 11px; font-weight: 600; background: transparent; }
            QLabel#HudVal { color: #ffffff; font-size: 12px; font-weight: 700; font-family: "Consolas", monospace; background: transparent; }
            QPushButton#HudClose { background: transparent; color: #8f8fa1; border: none; font-size: 14px; font-weight: 700; padding: 0 4px; }
            QPushButton#HudClose:hover { color: #ff2e5b; }
        """)

        lay = QVBoxLayout(self.frame)
        lay.setContentsMargins(12, 8, 12, 10)
        lay.setSpacing(5)

        top = QHBoxLayout()
        brand = QLabel("AETHER HUD")
        brand.setObjectName("HudBrand")
        self.btn_close = QPushButton("×")
        self.btn_close.setObjectName("HudClose")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self._hide_hud)
        top.addWidget(brand)
        top.addStretch()
        top.addWidget(self.btn_close)
        lay.addLayout(top)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(4)

        self.v_cpu = QLabel("0%")
        self.v_ram = QLabel("0%")
        self.v_gpu = QLabel("N/A")
        self.v_net = QLabel("↓ 0 KB/s")
        self.v_up = QLabel("00:00:00")

        self.extra_rows = []
        for r, (k_text, val_lbl, is_extra) in enumerate([
            ("CPU", self.v_cpu, False),
            ("RAM", self.v_ram, False),
            ("GPU", self.v_gpu, False),
            ("NET", self.v_net, True),
            ("UPTIME", self.v_up, True),
        ]):
            k_lbl = QLabel(k_text)
            k_lbl.setObjectName("HudKey")
            val_lbl.setObjectName("HudVal")
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(k_lbl, r, 0)
            grid.addWidget(val_lbl, r, 1)
            if is_extra:
                self.extra_rows.append((k_lbl, val_lbl))

        lay.addLayout(grid)
        root.addWidget(self.frame)
        self.setFixedWidth(235)
        self.reset_position()

    def _hide_hud(self):
        self.hide()
        self.closed_by_user.emit()

    def _apply_window_flags(self):
        was_visible = self.isVisible()
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self._always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        if self._click_through:
            flags |= Qt.WindowTransparentForInput
        self.setWindowFlags(flags)
        if was_visible:
            self.show()

    def set_always_on_top(self, enabled: bool):
        self._always_on_top = enabled
        self._apply_window_flags()

    def set_click_through(self, enabled: bool):
        self._click_through = enabled
        self.btn_close.setVisible(not enabled)
        self._apply_window_flags()

    def set_compact_mode(self, compact: bool):
        for k_lbl, v_lbl in self.extra_rows:
            k_lbl.setVisible(not compact)
            v_lbl.setVisible(not compact)
        self.adjustSize()

    def reset_position(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.right() - self.width() - 24, geo.top() + 24)

    def update_stats(self, cpu_str: str, ram_str: str, gpu_str: str, net_str: str, uptime_str: str):
        self.v_cpu.setText(cpu_str)
        self.v_ram.setText(ram_str)
        self.v_gpu.setText(gpu_str)
        self.v_net.setText(net_str)
        self.v_up.setText(uptime_str)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self._click_through:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and not self._click_through:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
