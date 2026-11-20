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

import math
import random
import ctypes
import logging
from ctypes import wintypes
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QRadialGradient, QFont
from PySide6.QtWidgets import QApplication, QWidget

user32 = ctypes.windll.user32

user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND

user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowExW.restype = wintypes.HWND

user32.SendMessageTimeoutW.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
    wintypes.UINT, wintypes.UINT, ctypes.POINTER(wintypes.DWORD)
]
user32.SendMessageTimeoutW.restype = wintypes.LPARAM

user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
user32.SetParent.restype = wintypes.HWND

user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.UINT
]
user32.SetWindowPos.restype = wintypes.BOOL

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SW_SHOW = 5


def _find_desktop_target() -> tuple[int, int]:
    """
    Возвращает (parent_hwnd, insert_after_hwnd).
    Поддерживает и классический WorkerW (Win10/Win11 23H2), и новый Progman (Win11 24H2+).
    """
    progman = user32.FindWindowW("Progman", None)
    if not progman:
        return 0, 0

    result = wintypes.DWORD(0)
    user32.SendMessageTimeoutW(progman, 0x052C, 0xD, 0x1, 0x0000, 1000, ctypes.byref(result))

    # 1. Windows 11 24H2+: SHELLDLL_DefView лежит напрямую внутри Progman
    shell_in_progman = user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
    if shell_in_progman:
        # Ставим наше окно внутрь Progman строго ПОЗАДИ SHELLDLL_DefView (иконок)
        return int(progman), int(shell_in_progman)

    # 2. Классический режим (Win 10 / Win 11 до 24H2): ищем соседний WorkerW
    workerw = ctypes.c_void_p(0)

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum_proc(hwnd, lparam):
        shell = user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
        if shell:
            w = user32.FindWindowExW(0, hwnd, "WorkerW", None)
            if w:
                workerw.value = w
            return False
        return True

    user32.EnumWindows(enum_proc, 0)
    if workerw.value:
        return int(workerw.value), 0

    return 0, 0


class LiveWallpaperWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._mode = "particles"  # particles | aurora | matrix
        self._accent = QColor("#ff2e5b")
        self._phase = 0.0
        self._attached = False

        # Без WindowTransparentForInput — иначе дочернее окно в Progman/WorkerW не рисуется
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self._particles = []
        self._drops = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def _init_scene(self):
        w, h = max(self.width(), 1920), max(self.height(), 1080)
        self._particles = [
            [random.uniform(0, w), random.uniform(0, h),
             random.uniform(-0.8, 0.8), random.uniform(-0.8, 0.8),
             random.uniform(1.5, 3.2)]
            for _ in range(75)
        ]
        cols = max(w // 22, 40)
        self._drops = [random.randint(-40, 0) for _ in range(cols)]

    def set_mode(self, mode: str):
        self._mode = mode
        self.update()

    def set_accent(self, hex_color: str):
        self._accent = QColor(hex_color)
        self.update()

    def start_wallpaper(self):
        screen = QApplication.primaryScreen()
        geo = screen.geometry() if screen else self.geometry()
        dpr = screen.devicePixelRatio() if screen else 1.0
        phys_w = int(geo.width() * dpr)
        phys_h = int(geo.height() * dpr)

        self.setGeometry(0, 0, geo.width(), geo.height())
        self._init_scene()

        parent_hwnd, after_hwnd = _find_desktop_target()
        logging.info(f"LiveWallpaper target: parent={parent_hwnd}, after={after_hwnd}, size={phys_w}x{phys_h}")

        if not parent_hwnd:
            self.hide()
            return

        self.show()
        my_hwnd = int(self.winId())
        user32.SetParent(my_hwnd, parent_hwnd)

        if after_hwnd:
            # Вставляем строго за иконками (SHELLDLL_DefView)
            user32.SetWindowPos(
                my_hwnd, after_hwnd, 0, 0, phys_w, phys_h,
                SWP_NOACTIVATE | SWP_SHOWWINDOW
            )
        else:
            user32.SetWindowPos(
                my_hwnd, 0, 0, 0, phys_w, phys_h,
                SWP_NOZORDER | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )

        user32.ShowWindow(my_hwnd, SW_SHOW)
        self._attached = True
        self._timer.start(33)  # ~30 FPS

    def stop_wallpaper(self):
        self._timer.stop()
        if self._attached:
            user32.SetParent(int(self.winId()), 0)
            self._attached = False
        self.hide()
        user32.SystemParametersInfoW(0x0014, 0, None, 0x02)

    def _tick(self):
        self._phase += 0.025
        w, h = self.width(), self.height()

        if self._mode == "particles":
            for p in self._particles:
                p[0] += p[2]
                p[1] += p[3]
                if p[0] < 0 or p[0] > w:
                    p[2] *= -1
                if p[1] < 0 or p[1] > h:
                    p[3] *= -1
        elif self._mode == "matrix":
            max_rows = max(h // 22, 30)
            for i in range(len(self._drops)):
                self._drops[i] += 1
                if self._drops[i] > max_rows and random.random() > 0.94:
                    self._drops[i] = random.randint(-15, 0)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor("#07070a"))

        if self._mode == "particles":
            self._draw_particles(painter)
        elif self._mode == "aurora":
            self._draw_aurora(painter, w, h)
        elif self._mode == "matrix":
            self._draw_matrix(painter)

    def _draw_particles(self, painter: QPainter):
        c_line = QColor(self._accent)
        for i, p1 in enumerate(self._particles):
            for p2 in self._particles[i + 1:]:
                dx, dy = p1[0] - p2[0], p1[1] - p2[1]
                dist2 = dx * dx + dy * dy
                if dist2 < 160 * 160:
                    alpha = int(130 * (1.0 - math.sqrt(dist2) / 160.0))
                    c_line.setAlpha(max(0, alpha))
                    painter.setPen(QPen(c_line, 1.1))
                    painter.drawLine(QPointF(p1[0], p1[1]), QPointF(p2[0], p2[1]))

        painter.setPen(Qt.NoPen)
        c_dot = QColor(self._accent)
        c_dot.setAlpha(210)
        painter.setBrush(c_dot)
        for p in self._particles:
            painter.drawEllipse(QPointF(p[0], p[1]), p[4], p[4])

    def _draw_aurora(self, painter: QPainter, w: int, h: int):
        blobs = [
            (w * (0.3 + 0.18 * math.sin(self._phase)), h * (0.4 + 0.12 * math.cos(self._phase * 0.7)), self._accent),
            (w * (0.7 + 0.15 * math.cos(self._phase * 0.8)), h * (0.55 + 0.15 * math.sin(self._phase * 0.6)), QColor("#38bdf8")),
            (w * (0.5 + 0.2 * math.sin(self._phase * 0.5)), h * (0.75 + 0.1 * math.cos(self._phase)), QColor("#8b5cf6")),
        ]
        painter.setPen(Qt.NoPen)
        for bx, by, col in blobs:
            rad = max(w, h) * 0.42
            grad = QRadialGradient(bx, by, rad)
            c1 = QColor(col)
            c1.setAlpha(95)
            c2 = QColor(col)
            c2.setAlpha(0)
            grad.setColorAt(0.0, c1)
            grad.setColorAt(1.0, c2)
            painter.setBrush(grad)
            painter.drawEllipse(QPointF(bx, by), rad, rad)

    def _draw_matrix(self, painter: QPainter):
        painter.setFont(QFont("Consolas", 13, QFont.Bold))
        chars = "01AETHER<>/{}[]#*"
        for i, row in enumerate(self._drops):
            x = i * 22
            for tail in range(10):
                y = (row - tail) * 22
                if y < 0 or y > self.height():
                    continue
                c = QColor("#ffffff") if tail == 0 else QColor(self._accent)
                c.setAlpha(max(20, 230 - tail * 22))
                painter.setPen(c)
                ch = chars[(i + row - tail) % len(chars)]
                painter.drawText(x, y, ch)
