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

import sys
import os
import json
import time
import logging
import platform
import datetime
import multiprocessing

import psutil
from PySide6.QtCore import (
    Qt, QTimer, QSize, QPoint, QPropertyAnimation, QVariantAnimation, QEasingCurve
)
from PySide6.QtGui import QFont, QColor, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QPushButton, QLabel, QFrame, QTextEdit, QScrollArea,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QTabWidget, QSlider, QFileDialog, QLineEdit, QSystemTrayIcon, QMenu,
    QColorDialog, QSizeGrip
)

from core.engine import WindowsTweaker, PROTECTED_PROCESSES
from core.workers import GpuWorker, BenchmarkWorker, SessionHistoryWorker, DiskAnalyzerWorker
from core.cursor import CursorManager
from ui.styles import build_stylesheet, make_svg_icon, load_color_for_percent
from ui.widgets import (
    SparklineWidget, ToggleSwitch, AnimatedProgressBar,
    AnimatedStackedWidget, ToastNotification
)
from ui.hud import DesktopHUD
from ui.click_fx import ClickRippleOverlay
from ui.live_wallpaper import LiveWallpaperWindow
from ui.keystroke_osd import KeystrokeOSD
from ui.desktop_widgets import GlassClockWidget

logging.basicConfig(
    filename=os.path.join(os.path.dirname(__file__), "aether.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)


class CustomTitleBar(QFrame):
    """Кастомная шапка окна без стандартной рамки Windows."""
    def __init__(self, parent_win: QMainWindow):
        super().__init__(parent_win)
        self.parent_win = parent_win
        self._drag_pos = QPoint()
        self.setObjectName("TitleBar")
        self.setFixedHeight(36)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 0, 0)
        lay.setSpacing(6)

        lbl = QLabel("AETHER SUITE v2.5  //  WINDOWS OPTIMIZER & CUSTOMIZER")
        lbl.setObjectName("TitleText")
        lay.addWidget(lbl)
        lay.addStretch()

        btn_min = QPushButton("—")
        btn_min.setObjectName("WinBtn")
        btn_min.clicked.connect(parent_win.showMinimized)

        self.btn_max = QPushButton("□")
        self.btn_max.setObjectName("WinBtn")
        self.btn_max.clicked.connect(self._toggle_max)

        btn_close = QPushButton("×")
        btn_close.setObjectName("WinCloseBtn")
        btn_close.clicked.connect(parent_win.close)

        lay.addWidget(btn_min)
        lay.addWidget(self.btn_max)
        lay.addWidget(btn_close)

    def _toggle_max(self):
        if self.parent_win.isMaximized():
            self.parent_win.showNormal()
            self.btn_max.setText("□")
        else:
            self.parent_win.showMaximized()
            self.btn_max.setText("❐")

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_max()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.parent_win.isMaximized():
            self._drag_pos = event.globalPosition().toPoint() - self.parent_win.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and not self.parent_win.isMaximized():
            self.parent_win.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


class WinOptimizerApp(QMainWindow):
    SIDEBAR_FULL = 240
    SIDEBAR_MINI = 68

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setWindowTitle("AETHER SUITE v2.5")
        self.resize(1260, 800)
        self.setMinimumSize(1020, 660)

        self.current_theme = "crimson"
        self.current_accent = "#ff2e5b"
        self.prev_net = psutil.net_io_counters()
        self.prev_time = time.time()
        self.last_gpu_str = "N/A"
        self.bench_worker = None
        self.session_worker = None
        self.disk_worker = None
        self.sidebar_collapsed = False
        self._sb_anim = None
        self._ind_anim = None

        self.hud = DesktopHUD()
        self.hud.closed_by_user.connect(lambda: self._sync_hud_buttons(False))
        self.click_fx = ClickRippleOverlay()
        self.live_wp = LiveWallpaperWindow()
        self.key_osd = KeystrokeOSD()
        self.glass_clock = GlassClockWidget()

        self._build_ui()
        self._setup_tray()
        self.toast = ToastNotification(self)

        for p in psutil.process_iter():
            try:
                p.cpu_percent(None)
            except Exception:
                pass

        self.gpu_worker = GpuWorker()
        self.gpu_worker.gpu_data.connect(self._on_gpu_data)
        self.gpu_worker.start()

        self.mon_timer = QTimer(self)
        self.mon_timer.timeout.connect(self._update_metrics)
        self.mon_timer.start(1000)
        self._update_metrics()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "toast"):
            self.toast.relayout()

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(make_svg_icon("bench", "#ff2e5b", 22), self)
        menu = QMenu()
        act_show = QAction("Открыть Aether Suite", self)
        act_show.triggered.connect(self.showNormal)
        act_hud = QAction("Вкл / Выкл HUD", self)
        act_hud.triggered.connect(self._toggle_hud)
        act_fx = QAction("Вкл / Выкл Волну кликов", self)
        act_fx.triggered.connect(lambda: self.sw_click_fx.setChecked(not self.sw_click_fx.isChecked()))
        act_trail = QAction("Вкл / Выкл След за курсором", self)
        act_trail.triggered.connect(lambda: self.sw_trail_fx.setChecked(not self.sw_trail_fx.isChecked()))
        act_quit = QAction("Выход", self)
        act_quit.triggered.connect(self._quit_app)
        menu.addAction(act_show)
        menu.addAction(act_hud)
        menu.addAction(act_fx)
        menu.addAction(act_trail)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda r: self.showNormal() if r == QSystemTrayIcon.DoubleClick else None)
        self.tray.show()

    def _quit_app(self):
        self.gpu_worker.stop()
        self.gpu_worker.wait(500)
        self.hud.close()
        self.click_fx.set_enabled(False)
        self.click_fx.set_trail_enabled(False)
        self.click_fx.close()
        self.live_wp.stop_wallpaper()
        self.key_osd.set_enabled(False)
        self.key_osd.close()
        self.glass_clock.close()
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage("AETHER SUITE", "Свёрнуто в системный трей. Двойной клик — открыть.", QSystemTrayIcon.Information, 2000)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        outer.addWidget(self.title_bar)

        body = QWidget()
        root_layout = QHBoxLayout(body)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- БОКОВАЯ ПАНЕЛЬ ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(self.SIDEBAR_FULL)
        self.sb_layout = QVBoxLayout(self.sidebar)
        self.sb_layout.setContentsMargins(14, 14, 14, 12)
        self.sb_layout.setSpacing(5)

        brand_row = QHBoxLayout()
        self.lbl_brand = QLabel("AETHER v2.5")
        self.lbl_brand.setObjectName("BrandTitle")
        btn_collapse = QPushButton()
        btn_collapse.setObjectName("NavBtn")
        btn_collapse.setIcon(make_svg_icon("menu", "#a6a6b5", 20))
        btn_collapse.setIconSize(QSize(20, 20))
        btn_collapse.setFixedSize(36, 34)
        btn_collapse.setCursor(Qt.PointingHandCursor)
        btn_collapse.setToolTip("Свернуть / развернуть панель")
        btn_collapse.clicked.connect(self._toggle_sidebar)
        brand_row.addWidget(self.lbl_brand)
        brand_row.addStretch()
        brand_row.addWidget(btn_collapse)
        self.sb_layout.addLayout(brand_row)
        self.sb_layout.addSpacing(8)

        self.nav_buttons = []
        self.nav_meta = [
            ("Статистика ПК", "stats", 0),
            ("Шаблоны", "presets", 1),
            ("Твики и Кастом", "tweaks", 2),
            ("Автозагрузка и Службы", "startup", 3),
            ("Диск и Сеть", "disk", 4),
            ("Бенчмарк", "bench", 5),
            ("Сессии и Процессы", "sessions", 6),
            ("HUD Оверлей", "hud", 7),
            ("Курсор и Клики", "cursor", 8),
            ("Визуал и Обои", "visuals", 9),
        ]
        for label, icon_key, idx in self.nav_meta:
            btn = QPushButton(f"  {label}")
            btn.setObjectName("NavBtn")
            btn.setToolTip(label)
            btn.setIcon(make_svg_icon(icon_key, "#a6a6b5", 20))
            btn.setIconSize(QSize(20, 20))
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, i=idx: self._switch_page(i))
            self.sb_layout.addWidget(btn)
            self.nav_buttons.append((btn, label, icon_key))

        self.sb_layout.addStretch()

        self.sb_hud_btn = QPushButton("Включить HUD")
        self.sb_hud_btn.setObjectName("PrimaryBtn")
        self.sb_hud_btn.setCursor(Qt.PointingHandCursor)
        self.sb_hud_btn.clicked.connect(self._toggle_hud)
        self.sb_layout.addWidget(self.sb_hud_btn)

        is_adm = WindowsTweaker.is_admin()
        self.admin_label = QLabel("Администратор" if is_adm else "Обычный юзер")
        self.admin_label.setAlignment(Qt.AlignCenter)
        self.admin_label.setStyleSheet(
            "color: #22c55e; font-weight: 700; font-size: 12px;"
            if is_adm else "color: #f59e0b; font-weight: 700; font-size: 12px;"
        )
        self.sb_layout.addWidget(self.admin_label)

        self.adm_btn = None
        if not is_adm:
            self.adm_btn = QPushButton("От Админа")
            self.adm_btn.setObjectName("SecondaryBtn")
            self.adm_btn.clicked.connect(self._elevate_admin)
            self.sb_layout.addWidget(self.adm_btn)

        self.nav_indicator = QFrame(self.sidebar)
        self.nav_indicator.setObjectName("NavIndicator")
        self.nav_indicator.setFixedSize(3, 22)
        self.nav_indicator.move(0, -40)
        self.nav_indicator.raise_()

        # --- СТРАНИЦЫ ---
        self.stack = AnimatedStackedWidget()
        self.stack.addWidget(self._build_dashboard_page())
        self.stack.addWidget(self._build_presets_page())
        self.stack.addWidget(self._build_tweaks_page())
        self.stack.addWidget(self._build_startup_services_page())
        self.stack.addWidget(self._build_disk_net_page())
        self.stack.addWidget(self._build_benchmark_page())
        self.stack.addWidget(self._build_sessions_page())
        self.stack.addWidget(self._build_hud_page())
        self.stack.addWidget(self._build_cursor_fx_page())
        self.stack.addWidget(self._build_visuals_page())

        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(self.stack, 1)
        outer.addWidget(body, 1)

        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 2, 2)
        grip_row.addStretch()
        grip_row.addWidget(QSizeGrip(self))
        outer.addLayout(grip_row)

        self._switch_page(0)
        QTimer.singleShot(0, lambda: self._move_indicator(False))

    def _move_indicator(self, animated: bool):
        btn = self.nav_buttons[self.stack.currentIndex()][0]
        target = QPoint(0, btn.y() + (btn.height() - self.nav_indicator.height()) // 2)
        self.nav_indicator.raise_()
        if animated and self.nav_indicator.y() >= 0:
            self._ind_anim = QPropertyAnimation(self.nav_indicator, b"pos", self)
            self._ind_anim.setDuration(260)
            self._ind_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._ind_anim.setEndValue(target)
            self._ind_anim.start()
        else:
            self.nav_indicator.move(target)

    def _toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        collapsed = self.sidebar_collapsed
        start = self.sidebar.width()
        end = self.SIDEBAR_MINI if collapsed else self.SIDEBAR_FULL

        for w in (self.lbl_brand, self.admin_label, self.adm_btn):
            if w is not None:
                w.setVisible(not collapsed)
        if collapsed:
            self.sb_layout.setContentsMargins(10, 14, 10, 12)
            self.sb_hud_btn.setText("HUD")
            for btn, _, _ in self.nav_buttons:
                btn.setText("")

        self._sb_anim = QVariantAnimation(self)
        self._sb_anim.setDuration(220)
        self._sb_anim.setStartValue(start)
        self._sb_anim.setEndValue(end)
        self._sb_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._sb_anim.valueChanged.connect(lambda v: self.sidebar.setFixedWidth(int(v)))
        self._sb_anim.finished.connect(self._after_sidebar_anim)
        self._sb_anim.start()

    def _after_sidebar_anim(self):
        if not self.sidebar_collapsed:
            self.sb_layout.setContentsMargins(14, 14, 14, 12)
            self.sb_hud_btn.setText("Скрыть HUD" if self.hud.isVisible() else "Включить HUD")
            for btn, label, _ in self.nav_buttons:
                btn.setText(f"  {label}")
        QTimer.singleShot(0, lambda: self._move_indicator(False))

    def _switch_page(self, index: int):
        self.stack.set_current_index_animated(index)
        active_col = "#ffffff" if self.current_theme == "monochrome" else self.current_accent
        for i, (btn, _, icon_key) in enumerate(self.nav_buttons):
            active = (i == index)
            btn.setProperty("active", "true" if active else "false")
            btn.setIcon(make_svg_icon(icon_key, active_col if active else "#a6a6b5", 20))
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._move_indicator(True)
        if index == 2:
            self._sync_tweaks_from_registry()
        elif index == 3:
            self._refresh_startup_and_services()
        elif index == 6:
            self._refresh_sessions_all()

    def _elevate_admin(self):
        WindowsTweaker.run_as_admin(sys.argv)
        self._quit_app()

    def _make_card(self, title_text: str = "") -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        if title_text:
            lbl = QLabel(title_text)
            lbl.setObjectName("CardTitle")
            lay.addWidget(lbl)
        return card, lay

    # =================================================================
    # 0. ДАШБОРД
    # =================================================================
    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 14)
        layout.setSpacing(14)

        top = QHBoxLayout()
        header = QLabel("Статистика ПК в реальном времени")
        header.setObjectName("PageTitle")
        btn_report = QPushButton("Экспорт HTML-отчёта")
        btn_report.setObjectName("SecondaryBtn")
        btn_report.clicked.connect(self._export_html_report)
        top.addWidget(header)
        top.addStretch()
        top.addWidget(btn_report)
        layout.addLayout(top)

        grid = QGridLayout()
        grid.setSpacing(14)

        c_cpu, l_cpu = self._make_card("Процессор (CPU)")
        self.lbl_cpu_val = QLabel("0%")
        self.lbl_cpu_val.setObjectName("MetricValue")
        self.pb_cpu = AnimatedProgressBar()
        self.sp_cpu = SparklineWidget(60, "#22c55e", 100.0)
        self.lbl_cpu_sub = QLabel("")
        self.lbl_cpu_sub.setObjectName("Muted")
        for w in (self.lbl_cpu_val, self.pb_cpu, self.sp_cpu, self.lbl_cpu_sub):
            l_cpu.addWidget(w)
        grid.addWidget(c_cpu, 0, 0)

        c_ram, l_ram = self._make_card("Оперативная память (RAM)")
        self.lbl_ram_val = QLabel("0%")
        self.lbl_ram_val.setObjectName("MetricValue")
        self.pb_ram = AnimatedProgressBar()
        self.sp_ram = SparklineWidget(60, "#22c55e", 100.0)
        self.lbl_ram_sub = QLabel("")
        self.lbl_ram_sub.setObjectName("Muted")
        for w in (self.lbl_ram_val, self.pb_ram, self.sp_ram, self.lbl_ram_sub):
            l_ram.addWidget(w)
        grid.addWidget(c_ram, 0, 1)

        c_gpu, l_gpu = self._make_card("Видеокарта (GPU)")
        self.lbl_gpu_val = QLabel("Опрос...")
        self.lbl_gpu_val.setObjectName("MetricValue")
        self.pb_gpu = AnimatedProgressBar()
        self.sp_gpu = SparklineWidget(60, "#22c55e", 100.0)
        self.lbl_gpu_sub = QLabel("Асинхронный мониторинг")
        self.lbl_gpu_sub.setObjectName("Muted")
        for w in (self.lbl_gpu_val, self.pb_gpu, self.sp_gpu, self.lbl_gpu_sub):
            l_gpu.addWidget(w)
        grid.addWidget(c_gpu, 0, 2)

        c_disk, l_disk = self._make_card("Системный диск (C:)")
        self.lbl_disk_val = QLabel("0%")
        self.lbl_disk_val.setObjectName("MetricValue")
        self.pb_disk = AnimatedProgressBar()
        self.lbl_disk_sub = QLabel("")
        self.lbl_disk_sub.setObjectName("Muted")
        for w in (self.lbl_disk_val, self.pb_disk, self.lbl_disk_sub):
            l_disk.addWidget(w)
        l_disk.addStretch()
        grid.addWidget(c_disk, 1, 0)

        c_net, l_net = self._make_card("Сеть (Входящий трафик)")
        self.lbl_net_val = QLabel("↓ 0 КБ/с")
        self.lbl_net_val.setObjectName("MetricValue")
        self.sp_net = SparklineWidget(60, "#38bdf8", None)
        self.lbl_net_sub = QLabel("")
        self.lbl_net_sub.setObjectName("Muted")
        for w in (self.lbl_net_val, self.sp_net, self.lbl_net_sub):
            l_net.addWidget(w)
        grid.addWidget(c_net, 1, 1)

        c_sys, l_sys = self._make_card("Система и Аптайм")
        self.lbl_uptime = QLabel("00:00:00")
        self.lbl_uptime.setObjectName("MetricValue")
        self.lbl_uptime.setStyleSheet("color: #ffffff;")
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})\nХост: {platform.node()}"
        lbl_os = QLabel(os_info)
        lbl_os.setObjectName("Muted")
        l_sys.addWidget(self.lbl_uptime)
        l_sys.addWidget(lbl_os)
        l_sys.addStretch()
        grid.addWidget(c_sys, 1, 2)

        layout.addLayout(grid)

        c_q, l_q = self._make_card("Быстрые действия и Безопасность")
        row = QHBoxLayout()
        for text, style, fn in [
            ("Очистить Temp", "PrimaryBtn", self._confirm_clean_temp),
            ("Откатить последний твик", "SecondaryBtn", self._do_restore_backup),
            ("Точка восстановления", "SecondaryBtn", self._do_restore_point),
            ("Перезапустить Explorer", "SecondaryBtn", lambda: self._toast_call(WindowsTweaker.restart_explorer)),
        ]:
            b = QPushButton(text)
            b.setObjectName(style)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch()
        l_q.addLayout(row)
        layout.addWidget(c_q)
        layout.addStretch()
        return page

    def _on_gpu_data(self, ok: bool, name: str, util: int, mem_str: str, temp_str: str):
        if ok:
            col = load_color_for_percent(util)
            self.last_gpu_str = f"{util}% | {temp_str}"
            self.lbl_gpu_val.setText(self.last_gpu_str)
            self.lbl_gpu_val.setStyleSheet(f"color: {col};")
            self.pb_gpu.set_animated_value(util)
            self.sp_gpu.push(util, col)
            self.lbl_gpu_sub.setText(f"{name} ({mem_str})")
        else:
            self.last_gpu_str = "N/A"
            self.lbl_gpu_val.setText("N/A")
            self.lbl_gpu_val.setStyleSheet("color: #8e8e9e;")
            self.pb_gpu.set_animated_value(0)
            self.lbl_gpu_sub.setText(name)

    def _update_metrics(self):
        cpu_pct = psutil.cpu_percent(interval=None)
        cpu_col = load_color_for_percent(cpu_pct)
        freq = psutil.cpu_freq()
        self.lbl_cpu_val.setText(f"{cpu_pct:.1f}%")
        self.lbl_cpu_val.setStyleSheet(f"color: {cpu_col};")
        self.pb_cpu.set_animated_value(cpu_pct)
        self.sp_cpu.push(cpu_pct, cpu_col)
        self.lbl_cpu_sub.setText(f"{psutil.cpu_count(logical=False)}P/{psutil.cpu_count()}L • {freq.current:.0f} МГц" if freq else "")

        ram = psutil.virtual_memory()
        ram_col = load_color_for_percent(ram.percent)
        self.lbl_ram_val.setText(f"{ram.percent:.1f}%")
        self.lbl_ram_val.setStyleSheet(f"color: {ram_col};")
        self.pb_ram.set_animated_value(ram.percent)
        self.sp_ram.push(ram.percent, ram_col)
        self.lbl_ram_sub.setText(f"{ram.used / (1024**3):.2f} / {ram.total / (1024**3):.2f} ГБ")

        try:
            disk = psutil.disk_usage("C:\\")
            d_col = load_color_for_percent(disk.percent)
            self.lbl_disk_val.setText(f"{disk.percent:.1f}%")
            self.lbl_disk_val.setStyleSheet(f"color: {d_col};")
            self.pb_disk.set_animated_value(disk.percent)
            self.lbl_disk_sub.setText(f"Свободно {disk.free / (1024**3):.1f} из {disk.total / (1024**3):.1f} ГБ")
        except Exception:
            pass

        now = time.time()
        dt = max(now - self.prev_time, 0.1)
        net = psutil.net_io_counters()
        down_kbs = (net.bytes_recv - self.prev_net.bytes_recv) / 1024 / dt
        up_kbs = (net.bytes_sent - self.prev_net.bytes_sent) / 1024 / dt
        self.prev_net, self.prev_time = net, now
        down_str = f"{down_kbs/1024:.2f} МБ/с" if down_kbs > 1024 else f"{down_kbs:.0f} КБ/с"
        up_str = f"{up_kbs/1024:.2f} МБ/с" if up_kbs > 1024 else f"{up_kbs:.0f} КБ/с"
        self.lbl_net_val.setText(f"↓ {down_str}")
        self.lbl_net_val.setStyleSheet("color: #38bdf8;")
        self.sp_net.push(down_kbs, "#38bdf8")
        self.lbl_net_sub.setText(f"↑ {up_str} • Всего: {(net.bytes_recv + net.bytes_sent)/(1024**3):.2f} ГБ")

        up_sec = int(time.time() - psutil.boot_time())
        hrs, rem = divmod(up_sec, 3600)
        mins, secs = divmod(rem, 60)
        up_str_t = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        self.lbl_uptime.setText(up_str_t)

        if self.hud.isVisible():
            self.hud.update_stats(
                f"{cpu_pct:.1f}%", f"{ram.percent:.0f}% ({ram.used/(1024**3):.1f}G)",
                self.last_gpu_str, f"↓{down_str}", up_str_t
            )

    def _toast_call(self, fn):
        ok, msg = fn()
        self.toast.show_message(msg, "ok" if ok else "warn")

    def _confirm_clean_temp(self):
        cnt, mb = WindowsTweaker.scan_temp_files()
        ans = QMessageBox.question(self, "Очистка Temp", f"Найдено временных файлов: {cnt} (~{mb:.1f} МБ).\nУдалить доступные файлы?")
        if ans == QMessageBox.Yes:
            self._toast_call(WindowsTweaker.clean_temp_files)

    def _do_restore_backup(self):
        ok, logs = WindowsTweaker.restore_backup()
        self.toast.show_message("Настройки откачены к бэкапу!" if ok else logs[0], "ok" if ok else "warn")
        if hasattr(self, "preset_log"):
            self.preset_log.append("\n=== Откат настроек ===\n" + "\n".join(logs))

    def _do_restore_point(self):
        self.toast.show_message("Создание точки восстановления...", "warn")
        QApplication.processEvents()
        self._toast_call(WindowsTweaker.create_restore_point)

    # =================================================================
    # 1. ШАБЛОНЫ
    # =================================================================
    def _build_presets_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 14)
        layout.setSpacing(12)

        top = QHBoxLayout()
        header = QLabel("Готовые шаблоны (с автобэкапом перед применением)")
        header.setObjectName("PageTitle")
        btn_undo = QPushButton("Откатить последнее")
        btn_undo.setObjectName("SecondaryBtn")
        btn_undo.clicked.connect(self._do_restore_backup)
        top.addWidget(header)
        top.addStretch()
        top.addWidget(btn_undo)
        layout.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget()
        grid = QGridLayout(cont)
        grid.setSpacing(14)

        presets = [
            ("Гейминг (Max FPS)", "Схема питания Ultimate, отключение GameDVR, Raw Input мыши, отключение прозрачности и телеметрии, меню 0 мс, сброс DNS.", [
                lambda: WindowsTweaker.set_power_plan("ultimate"),
                lambda: WindowsTweaker.set_game_dvr(True),
                lambda: WindowsTweaker.set_mouse_acceleration(True),
                lambda: WindowsTweaker.set_transparency(False),
                lambda: WindowsTweaker.set_telemetry(True),
                lambda: WindowsTweaker.set_menu_delay(0),
                WindowsTweaker.flush_dns,
            ]),
            ("Программирование (Dev)", "Режим разработчика, расширения файлов, скрытые папки, тёмная тема, история буфера (Win+V), без Bing, High Performance.", [
                lambda: WindowsTweaker.set_developer_mode(True),
                lambda: WindowsTweaker.set_show_extensions(True),
                lambda: WindowsTweaker.set_show_hidden(True),
                lambda: WindowsTweaker.set_dark_mode(True),
                lambda: WindowsTweaker.set_clipboard_history(True),
                lambda: WindowsTweaker.set_bing_search(True),
                lambda: WindowsTweaker.set_power_plan("high"),
            ]),
            ("Многозадачность", "Balanced питание, история буфера, панель задач слева, расширения файлов, ускоренные меню (50 мс), без Bing.", [
                lambda: WindowsTweaker.set_power_plan("balanced"),
                lambda: WindowsTweaker.set_clipboard_history(True),
                lambda: WindowsTweaker.set_taskbar_align("left"),
                lambda: WindowsTweaker.set_show_extensions(True),
                lambda: WindowsTweaker.set_menu_delay(50),
                lambda: WindowsTweaker.set_bing_search(True),
            ]),
            ("Стрим / Запись", "High Performance, отключение GameDVR (для OBS), отключение телеметрии, тёмная тема, сброс DNS.", [
                lambda: WindowsTweaker.set_power_plan("high"),
                lambda: WindowsTweaker.set_game_dvr(True),
                lambda: WindowsTweaker.set_telemetry(True),
                lambda: WindowsTweaker.set_dark_mode(True),
                WindowsTweaker.flush_dns,
            ]),
            ("Тихий / Минимализм", "Power Saver, отключение прозрачности и эффектов, тёмная тема, без телеметрии и Bing.", [
                lambda: WindowsTweaker.set_power_plan("saver"),
                lambda: WindowsTweaker.set_transparency(False),
                lambda: WindowsTweaker.set_visual_performance(True),
                lambda: WindowsTweaker.set_dark_mode(True),
                lambda: WindowsTweaker.set_telemetry(True),
                lambda: WindowsTweaker.set_bing_search(True),
            ]),
            ("Сброс к стандарту Windows", "Balanced питание, стандартные эффекты, панель задач по центру, возврат GameDVR и ускорения мыши.", [
                lambda: WindowsTweaker.set_power_plan("balanced"),
                lambda: WindowsTweaker.set_visual_performance(False),
                lambda: WindowsTweaker.set_transparency(True),
                lambda: WindowsTweaker.set_taskbar_align("center"),
                lambda: WindowsTweaker.set_game_dvr(False),
                lambda: WindowsTweaker.set_mouse_acceleration(False),
                lambda: WindowsTweaker.set_menu_delay(400),
            ]),
        ]

        for idx, (title, desc, steps) in enumerate(presets):
            card, clay = self._make_card(title)
            lbl = QLabel(desc)
            lbl.setObjectName("Muted")
            lbl.setWordWrap(True)
            btn = QPushButton("Предпросмотр и применить")
            btn.setObjectName("PrimaryBtn" if idx < 5 else "SecondaryBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, t=title, d=desc, s=steps: self._apply_preset_with_preview(t, d, s))
            clay.addWidget(lbl)
            clay.addStretch()
            clay.addWidget(btn)
            grid.addWidget(card, idx // 2, idx % 2)

        scroll.setWidget(cont)
        layout.addWidget(scroll, 1)

        self.preset_log = QTextEdit()
        self.preset_log.setObjectName("LogBox")
        self.preset_log.setReadOnly(True)
        self.preset_log.setFixedHeight(115)
        layout.addWidget(self.preset_log)
        return page

    def _apply_preset_with_preview(self, title: str, desc: str, steps: list):
        ans = QMessageBox.question(
            self, f"Применить шаблон: {title}",
            f"Будут применены изменения:\n\n{desc}\n\nТекущие настройки автоматически сохранятся в бэкап для отката. Продолжить?"
        )
        if ans != QMessageBox.Yes:
            return
        ok_b, msg_b = WindowsTweaker.save_backup()
        self.preset_log.append(f"\n=== {title} ===\n[BACKUP] {msg_b}")
        for fn in steps:
            ok, msg = fn()
            self.preset_log.append(f"[{'OK' if ok else 'WARN'}] {msg}")
        self.toast.show_message(f"Шаблон «{title}» применён!", "ok")

    # =================================================================
    # 2. РУЧНЫЕ ТВИКИ
    # =================================================================
    def _build_tweaks_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 14)
        layout.setSpacing(12)

        top = QHBoxLayout()
        header = QLabel("Твики и Кастомизация")
        header.setObjectName("PageTitle")
        btn_save_json = QPushButton("Сохранить JSON")
        btn_save_json.setObjectName("SecondaryBtn")
        btn_save_json.clicked.connect(self._export_custom_preset)
        btn_load_json = QPushButton("Загрузить JSON")
        btn_load_json.setObjectName("SecondaryBtn")
        btn_load_json.clicked.connect(self._import_custom_preset)
        top.addWidget(header)
        top.addStretch()
        top.addWidget(btn_save_json)
        top.addWidget(btn_load_json)
        layout.addLayout(top)

        cols = QHBoxLayout()
        cols.setSpacing(14)

        c_perf, l_perf = self._make_card("Производительность")
        l_perf.addWidget(QLabel("Схема электропитания:"))
        self.combo_power = QComboBox()
        self.combo_power.addItems(["Ultimate Performance", "High Performance", "Balanced", "Power Saver"])
        l_perf.addWidget(self.combo_power)

        self.sw_telemetry = ToggleSwitch("Отключить телеметрию [Админ]")
        self.sw_gamedvr = ToggleSwitch("Отключить Xbox GameDVR")
        self.sw_mouse = ToggleSwitch("Отключить ускорение мыши (Raw)")
        self.sw_fast_fx = ToggleSwitch("Визуальные эффекты: быстродействие")
        self.sw_devmode = ToggleSwitch("Режим разработчика [Админ]")
        self.sw_menu0 = ToggleSwitch("Задержка меню 0 мс")
        for w in (self.sw_telemetry, self.sw_gamedvr, self.sw_mouse, self.sw_fast_fx, self.sw_devmode, self.sw_menu0):
            l_perf.addWidget(w)
        l_perf.addStretch()
        cols.addWidget(c_perf)

        c_cust, l_cust = self._make_card("Интерфейс и Проводник")
        l_cust.addWidget(QLabel("Панель задач (Windows 11):"))
        self.combo_taskbar = QComboBox()
        self.combo_taskbar.addItems(["По центру", "Слева"])
        l_cust.addWidget(self.combo_taskbar)

        self.sw_dark = ToggleSwitch("Тёмная тема Windows")
        self.sw_no_transp = ToggleSwitch("Отключить прозрачность (Acrylic/Mica)")
        self.sw_ext = ToggleSwitch("Показывать расширения файлов")
        self.sw_hidden = ToggleSwitch("Показывать скрытые файлы")
        self.sw_bing = ToggleSwitch("Отключить поиск Bing в Пуск")
        self.sw_clip = ToggleSwitch("История буфера обмена (Win+V)")
        for w in (self.sw_dark, self.sw_no_transp, self.sw_ext, self.sw_hidden, self.sw_bing, self.sw_clip):
            l_cust.addWidget(w)
        l_cust.addStretch()
        cols.addWidget(c_cust)

        layout.addLayout(cols)

        btn_row = QHBoxLayout()
        btn_apply = QPushButton("Применить настройки")
        btn_apply.setObjectName("PrimaryBtn")
        btn_apply.clicked.connect(self._apply_custom_tweaks)
        btn_sync = QPushButton("Обновить из реестра")
        btn_sync.setObjectName("SecondaryBtn")
        btn_sync.clicked.connect(self._sync_tweaks_from_registry)
        btn_row.addWidget(btn_apply)
        btn_row.addWidget(btn_sync)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addStretch()
        return page

    def _sync_tweaks_from_registry(self):
        s = WindowsTweaker.read_current_state()
        self.sw_dark.setChecked(s["dark_mode"])
        self.sw_no_transp.setChecked(s["no_transparency"])
        self.sw_ext.setChecked(s["show_extensions"])
        self.sw_hidden.setChecked(s["show_hidden"])
        self.combo_taskbar.setCurrentIndex(1 if s["taskbar_align"] == "left" else 0)
        self.sw_bing.setChecked(s["disable_bing"])
        self.sw_gamedvr.setChecked(s["disable_gamedvr"])
        self.sw_telemetry.setChecked(s["disable_telemetry"])
        self.sw_clip.setChecked(s["clipboard_history"])
        self.sw_devmode.setChecked(s["dev_mode"])
        self.sw_mouse.setChecked(s["disable_mouse_accel"])
        self.sw_fast_fx.setChecked(s["fast_visuals"])
        self.sw_menu0.setChecked(s["menu_delay_zero"])

    def _apply_custom_tweaks(self):
        WindowsTweaker.save_backup()
        power_map = {0: "ultimate", 1: "high", 2: "balanced", 3: "saver"}
        WindowsTweaker.set_power_plan(power_map[self.combo_power.currentIndex()])
        WindowsTweaker.set_telemetry(self.sw_telemetry.isChecked())
        WindowsTweaker.set_game_dvr(self.sw_gamedvr.isChecked())
        WindowsTweaker.set_mouse_acceleration(self.sw_mouse.isChecked())
        WindowsTweaker.set_visual_performance(self.sw_fast_fx.isChecked())
        WindowsTweaker.set_developer_mode(self.sw_devmode.isChecked())
        WindowsTweaker.set_menu_delay(0 if self.sw_menu0.isChecked() else 400)
        WindowsTweaker.set_taskbar_align("left" if self.combo_taskbar.currentIndex() == 1 else "center")
        WindowsTweaker.set_dark_mode(self.sw_dark.isChecked())
        WindowsTweaker.set_transparency(not self.sw_no_transp.isChecked())
        WindowsTweaker.set_show_extensions(self.sw_ext.isChecked())
        WindowsTweaker.set_show_hidden(self.sw_hidden.isChecked())
        WindowsTweaker.set_bing_search(self.sw_bing.isChecked())
        WindowsTweaker.set_clipboard_history(self.sw_clip.isChecked())
        self.toast.show_message("Настройки применены (бэкап сохранён)", "ok")

    def _export_custom_preset(self):
        fp, _ = QFileDialog.getSaveFileName(self, "Сохранить пресет", "my_preset.json", "JSON (*.json)")
        if not fp:
            return
        data = {
            "power_idx": self.combo_power.currentIndex(), "taskbar_idx": self.combo_taskbar.currentIndex(),
            "telemetry": self.sw_telemetry.isChecked(), "gamedvr": self.sw_gamedvr.isChecked(),
            "mouse": self.sw_mouse.isChecked(), "fast_fx": self.sw_fast_fx.isChecked(),
            "devmode": self.sw_devmode.isChecked(), "menu0": self.sw_menu0.isChecked(),
            "dark": self.sw_dark.isChecked(), "no_transp": self.sw_no_transp.isChecked(),
            "ext": self.sw_ext.isChecked(), "hidden": self.sw_hidden.isChecked(),
            "bing": self.sw_bing.isChecked(), "clip": self.sw_clip.isChecked(),
        }
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.toast.show_message("Пресет сохранён в JSON", "ok")

    def _import_custom_preset(self):
        fp, _ = QFileDialog.getOpenFileName(self, "Загрузить пресет", "", "JSON (*.json)")
        if not fp:
            return
        try:
            with open(fp, "r", encoding="utf-8") as f:
                d = json.load(f)
            self.combo_power.setCurrentIndex(d.get("power_idx", 2))
            self.combo_taskbar.setCurrentIndex(d.get("taskbar_idx", 0))
            self.sw_telemetry.setChecked(d.get("telemetry", False))
            self.sw_gamedvr.setChecked(d.get("gamedvr", False))
            self.sw_mouse.setChecked(d.get("mouse", False))
            self.sw_fast_fx.setChecked(d.get("fast_fx", False))
            self.sw_devmode.setChecked(d.get("devmode", False))
            self.sw_menu0.setChecked(d.get("menu0", False))
            self.sw_dark.setChecked(d.get("dark", False))
            self.sw_no_transp.setChecked(d.get("no_transp", False))
            self.sw_ext.setChecked(d.get("ext", False))
            self.sw_hidden.setChecked(d.get("hidden", False))
            self.sw_bing.setChecked(d.get("bing", False))
            self.sw_clip.setChecked(d.get("clip", False))
            self.toast.show_message("Пресет загружен! Нажмите «Применить».", "ok")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", str(e))

    # =================================================================
    # 3. АВТОЗАГРУЗКА И СЛУЖБЫ
    # =================================================================
    def _build_startup_services_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 14)
        layout.setSpacing(12)

        top = QHBoxLayout()
        header = QLabel("Автозагрузка и Службы Windows")
        header.setObjectName("PageTitle")
        btn_ref = QPushButton("Обновить")
        btn_ref.setObjectName("PrimaryBtn")
        btn_ref.clicked.connect(self._refresh_startup_and_services)
        top.addWidget(header)
        top.addStretch()
        top.addWidget(btn_ref)
        layout.addLayout(top)

        tabs = QTabWidget()
        self.tbl_startup = QTableWidget(0, 4)
        self.tbl_startup.setHorizontalHeaderLabels(["Программа", "Ветка", "Команда", "Статус"])
        self.tbl_startup.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_startup.setEditTriggers(QTableWidget.NoEditTriggers)
        tabs.addTab(self.tbl_startup, "Автозагрузка (Run)")

        self.tbl_services = QTableWidget(0, 4)
        self.tbl_services.setHorizontalHeaderLabels(["Служба", "Описание", "Состояние", "Действие"])
        self.tbl_services.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_services.setEditTriggers(QTableWidget.NoEditTriggers)
        tabs.addTab(self.tbl_services, "Безопасные службы")

        layout.addWidget(tabs, 1)
        return page

    def _refresh_startup_and_services(self):
        items = WindowsTweaker.get_startup_items()
        self.tbl_startup.setRowCount(0)
        for it in items:
            row = self.tbl_startup.rowCount()
            self.tbl_startup.insertRow(row)
            self.tbl_startup.setItem(row, 0, QTableWidgetItem(it["name"]))
            self.tbl_startup.setItem(row, 1, QTableWidgetItem(it["scope"]))
            self.tbl_startup.setItem(row, 2, QTableWidgetItem(it["command"]))
            btn = QPushButton("Отключить" if it["enabled"] else "Включить")
            btn.setObjectName("SecondaryBtn")
            btn.clicked.connect(lambda _, n=it["name"], s=it["scope"], en=not it["enabled"]: self._toggle_startup(n, s, en))
            self.tbl_startup.setCellWidget(row, 3, btn)

        svcs = WindowsTweaker.get_services_status()
        self.tbl_services.setRowCount(0)
        for sv in svcs:
            row = self.tbl_services.rowCount()
            self.tbl_services.insertRow(row)
            self.tbl_services.setItem(row, 0, QTableWidgetItem(f"{sv['title']} ({sv['id']})"))
            self.tbl_services.setItem(row, 1, QTableWidgetItem(sv["desc"]))
            self.tbl_services.setItem(row, 2, QTableWidgetItem(sv["state"]))
            is_running = (sv["state"] == "Работает")
            btn = QPushButton("Отключить" if is_running else "Включить")
            btn.setObjectName("SecondaryBtn")
            btn.clicked.connect(lambda _, sid=sv["id"], en=not is_running: self._toggle_service(sid, en))
            self.tbl_services.setCellWidget(row, 3, btn)

    def _toggle_startup(self, name: str, scope: str, enable: bool):
        self._toast_call(lambda: WindowsTweaker.toggle_startup_item(name, scope, enable))
        self._refresh_startup_and_services()

    def _toggle_service(self, svc_id: str, enable: bool):
        self._toast_call(lambda: WindowsTweaker.set_service_state(svc_id, enable))
        self._refresh_startup_and_services()

    # =================================================================
    # 4. ДИСК И СЕТЬ
    # =================================================================
    def _build_disk_net_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 14)
        layout.setSpacing(14)

        header = QLabel("Анализ диска и Сетевые инструменты")
        header.setObjectName("PageTitle")
        layout.addWidget(header)

        c_net, l_net = self._make_card("Сеть и DNS")
        nrow = QHBoxLayout()
        for label, fn in [
            ("DNS: Cloudflare", lambda: self._toast_call(lambda: WindowsTweaker.set_dns_provider("cloudflare"))),
            ("DNS: Google", lambda: self._toast_call(lambda: WindowsTweaker.set_dns_provider("google"))),
            ("DNS: Авто", lambda: self._toast_call(lambda: WindowsTweaker.set_dns_provider("auto"))),
            ("Сброс DNS", lambda: self._toast_call(WindowsTweaker.flush_dns)),
            ("Сброс Winsock", lambda: self._toast_call(WindowsTweaker.reset_winsock)),
            ("Пинг 1.1.1.1", self._do_ping),
        ]:
            b = QPushButton(label)
            b.setObjectName("SecondaryBtn")
            b.clicked.connect(fn)
            nrow.addWidget(b)
        l_net.addLayout(nrow)
        self.lbl_ping = QLabel("Нажмите «Пинг 1.1.1.1» для проверки задержки.")
        self.lbl_ping.setObjectName("Muted")
        l_net.addWidget(self.lbl_ping)
        layout.addWidget(c_net)

        c_disk, l_disk = self._make_card("Поиск больших файлов (> 50 МБ) и Очистка")
        drow = QHBoxLayout()
        btn_scan = QPushButton("Выбрать папку и сканировать")
        btn_scan.setObjectName("PrimaryBtn")
        btn_scan.clicked.connect(self._start_disk_scan)
        btn_bin = QPushButton("Очистить Корзину")
        btn_bin.setObjectName("SecondaryBtn")
        btn_bin.clicked.connect(lambda: self._toast_call(WindowsTweaker.empty_recycle_bin))
        drow.addWidget(btn_scan)
        drow.addWidget(btn_bin)
        drow.addStretch()
        l_disk.addLayout(drow)

        self.tbl_disk = QTableWidget(0, 2)
        self.tbl_disk.setHorizontalHeaderLabels(["Размер (МБ)", "Путь к файлу"])
        self.tbl_disk.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_disk.setEditTriggers(QTableWidget.NoEditTriggers)
        l_disk.addWidget(self.tbl_disk)
        layout.addWidget(c_disk, 1)
        return page

    def _do_ping(self):
        self.lbl_ping.setText("Выполняется пинг...")
        QApplication.processEvents()
        self.lbl_ping.setText(WindowsTweaker.ping_host("1.1.1.1"))

    def _start_disk_scan(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для анализа", os.path.expanduser("~"))
        if not folder:
            return
        self.toast.show_message("Сканирование больших файлов...", "warn")
        self.disk_worker = DiskAnalyzerWorker(folder)
        self.disk_worker.finished_scan.connect(self._on_disk_scanned)
        self.disk_worker.start()

    def _on_disk_scanned(self, files: list):
        self.tbl_disk.setRowCount(0)
        for mb, path in files:
            r = self.tbl_disk.rowCount()
            self.tbl_disk.insertRow(r)
            self.tbl_disk.setItem(r, 0, QTableWidgetItem(f"{mb:.1f}"))
            self.tbl_disk.setItem(r, 1, QTableWidgetItem(path))
        self.toast.show_message(f"Найдено крупных файлов: {len(files)}", "ok")

    # =================================================================
    # 5. БЕНЧМАРК
    # =================================================================
    def _build_benchmark_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 14)
        layout.setSpacing(14)

        header = QLabel("Бенчмарк производительности и История")
        header.setObjectName("PageTitle")
        layout.addWidget(header)

        card, clay = self._make_card("Запуск тестов")
        row = QHBoxLayout()
        self.bench_buttons = []
        for label, mode, style in [
            ("Полный тест (All)", "all", "PrimaryBtn"),
            ("CPU Single", "cpu_single", "SecondaryBtn"),
            ("CPU Multi", "cpu_multi", "SecondaryBtn"),
            ("RAM (оценка)", "ram", "SecondaryBtn"),
            ("Диск", "disk", "SecondaryBtn"),
        ]:
            b = QPushButton(label)
            b.setObjectName(style)
            b.clicked.connect(lambda _, m=mode: self._start_benchmark(m))
            row.addWidget(b)
            self.bench_buttons.append(b)
        clay.addLayout(row)

        self.bench_status = QLabel("Выберите тест.")
        self.bench_status.setObjectName("Muted")
        self.bench_pb = AnimatedProgressBar()
        clay.addWidget(self.bench_status)
        clay.addWidget(self.bench_pb)
        layout.addWidget(card)

        cols = QHBoxLayout()
        self.bench_table = QTableWidget(0, 2)
        self.bench_table.setHorizontalHeaderLabels(["Тест", "Результат"])
        self.bench_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        cols.addWidget(self.bench_table, 2)

        self.bench_hist_table = QTableWidget(0, 2)
        self.bench_hist_table.setHorizontalHeaderLabels(["Дата", "Общий балл"])
        self.bench_hist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        cols.addWidget(self.bench_hist_table, 1)
        layout.addLayout(cols, 1)

        self._load_bench_history()
        return page

    def _load_bench_history(self):
        hist = BenchmarkWorker.load_history()
        self.bench_hist_table.setRowCount(0)
        for item in reversed(hist):
            r = self.bench_hist_table.rowCount()
            self.bench_hist_table.insertRow(r)
            self.bench_hist_table.setItem(r, 0, QTableWidgetItem(item["date"]))
            self.bench_hist_table.setItem(r, 1, QTableWidgetItem(f"{item['score']} pts"))

    def _start_benchmark(self, mode: str):
        if self.bench_worker and self.bench_worker.isRunning():
            return
        for b in self.bench_buttons:
            b.setEnabled(False)
        self.bench_worker = BenchmarkWorker(mode)
        self.bench_worker.progress.connect(lambda p, t: (self.bench_pb.set_animated_value(p, False), self.bench_status.setText(t)))
        self.bench_worker.finished_result.connect(self._on_bench_done)
        self.bench_worker.start()

    def _on_bench_done(self, results: dict):
        for b in self.bench_buttons:
            b.setEnabled(True)
        self.bench_table.setRowCount(0)
        for k, v in results.items():
            r = self.bench_table.rowCount()
            self.bench_table.insertRow(r)
            ik, iv = QTableWidgetItem(k), QTableWidgetItem(str(v))
            if k == "ОБЩИЙ БАЛЛ":
                f = QFont()
                f.setBold(True)
                ik.setFont(f)
                iv.setFont(f)
                iv.setForeground(QColor("#ff2e5b"))
            self.bench_table.setItem(r, 0, ik)
            self.bench_table.setItem(r, 1, iv)
        self._load_bench_history()
        self.toast.show_message("Бенчмарк завершён!", "ok")

    # =================================================================
    # 6. СЕССИИ И ПРОЦЕССЫ
    # =================================================================
    def _build_sessions_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 14)
        layout.setSpacing(12)

        top = QHBoxLayout()
        header = QLabel("Сессии, События и Процессы")
        header.setObjectName("PageTitle")
        btn_ref = QPushButton("Обновить")
        btn_ref.setObjectName("PrimaryBtn")
        btn_ref.clicked.connect(self._refresh_sessions_all)
        top.addWidget(header)
        top.addStretch()
        top.addWidget(btn_ref)
        layout.addLayout(top)

        c_cur, l_cur = self._make_card("Текущая сессия")
        self.lbl_session_info = QLabel("Загрузка...")
        self.lbl_session_info.setObjectName("Muted")
        l_cur.addWidget(self.lbl_session_info)
        layout.addWidget(c_cur)

        tabs = QTabWidget()

        self.tbl_history = QTableWidget(0, 4)
        self.tbl_history.setHorizontalHeaderLabels(["Время", "Event ID", "Событие", "Источник"])
        self.tbl_history.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_history.setSortingEnabled(True)
        tabs.addTab(self.tbl_history, "История сессий Windows")

        self.tbl_net = QTableWidget(0, 5)
        self.tbl_net.setHorizontalHeaderLabels(["PID", "Процесс", "Локальный", "Удалённый", "Статус"])
        self.tbl_net.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_net.setSortingEnabled(True)
        tabs.addTab(self.tbl_net, "Сетевые сессии")

        proc_tab = QWidget()
        p_lay = QVBoxLayout(proc_tab)
        p_top = QHBoxLayout()
        self.proc_search = QLineEdit()
        self.proc_search.setPlaceholderText("Поиск процесса по имени...")
        self.proc_search.textChanged.connect(self._filter_processes)
        btn_kill = QPushButton("Завершить процесс")
        btn_kill.setObjectName("SecondaryBtn")
        btn_kill.clicked.connect(self._kill_selected_process)
        p_top.addWidget(self.proc_search, 1)
        p_top.addWidget(btn_kill)
        p_lay.addLayout(p_top)

        self.tbl_procs = QTableWidget(0, 4)
        self.tbl_procs.setHorizontalHeaderLabels(["PID", "Имя", "CPU %", "RAM (МБ)"])
        self.tbl_procs.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_procs.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_procs.setSortingEnabled(True)
        p_lay.addWidget(self.tbl_procs)
        tabs.addTab(proc_tab, "Активные процессы")

        layout.addWidget(tabs, 1)
        return page

    def _refresh_sessions_all(self):
        boot_dt = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
        users = [f"{u.name} ({datetime.datetime.fromtimestamp(u.started).strftime('%H:%M')})" for u in psutil.users()]
        self.lbl_session_info.setText(f"Загрузка ПК: {boot_dt}   |   Пользователи: {', '.join(users) or 'Нет данных'}")

        if not self.session_worker or not self.session_worker.isRunning():
            self.session_worker = SessionHistoryWorker()
            self.session_worker.loaded.connect(self._populate_history)
            self.session_worker.start()

        self.tbl_net.setSortingEnabled(False)
        self.tbl_net.setRowCount(0)
        try:
            for c in psutil.net_connections(kind="inet")[:80]:
                if c.status not in ("ESTABLISHED", "LISTEN"):
                    continue
                pid = c.pid or 0
                try:
                    pname = psutil.Process(pid).name() if pid else "System"
                except Exception:
                    pname = "N/A"
                r = self.tbl_net.rowCount()
                self.tbl_net.insertRow(r)
                for col, val in enumerate((
                    str(pid), pname,
                    f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "-",
                    f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "-",
                    c.status
                )):
                    self.tbl_net.setItem(r, col, QTableWidgetItem(val))
        except Exception:
            pass
        self.tbl_net.setSortingEnabled(True)

        self.tbl_procs.setSortingEnabled(False)
        self.tbl_procs.setRowCount(0)
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                mb = p.info["memory_info"].rss / (1024 * 1024) if p.info["memory_info"] else 0.0
                procs.append((p.info["pid"], p.info["name"] or "?", p.info["cpu_percent"] or 0.0, mb))
            except Exception:
                pass
        procs.sort(key=lambda x: x[3], reverse=True)
        for pid, name, cpu_p, mb in procs[:70]:
            r = self.tbl_procs.rowCount()
            self.tbl_procs.insertRow(r)
            self.tbl_procs.setItem(r, 0, QTableWidgetItem(str(pid)))
            self.tbl_procs.setItem(r, 1, QTableWidgetItem(name))
            self.tbl_procs.setItem(r, 2, QTableWidgetItem(f"{cpu_p:.1f}"))
            item_ram = QTableWidgetItem(f"{mb:.1f}")
            if mb > 800:
                item_ram.setForeground(QColor("#ff2e5b"))
            self.tbl_procs.setItem(r, 3, item_ram)
        self.tbl_procs.setSortingEnabled(True)
        self._filter_processes(self.proc_search.text())

    def _populate_history(self, rows: list):
        self.tbl_history.setSortingEnabled(False)
        self.tbl_history.setRowCount(0)
        for ts, eid, desc, prov in rows:
            r = self.tbl_history.rowCount()
            self.tbl_history.insertRow(r)
            for col, val in enumerate((ts, eid, desc, prov)):
                self.tbl_history.setItem(r, col, QTableWidgetItem(val))
        self.tbl_history.setSortingEnabled(True)

    def _filter_processes(self, text: str):
        q = text.strip().lower()
        for r in range(self.tbl_procs.rowCount()):
            name = self.tbl_procs.item(r, 1).text().lower()
            self.tbl_procs.setRowHidden(r, q not in name)

    def _kill_selected_process(self):
        row = self.tbl_procs.currentRow()
        if row < 0:
            return
        pid = int(self.tbl_procs.item(row, 0).text())
        name = self.tbl_procs.item(row, 1).text()
        if name.lower() in PROTECTED_PROCESSES:
            QMessageBox.critical(self, "Защита системы", f"Процесс {name} защищён от завершения.")
            return
        if QMessageBox.question(self, "Подтверждение", f"Завершить процесс {name} (PID {pid})?") != QMessageBox.Yes:
            return
        try:
            psutil.Process(pid).terminate()
            self.toast.show_message(f"Процесс {name} завершён", "ok")
            self._refresh_sessions_all()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", str(e))

    # =================================================================
    # 7. НАСТРОЙКИ HUD
    # =================================================================
    def _build_hud_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 14)
        layout.setSpacing(14)

        header = QLabel("Настройки HUD-оверлея")
        header.setObjectName("PageTitle")
        layout.addWidget(header)

        card, clay = self._make_card("Управление мини-виджетом")
        self.btn_hud_toggle = QPushButton("Включить HUD на экране")
        self.btn_hud_toggle.setObjectName("PrimaryBtn")
        self.btn_hud_toggle.clicked.connect(self._toggle_hud)
        clay.addWidget(self.btn_hud_toggle)

        sw_top = ToggleSwitch("Поверх всех окон (Always On Top)")
        sw_top.setChecked(True)
        sw_top.toggled.connect(self.hud.set_always_on_top)
        clay.addWidget(sw_top)

        sw_compact = ToggleSwitch("Компактный режим (только CPU, RAM, GPU)")
        sw_compact.toggled.connect(self.hud.set_compact_mode)
        clay.addWidget(sw_compact)

        sw_ct = ToggleSwitch("Сквозной клик (Click-Through)")
        sw_ct.toggled.connect(self.hud.set_click_through)
        clay.addWidget(sw_ct)

        op_row = QHBoxLayout()
        self.lbl_op = QLabel("Прозрачность: 92%")
        sl = QSlider(Qt.Horizontal)
        sl.setRange(35, 100)
        sl.setValue(92)
        sl.valueChanged.connect(lambda v: (self.lbl_op.setText(f"Прозрачность: {v}%"), self.hud.setWindowOpacity(v / 100.0)))
        op_row.addWidget(self.lbl_op)
        op_row.addWidget(sl, 1)
        clay.addLayout(op_row)

        btn_reset = QPushButton("Сбросить позицию HUD")
        btn_reset.setObjectName("SecondaryBtn")
        btn_reset.clicked.connect(self.hud.reset_position)
        clay.addWidget(btn_reset, alignment=Qt.AlignLeft)
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _toggle_hud(self):
        vis = not self.hud.isVisible()
        self.hud.setVisible(vis)
        self._sync_hud_buttons(vis)

    def _sync_hud_buttons(self, visible: bool):
        self.sb_hud_btn.setText("HUD" if self.sidebar_collapsed else ("Скрыть HUD" if visible else "Включить HUD"))
        self.btn_hud_toggle.setText("Скрыть HUD с экрана" if visible else "Включить HUD на экране")

    # =================================================================
    # 8. КУРСОР, СЛЕД ЗА КУРСОРОМ И ВОЛНА КЛИКОВ
    # =================================================================
    def _build_cursor_fx_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 18, 24, 14)
        outer.setSpacing(12)

        header = QLabel("Курсор, След за мышью и Анимация кликов")
        header.setObjectName("PageTitle")
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget()
        layout = QVBoxLayout(cont)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(14)

        # Карточка 1: След за курсором
        c_tr, l_tr = self._make_card("След за курсором (Cursor Trail — везде в Windows)")
        self.sw_trail_fx = ToggleSwitch("Включить след за курсором")
        self.sw_trail_fx.toggled.connect(self._on_toggle_trail_fx)
        l_tr.addWidget(self.sw_trail_fx)

        st_row = QHBoxLayout()
        st_row.addWidget(QLabel("Стиль следа:"))
        for label, key in [
            ("Неоновый хвост", "ribbon"),
            ("Искры / Партиклы", "particles"),
            ("Точки", "dots"),
            ("Свечение (Glow)", "glow"),
        ]:
            b = QPushButton(label)
            b.setObjectName("SecondaryBtn")
            b.clicked.connect(lambda _, k=key, lbl=label: (self.click_fx.set_trail_style(k), self.toast.show_message(f"Стиль следа: {lbl}", "ok")))
            st_row.addWidget(b)
        st_row.addStretch()
        l_tr.addLayout(st_row)

        sw_rgb = ToggleSwitch("Радужный режим (RGB переливание)")
        sw_rgb.toggled.connect(lambda v: setattr(self.click_fx, "trail_rainbow", v))
        l_tr.addWidget(sw_rgb)

        len_row = QHBoxLayout()
        self.lbl_trail_len = QLabel("Длина / Размер следа: 26")
        sl_len = QSlider(Qt.Horizontal)
        sl_len.setRange(10, 55)
        sl_len.setValue(26)
        sl_len.valueChanged.connect(lambda v: (self.lbl_trail_len.setText(f"Длина / Размер следа: {v}"), setattr(self.click_fx, "trail_length", v)))
        len_row.addWidget(self.lbl_trail_len)
        len_row.addWidget(sl_len, 1)
        l_tr.addLayout(len_row)

        tcol_row = QHBoxLayout()
        tcol_row.addWidget(QLabel("Цвет следа:"))
        for cname, hex_c in [("Crimson", "#ff2e5b"), ("Cyan", "#38bdf8"), ("White", "#ffffff"), ("Neon Green", "#22c55e")]:
            b = QPushButton(cname)
            b.setObjectName("SecondaryBtn")
            b.clicked.connect(lambda _, hx=hex_c: self._set_trail_color(hx))
            tcol_row.addWidget(b)
        btn_tpick = QPushButton("Свой цвет...")
        btn_tpick.setObjectName("PrimaryBtn")
        btn_tpick.clicked.connect(self._pick_custom_trail_color)
        tcol_row.addWidget(btn_tpick)
        tcol_row.addStretch()
        l_tr.addLayout(tcol_row)
        layout.addWidget(c_tr)

        # Карточка 2: Волна при клике
        c_fx, l_fx = self._make_card("Глобальная анимация клика (Волна)")
        self.sw_click_fx = ToggleSwitch("Включить волну при клике (рабочий стол, браузер, окна)")
        self.sw_click_fx.toggled.connect(self._on_toggle_click_fx)
        l_fx.addWidget(self.sw_click_fx)

        sw_double = ToggleSwitch("Двойная волна (второе кольцо внутри)")
        sw_double.setChecked(True)
        sw_double.toggled.connect(lambda v: setattr(self.click_fx, "double_wave", v))
        l_fx.addWidget(sw_double)

        sw_rmb = ToggleSwitch("Отдельная волна на правый клик (ПКМ)")
        sw_rmb.setChecked(True)
        sw_rmb.toggled.connect(lambda v: setattr(self.click_fx, "track_rmb", v))
        l_fx.addWidget(sw_rmb)

        rad_row = QHBoxLayout()
        self.lbl_rad = QLabel("Радиус волны: 48 px")
        sl_rad = QSlider(Qt.Horizontal)
        sl_rad.setRange(24, 110)
        sl_rad.setValue(48)
        sl_rad.valueChanged.connect(lambda v: (self.lbl_rad.setText(f"Радиус волны: {v} px"), setattr(self.click_fx, "max_radius", v)))
        rad_row.addWidget(self.lbl_rad)
        rad_row.addWidget(sl_rad, 1)
        l_fx.addLayout(rad_row)

        col_row = QHBoxLayout()
        col_row.addWidget(QLabel("Цвет волны (ЛКМ):"))
        for cname, hex_c in [("Crimson", "#ff2e5b"), ("Cyan", "#38bdf8"), ("White", "#ffffff"), ("Neon Green", "#22c55e")]:
            b = QPushButton(cname)
            b.setObjectName("SecondaryBtn")
            b.clicked.connect(lambda _, hx=hex_c: self._set_ripple_color(hx))
            col_row.addWidget(b)
        btn_pick = QPushButton("Свой цвет...")
        btn_pick.setObjectName("PrimaryBtn")
        btn_pick.clicked.connect(self._pick_custom_ripple_color)
        col_row.addWidget(btn_pick)
        col_row.addStretch()
        l_fx.addLayout(col_row)
        layout.addWidget(c_fx)

        # Карточка 3: Системный курсор Windows
        c_cur, l_cur = self._make_card("Кастомизация системного курсора Windows")
        cur_size = CursorManager.get_cursor_size()
        sz_row = QHBoxLayout()
        self.lbl_cur_size = QLabel(f"Размер курсора: {cur_size} px")
        self.sl_cur_size = QSlider(Qt.Horizontal)
        self.sl_cur_size.setRange(32, 96)
        self.sl_cur_size.setValue(cur_size)
        self.sl_cur_size.valueChanged.connect(lambda v: self.lbl_cur_size.setText(f"Размер курсора: {v} px"))
        btn_apply_sz = QPushButton("Применить размер")
        btn_apply_sz.setObjectName("SecondaryBtn")
        btn_apply_sz.clicked.connect(lambda: self._toast_call(lambda: CursorManager.set_cursor_size(self.sl_cur_size.value())))
        sz_row.addWidget(self.lbl_cur_size)
        sz_row.addWidget(self.sl_cur_size, 1)
        sz_row.addWidget(btn_apply_sz)
        l_cur.addLayout(sz_row)

        sch_row = QHBoxLayout()
        sch_row.addWidget(QLabel("Стиль курсора:"))
        for label, key in [("Стандартный (Белый)", "default"), ("Чёрный (Dark)", "black"), ("Инвертированный", "inverted")]:
            b = QPushButton(label)
            b.setObjectName("SecondaryBtn")
            b.clicked.connect(lambda _, k=key: self._toast_call(lambda: CursorManager.apply_scheme(k)))
            sch_row.addWidget(b)
        sch_row.addStretch()
        l_cur.addLayout(sch_row)

        file_row = QHBoxLayout()
        btn_arrow = QPushButton("Загрузить .cur/.ani (Стрелка)")
        btn_arrow.setObjectName("PrimaryBtn")
        btn_arrow.clicked.connect(lambda: self._load_custom_cursor("Arrow"))
        btn_hand = QPushButton("Загрузить .cur/.ani (Рука)")
        btn_hand.setObjectName("SecondaryBtn")
        btn_hand.clicked.connect(lambda: self._load_custom_cursor("Hand"))
        btn_reset_cur = QPushButton("Сбросить курсор")
        btn_reset_cur.setObjectName("SecondaryBtn")
        btn_reset_cur.clicked.connect(self._reset_cursor)
        file_row.addWidget(btn_arrow)
        file_row.addWidget(btn_hand)
        file_row.addWidget(btn_reset_cur)
        file_row.addStretch()
        l_cur.addLayout(file_row)

        layout.addWidget(c_cur)
        layout.addStretch()

        scroll.setWidget(cont)
        outer.addWidget(scroll, 1)
        return page

    def _on_toggle_trail_fx(self, enabled: bool):
        self.click_fx.set_trail_enabled(enabled)
        self.toast.show_message("След за курсором включён!" if enabled else "След за курсором выключен", "ok")

    def _set_trail_color(self, hex_color: str):
        self.click_fx.trail_color = QColor(hex_color)
        self.toast.show_message(f"Цвет следа: {hex_color}", "ok")

    def _pick_custom_trail_color(self):
        col = QColorDialog.getColor(self.click_fx.trail_color, self, "Выберите цвет следа")
        if col.isValid():
            self.click_fx.trail_color = col
            self.toast.show_message(f"Выбран цвет следа: {col.name()}", "ok")

    def _on_toggle_click_fx(self, enabled: bool):
        self.click_fx.set_enabled(enabled)
        self.toast.show_message("Волна кликов включена!" if enabled else "Волна кликов выключена", "ok")

    def _set_ripple_color(self, hex_color: str):
        self.click_fx.color_lmb = QColor(hex_color)
        self.toast.show_message(f"Цвет волны: {hex_color}", "ok")

    def _pick_custom_ripple_color(self):
        col = QColorDialog.getColor(self.click_fx.color_lmb, self, "Выберите цвет волны")
        if col.isValid():
            self.click_fx.color_lmb = col
            self.toast.show_message(f"Выбран цвет: {col.name()}", "ok")

    def _load_custom_cursor(self, role: str):
        fp, _ = QFileDialog.getOpenFileName(self, "Выберите файл курсора", "", "Курсоры Windows (*.cur *.ani)")
        if fp:
            self._toast_call(lambda: CursorManager.set_custom_cursor_file(role, fp))

    def _reset_cursor(self):
        self._toast_call(CursorManager.reset_default)
        self.sl_cur_size.setValue(32)

    # =================================================================
    # 9. ВИЗУАЛ: ЖИВЫЕ ОБОИ, KEYSTROKE OSD, GLASS ЧАСЫ, ТЕМЫ
    # =================================================================
    def _build_visuals_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 14)
        layout.setSpacing(14)

        header = QLabel("Визуальная кастомизация: Обои, Виджеты и Темы")
        header.setObjectName("PageTitle")
        layout.addWidget(header)

        c_wp, l_wp = self._make_card("Живые обои (позади иконок рабочего стола)")
        sw_wp = ToggleSwitch("Включить живые обои на рабочем столе")
        sw_wp.toggled.connect(self._toggle_live_wallpaper)
        l_wp.addWidget(sw_wp)

        wp_row = QHBoxLayout()
        wp_row.addWidget(QLabel("Стиль анимации:"))
        for label, mode in [("Созвездие (Частицы)", "particles"), ("Северное сияние (Aurora)", "aurora"), ("Цифровой дождь (Matrix)", "matrix")]:
            b = QPushButton(label)
            b.setObjectName("SecondaryBtn")
            b.clicked.connect(lambda _, m=mode: (self.live_wp.set_mode(m), self.toast.show_message(f"Режим обоев: {m}", "ok")))
            wp_row.addWidget(b)
        wp_row.addStretch()
        l_wp.addLayout(wp_row)
        layout.addWidget(c_wp)

        cols = QHBoxLayout()
        cols.setSpacing(14)

        c_key, l_key = self._make_card("Виджет нажатий клавиш (Keystroke OSD)")
        sw_key = ToggleSwitch("Показывать нажатые клавиши и комбинации")
        sw_key.toggled.connect(lambda v: (self.key_osd.set_enabled(v), self.toast.show_message("Keystroke OSD включён" if v else "Keystroke OSD выключен", "ok")))
        l_key.addWidget(sw_key)
        lbl_k = QLabel("Отображает Ctrl+C, Alt+Tab, Space и любые клавиши внизу экрана.")
        lbl_k.setObjectName("Muted")
        lbl_k.setWordWrap(True)
        l_key.addWidget(lbl_k)
        cols.addWidget(c_key)

        c_clk, l_clk = self._make_card("Виджет часов (Rainmeter / Liquid Glass)")
        sw_clk = ToggleSwitch("Показать стеклянные часы на рабочем столе")
        sw_clk.toggled.connect(lambda v: self.glass_clock.setVisible(v))
        l_clk.addWidget(sw_clk)
        sw_clk_top = ToggleSwitch("Поверх всех окон (Always On Top)")
        sw_clk_top.toggled.connect(self.glass_clock.set_always_on_top)
        l_clk.addWidget(sw_clk_top)
        btn_clk_rst = QPushButton("Сбросить позицию часов")
        btn_clk_rst.setObjectName("SecondaryBtn")
        btn_clk_rst.clicked.connect(self.glass_clock.reset_position)
        l_clk.addWidget(btn_clk_rst, alignment=Qt.AlignLeft)
        cols.addWidget(c_clk)

        layout.addLayout(cols)

        c_th, l_th = self._make_card("Темы оформления и Акцентный цвет Aether Suite")
        th_row = QHBoxLayout()
        for label, tkey, acc in [
            ("Crimson Dark", "crimson", "#ff2e5b"),
            ("Monochrome (Ч/Б)", "monochrome", "#ffffff"),
            ("Liquid Glass", "liquid_glass", "#38bdf8"),
        ]:
            b = QPushButton(label)
            b.setObjectName("SecondaryBtn")
            b.clicked.connect(lambda _, tk=tkey, ac=acc: self._apply_theme(tk, ac))
            th_row.addWidget(b)

        btn_acc = QPushButton("Выбрать свой акцент...")
        btn_acc.setObjectName("PrimaryBtn")
        btn_acc.clicked.connect(self._pick_app_accent)
        th_row.addWidget(btn_acc)
        th_row.addStretch()
        l_th.addLayout(th_row)

        layout.addWidget(c_th)
        layout.addStretch()
        return page

    def _toggle_live_wallpaper(self, enabled: bool):
        if enabled:
            self.live_wp.set_accent(self.current_accent)
            self.live_wp.start_wallpaper()
            self.toast.show_message("Живые обои запущены!", "ok")
        else:
            self.live_wp.stop_wallpaper()
            self.toast.show_message("Живые обои остановлены", "warn")

    def _apply_theme(self, theme_name: str, accent_hex: str):
        self.current_theme = theme_name
        self.current_accent = accent_hex
        QApplication.instance().setStyleSheet(build_stylesheet(theme_name, accent_hex))
        self.setWindowOpacity(0.95 if theme_name == "liquid_glass" else 1.0)
        self.live_wp.set_accent(accent_hex)
        self.key_osd.set_accent(accent_hex)
        self.glass_clock.set_accent(accent_hex)
        self.click_fx.trail_color = QColor(accent_hex)
        self._switch_page(self.stack.currentIndex())
        self.toast.show_message(f"Тема применена: {theme_name.upper()}", "ok")

    def _pick_app_accent(self):
        col = QColorDialog.getColor(QColor(self.current_accent), self, "Выберите акцентный цвет")
        if col.isValid():
            self._apply_theme(self.current_theme if self.current_theme != "monochrome" else "crimson", col.name())

    # =================================================================
    # ЭКСПОРТ HTML-ОТЧЁТА
    # =================================================================
    def _export_html_report(self):
        fp, _ = QFileDialog.getSaveFileName(self, "Сохранить отчёт", "aether_report.html", "HTML (*.html)")
        if not fp:
            return
        ram = psutil.virtual_memory()
        hist = BenchmarkWorker.load_history()
        last_bench = hist[-1] if hist else {"date": "Не запускался", "score": 0}
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Aether Suite Report</title>
        <style>body{{background:#0b0b0e;color:#e6e6eb;font-family:Segoe UI,sans-serif;padding:30px;}}
        .card{{background:#131319;border:1px solid #22222c;border-radius:12px;padding:18px;margin-bottom:16px;}}
        h1{{color:{self.current_accent};}}</style></head><body>
        <h1>AETHER SUITE — Отчёт о системе</h1>
        <div class="card"><b>ОС:</b> {platform.system()} {platform.release()} ({platform.machine()})<br>
        <b>Хост:</b> {platform.node()}<br>
        <b>CPU:</b> {psutil.cpu_count(logical=False)}P / {psutil.cpu_count()}L<br>
        <b>RAM:</b> {ram.total / (1024**3):.2f} ГБ<br>
        <b>GPU:</b> {self.lbl_gpu_sub.text()}</div>
        <div class="card"><b>Последний бенчмарк ({last_bench['date']}):</b> {last_bench['score']} pts</div>
        </body></html>"""
        with open(fp, "w", encoding="utf-8") as f:
            f.write(html)
        self.toast.show_message("HTML-отчёт сохранён!", "ok")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(build_stylesheet("crimson", "#ff2e5b"))
    app.setQuitOnLastWindowClosed(False)
    win = WinOptimizerApp()
    win.show()
    sys.exit(app.exec())
