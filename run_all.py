"""一次跑完一整輪評測：準備資料 → 冒煙測試 → 正式測試（run + score）→ Jetson 換算 → 報告。

  python run_all.py --plan configs/plans/round1.yaml                # 冒煙測試通過後自動接正式測試
  python run_all.py --plan configs/plans/round1.yaml --smoke-only   # 只跑冒煙測試（順便下載好所有模型）
  python run_all.py --plan configs/plans/round1.yaml --skip-smoke
  python run_all.py --plan configs/plans/round1.yaml --only stt --langs es-ES pt-PT   # 補跑部分
  python run_all.py --plan configs/plans/round1.yaml --dry-run      # 只列出會執行的指令

冒煙測試：每個步驟只跑 1–2 句，結果放在 results/_smoke/（不進報告）。
任何模型載入、執行或評分失敗就停下，避免整晚跑完才發現錯誤。
正式測試：單一步驟失敗會記錄後繼續下一步；每完成一步就更新報告，中途中斷也有目前為止的結果。
log：logs/<plan>_<時間>.log
"""
import argparse
import datetime
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
PY = sys.executable


class Log:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.f = open(path, "a", encoding="utf-8")

    def __call__(self, msg=""):
        print(msg, flush=True)
        self.f.write(msg + "\n")
        self.f.flush()


def keep_awake(on):
    """Windows：執行期間不讓系統自動睡眠（螢幕仍可關閉；闔上筆電上蓋仍會睡眠）。"""
    if os.name != "nt":
        return
    import ctypes
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))


def preflight(log):
    """正式測試前檢查背景 CPU 占用與電源：這些會讓速度數據失真（只警告，不中止）。"""
    import psutil
    procs = [p for p in psutil.process_iter(["name"]) if p.pid != os.getpid()]
    for p in procs:
        try:
            p.cpu_percent(None)
        except psutil.Error:
            pass
    total = psutil.cpu_percent(interval=5)
    ncpu = psutil.cpu_count() or 1
    busy = []
    for p in procs:
        try:
            pct = p.cpu_percent(None) / ncpu
        except psutil.Error:
            continue
        if pct >= 2 and p.info["name"] not in ("System Idle Process",):
            busy.append((pct, p.info["name"]))
    log(f"開跑前檢查：背景 CPU 使用率 {total:.0f}%（建議 < 20%）")
    for pct, name in sorted(busy, reverse=True)[:6]:
        log(f"    {name:28s} {pct:5.1f}%")
    battery = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    if battery is not None and not battery.power_plugged:
        log("警告：目前使用電池，CPU 會降頻。請接上電源")
    if os.name == "nt":
        scheme = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True,
                                errors="replace").stdout.strip()
        log(f"    電源配置：{scheme}")
    if total >= 20:
        log("警告：背景程式占用 CPU，速度數據（RTF、延遲）會偏慢且不穩定。建議關閉瀏覽器下載、工作管理員，"
            "並把專案資料夾排除在 Windows 搜尋索引之外")


def fmt_dur(sec):
    h, rem = divmod(int(sec), 3600)
    return f"{h}h{rem // 60:02d}m" if h else f"{rem // 60}m{rem % 60:02d}s"


def run_cmd(cmd, log, dry):
    """執行子程序，輸出同時寫入 log；回傳 (exit code, 以 '!!' 開頭的警告行)。"""
    cmd = [str(c) for c in cmd]
    log(f"$ {' '.join(cmd)}")
    if dry:
        return 0, []
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1",
           "HF_HUB_DISABLE_SYMLINKS_WARNING": "1"}
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    alerts = []
    for line in proc.stdout:
        line = line.rstrip("\n")
        log(line)
        if line.lstrip().startswith("!!"):      # run.py 以 "!!" 標示模型載入 / 執行失敗
            alerts.append(line.strip())
    return proc.wait(), alerts


def run_step(step, run_id, hw, limit, langs, log, dry):
    """run.py 推論 + score.py 評分。回傳 (exit code, 警告行)。"""
    cmd = [PY, "run.py", "--suite", step["suite"], "--hw", hw, "--run-id", run_id]
    if step.get("models"):
        cmd += ["--models", *step["models"]]
    if langs:
        cmd += ["--langs", *langs]
    if limit:
        cmd += ["--limit", limit]
    code, alerts = run_cmd(cmd, log, dry)
    if code != 0:
        return code, alerts
    code, more = run_cmd([PY, "score.py", f"results/{run_id}", *step.get("score", [])], log, dry)
    return code, alerts + more


