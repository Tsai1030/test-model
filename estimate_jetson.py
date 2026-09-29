"""開發機 → Jetson Orin NX 速度換算。

  # 1) 產生預估：把 pc / colab-t4 的結果依 backend_category 除以係數 k，寫入 results/_estimates/summary.csv
  python estimate_jetson.py

  # 2) 拿到 Jetson 後校準：同一批錨點模型在兩台機器的結果 → 經驗係數，寫入 configs/calibration.yaml
  python estimate_jetson.py --calibrate --source results/<pc_run> --target results/<jetson_run>
  python estimate_jetson.py          # 用校準後的係數重新預估

只換算速度類指標；準確度、MOS 與硬體無關，直接沿用。記憶體沿用開發機數值（Jetson 為共用記憶體，實測為準）。
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent
CAL_PATH = ROOT / "configs" / "calibration.yaml"
EST_DIR = ROOT / "results" / "_estimates"

DIVIDE_COLS = ["rtf_p50", "rtf_p90", "latency_ms_p50", "latency_ms_p90", "ttfa_ms_p50", "ttfa_ms_p90",
               "first_partial_ms_p50", "stream_final_ms_p50"]
DROP_COLS = ["avg_cpu_pct", "avg_gpu_pct", "avg_power_w", "load_time_s"]


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_factors():
    hw = load_yaml(ROOT / "configs" / "hardware.yaml")
    factors = hw["estimate"]["factors"]
    if CAL_PATH.exists():
        for profile, cats in (load_yaml(CAL_PATH) or {}).items():
            factors.setdefault(profile, {}).update(cats)
    return hw["estimate"]["target_profile"], factors


def read_summaries(paths=None):
    paths = paths or [p for p in (ROOT / "results").glob("*/summary.csv") if p.parent.name != "_estimates"]
    frames = [pd.read_csv(p) for p in paths]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ---------------------------------------------------------------- estimate
def estimate():
    target, factors = load_factors()
    df = read_summaries()
    if df.empty:
        raise SystemExit("沒有可換算的 summary.csv")
    src = df[df.hw_profile.isin(list(factors)) & ~df.is_estimated.astype(bool) & df.lang.notna()]
    out, warned = [], set()

    def factor(profile, cat):
        f = factors.get(profile, {}).get(cat)
        if f is None and (profile, cat) not in warned:
            warned.add((profile, cat))
            print(f"!! 沒有 {profile}/{cat} 的換算係數，略過")
        return f

    for _, r in src.iterrows():
        row = r.to_dict()
        if row["task"] in ("stt", "tts"):
            f = factor(row["hw_profile"], row["backend_category"])
            if f is None:
                continue
            for c in DIVIDE_COLS:
                if pd.notna(row.get(c)):
                    row[c] = round(row[c] / f["k"], 4)
            row["backend_category"] = f["jetson_backend"]
            row["est_note"] = f"k={f['k']} ({f['source']})"
        elif row["task"] == "dialogue":
            fs = {p: factor(row["hw_profile"], row[f"{p}_category"]) for p in ("stt", "llm", "tts")}
            if any(v is None for v in fs.values()):
                continue
            stt = row["stt_ms_p50"] / fs["stt"]["k"]
            llm_first = row["llm_first_sentence_ms_p50"] / fs["llm"]["k"]
            tts = row["tts_ttfa_ms_p50"] / fs["tts"]["k"]
            new_p50 = row["vad_endpoint_ms"] + stt + llm_first + tts
            ratio = (new_p50 - row["vad_endpoint_ms"]) / max(row["turn_latency_ms_p50"] - row["vad_endpoint_ms"], 1e-6)
            row.update({
                "stt_ms_p50": round(stt, 1), "llm_first_sentence_ms_p50": round(llm_first, 1),
                "llm_ttft_ms_p50": round(row["llm_ttft_ms_p50"] / fs["llm"]["k"], 1),
                "llm_tok_s": round(row["llm_tok_s"] * fs["llm"]["k"], 2),
                "tts_ttfa_ms_p50": round(tts, 1), "turn_latency_ms_p50": round(new_p50, 1),
                "turn_latency_ms_p90": round(row["vad_endpoint_ms"] + (row["turn_latency_ms_p90"] - row["vad_endpoint_ms"]) * ratio, 1),
                "est_note": " / ".join(f"{p} k={fs[p]['k']} ({fs[p]['source']})" for p in fs),
            })
            for p in ("stt", "llm", "tts"):
                row[f"{p}_category"] = fs[p]["jetson_backend"]
        else:
            continue
        for c in DROP_COLS:
            row[c] = None
        row.update({"run_id": f"est:{row['run_id']}", "hw_profile": target, "is_estimated": True})
        out.append(row)

    EST_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(out).to_csv(EST_DIR / "summary.csv", index=False, encoding="utf-8-sig")
    print(f"wrote {EST_DIR / 'summary.csv'} ({len(out)} rows)")


# ---------------------------------------------------------------- calibrate
def calibrate(source_dir, target_dir):
    anchors = load_yaml(ROOT / "configs" / "anchors.yaml")["anchors"]
    mapping = {a["source"]: a["target"] for a in anchors}
    s = read_summaries([Path(source_dir) / "summary.csv"])
    t = read_summaries([Path(target_dir) / "summary.csv"])
    src_profile = s.hw_profile.iloc[0]

    def map_name(name):
        return "+".join(mapping.get(p, p) for p in name.split("+"))

    ratios = {}   # (source_category, target_category) -> [k...]
    keys = ["task", "lang", "dataset", "condition"]
    for _, r in s.iterrows():
        if r.task in ("stt", "tts") and r.model not in mapping:
            continue
        m = t[(t.model == map_name(r.model)) & (t[keys] == r[keys]).all(axis=1)]
        if m.empty:
            continue
        tr = m.iloc[0]
        if r.task in ("stt", "tts") and pd.notna(r.rtf_p50) and pd.notna(tr.rtf_p50) and tr.rtf_p50 > 0:
            ratios.setdefault((r.backend_category, tr.backend_category), []).append(r.rtf_p50 / tr.rtf_p50)
        elif r.task == "dialogue" and r.model.split("+")[1] in mapping:
            if pd.notna(r.llm_first_sentence_ms_p50) and tr.llm_first_sentence_ms_p50 > 0:
                ratios.setdefault((r.llm_category, tr.llm_category), []).append(
                    r.llm_first_sentence_ms_p50 / tr.llm_first_sentence_ms_p50)

    if not ratios:
        raise SystemExit("找不到可配對的錨點結果（確認 anchors.yaml 與兩邊跑過相同語言/資料集）")

    # 驗證舊係數：用舊 k 預估的值與 Jetson 實測相比，誤差 > 30% 的類別代表理論值不可靠
    _, old = load_factors()
    for (src_cat, _), ks in ratios.items():
        f = old.get(src_profile, {}).get(src_cat)
        if f:
            errs = [abs(k / f["k"] - 1) for k in ks]   # 預估/實測 - 1 = k_實際/k_舊 - 1
            flag = "  <-- 超過 30%，已由校準值取代" if np.median(errs) > 0.3 else ""
            print(f"舊係數 {src_cat} k={f['k']} ({f['source']})：預估誤差中位數 {np.median(errs):.0%}{flag}")

    cal = load_yaml(CAL_PATH) if CAL_PATH.exists() else {}
    cal = cal or {}
    for (src_cat, tgt_cat), ks in ratios.items():
        k = float(np.median(ks))
        cal.setdefault(src_profile, {})[src_cat] = {
            "k": round(k, 3), "jetson_backend": tgt_cat,
            "source": f"calibrated n={len(ks)} spread={min(ks):.2f}-{max(ks):.2f}",
        }
        print(f"{src_profile}/{src_cat} -> {tgt_cat}: k = {k:.2f}  (n={len(ks)}, {min(ks):.2f}–{max(ks):.2f})")
    CAL_PATH.write_text(yaml.safe_dump(cal, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"wrote {CAL_PATH}；重新執行 `python estimate_jetson.py` 產生新預估。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--source")
    ap.add_argument("--target")
    args = ap.parse_args()
    if args.calibrate:
        if not (args.source and args.target):
            raise SystemExit("--calibrate 需要 --source 與 --target")
        calibrate(args.source, args.target)
    else:
        estimate()


if __name__ == "__main__":
    main()
