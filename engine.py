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
import json
import ctypes
import shutil
import winreg
import logging
import tempfile
import datetime
import subprocess

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
BACKUP_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "aether_backup.json")

PROTECTED_PROCESSES = {
    "system", "smss.exe", "csrss.exe", "wininit.exe", "services.exe",
    "lsass.exe", "winlogon.exe", "fontdrvhost.exe", "dwm.exe",
    "svchost.exe", "explorer.exe", "memory compression"
}

SAFE_SERVICES = [
    ("SysMain", "Superfetch / SysMain", "Кэширование приложений в RAM. На SSD часто создаёт лишнюю нагрузку."),
    ("DiagTrack", "Телеметрия Windows", "Сбор и отправка диагностических данных в Microsoft."),
    ("XblAuthManager", "Xbox Live Auth", "Диспетчер аутентификации Xbox Live (не нужен, если не играешь через MS Store)."),
    ("XblGameSave", "Xbox Live Game Save", "Синхронизация сохранений игр Xbox."),
    ("XboxNetApiSvc", "Xbox Live Networking", "Сетевая служба Xbox Live."),
    ("MapsBroker", "Диспетчер скачанных карт", "Фоновое обновление офлайн-карт Windows."),
    ("Fax", "Служба факсов", "Устаревшая служба отправки факсов."),
]


