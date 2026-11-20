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

import datetime
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QFrame, QLabel


DAYS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]


class GlassClockWidget(QWidget):
    """Виджет часов и даты в стиле Rainmeter / Liquid Glass."""
    def __init__(self):
        super().__init__()
        self._drag_pos = QPoint()
        self._always_on_top = False
        self._accent = "#ff2e5b"

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._apply_flags()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame()
        self.card.setObjectName("GlassClockCard")
        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(4)

        self.lbl_time = QLabel("00:00:00")
        self.lbl_time.setAlignment(Qt.AlignCenter)
        self.lbl_date = QLabel("")
        self.lbl_date.setAlignment(Qt.AlignCenter)

        lay.addWidget(self.lbl_time)
        lay.addWidget(self.lbl_date)
        root.addWidget(self.card)

        self._apply_style()
        self.setFixedWidth(290)
        self.reset_position()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_clock)
        self._timer.start(500)
        self._update_clock()

    def _apply_style(self):
        self.card.setStyleSheet(f"""
            QFrame#GlassClockCard {{
                background-color: rgba(18, 18, 26, 170);
                border: 1px solid rgba(255, 255, 255, 42);
                border-top: 1px solid rgba(255, 255, 255, 78);
                border-radius: 18px;
            }}
        """)
        self.lbl_time.setStyleSheet(f"""
            color: #ffffff;
            font-family: "Segoe UI", "Inter", sans-serif;
            font-size: 40px;
            font-weight: 800;
            letter-spacing: 2px;
            background: transparent;
        """)
        self.lbl_date.setStyleSheet(f"""
            color: {self._accent};
            font-family: "Segoe UI", "Inter", sans-serif;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.5px;
            background: transparent;
        """)

    def set_accent(self, hex_color: str):
        self._accent = hex_color
        self._apply_style()

    def _apply_flags(self):
        was_vis = self.isVisible()
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self._always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags |= Qt.WindowStaysOnBottomHint
        self.setWindowFlags(flags)
        if was_vis:
            self.show()

    def set_always_on_top(self, enabled: bool):
        self._always_on_top = enabled
        self._apply_flags()

    def reset_position(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.left() + 36, geo.top() + 36)

    def _update_clock(self):
        now = datetime.datetime.now()
        self.lbl_time.setText(now.strftime("%H:%M:%S"))
        day_name = DAYS_RU[now.weekday()]
        month_name = MONTHS_RU[now.month]
        self.lbl_date.setText(f"{day_name}, {now.day} {month_name} {now.year}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
