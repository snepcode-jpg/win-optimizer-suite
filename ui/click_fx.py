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
import math
import random
import ctypes
from collections import deque
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QCursor, QRadialGradient
from PySide6.QtWidgets import QApplication, QWidget

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02


class ClickRippleOverlay(QWidget):
    """Глобальный сквозной оверлей: волны при клике + настраиваемый след за курсором."""
    def __init__(self):
        super().__init__()
        self._ripple_enabled = False
        self._trail_enabled = False

        self._lmb_was_down = False
        self._rmb_was_down = False
        self._ripples = []

        # Настройки волн клика
        self.color_lmb = QColor("#ff2e5b")
        self.color_rmb = QColor("#38bdf8")
        self.max_radius = 48
        self.duration_sec = 0.42
        self.ring_width = 2.5
        self.double_wave = True
        self.track_rmb = True

        # Настройки следа за курсором
        self.trail_style = "ribbon"   # ribbon | particles | dots | glow
        self.trail_color = QColor("#ff2e5b")
        self.trail_rainbow = False
        self.trail_length = 26        # 10..55
        self._trail_pts = deque(maxlen=60)
        self._particles = []
        self._last_pos = None
        self._glow_pos = None

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def _sync_state(self):
        active = self._ripple_enabled or self._trail_enabled
        if active:
            if not self.isVisible():
                screen = QApplication.primaryScreen()
                if screen:
                    self.setGeometry(screen.virtualGeometry())
                self.show()
            if not self._timer.isActive():
                self._timer.start(16)  # ~60 FPS
        else:
            self._timer.stop()
            self._ripples.clear()
            self._trail_pts.clear()
            self._particles.clear()
            self._last_pos = None
            self._glow_pos = None
            self.hide()

    def set_enabled(self, enabled: bool):
        """Вкл/выкл волну при клике."""
        self._ripple_enabled = enabled
        if not enabled:
            self._ripples.clear()
        self._sync_state()

    def set_trail_enabled(self, enabled: bool):
        """Вкл/выкл след за курсором."""
        self._trail_enabled = enabled
        if not enabled:
            self._trail_pts.clear()
            self._particles.clear()
            self._last_pos = None
            self._glow_pos = None
        self._sync_state()

    def set_trail_style(self, style: str):
        self.trail_style = style
        self._trail_pts.clear()
        self._particles.clear()
        self.update()

    def _get_trail_color(self, now: float, offset: float = 0.0) -> QColor:
        if self.trail_rainbow:
            hue = int((now * 180.0 + offset) % 360)
            return QColor.fromHsv(hue, 230, 255)
        return QColor(self.trail_color)

    def _spawn_ripple(self, color: QColor):
        pos = self.mapFromGlobal(QCursor.pos())
        self._ripples.append({
            "x": pos.x(),
            "y": pos.y(),
            "t0": time.perf_counter(),
            "color": QColor(color),
        })

    def _tick(self):
        now = time.perf_counter()
        needs_paint = False

        # 1. Отслеживание кликов
        if self._ripple_enabled:
            user32 = ctypes.windll.user32
            lmb_down = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
            if lmb_down and not self._lmb_was_down:
                self._spawn_ripple(self._get_trail_color(now) if self.trail_rainbow else self.color_lmb)
            self._lmb_was_down = lmb_down

            if self.track_rmb:
                rmb_down = bool(user32.GetAsyncKeyState(VK_RBUTTON) & 0x8000)
                if rmb_down and not self._rmb_was_down:
                    self._spawn_ripple(self.color_rmb)
                self._rmb_was_down = rmb_down

            if self._ripples:
                self._ripples = [r for r in self._ripples if (now - r["t0"]) < self.duration_sec]
                needs_paint = True

        # 2. Отслеживание следа за курсором
        if self._trail_enabled:
            pos = self.mapFromGlobal(QCursor.pos())
            px, py = float(pos.x()), float(pos.y())

            if self._last_pos is None:
                self._last_pos = (px, py)
                self._glow_pos = [px, py]

            dx = px - self._last_pos[0]
            dy = py - self._last_pos[1]
            dist = math.hypot(dx, dy)
            self._last_pos = (px, py)

            if self.trail_style in ("ribbon", "dots"):
                if dist > 1.0:
                    self._trail_pts.append((px, py, now))
                life = 0.16 + (self.trail_length / 100.0)
                while self._trail_pts and (
                    (now - self._trail_pts[0][2]) > life or len(self._trail_pts) > self.trail_length
                ):
                    self._trail_pts.popleft()
                if self._trail_pts:
                    needs_paint = True

            elif self.trail_style == "particles":
                if dist > 2.5:
                    count = min(3, max(1, int(dist / 12)))
                    for _ in range(count):
                        angle = random.uniform(0, math.tau)
                        spd = random.uniform(0.4, 1.8)
                        self._particles.append({
                            "x": px + random.uniform(-3, 3),
                            "y": py + random.uniform(-3, 3),
                            "vx": math.cos(angle) * spd,
                            "vy": math.sin(angle) * spd + 0.35,
                            "r": random.uniform(2.0, 4.5),
                            "t0": now,
                            "life": 0.25 + (self.trail_length / 90.0),
                            "hue_off": random.uniform(0, 60),
                        })
                if self._particles:
                    alive = []
                    for pt in self._particles:
                        if (now - pt["t0"]) < pt["life"]:
                            pt["x"] += pt["vx"]
                            pt["y"] += pt["vy"]
                            pt["vx"] *= 0.96
                            pt["vy"] *= 0.96
                            alive.append(pt)
                    self._particles = alive
                    needs_paint = True

            elif self.trail_style == "glow":
                self._glow_pos[0] += (px - self._glow_pos[0]) * 0.28
                self._glow_pos[1] += (py - self._glow_pos[1]) * 0.28
                needs_paint = True

        if needs_paint:
            self.update()

    def paintEvent(self, event):
        if not (self._ripples or self._trail_pts or self._particles or (self._trail_enabled and self.trail_style == "glow")):
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        now = time.perf_counter()

        #ОТРИСОВКА СЛЕДА 
        if self._trail_enabled:
            if self.trail_style == "ribbon" and len(self._trail_pts) >= 2:
                pts = list(self._trail_pts)
                n = len(pts)
                for i in range(1, n):
                    t = i / n
                    col = self._get_trail_color(now, i * 8.0)
                    col.setAlpha(int(220 * t))
                    pen = QPen(col, max(1.0, t * 7.5))
                    pen.setCapStyle(Qt.RoundCap)
                    painter.setPen(pen)
                    painter.drawLine(QPointF(pts[i - 1][0], pts[i - 1][1]), QPointF(pts[i][0], pts[i][1]))

            elif self.trail_style == "dots" and self._trail_pts:
                pts = list(self._trail_pts)
                n = len(pts)
                painter.setPen(Qt.NoPen)
                for i, (x, y, _) in enumerate(pts):
                    t = (i + 1) / n
                    col = self._get_trail_color(now, i * 10.0)
                    col.setAlpha(int(210 * t))
                    painter.setBrush(col)
                    rad = 1.5 + t * 5.0
                    painter.drawEllipse(QPointF(x, y), rad, rad)

            elif self.trail_style == "particles" and self._particles:
                painter.setPen(Qt.NoPen)
                for pt in self._particles:
                    p = (now - pt["t0"]) / pt["life"]
                    if p >= 1.0:
                        continue
                    col = self._get_trail_color(now, pt["hue_off"])
                    col.setAlpha(int(230 * (1.0 - p)))
                    painter.setBrush(col)
                    rad = max(0.5, pt["r"] * (1.0 - p * 0.6))
                    painter.drawEllipse(QPointF(pt["x"], pt["y"]), rad, rad)

            elif self.trail_style == "glow" and self._glow_pos:
                gx, gy = self._glow_pos
                rad = 16.0 + self.trail_length * 1.1
                col = self._get_trail_color(now)
                grad = QRadialGradient(gx, gy, rad)
                c1 = QColor(col)
                c1.setAlpha(125)
                c2 = QColor(col)
                c2.setAlpha(0)
                grad.setColorAt(0.0, c1)
                grad.setColorAt(1.0, c2)
                painter.setPen(Qt.NoPen)
                painter.setBrush(grad)
                painter.drawEllipse(QPointF(gx, gy), rad, rad)

        #ОТРИСОВКА ВОЛН КЛИКА
        for r in self._ripples:
            progress = (now - r["t0"]) / self.duration_sec
            if progress >= 1.0:
                continue
            ease = 1.0 - (1.0 - progress) ** 3
            radius = 6.0 + ease * self.max_radius
            alpha = int(230 * (1.0 - progress))

            c = QColor(r["color"])
            c.setAlpha(max(0, alpha))
            painter.setPen(QPen(c, self.ring_width))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(int(r["x"] - radius), int(r["y"] - radius), int(radius * 2), int(radius * 2))

            if self.double_wave and progress > 0.15:
                p2 = (progress - 0.15) / 0.85
                ease2 = 1.0 - (1.0 - p2) ** 3
                rad2 = 4.0 + ease2 * (self.max_radius * 0.65)
                c2 = QColor(r["color"])
                c2.setAlpha(max(0, int(160 * (1.0 - p2))))
                painter.setPen(QPen(c2, max(1.2, self.ring_width - 1.0)))
                painter.drawEllipse(int(r["x"] - rad2), int(r["y"] - rad2), int(rad2 * 2), int(rad2 * 2))
