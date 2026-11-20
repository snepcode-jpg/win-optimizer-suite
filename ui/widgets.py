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

from collections import deque
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QAbstractAnimation,
    Property, QTimer, QPointF, QRectF, Signal, QSize
)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath
from PySide6.QtWidgets import (
    QWidget, QAbstractButton, QProgressBar, QStackedWidget,
    QGraphicsOpacityEffect, QLabel, QFrame, QHBoxLayout
)
from ui.styles import load_color_for_percent


def _mix(c1: QColor, c2: QColor, t: float) -> QColor:
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
    )


class SparklineWidget(QWidget):
    """Мини-график с сеткой, градиентом и выравниванием по правому краю."""
    def __init__(self, max_points: int = 60, color: str = "#ff2e5b", max_val: float | None = 100.0):
        super().__init__()
        self.maxlen = max_points
        self.data = deque(maxlen=max_points)
        self.color = QColor(color)
        self.max_val = max_val
        self.setFixedHeight(46)
        self.setMinimumWidth(80)

    def push(self, value: float, color_hex: str | None = None):
        self.data.append(max(0.0, float(value)))
        if color_hex:
            c = QColor(color_hex)
            if c != self.color:
                self.color = c
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(QPen(QColor("#1d1d26"), 1))
        p.drawLine(0, h - 1, w, h - 1)
        p.drawLine(0, h // 2, w, h // 2)

        n = len(self.data)
        if n < 2:
            return
        vmax = self.max_val if self.max_val else max(max(self.data) * 1.2, 1e-6)
        step = w / (self.maxlen - 1)
        pts = []
        for i, v in enumerate(self.data):
            x = w - (n - 1 - i) * step
            y = (h - 3) - (min(v, vmax) / vmax) * (h - 8)
            pts.append(QPointF(x, y))

        line = QPainterPath(pts[0])
        for pt in pts[1:]:
            line.lineTo(pt)

        fill = QPainterPath(line)
        fill.lineTo(QPointF(pts[-1].x(), h))
        fill.lineTo(QPointF(pts[0].x(), h))
        fill.closeSubpath()

        top = QColor(self.color)
        top.setAlpha(110)
        bottom = QColor(self.color)
        bottom.setAlpha(0)
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, top)
        grad.setColorAt(1.0, bottom)

        p.fillPath(fill, QBrush(grad))
        p.setPen(QPen(self.color, 1.7))
        p.drawPath(line)


class ToggleSwitch(QAbstractButton):
    """Переключатель в стиле iOS с плавным перетеканием цвета и ползунка."""
    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._offset = 0.0
        self._accent = QColor("#ff2e5b")
        self.setText(text)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setMinimumHeight(26)

        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.toggled.connect(self._animate)

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, v: float):
        self._offset = v
        self.update()

    offset = Property(float, _get_offset, _set_offset)

    def _animate(self, checked: bool):
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def setChecked(self, checked: bool):
        self._anim.stop()
        super().setChecked(checked)
        self._offset = 1.0 if checked else 0.0
        self.update()

    def sizeHint(self) -> QSize:
        fm = self.fontMetrics()
        tw = fm.horizontalAdvance(self.text()) if self.text() else 0
        return QSize(44 + (10 + tw if tw else 0), 26)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        tw, th = 44, 24
        y_off = (self.height() - th) / 2.0

        track = _mix(QColor("#2c2c38"), self._accent, self._offset)
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, y_off, tw, th), th / 2, th / 2)

        x = 3.0 + self._offset * (tw - th)
        p.setBrush(QColor("#ffffff") if self.isEnabled() else QColor("#888"))
        p.drawEllipse(QRectF(x, y_off + 3.0, th - 6.0, th - 6.0))

        if self.text():
            p.setPen(QColor("#e6e6eb"))
            p.drawText(
                QRectF(tw + 10, 0, self.width() - tw - 10, self.height()),
                Qt.AlignVCenter | Qt.AlignLeft,
                self.text()
            )


class AnimatedProgressBar(QProgressBar):
    """Прогресс-бар с диапазоном 0..1000 и плавной анимацией 380 мс OutCubic."""
    def __init__(self):
        super().__init__()
        self.setRange(0, 1000)
        self.setTextVisible(False)
        self.setFixedHeight(10)
        self._anim = QPropertyAnimation(self, b"value", self)
        self._anim.setDuration(380)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._last_color = ""

    def set_animated_value(self, pct: float, dynamic_color: bool = True):
        pct = max(0.0, min(100.0, float(pct)))
        end = int(pct * 10)
        if dynamic_color:
            col = load_color_for_percent(pct)
            if col != self._last_color:
                self._last_color = col
                self.setStyleSheet(
                    f"QProgressBar::chunk {{ background-color: {col}; border-radius: 5px; }}"
                )
        self._anim.stop()
        self._anim.setStartValue(self.value())
        self._anim.setEndValue(end)
        self._anim.start()


class AnimatedStackedWidget(QStackedWidget):
    """QStackedWidget с плавным fade-переходом 240 мс OutCubic."""
    def set_current_index_animated(self, index: int):
        if index == self.currentIndex():
            return
        self.setCurrentIndex(index)
        page = self.currentWidget()
        if not page:
            return
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", page)
        anim.setDuration(240)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(lambda p=page: p.setGraphicsEffect(None))
        anim.start(QAbstractAnimation.DeleteWhenStopped)


class ToastItem(QFrame):
    """Всплывающий тост с цветной полоской и fade-in / fade-out."""
    closed = Signal(object)

    def __init__(self, parent: QWidget, text: str, kind: str = "ok"):
        super().__init__(parent)
        color = {"ok": "#22c55e", "warn": "#f59e0b", "err": "#ff2e5b"}.get(kind, "#22c55e")
        self.setObjectName("Toast")
        self.setStyleSheet(
            f"QFrame#Toast {{ background-color: #1a1a22; border: 1px solid #2c2c38; "
            f"border-left: 3px solid {color}; border-radius: 10px; }}"
            f"QLabel {{ background: transparent; color: #f0f0f5; font-weight: 600; }}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        self.setFixedWidth(340)
        self.adjustSize()

        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._fade(0.0, 1.0, 200)
        QTimer.singleShot(3200, self._hide_out)
        self.show()
        self.raise_()

    def _fade(self, a: float, b: float, ms: int):
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(ms)
        self._anim.setStartValue(a)
        self._anim.setEndValue(b)
        self._anim.start()

    def _hide_out(self):
        self._fade(1.0, 0.0, 300)
        self._anim.finished.connect(self._finish)

    def _finish(self):
        self.closed.emit(self)
        self.deleteLater()


class ToastNotification:
    """Менеджер стека тостов в правом нижнем углу окна."""
    def __init__(self, host_window: QWidget):
        self.host = host_window
        self._toasts: list[ToastItem] = []

    def show_message(self, text: str, kind: str = "ok"):
        if text.startswith("⚠"):
            kind = "warn"
        t = ToastItem(self.host, text, kind)
        t.closed.connect(self._on_closed)
        self._toasts.append(t)
        self.relayout()

    def _on_closed(self, t: ToastItem):
        if t in self._toasts:
            self._toasts.remove(t)
        self.relayout()

    def relayout(self):
        y = self.host.height() - 22
        for t in reversed(self._toasts):
            y -= t.height()
            t.move(self.host.width() - t.width() - 24, y)
            y -= 10
