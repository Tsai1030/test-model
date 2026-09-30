"""彙整所有 run 的 summary.csv（含 Jetson 預估），套用統一評分，輸出報告。

  python report.py                  # → reports/report.md、reports/combined.csv、reports/*.png
"""
import argparse
import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from bench import languages as L

ROOT = Path(__file__).resolve().parent
PASS_COLOR, FAIL_COLOR, INK, MUTED, GRID = "#2a78d6", "#898781", "#0b0b0b", "#52514e", "#e8e7e3"


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(v) else v


def lin(v, scale):
    """把指標線性映射到 0–100：scale = [100 分的值, 0 分的值]。"""
    v = num(v)
    if v is None:
        return None
    best, worst = scale
    return float(np.clip((v - worst) / (best - worst), 0, 1) * 100)


def weighted(components, weights):
    avail = {k: v for k, v in components.items() if v is not None}
    if not avail:
        return None, ",".join(components)
    total = sum(weights[k] for k in avail)
    score = sum(avail[k] * weights[k] for k in avail) / total
    missing = ",".join(k for k, v in components.items() if v is None)
    return round(score, 1), missing


def mem_of(row):
    vals = [num(row.get(c)) for c in ("ram_delta_mb", "peak_vram_mb", "sys_ram_delta_mb")]
    vals = [v for v in vals if v is not None]
    return max(vals) if vals else num(row.get("peak_ram_mb"))


def load_all():
    frames = []
    for p in sorted((ROOT / "results").glob("*/summary.csv")):
        frames.append(pd.read_csv(p))
    if not frames:
        raise SystemExit("找不到 results/*/summary.csv，請先執行 run.py 與 score.py")
    df = pd.concat(frames, ignore_index=True)
    # 同一組合測過多次（例如修正後重跑）只採用最新一次；run_id 以時間開頭，估算列為 "est:<run_id>"
    key = ["task", "model", "lang", "dataset", "condition", "hw_profile"]
    df = (df.assign(_order=df.run_id.astype(str).str.removeprefix("est:"))
            .sort_values("_order", kind="stable").drop_duplicates(key, keep="last"))
    return df.drop(columns="_order").reset_index(drop=True)