class WindowsTweaker:
    @staticmethod
    def is_admin() -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    @staticmethod
    def run_as_admin(script_args: list[str]):
        params = " ".join([f'"{arg}"' for arg in script_args])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", os.sys.executable, params, None, 1)

    @staticmethod
    def run_cmd(cmd: list[str], timeout: int = 15) -> tuple[bool, str]:
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=CREATE_NO_WINDOW,
                encoding="utf-8",
                errors="ignore"
            )
            out = (res.stdout or res.stderr or "").strip()
            return res.returncode == 0, out
        except Exception as e:
            logging.error(f"run_cmd error ({cmd}): {e}")
            return False, str(e)

    # ---------------- РЕЕСТР (ЧТЕНИЕ И ЗАПИСЬ) ----------------
    @staticmethod
    def get_reg(root, path: str, name: str, default=None):
        try:
            key = winreg.OpenKey(root, path, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
            return val
        except Exception:
            return default

    @staticmethod
    def set_reg(root, path: str, name: str, value, reg_type=winreg.REG_DWORD) -> tuple[bool, str]:
        try:
            key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, name, 0, reg_type, value)
            winreg.CloseKey(key)
            logging.info(f"REG SET: {path}\\{name} = {value}")
            return True, f"Реестр обновлён: {name} = {value}"
        except PermissionError:
            return False, f"Нужны права Администратора для: {name}"
        except Exception as e:
            logging.error(f"REG ERR ({name}): {e}")
            return False, f"Ошибка реестра ({name}): {e}"

    # ---------------- БЭКАП И ОТКАТ ----------------
    @classmethod
    def get_active_power_guid(cls) -> str:
        ok, out = cls.run_cmd(["powercfg", "/getactivescheme"])
        if ok and ":" in out:
            parts = out.split(":")[1].strip().split()
            if parts:
                return parts[0].strip()
        return "381b4222-f694-41f0-9685-ff5bb260df2e"

    @classmethod
    def read_current_state(cls) -> dict:
        """Считывает реальное текущее состояние всех твиков из Windows."""
        p_theme = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        p_exp = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        return {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "power_guid": cls.get_active_power_guid(),
            "dark_mode": cls.get_reg(winreg.HKEY_CURRENT_USER, p_theme, "AppsUseLightTheme", 1) == 0,
            "no_transparency": cls.get_reg(winreg.HKEY_CURRENT_USER, p_theme, "EnableTransparency", 1) == 0,
            "show_extensions": cls.get_reg(winreg.HKEY_CURRENT_USER, p_exp, "HideFileExt", 1) == 0,
            "show_hidden": cls.get_reg(winreg.HKEY_CURRENT_USER, p_exp, "Hidden", 2) == 1,
            "taskbar_align": "left" if cls.get_reg(winreg.HKEY_CURRENT_USER, p_exp, "TaskbarAl", 1) == 0 else "center",
            "disable_bing": cls.get_reg(winreg.HKEY_CURRENT_USER, r"Software\Policies\Microsoft\Windows\Explorer", "DisableSearchBoxSuggestions", 0) == 1,
            "disable_gamedvr": cls.get_reg(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore", "GameDVR_Enabled", 1) == 0,
            "disable_telemetry": cls.get_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 1) == 0,
            "clipboard_history": cls.get_reg(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Clipboard", "EnableClipboardHistory", 0) == 1,
            "dev_mode": cls.get_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock", "AllowDevelopmentWithoutDevLicense", 0) == 1,
            "disable_mouse_accel": str(cls.get_reg(winreg.HKEY_CURRENT_USER, r"Control Panel\Mouse", "MouseSpeed", "1")) == "0",
            "fast_visuals": cls.get_reg(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting", 0) == 2,
            "menu_delay_zero": str(cls.get_reg(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", "MenuShowDelay", "400")) == "0",
        }

    @classmethod
    def save_backup(cls) -> tuple[bool, str]:
        try:
            state = cls.read_current_state()
            with open(BACKUP_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            return True, f"Снимок настроек сохранён ({state['timestamp']})"
        except Exception as e:
            return False, f"Ошибка сохранения бэкапа: {e}"

    @classmethod
    def restore_backup(cls) -> tuple[bool, list[str]]:
        if not os.path.exists(BACKUP_FILE):
            return False, ["Файл бэкапа не найден. Сначала примените любой шаблон или твик."]
        try:
            with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                s = json.load(f)
            logs = []
            if s.get("power_guid"):
                ok, msg = cls.run_cmd(["powercfg", "/setactive", s["power_guid"]])
                logs.append(f"[{'OK' if ok else 'WARN'}] Схема питания восстановлена: {s['power_guid']}")
            actions = [
                cls.set_dark_mode(s.get("dark_mode", False)),
                cls.set_transparency(not s.get("no_transparency", False)),
                cls.set_show_extensions(s.get("show_extensions", False)),
                cls.set_show_hidden(s.get("show_hidden", False)),
                cls.set_taskbar_align(s.get("taskbar_align", "center")),
                cls.set_bing_search(s.get("disable_bing", False)),
                cls.set_game_dvr(s.get("disable_gamedvr", False)),
                cls.set_telemetry(s.get("disable_telemetry", False)),
                cls.set_clipboard_history(s.get("clipboard_history", False)),
                cls.set_developer_mode(s.get("dev_mode", False)),
                cls.set_mouse_acceleration(s.get("disable_mouse_accel", False)),
                cls.set_visual_performance(s.get("fast_visuals", False)),
                cls.set_menu_delay(0 if s.get("menu_delay_zero", False) else 400),
            ]
            for ok, msg in actions:
                logs.append(f"[{'OK' if ok else 'WARN'}] {msg}")
            return True, logs
        except Exception as e:
            return False, [f"Ошибка отката: {e}"]

    @classmethod
    def create_restore_point(cls) -> tuple[bool, str]:
        if not cls.is_admin():
            return False, "Для создания точки восстановления нужны права Администратора."
        ps = "Checkpoint-Computer -Description 'AetherSuite_Backup' -RestorePointType 'MODIFY_SETTINGS'"
        ok, out = cls.run_cmd(["powershell", "-NoProfile", "-Command", ps], timeout=45)
        return ok, "Точка восстановления Windows создана!" if ok else f"Не удалось создать точку: {out}"

    # ---------------- ТВИКИ ----------------
    @classmethod
    def set_power_plan(cls, mode: str) -> tuple[bool, str]:
        plans = {
            "ultimate": "e9a42b02-d5df-448d-aa00-03f14749eb61",
            "high": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
            "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
            "saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
        }
        guid = plans.get(mode, plans["balanced"])
        if mode == "ultimate":
            cls.run_cmd(["powercfg", "-duplicatescheme", guid])
        ok, out = cls.run_cmd(["powercfg", "/setactive", guid])
        return ok, f"Схема питания: {mode.upper()}" if ok else f"Ошибка схемы питания: {out}"

    @classmethod
    def set_dark_mode(cls, enabled: bool) -> tuple[bool, str]:
        val = 0 if enabled else 1
        path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        ok1, m1 = cls.set_reg(winreg.HKEY_CURRENT_USER, path, "AppsUseLightTheme", val)
        ok2, m2 = cls.set_reg(winreg.HKEY_CURRENT_USER, path, "SystemUsesLightTheme", val)
        if ok1 and ok2:
            return True, "Тёмная тема включена" if enabled else "Светлая тема включена"
        return False, f"Ошибка темы: {m1}; {m2}"

    @classmethod
    def set_transparency(cls, enabled: bool) -> tuple[bool, str]:
        path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        return cls.set_reg(winreg.HKEY_CURRENT_USER, path, "EnableTransparency", 1 if enabled else 0)

    @classmethod
    def set_show_extensions(cls, show: bool) -> tuple[bool, str]:
        path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        return cls.set_reg(winreg.HKEY_CURRENT_USER, path, "HideFileExt", 0 if show else 1)

    @classmethod
    def set_show_hidden(cls, show: bool) -> tuple[bool, str]:
        path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        return cls.set_reg(winreg.HKEY_CURRENT_USER, path, "Hidden", 1 if show else 2)

    @classmethod
    def set_taskbar_align(cls, align: str) -> tuple[bool, str]:
        val = 0 if align == "left" else 1
        path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        return cls.set_reg(winreg.HKEY_CURRENT_USER, path, "TaskbarAl", val)

    @classmethod
    def set_bing_search(cls, disable: bool) -> tuple[bool, str]:
        path = r"Software\Policies\Microsoft\Windows\Explorer"
        return cls.set_reg(winreg.HKEY_CURRENT_USER, path, "DisableSearchBoxSuggestions", 1 if disable else 0)

    @classmethod
    def set_game_dvr(cls, disable: bool) -> tuple[bool, str]:
        val = 0 if disable else 1
        ok1, _ = cls.set_reg(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore", "GameDVR_Enabled", val)
        ok2, _ = cls.set_reg(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", val)
        return (ok1 and ok2), "GameDVR отключён" if disable else "GameDVR включён"

    @classmethod
    def set_telemetry(cls, disable: bool) -> tuple[bool, str]:
        return cls.set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0 if disable else 1)

    @classmethod
    def set_clipboard_history(cls, enabled: bool) -> tuple[bool, str]:
        return cls.set_reg(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Clipboard", "EnableClipboardHistory", 1 if enabled else 0)

    @classmethod
    def set_developer_mode(cls, enabled: bool) -> tuple[bool, str]:
        return cls.set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock", "AllowDevelopmentWithoutDevLicense", 1 if enabled else 0)

    @classmethod
    def set_mouse_acceleration(cls, disable: bool) -> tuple[bool, str]:
        path = r"Control Panel\Mouse"
        ok1, _ = cls.set_reg(winreg.HKEY_CURRENT_USER, path, "MouseSpeed", "0" if disable else "1", winreg.REG_SZ)
        ok2, _ = cls.set_reg(winreg.HKEY_CURRENT_USER, path, "MouseThreshold1", "0" if disable else "6", winreg.REG_SZ)
        ok3, _ = cls.set_reg(winreg.HKEY_CURRENT_USER, path, "MouseThreshold2", "0" if disable else "10", winreg.REG_SZ)
        return (ok1 and ok2 and ok3), "Ускорение мыши отключено (Raw)" if disable else "Ускорение мыши включено"

    @classmethod
    def set_visual_performance(cls, fast: bool) -> tuple[bool, str]:
        return cls.set_reg(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting", 2 if fast else 0)

    @classmethod
    def set_menu_delay(cls, delay_ms: int) -> tuple[bool, str]:
        return cls.set_reg(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", "MenuShowDelay", str(delay_ms), winreg.REG_SZ)

    @classmethod
    def restart_explorer(cls) -> tuple[bool, str]:
        cls.run_cmd(["taskkill", "/f", "/im", "explorer.exe"])
        subprocess.Popen(["explorer.exe"])
        return True, "Проводник (explorer.exe) перезапущен"

    # ---------------- ОЧИСТКА TEMP И КОРЗИНЫ ----------------
    @classmethod
    def scan_temp_files(cls) -> tuple[int, float]:
        folders = [tempfile.gettempdir(), os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp")]
        count, total_bytes = 0, 0
        for folder in folders:
            if not os.path.exists(folder):
                continue
            for root_dir, _, files in os.walk(folder):
                for f in files:
                    try:
                        total_bytes += os.path.getsize(os.path.join(root_dir, f))
                        count += 1
                    except Exception:
                        pass
        return count, total_bytes / (1024 * 1024)

    @classmethod
    def clean_temp_files(cls) -> tuple[bool, str]:
        folders = [tempfile.gettempdir(), os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp")]
        deleted, skipped, freed = 0, 0, 0
        for folder in folders:
            if not os.path.exists(folder):
                continue
            for root_dir, dirs, files in os.walk(folder):
                for f in files:
                    fp = os.path.join(root_dir, f)
                    try:
                        sz = os.path.getsize(fp)
                        os.remove(fp)
                        deleted += 1
                        freed += sz
                    except Exception:
                        skipped += 1
                for d in dirs:
                    try:
                        shutil.rmtree(os.path.join(root_dir, d), ignore_errors=False)
                    except Exception:
                        pass
        return True, f"Удалено: {deleted} файлов ({freed / (1024**2):.1f} МБ), пропущено (занято/права): {skipped}"

    @staticmethod
    def empty_recycle_bin() -> tuple[bool, str]:
        try:
            # SHERB_NOCONFIRMATION (1) | SHERB_NOPROGRESSUI (2) | SHERB_NOSOUND (4)
            res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
            if res == 0:
                return True, "Корзина успешно очищена"
            return False, "Корзина уже пуста или ошибка доступа"
        except Exception as e:
            return False, f"Ошибка очистки корзины: {e}"

    # ---------------- АВТОЗАГРУЗКА ----------------
    @staticmethod
    def get_startup_items() -> list[dict]:
        items = []
        run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        disabled_path = r"Software\Microsoft\Windows\CurrentVersion\Run_AetherDisabled"

        for root, scope in ((winreg.HKEY_CURRENT_USER, "HKCU"), (winreg.HKEY_LOCAL_MACHINE, "HKLM")):
            for path, enabled in ((run_path, True), (disabled_path, False)):
                try:
                    key = winreg.OpenKey(root, path, 0, winreg.KEY_READ)
                    idx = 0
                    while True:
                        try:
                            name, val, _ = winreg.EnumValue(key, idx)
                            items.append({"name": name, "command": str(val), "scope": scope, "enabled": enabled})
                            idx += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except Exception:
                    pass
        return items

    @staticmethod
    def toggle_startup_item(name: str, scope: str, enable: bool) -> tuple[bool, str]:
        root = winreg.HKEY_CURRENT_USER if scope == "HKCU" else winreg.HKEY_LOCAL_MACHINE
        run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        dis_path = r"Software\Microsoft\Windows\CurrentVersion\Run_AetherDisabled"
        src, dst = (dis_path, run_path) if enable else (run_path, dis_path)
        try:
            k_src = winreg.OpenKey(root, src, 0, winreg.KEY_ALL_ACCESS)
            val, rtype = winreg.QueryValueEx(k_src, name)
            k_dst = winreg.CreateKeyEx(root, dst, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k_dst, name, 0, rtype, val)
            winreg.CloseKey(k_dst)
            winreg.DeleteValue(k_src, name)
            winreg.CloseKey(k_src)
            return True, f"Автозагрузка '{name}': {'включена' if enable else 'отключена'}"
        except PermissionError:
            return False, f"Нужны права Администратора для изменения {scope}\\{name}"
        except Exception as e:
            return False, f"Ошибка автозагрузки ({name}): {e}"

    # ---------------- СЛУЖБЫ WINDOWS ----------------
    @classmethod
    def get_services_status(cls) -> list[dict]:
        res = []
        for svc_id, title, desc in SAFE_SERVICES:
            ok, out = cls.run_cmd(["sc", "query", svc_id], timeout=4)
            state = "Неизвестно"
            if ok:
                if "RUNNING" in out:
                    state = "Работает"
                elif "STOPPED" in out:
                    state = "Остановлена"
            res.append({"id": svc_id, "title": title, "desc": desc, "state": state})
        return res

    @classmethod
    def set_service_state(cls, svc_id: str, enable: bool) -> tuple[bool, str]:
        if enable:
            cls.run_cmd(["sc", "config", svc_id, "start=", "auto"])
            ok, out = cls.run_cmd(["sc", "start", svc_id])
            return ok, f"Служба {svc_id} запущена" if ok else f"Ошибка запуска {svc_id}: {out}"
        else:
            cls.run_cmd(["sc", "stop", svc_id])
            ok, out = cls.run_cmd(["sc", "config", svc_id, "start=", "disabled"])
            return ok, f"Служба {svc_id} отключена" if ok else f"Нужен Админ для {svc_id}: {out}"

    # ---------------- СЕТЬ ----------------
    @classmethod
    def flush_dns(cls) -> tuple[bool, str]:
        ok, out = cls.run_cmd(["ipconfig", "/flushdns"])
        return ok, "DNS-кэш очищен" if ok else f"Ошибка DNS: {out}"

    @classmethod
    def reset_winsock(cls) -> tuple[bool, str]:
        ok, out = cls.run_cmd(["netsh", "winsock", "reset"])
        return ok, "Стек Winsock сброшен (нужна перезагрузка)" if ok else f"Нужен Админ: {out}"

    @classmethod
    def set_dns_provider(cls, provider: str) -> tuple[bool, str]:
        if not cls.is_admin():
            return False, "Для смены DNS нужны права Администратора."
        dns_map = {
            "cloudflare": ("1.1.1.1", "1.0.0.1"),
            "google": ("8.8.8.8", "8.8.4.4"),
            "auto": None
        }
        ps_iface = "(Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object -First 1).Name"
        ok, iface = cls.run_cmd(["powershell", "-NoProfile", "-Command", ps_iface])
        if not ok or not iface:
            return False, "Активный сетевой адаптер не найден."
        if dns_map.get(provider) is None:
            ok2, out2 = cls.run_cmd(["netsh", "interface", "ip", "set", "dns", f"name={iface}", "source=dhcp"])
            return ok2, f"DNS для '{iface}' сброшен на Авто (DHCP)" if ok2 else out2
        p1, p2 = dns_map[provider]
        ok1, _ = cls.run_cmd(["netsh", "interface", "ip", "set", "dns", f"name={iface}", "static", p1])
        cls.run_cmd(["netsh", "interface", "ip", "add", "dns", f"name={iface}", p2, "index=2"])
        return ok1, f"Установлен DNS {provider.upper()} ({p1}, {p2}) для '{iface}'"

    @classmethod
    def ping_host(cls, host: str = "1.1.1.1") -> str:
        ok, out = cls.run_cmd(["ping", "-n", "2", "-w", "1000", host], timeout=5)
        if not ok:
            return f"{host}: недоступен"
        for line in out.splitlines():
            if "ms" in line or "мс" in line:
                if "Average" in line or "Среднее" in line:
                    return f"{host} → {line.strip()}"
        return f"{host}: ответ получен"
