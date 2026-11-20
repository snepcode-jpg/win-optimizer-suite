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

from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

ICON_SVG = {
    "stats": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    "presets": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    "tweaks": (
        '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/>'
        '<line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/>'
        '<line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>'
        '<line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/>'
        '<line x1="17" y1="16" x2="23" y2="16"/>'
    ),
    "startup": '<path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/>',
    "disk": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>',
    "bench": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "sessions": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "hud": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/>',
    "cursor": '<path d="M4 4l7.07 17 2.51-7.39L21 11.07z"/>',
    "visuals": '<path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>',
    "menu": '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
}


def make_svg_icon(name: str, color: str = "#a6a6b5", size: int = 20) -> QIcon:
    """Чёткая HiDPI SVG-иконка (суперсэмплинг x2, стиль Feather/Lucide)."""
    body = ICON_SVG.get(name, ICON_SVG["stats"])
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round">{body}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    return QIcon(pm)


def load_color_for_percent(pct: float) -> str:
    if pct < 55:
        return "#22c55e"
    if pct < 82:
        return "#f59e0b"
    return "#ff2e5b"


def build_stylesheet(theme: str = "crimson", accent: str = "#ff2e5b") -> str:
    if theme == "monochrome":
        bg = "#09090b"
        sidebar_bg = "#101014"
        card_bg = "#141418"
        border = "#27272e"
        accent = "#ffffff"
        btn_text = "#09090b"
        active_bg = "#202026"
    elif theme == "liquid_glass":
        bg = "rgba(12, 12, 18, 225)"
        sidebar_bg = "rgba(18, 18, 28, 210)"
        card_bg = "rgba(255, 255, 255, 14)"
        border = "rgba(255, 255, 255, 36)"
        btn_text = "#ffffff"
        active_bg = "rgba(255, 255, 255, 22)"
    else:
        bg = "#0b0b0e"
        sidebar_bg = "#111116"
        card_bg = "#131319"
        border = "#22222c"
        btn_text = "#ffffff"
        active_bg = "#1f1419"

    return f"""
QMainWindow, QWidget {{
    background-color: {bg};
    color: #e6e6eb;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}}
QLabel {{ background: transparent; }}
QToolTip {{ background-color: #1a1a22; color: #fff; border: 1px solid #2c2c38; padding: 4px; }}

#TitleBar {{
    background-color: {sidebar_bg};
    border-bottom: 1px solid {border};
}}
#TitleText {{
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QPushButton#WinBtn, QPushButton#WinCloseBtn {{
    background: transparent;
    color: #a6a6b5;
    border: none;
    font-size: 14px;
    font-weight: 700;
    min-width: 38px;
    min-height: 32px;
}}
QPushButton#WinBtn:hover {{
    background-color: rgba(255, 255, 255, 18);
    color: #ffffff;
}}
QPushButton#WinCloseBtn:hover {{
    background-color: #e11d48;
    color: #ffffff;
}}

#Sidebar {{
    background-color: {sidebar_bg};
    border-right: 1px solid {border};
}}
#BrandTitle {{
    color: #ffffff;
    font-size: 17px;
    font-weight: 800;
    letter-spacing: 1px;
}}
#NavIndicator {{
    background-color: {accent};
    border-radius: 2px;
}}
QPushButton#NavBtn {{
    background-color: transparent;
    color: #a6a6b5;
    border: none;
    border-radius: 8px;
    padding: 9px 12px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#NavBtn:hover {{
    background-color: rgba(255, 255, 255, 14);
    color: #ffffff;
}}
QPushButton#NavBtn[active="true"] {{
    background-color: {active_bg};
    color: {accent};
}}

QFrame#Card {{
    background-color: {card_bg};
    border: 1px solid {border};
    border-radius: 12px;
}}
QFrame#Card:hover {{
    border: 1px solid {accent};
}}
QLabel#PageTitle {{
    font-size: 21px;
    font-weight: 700;
    color: #ffffff;
}}
QLabel#CardTitle {{
    font-size: 14px;
    font-weight: 700;
    color: #ffffff;
}}
QLabel#MetricValue {{
    font-size: 23px;
    font-weight: 800;
    color: #22c55e;
}}
QLabel#Muted {{
    color: #8e8e9e;
    font-size: 12px;
}}
QPushButton#PrimaryBtn {{
    background-color: {accent};
    color: {btn_text};
    border: none;
    border-radius: 8px;
    padding: 9px 15px;
    font-weight: 700;
}}
QPushButton#PrimaryBtn:hover {{
    opacity: 0.9;
}}
QPushButton#PrimaryBtn:disabled {{
    background-color: #3a2028;
    color: #888;
}}
QPushButton#SecondaryBtn {{
    background-color: rgba(255, 255, 255, 10);
    color: #e6e6eb;
    border: 1px solid {border};
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 600;
}}
QPushButton#SecondaryBtn:hover {{
    border-color: {accent};
}}
QProgressBar {{
    background-color: rgba(255, 255, 255, 12);
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {accent};
    border-radius: 5px;
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: rgba(255, 255, 255, 18);
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {accent};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::sub-page:horizontal {{
    background: {accent};
    border-radius: 3px;
}}
QTextEdit#LogBox, QLineEdit {{
    background-color: rgba(0, 0, 0, 120);
    border: 1px solid {border};
    border-radius: 8px;
    color: #c8c8d4;
    padding: 6px 10px;
}}
QTextEdit#LogBox {{
    font-family: "Consolas", "Cascadia Code", monospace;
    font-size: 12px;
}}
QTableWidget {{
    background-color: rgba(14, 14, 20, 180);
    border: 1px solid {border};
    border-radius: 8px;
    gridline-color: {border};
    selection-background-color: {active_bg};
    selection-color: #ffffff;
}}
QHeaderView::section {{
    background-color: {sidebar_bg};
    color: #b4b4c4;
    padding: 7px;
    border: none;
    border-bottom: 1px solid {border};
    font-weight: 700;
}}
QComboBox {{
    background-color: {sidebar_bg};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 6px 10px;
    color: #ffffff;
}}
QTabWidget::pane {{
    border: 1px solid {border};
    border-radius: 8px;
    background: transparent;
}}
QTabBar::tab {{
    background: {sidebar_bg};
    color: #9e9eae;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
}}
QTabBar::tab:selected {{
    background: {accent};
    color: {btn_text};
    font-weight: 700;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
"""


APP_STYLESHEET = build_stylesheet("crimson", "#ff2e5b")