# ---------------------------------------------------------------- scoring
def score_rows(df, cfg):
    sc, w, gates = cfg["scales"], cfg["weights"], cfg["gates"]
    rob_cond = cfg.get("robustness_condition", "snr10")
    out = []
    for _, r in df.iterrows():
        row = r.to_dict()
        task = row["task"]
        mem = mem_of(row)
        row["mem_mb"] = mem
        if task == "stt":
            if row.get("dataset") == "silence" or row.get("condition") != "clean":
                continue    # 噪音 / 靜音結果併入乾淨語音那一列
            same = df[(df.task == "stt") & (df.model == row["model"]) & (df.lang == row["lang"])
                      & (df.dataset == row["dataset"]) & (df.hw_profile == row["hw_profile"])]
            noisy = same[same.condition == rob_cond]
            row["noisy_err_rate"] = num(noisy.err_rate.iloc[0]) if len(noisy) else None
            sil = df[(df.task == "stt") & (df.model == row["model"]) & (df.lang == row["lang"])
                     & (df.dataset == "silence") & (df.hw_profile == row["hw_profile"])]
            row["hallucination_rate"] = num(sil.hallucination_rate.iloc[0]) if len(sil) else None
            comps = {
                "accuracy": lin(row.get("err_rate"), sc["err_rate"]),
                "speed": lin(row.get("rtf_p50"), sc["rtf"]),
                "robustness": lin(row["noisy_err_rate"], sc["err_rate"]),
                "resource": lin(mem, sc["mem_mb"]),
            }
        elif task == "tts":
            nat = num(row.get("mos")) if num(row.get("mos")) is not None else num(row.get("utmos"))
            row["naturalness_src"] = "MOS" if num(row.get("mos")) is not None else ("UTMOS" if nat else None)
            comps = {
                "naturalness": lin(nat, sc["mos"]),
                "intelligibility": lin(row.get("asr_err"), sc["err_rate"]),
                "ttfa": lin(row.get("ttfa_ms_p50"), sc["ttfa_ms"]),
                "resource": lin(mem, sc["mem_mb"]),
            }
        elif task == "dialogue":
            quality_parts = [num(row.get("fact_recall")), num(row.get("lang_ok_rate"))]
            hr = num(row.get("human_relevance"))
            if hr is not None:
                quality_parts.append((hr - 1) / 4)
            quality_parts = [q for q in quality_parts if q is not None]
            nat = next((v for v in (num(row.get("human_naturalness")), num(row.get("mos")), num(row.get("utmos")))
                        if v is not None), None)
            comps = {
                "quality": lin(np.mean(quality_parts), sc["ratio"]) if quality_parts else None,
                "latency": lin(row.get("turn_latency_ms_p50"), sc["turn_latency_ms"]),
                "naturalness": lin(nat, sc["mos"]),
            }
        else:
            continue
        row["score"], row["score_missing"] = weighted(comps, w[task])
        for k, v in comps.items():
            row[f"s_{k}"] = None if v is None else round(v, 1)

        fails = []
        if isinstance(row.get("error"), str) and row["error"]:
            fails.append("error")
        if gates.get("commercial_only") and "non-commercial" in str(row.get("license", "")).lower():
            fails.append("license")
        err = {"stt": row.get("err_rate"), "tts": row.get("asr_err")}.get(task)
        if gates.get("max_err_rate") is not None and num(err) is not None and num(err) > gates["max_err_rate"]:
            fails.append("accuracy")
        if str(row["hw_profile"]).startswith("jetson") and task in ("stt", "tts"):
            rtf = num(row.get("rtf_p50"))
            if rtf is not None and rtf > gates["jetson_rtf_max"]:
                fails.append("rtf")
        budget = gates["memory_budget_mb"].get(task)
        if budget and mem is not None and mem > budget:
            fails.append("memory")
        row["gate"] = "PASS" if not fails else "FAIL:" + "+".join(fails)
        out.append(row)
    return pd.DataFrame(out)


# ---------------------------------------------------------------- markdown
def fmt(v, kind="f"):
    v = num(v)
    if v is None:
        return "–"
    if kind == "pct":
        return f"{v * 100:.1f}%"
    if kind == "int":
        return f"{v:.0f}"
    return f"{v:.2f}"


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def rank(g):
    g = g.assign(_pass=g.gate.eq("PASS"), _score=g.score.fillna(-1))
    return g.sort_values(["_pass", "_score"], ascending=False)


def section_stt(g):
    rows = []
    for i, (_, r) in enumerate(rank(g).iterrows(), 1):
        ci = f"{fmt(r.err_ci95_low, 'pct')}–{fmt(r.err_ci95_high, 'pct')}"
        metric = r.err_metric.upper() if isinstance(r.err_metric, str) else ""
        rows.append([i, r.model, r.dataset, fmt(r.score), r.gate,
                     f"{fmt(r.err_rate, 'pct')} {metric}".strip(), ci, fmt(r.noisy_err_rate, "pct"),
                     fmt(r.hallucination_rate, "pct"), fmt(r.rtf_p50), fmt(r.latency_ms_p50, "int"),
                     fmt(r.mem_mb, "int"), r.license])
    return md_table(["#", "模型", "資料集", "總分", "門檻", "錯誤率", "95% 信賴區間", "噪音錯誤率",
                     "幻覺率", "RTF p50", "延遲 ms p50", "記憶體 MB", "授權"], rows)


def section_tts(g):
    rows = []
    for i, (_, r) in enumerate(rank(g).iterrows(), 1):
        nat = r.mos if num(r.mos) is not None else r.utmos
        src = r.naturalness_src if isinstance(r.naturalness_src, str) else "–"
        rows.append([i, r.model, fmt(r.score), r.gate, f"{fmt(nat)} ({src})",
                     fmt(r.asr_err, "pct"), fmt(r.ttfa_ms_p50, "int"), fmt(r.rtf_p50),
                     fmt(r.mem_mb, "int"), r.license])
    return md_table(["#", "模型", "總分", "門檻", "自然度", "ASR 回測錯誤率", "TTFA ms p50",
                     "RTF p50", "記憶體 MB", "授權"], rows)


