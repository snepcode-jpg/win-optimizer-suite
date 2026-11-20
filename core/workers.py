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
import time
import math
import tempfile
import datetime
from concurrent.futures import ProcessPoolExecutor

from PySide6.QtCore import QThread, Signal
from core.engine import WindowsTweaker

BENCH_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "aether_benchmarks.json")


def _cpu_math_worker(iterations: int) -> float:
    acc = 0.0
    for i in range(1, iterations):
        acc += math.sqrt(i) * math.sin(i % 360) + math.cos(i % 180)
    return acc


class GpuWorker(QThread):
    """Асинхронный опрос NVIDIA GPU раз в 3 секунды. Отключается сам, если GPU нет."""
    gpu_data = Signal(bool, str, int, str, str)  # ok, name, util, mem_str, temp_str

    def __init__(self):
        super().__init__()
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            ok, out = WindowsTweaker.run_cmd([
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits"
            ], timeout=2)
            if ok and out:
                parts = [p.strip() for p in out.splitlines()[0].split(",")]
                if len(parts) >= 5:
                    name, util, mem_u, mem_t, temp = parts[:5]
                    self.gpu_data.emit(True, name, int(float(util)), f"{mem_u}/{mem_t} МБ", f"{temp}°C")
                else:
                    self.gpu_data.emit(False, "N/A", 0, "", "")
            else:
                self.gpu_data.emit(False, "NVIDIA GPU не найдена", 0, "", "")
                break  # Не дёргаем систему повторно, если нет NVIDIA
            for _ in range(30):
                if not self._running:
                    break
                time.sleep(0.1)


class BenchmarkWorker(QThread):
    progress = Signal(int, str)
    finished_result = Signal(dict)

    def __init__(self, mode: str = "all"):
        super().__init__()
        self.mode = mode

    def run(self):
        results = {}
        total_score = 0

        if self.mode in ("all", "cpu_single"):
            self.progress.emit(12, "Тест CPU (Single-Core)...")
            iters = 4_500_000
            t0 = time.perf_counter()
            _cpu_math_worker(iters)
            dt = max(time.perf_counter() - t0, 0.001)
            score = int((iters / dt) / 1000)
            results["CPU Single-Core"] = f"{score} pts ({dt:.2f} сек)"
            total_score += score

        if self.mode in ("all", "cpu_multi"):
            cores = os.cpu_count() or 4
            self.progress.emit(38, f"Тест CPU (Multi-Core, {cores} потоков)...")
            iters_per_worker = 3_500_000
            t0 = time.perf_counter()
            with ProcessPoolExecutor(max_workers=cores) as ex:
                list(ex.map(_cpu_math_worker, [iters_per_worker] * cores))
            dt = max(time.perf_counter() - t0, 0.001)
            score = int(((iters_per_worker * cores) / dt) / 1000)
            results[f"CPU Multi-Core ({cores}T)"] = f"{score} pts ({dt:.2f} сек)"
            total_score += int(score * 0.5)

        if self.mode in ("all", "ram"):
            self.progress.emit(68, "Тест RAM (оценка пропускной способности Python)...")
            size_mb = 256
            size_bytes = size_mb * 1024 * 1024
            t0 = time.perf_counter()
            buf = bytearray(size_bytes)
            buf[:] = b"\xAA" * size_bytes
            copy_buf = bytearray(buf)
            dt = max(time.perf_counter() - t0, 0.001)
            del buf, copy_buf
            speed_gb = (size_mb * 2 / 1024) / dt
            score = int(speed_gb * 1200)
            results["RAM (оценка Python)"] = f"{speed_gb:.2f} ГБ/с ({score} pts)"
            total_score += score

        if self.mode in ("all", "disk"):
            self.progress.emit(88, "Тест Диска (запись/чтение 128 МБ)...")
            test_file = os.path.join(tempfile.gettempdir(), "aether_bench_tmp.bin")
            chunk = os.urandom(1024 * 1024)
            chunks = 128
            try:
                t0 = time.perf_counter()
                with open(test_file, "wb") as f:
                    for _ in range(chunks):
                        f.write(chunk)
                    f.flush()
                    os.fsync(f.fileno())
                w_speed = chunks / max(time.perf_counter() - t0, 0.001)

                t1 = time.perf_counter()
                with open(test_file, "rb") as f:
                    while f.read(1024 * 1024):
                        pass
                r_speed = chunks / max(time.perf_counter() - t1, 0.001)

                score = int((w_speed + r_speed) * 1.5)
                results["Disk Write"] = f"{w_speed:.1f} МБ/с"
                results["Disk Read"] = f"{r_speed:.1f} МБ/с"
                total_score += score
            except Exception as e:
                results["Disk"] = f"Ошибка: {e}"
            finally:
                if os.path.exists(test_file):
                    try:
                        os.remove(test_file)
                    except Exception:
                        pass

        results["ОБЩИЙ БАЛЛ"] = f"{total_score} pts"
        if self.mode == "all":
            self._save_history(total_score, results)

        self.progress.emit(100, "Бенчмарк завершён!")
        self.finished_result.emit(results)

    @staticmethod
    def _save_history(total_score: int, results: dict):
        history = []
        if os.path.exists(BENCH_HISTORY_FILE):
            try:
                with open(BENCH_HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                pass
        history.append({
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "score": total_score,
            "details": results
        })
        with open(BENCH_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-15:], f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_history() -> list[dict]:
        if not os.path.exists(BENCH_HISTORY_FILE):
            return []
        try:
            with open(BENCH_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


class SessionHistoryWorker(QThread):
    loaded = Signal(list)

    def run(self):
        ps_cmd = (
            "Get-WinEvent -FilterHashtable @{LogName='System'; Id=6005,6006,6008,7001,7002,1074} "
            "-MaxEvents 40 -ErrorAction SilentlyContinue | "
            "ForEach-Object { \"$($_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss'))|$($_.Id)|$($_.ProviderName)\" }"
        )
        ok, out = WindowsTweaker.run_cmd(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=12)
        rows = []
        id_map = {
            "6005": "Запуск системы",
            "6006": "Корректное выключение",
            "6008": "Неожиданное завершение работы",
            "7001": "Вход пользователя",
            "7002": "Выход пользователя",
            "1074": "Перезагрузка / Выключение по запросу",
        }
        if ok and out:
            for line in out.splitlines():
                parts = line.split("|")
                if len(parts) >= 3:
                    rows.append((parts[0], parts[1], id_map.get(parts[1], f"Событие #{parts[1]}"), parts[2]))
        self.loaded.emit(rows)


class DiskAnalyzerWorker(QThread):
    finished_scan = Signal(list)

    def __init__(self, target_dir: str):
        super().__init__()
        self.target_dir = target_dir

    def run(self):
        large_files = []
        min_bytes = 50 * 1024 * 1024  # Файлы больше 50 МБ
        for root_dir, _, files in os.walk(self.target_dir):
            for f in files:
                fp = os.path.join(root_dir, f)
                try:
                    sz = os.path.getsize(fp)
                    if sz >= min_bytes:
                        large_files.append((sz / (1024 * 1024), fp))
                except Exception:
                    pass
        large_files.sort(key=lambda x: x[0], reverse=True)
        self.finished_scan.emit(large_files[:40])
