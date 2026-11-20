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

import os
import ctypes
import winreg

SPI_SETCURSORS = 0x0057


class CursorManager:
    REG_PATH = r"Control Panel\Cursors"

    @classmethod
    def _apply_system_cursors(cls):
        """Мгновенно применяет изменения курсора в Windows без перезагрузки."""
        ctypes.windll.user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)

    @classmethod
    def set_cursor_size(cls, size_px: int) -> tuple[bool, str]:
        """Устанавливает базовый размер курсора (32–96 px)."""
        size_px = max(32, min(96, int(size_px)))
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, cls.REG_PATH, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "CursorBaseSize", 0, winreg.REG_DWORD, size_px)
            winreg.CloseKey(key)
            cls._apply_system_cursors()
            return True, f"Размер курсора установлен: {size_px} px"
        except Exception as e:
            return False, f"Ошибка размера курсора: {e}"

    @classmethod
    def get_cursor_size(cls) -> int:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_PATH, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, "CursorBaseSize")
            winreg.CloseKey(key)
            return int(val)
        except Exception:
            return 32

    @classmethod
    def apply_scheme(cls, scheme: str) -> tuple[bool, str]:
        """Применяет встроенную схему курсоров Windows (default, black, inverted)."""
        cdir = r"%SystemRoot%\cursors"
        schemes = {
            "default": {
                "Arrow": f"{cdir}\\aero_arrow.cur",
                "Hand": f"{cdir}\\aero_link.cur",
                "Wait": f"{cdir}\\aero_busy.ani",
                "AppStarting": f"{cdir}\\aero_working.ani",
                "IBeam": "",
                "Crosshair": "",
            },
            "black": {
                "Arrow": f"{cdir}\\arrow_r.cur",
                "Hand": f"{cdir}\\aero_link.cur",
                "Wait": f"{cdir}\\busy_r.cur",
                "AppStarting": f"{cdir}\\wait_r.cur",
                "IBeam": f"{cdir}\\beam_r.cur",
                "Crosshair": f"{cdir}\\cross_r.cur",
            },
            "inverted": {
                "Arrow": f"{cdir}\\arrow_i.cur",
                "Hand": f"{cdir}\\aero_link.cur",
                "Wait": f"{cdir}\\busy_i.cur",
                "AppStarting": f"{cdir}\\wait_i.cur",
                "IBeam": f"{cdir}\\beam_i.cur",
                "Crosshair": f"{cdir}\\cross_i.cur",
            },
        }
        mapping = schemes.get(scheme, schemes["default"])
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, cls.REG_PATH, 0, winreg.KEY_SET_VALUE)
            for name, path in mapping.items():
                winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, path)
            winreg.CloseKey(key)
            cls._apply_system_cursors()
            return True, f"Схема курсора применена: {scheme.upper()}"
        except Exception as e:
            return False, f"Ошибка схемы курсора: {e}"

    @classmethod
    def set_custom_cursor_file(cls, role: str, file_path: str) -> tuple[bool, str]:
        """Устанавливает свой .cur или .ani файл для роли ('Arrow' или 'Hand')."""
        if not os.path.exists(file_path):
            return False, "Файл курсора не найден."
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, cls.REG_PATH, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, role, 0, winreg.REG_EXPAND_SZ, file_path)
            winreg.CloseKey(key)
            cls._apply_system_cursors()
            return True, f"Установлен кастомный курсор ({role}): {os.path.basename(file_path)}"
        except Exception as e:
            return False, f"Ошибка установки курсора: {e}"

    @classmethod
    def reset_default(cls) -> tuple[bool, str]:
        cls.set_cursor_size(32)
        return cls.apply_scheme("default")