def section_dialogue(g):
    rows = []
    for i, (_, r) in enumerate(rank(g).iterrows(), 1):
        rows.append([i, r.model, fmt(r.score), r.gate,
                     f"{fmt(r.turn_latency_ms_p50, 'int')} / {fmt(r.turn_latency_ms_p90, 'int')}",
                     fmt(r.stt_ms_p50, "int"), fmt(r.llm_first_sentence_ms_p50, "int"),
                     fmt(r.tts_ttfa_ms_p50, "int"), fmt(r.llm_tok_s, "f"),
                     fmt(r.fact_recall, "pct"), fmt(r.lang_ok_rate, "pct"), fmt(r.human_relevance)])
    return md_table(["#", "組合 (STT+LLM+TTS)", "總分", "門檻", "回合延遲 ms p50/p90", "STT ms",
                     "LLM 首句 ms", "TTS 首段 ms", "LLM tok/s", "事實正確", "語言正確", "人工相關度"], rows)


SECTIONS = {"stt": ("STT 語音辨識", section_stt), "tts": ("TTS 語音合成", section_tts),
            "dialogue": ("語音對話機器人（STT → LLM → TTS）", section_dialogue)}


def recommendations(scored, priority):
    rows = []
    for lang in L.ALL:
        cells = [lang]
        for task in ("stt", "tts", "dialogue"):
            has_data = ((scored.task == task) & (scored.lang == lang)).any()
            pick = "無模型通過門檻" if has_data else "–"
            for hw in priority:
                g = scored[(scored.task == task) & (scored.lang == lang) & (scored.hw_profile == hw)
                           & (scored.gate == "PASS")]
                if len(g):
                    best = rank(g).iloc[0]
                    pick = f"{best.model}（{fmt(best.score)} 分，{hw}）"
                    break
            cells.append(pick)
        rows.append(cells)
    return md_table(["語言", "STT", "TTS", "對話組合"], rows)