def prepare_data(plan, log, dry):
    prep = plan.get("prepare") or {}
    fl = prep.get("fleurs")
    if fl:
        missing = [l for l in fl["langs"] if not (ROOT / "data" / "manifests" / l / "fleurs.jsonl").exists()]
        if missing:
            log(f"== 準備資料：FLEURS {missing}")
            run_cmd([PY, "data/prepare_fleurs.py", "--langs", *missing, "--n", fl.get("n", 300)], log, dry)
    for cv in prep.get("commonvoice") or []:
        if (ROOT / "data" / "manifests" / cv["lang"] / "commonvoice.jsonl").exists():
            continue
        if not Path(cv["archive"]).exists():
            log(f"== 略過 Common Voice {cv['lang']}：找不到 {cv['archive']}")
            continue
        log(f"== 準備資料：Common Voice {cv['lang']}")
        run_cmd([PY, "data/prepare_commonvoice.py", "--cv", cv["archive"], "--lang", cv["lang"],
                 "--split", *cv.get("split", ["test", "dev"]), "--match", *cv["match"],
                 "--n", cv.get("n", 300), "--max-per-speaker", cv.get("max_per_speaker", 10),
                 *(["--exclude-word-lists"] if cv.get("exclude_word_lists") else [])], log, dry)


def banner(log, text):
    log("")
    log("=" * 72)
    log(text)
    log("=" * 72)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--hw", help="覆蓋 plan 裡的硬體 profile")
    ap.add_argument("--only", nargs="+", help="只跑這些步驟（plan 裡的 name）")
    ap.add_argument("--langs", nargs="+", help="只跑這些語言")
    ap.add_argument("--smoke-only", action="store_true")
    ap.add_argument("--skip-smoke", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(args.plan, encoding="utf-8") as f:
        plan = yaml.safe_load(f)
    hw = args.hw or plan["hw"]
    steps = [s for s in plan["steps"] if not args.only or s["name"] in args.only]
    stamp = f"{datetime.datetime.now():%Y%m%d-%H%M%S}"
    log = Log(ROOT / "logs" / f"{plan['name']}_{stamp}.log")
    log(f"plan={args.plan} hw={hw} steps={[s['name'] for s in steps]} log={log.path}")

    keep_awake(True)
    t_all = time.time()
    try:
        prepare_data(plan, log, args.dry_run)

        if not args.skip_smoke:
            banner(log, "冒煙測試：每個步驟只跑 1–2 句，確認所有模型都能下載、載入、執行、評分")
            failed = []
            for step in steps:
                sm = step.get("smoke") or {}
                code, alerts = run_step(step, f"_smoke/{stamp}_{step['name']}", hw, sm.get("limit", 2),
                                        args.langs or sm.get("langs") or step.get("langs"), log, args.dry_run)
                if code or alerts:
                    failed.append((step["name"], code, alerts))
            if failed:
                banner(log, "冒煙測試失敗，正式測試未執行。請修正後重跑：")
                for name, code, alerts in failed:
                    log(f"  [{name}] exit={code}")
                    for a in alerts:
                        log(f"      {a}")
                log(f"完整 log：{log.path}")
                return 1
            log("冒煙測試全部通過")
        if args.smoke_only:
            return 0

        if not args.dry_run:
            preflight(log)
        done = []
        for i, step in enumerate(steps, 1):
            run_id = f"{stamp}_{plan['name']}_{step['name']}_{hw}"
            banner(log, f"[{i}/{len(steps)}] {step['name']}  →  results/{run_id}")
            t = time.time()
            # step 可自訂 limit（每組句數）與 langs；命令列 --langs 優先
            code, alerts = run_step(step, run_id, hw, step.get("limit"), args.langs or step.get("langs"),
                                    log, args.dry_run)
            done.append((step["name"], run_id, code, alerts, time.time() - t))
            # 每步都更新報告：中途中斷也有目前為止的結果
            run_cmd([PY, "estimate_jetson.py"], log, args.dry_run)
            run_cmd([PY, "report.py"], log, args.dry_run)

        banner(log, f"全部完成，共 {fmt_dur(time.time() - t_all)}")
        for name, run_id, code, alerts, dt in done:
            status = "OK" if code == 0 and not alerts else f"有問題 (exit={code}, 警告 {len(alerts)} 則)"
            log(f"  {name:10s} {fmt_dur(dt):>8s}  {status}  results/{run_id}")
            for a in alerts:
                log(f"      {a}")
        log("報告：reports/report.md")
        log(f"log：{log.path}")
        return 0 if all(code == 0 for _, _, code, _, _ in done) else 1
    finally:
        keep_awake(False)


if __name__ == "__main__":
    sys.exit(main())
