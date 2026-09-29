"""記錄測試環境（硬體、套件版本、Jetson 功耗模式），寫入每次 run 的 run.json。"""
import datetime
import platform
import shutil
import subprocess
from importlib import metadata
from pathlib import Path

import psutil

PACKAGES = [
    "numpy", "torch", "onnxruntime", "onnxruntime-gpu", "ctranslate2", "faster-whisper",
    "transformers", "nemo_toolkit", "kokoro", "piper-tts", "melotts", "coqui-tts",
    "chatterbox-tts", "llama_cpp_python", "jiwer",
]


def _cpu_name() -> str:
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError:
            pass
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(errors="ignore").splitlines():
            if line.lower().startswith(("model name", "hardware")):
                return line.split(":", 1)[1].strip()
    return platform.processor() or platform.machine()


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return None


def collect_env() -> dict:
    freq = psutil.cpu_freq()
    env = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": _cpu_name(),
        "cpu_physical": psutil.cpu_count(logical=False),
        "cpu_logical": psutil.cpu_count(logical=True),
        "cpu_freq_mhz": round(freq.current) if freq else None,
        "ram_total_gb": round(psutil.virtual_memory().total / 1e9, 1),
        "python": platform.python_version(),
        "on_battery": None,
        "packages": {},
    }
    battery = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    if battery is not None:
        env["on_battery"] = not battery.power_plugged
    for pkg in PACKAGES:
        try:
            env["packages"][pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            pass
    tegra = Path("/etc/nv_tegra_release")
    if tegra.exists():
        env["jetson_release"] = tegra.read_text().strip()
        if shutil.which("nvpmodel"):
            env["jetson_nvpmodel"] = _run(["nvpmodel", "-q"])
    return env