# ---------------------------------------------------------------- charts
def pareto_charts(scored, out_dir):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Noto Sans CJK TC", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False      # 中文字型沒有 U+2212 負號，改用 ASCII "-"
    specs = {
        "stt": ("rtf_p50", "err_rate", "RTF p50（越左越快）", "WER / CER（越低越準）", True),
        "tts": ("ttfa_ms_p50", "utmos", "TTFA ms p50（越左越快）", "UTMOS（越高越自然）", False),
    }
    files = []
    for task, (xcol, ycol, xlabel, ylabel, lower_better) in specs.items():
        for hw, g_hw in scored[scored.task == task].groupby("hw_profile"):
            g_hw = g_hw.dropna(subset=[xcol, ycol])
            langs = [l for l in L.ALL if l in set(g_hw.lang)]
            if not langs:
                continue
            cols = min(3, len(langs))
            nrows = int(np.ceil(len(langs) / cols))
            fig, axes = plt.subplots(nrows, cols, figsize=(5 * cols, 4 * nrows), squeeze=False)
            for ax, lang in zip(axes.flat, langs):
                g = g_hw[g_hw.lang == lang]
                ok = g.gate.eq("PASS")
                ax.scatter(g[ok][xcol], g[ok][ycol], s=64, color=PASS_COLOR, edgecolor="white",
                           linewidth=2, label="通過門檻", zorder=3)
                ax.scatter(g[~ok][xcol], g[~ok][ycol], s=64, facecolor="none", edgecolor=FAIL_COLOR,
                           linewidth=2, label="未通過門檻", zorder=3)
                for _, r in g.iterrows():
                    ax.annotate(r.model, (r[xcol], r[ycol]), xytext=(6, 4), textcoords="offset points",
                                fontsize=8, color=MUTED)
                ax.set_title(f"{lang} · {L.LANGS[lang]['name']}", color=INK, fontsize=11, loc="left")
                ax.set_xlabel(xlabel, color=MUTED, fontsize=9)
                ax.set_ylabel(ylabel, color=MUTED, fontsize=9)
                if task == "stt":
                    ax.set_xscale("log")
                ax.grid(color=GRID, linewidth=0.8)
                ax.tick_params(colors=MUTED, labelsize=8)
                for side in ("top", "right"):
                    ax.spines[side].set_visible(False)
                for side in ("left", "bottom"):
                    ax.spines[side].set_color(GRID)
            for ax in list(axes.flat)[len(langs):]:
                ax.set_visible(False)
            handles, labels = axes.flat[0].get_legend_handles_labels()
            fig.legend(handles, labels, loc="upper right", frameon=False, fontsize=9)
            fig.suptitle(f"{task.upper()} 準確度與速度取捨 · {hw}", x=0.01, ha="left", color=INK, fontsize=13)
            fig.tight_layout(rect=(0, 0, 1, 0.95))
            path = out_dir / f"{task}_pareto_{hw}.png"
            fig.savefig(path, dpi=130, facecolor="#fcfcfb")
            plt.close(fig)
            files.append(path.name)
    return files


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports")
    args = ap.parse_args()
    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_yaml(ROOT / "configs" / "scoring.yaml")
    df = load_all()
    scored = score_rows(df, cfg)
    scored.to_csv(out_dir / "combined.csv", index=False, encoding="utf-8-sig")
    charts = pareto_charts(scored, out_dir)

    hw_order = [h for h in cfg["target_hw_priority"] if h in set(scored.hw_profile)]
    hw_order += sorted(set(scored.hw_profile) - set(hw_order))
    md = [
        "# 多語語音模型評測報告",
        f"產生時間：{datetime.datetime.now():%Y-%m-%d %H:%M}　｜　收錄 run：{df.run_id.nunique()} 個　｜　硬體：{', '.join(hw_order)}",
        "",
        "> 讀法：每張表先列通過門檻的模型，再依總分（0–100）排序。`*-est` 是換算的 Jetson 預估值，"
        "係數來源見 configs/hardware.yaml（theory = 理論值，尚未用錨點校準）。"
        "UTMOS 以英語資料訓練，非英語只能當相對參考；有人工 MOS 時優先採用人工分數。",
        "",
        "## 推薦組合（依 target_hw_priority 取第一個有數據的硬體）",
        recommendations(scored, cfg["target_hw_priority"]),
    ]
    for task, (title, fn) in SECTIONS.items():
        t = scored[scored.task == task]
        if t.empty:
            continue
        md += ["", f"## {title}"]
        if task == "stt":
            md += ["", "> 錯誤率：日語為 CER（字錯誤率），其他語言為 WER（詞錯誤率）。"
                       "噪音錯誤率與幻覺率只有 stt_full 套件會測，未測時顯示「–」。"]
        for lang in [l for l in L.ALL if l in set(t.lang)]:
            md += ["", f"### {lang} · {L.LANGS[lang]['name']}"]
            for hw in hw_order:
                g = t[(t.lang == lang) & (t.hw_profile == hw)]
                if len(g):
                    md += ["", f"**{hw}**", "", fn(g)]
    failed = df[df.error.notna() & df.lang.isna()] if "error" in df else pd.DataFrame()
    if len(failed):
        md += ["", "## 執行失敗的模型", md_table(["模型", "任務", "硬體", "錯誤"],
                                          [[r.model, r.task, r.hw_profile, r.error] for _, r in failed.iterrows()])]
    if charts:
        md += ["", "## 圖表"] + [f"![{c}]({c})" for c in charts]
    md += ["", "## 權重與門檻", "```yaml", yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False).strip(), "```"]
    # 人工撰寫的解讀放在 docs/analysis/（git 追蹤），每次產生報告都附在最後，重跑不會遺失
    notes = sorted((ROOT / "docs" / "analysis").glob("*.md"))
    if notes:
        md += ["", "## 分析與解讀"] + [s for n in notes for s in ("", n.read_text(encoding="utf-8").strip())]
    (out_dir / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {out_dir / 'report.md'}, combined.csv, {len(charts)} charts")


if __name__ == "__main__":
    main()
