"""資源監控：背景執行緒定時取樣。

- 所有平台：本程序（含子程序）RSS、CPU 使用率
- Jetson：另外解析 tegrastats（系統 RAM、GPU 使用率、VDD_IN 總功耗）
- 有 PyTorch CUDA 時：torch.cuda.max_memory_allocated
"""
import os
import re
import shutil
import subprocess
import sys
import threading

import psutil

_RE_RAM = re.compile(r"RAM (\d+)/(\d+)MB")
_RE_GPU = re.compile(r"GR3D_FREQ (\d+)%")
_RE_PWR = re.compile(r"VDD_IN (\d+)mW")


class ResourceMonitor:
    def __init__(self, interval_s: float = 0.05):
        self.interval = interval_s
        self.proc = psutil.Process(os.getpid())
        self._stop = threading.Event()
        self._thread = None
        self._tegra = None
        self._tegra_thread = None
        self.baseline_rss_mb = self.current_rss_mb()
        self.peak_rss_mb = self.baseline_rss_mb
        self.cpu_samples = []
        self.sys_ram_mb = []
        self.gpu_pct = []
        self.power_mw = []

    def current_rss_mb(self) -> float:
        rss = self.proc.memory_info().rss
        for child in self.proc.children(recursive=True):
            try:
                rss += child.memory_info().rss
            except psutil.Error:
                pass
        return rss / 1e6

    def _loop(self):
        self.proc.cpu_percent(None)
        while not self._stop.wait(self.interval):
            try:
                self.peak_rss_mb = max(self.peak_rss_mb, self.current_rss_mb())
                self.cpu_samples.append(self.proc.cpu_percent(None))
            except psutil.Error:
                pass

    def _tegra_loop(self):
        for line in self._tegra.stdout:
            if m := _RE_RAM.search(line):
                self.sys_ram_mb.append(int(m.group(1)))
            if m := _RE_GPU.search(line):
                self.gpu_pct.append(int(m.group(1)))
            if m := _RE_PWR.search(line):
                self.power_mw.append(int(m.group(1)))

    def start(self):
        if "torch" in sys.modules:
            torch = sys.modules["torch"]
            if torch.cuda.is_available():
                torch.cuda.reset_peak_memory_stats()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        if shutil.which("tegrastats"):
            self._tegra = subprocess.Popen(
                ["tegrastats", "--interval", "100"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            )
            self._tegra_thread = threading.Thread(target=self._tegra_loop, daemon=True)
            self._tegra_thread.start()
        return self

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join()
        if self._tegra:
            self._tegra.terminate()
            self._tegra.wait()

    def result(self) -> dict:
        n_cpu = psutil.cpu_count(logical=True) or 1
        res = {
            "baseline_rss_mb": round(self.baseline_rss_mb, 1),
            "peak_ram_mb": round(self.peak_rss_mb, 1),
            "ram_delta_mb": round(self.peak_rss_mb - self.baseline_rss_mb, 1),
            # cpu_percent 以單核 100% 計；除以邏輯核數得到整機占比
            "avg_cpu_pct": round(sum(self.cpu_samples) / len(self.cpu_samples) / n_cpu, 1)
            if self.cpu_samples else None,
            "peak_vram_mb": None,
            "peak_sys_ram_mb": max(self.sys_ram_mb) if self.sys_ram_mb else None,
            "sys_ram_delta_mb": (max(self.sys_ram_mb) - self.sys_ram_mb[0]) if self.sys_ram_mb else None,
            "avg_gpu_pct": round(sum(self.gpu_pct) / len(self.gpu_pct), 1) if self.gpu_pct else None,
            "avg_power_w": round(sum(self.power_mw) / len(self.power_mw) / 1000, 2) if self.power_mw else None,
        }
        if "torch" in sys.modules:
            torch = sys.modules["torch"]
            if torch.cuda.is_available():
                res["peak_vram_mb"] = round(torch.cuda.max_memory_allocated() / 1e6, 1)
        return res
