"""產生 final_report.md 的圖表（docs/figures/*.png）與數據表（docs/figures/final_report_data.json）。

  .venv-core\\Scripts\\python.exe docs\\figures\\make_final_report_figures.py

資料來源：results/ 各 run 的 raw 結果（STT 在相同句子上重新計算錯誤率）與 reports/combined.csv（TTS、對話的 Jetson 換算值）。
配色沿用 dataviz 參考色盤（已驗證）：類別色最多 3 色用於散佈圖、堆疊圖依驗證過的相鄰順序。
"""
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
import numpy as np
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, NullFormatter  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from metrics.wer_cer import utt_errors  # noqa: E402

OUT = ROOT / "docs" / "figures"
R = ROOT / "results"
STT_RUNS = [R / "20260929-145339_round1_stt_small_pc", R / "20260930-102219_round1_stt_small_ptpt_pc",
            R / "20260930-102219_round1_stt_mid_pc", R / "20261001-093415_round1_night3_stt_multi_pc",
            R / "20261001-093415_round1_night3_stt_specialized_pc"]
DIALOGUE_OLD = "20260930-102219_round1_dialogue_pc"            # 第二晚：Whisper small 等舊組合
DIALOGUE_NEW = "20261005-163306_round2_dialogue_dialogue_new_pc"  # 第二輪：各語言推薦 STT 的新組合
# 圖 5 顯示的組合：(run, STT 條件, LLM, TTS, 顯示名稱)。舊組合用第二晚的數字（比本次重測的舊基準快，比較較保守）
DIALOGUE_SHOW = [
    (DIALOGUE_NEW, "new", "qwen2.5-1.5b-q4", "piper-medium", "新｜推薦 STT ＋ Qwen2.5-1.5B ＋ Piper（無 ja）"),
    (DIALOGUE_NEW, "new", "qwen2.5-1.5b-q4", "supertonic-3", "新｜推薦 STT ＋ Qwen2.5-1.5B ＋ Supertonic-3"),
    (DIALOGUE_NEW, "new", "gemma-3-4b-q4", "supertonic-3", "新｜推薦 STT ＋ Gemma-3-4B ＋ Supertonic-3"),
    (DIALOGUE_OLD, "whisper-small-ct2-int8", "gemma-3-4b-q4", "piper-medium", "舊｜Whisper small ＋ Gemma-3-4B ＋ Piper（無 ja）"),
    (DIALOGUE_OLD, "whisper-small-ct2-int8", "qwen2.5-1.5b-q4", "kokoro-82m", "舊｜Whisper small ＋ Qwen2.5-1.5B ＋ Kokoro（無 pt-PT）"),
]

# ---- 參考色盤（light）
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
NEUTRAL = "#c3c2b7"
MISSING = "#f0efec"
SEQ = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf",
       "#1c5cab", "#184f95", "#104281", "#0d366b"]

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Microsoft JhengHei", "Segoe UI", "DejaVu Sans"],
    "axes.unicode_minus": False, "font.size": 9,
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.titlecolor": INK, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
})

LANGS = ["en", "es-ES", "es-419", "pt-BR", "pt-PT", "ja"]
LANG_LABEL = {"en": "en 英語", "es-ES": "es-ES 西班牙", "es-419": "es-419 拉美", "pt-BR": "pt-BR 巴西",
              "pt-PT": "pt-PT 葡萄牙", "ja": "ja 日語"}
STT_SHOW = [  # (model id, 顯示名稱, 類型)
    ("whisper-small-ct2-int8", "Whisper small（基準）", "多語"),
    ("whisper-large-v3-turbo-ct2-int8", "Whisper large-v3-turbo†", "多語"),
    ("parakeet-tdt-0.6b-v3-int8", "Parakeet-TDT-0.6B-v3", "多語"),
    ("qwen3-asr-0.6b", "Qwen3-ASR-0.6B", "多語"),
    ("sensevoice-small-int8", "SenseVoice-Small", "多語"),
    ("nemotron-3.5-asr-0.6b", "Nemotron-3.5-ASR-0.6B", "多語"),
    ("parakeet-v3-ptbr-tagarela", "Parakeet-v3 葡語微調", "葡語專用"),
    ("parakeet-tdt_ctc-0.6b-ja-int8", "Parakeet-ja", "日語專用"),
    ("kotoba-whisper-v2-ct2-int8", "kotoba-whisper-v2", "日語專用"),
    ("moonshine-tiny-ja", "Moonshine-tiny-ja", "日語專用"),
    ("granite-speech-5.0-470m-ctc", "Granite-Speech-470M", "英語專用"),
    ("parakeet-tdt-0.6b-v2-int8", "Parakeet-TDT-0.6B-v2", "英語專用"),
]
SHORT = {"whisper-small-ct2-int8": "Whisper small", "whisper-large-v3-turbo-ct2-int8": "turbo",
         "parakeet-tdt-0.6b-v3-int8": "Parakeet-v3", "qwen3-asr-0.6b": "Qwen3-ASR",
         "sensevoice-small-int8": "SenseVoice", "nemotron-3.5-asr-0.6b": "Nemotron",
         "parakeet-v3-ptbr-tagarela": "Parakeet 葡語", "parakeet-tdt_ctc-0.6b-ja-int8": "Parakeet-ja",
         "kotoba-whisper-v2-ct2-int8": "kotoba", "moonshine-tiny-ja": "Moonshine-ja",
         "granite-speech-5.0-470m-ctc": "Granite", "parakeet-tdt-0.6b-v2-int8": "Parakeet-v2"}
RECOMMEND = {"en": "granite-speech-5.0-470m-ctc", "es-ES": "parakeet-tdt-0.6b-v3-int8",
             "es-419": "parakeet-tdt-0.6b-v3-int8", "pt-BR": "parakeet-tdt-0.6b-v3-int8",
             "pt-PT": "parakeet-v3-ptbr-tagarela", "ja": "sensevoice-small-int8"}

MODELS = yaml.safe_load((ROOT / "configs" / "models.yaml").read_text(encoding="utf-8"))
HW = yaml.safe_load((ROOT / "configs" / "hardware.yaml").read_text(encoding="utf-8"))
K = {cat: f["k"] for cat, f in HW["estimate"]["factors"]["pc"].items()}
rng = np.random.default_rng(0)


def pct(v):
    return f"{v * 100:.1f}%"


# ---------------------------------------------------------------- STT 資料
def load_stt():
    data, mem = {}, {}
    for run in STT_RUNS:     # 依時間先後，同模型 × 語言以後者為準
        for p in (run / "raw").glob("*__clean.jsonl"):
            model, lang = p.name.split("__")[:2]
            data[(model, lang)] = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        with open(run / "summary.csv", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r["ram_delta_mb"]:
                    mem[r["model"]] = float(r["ram_delta_mb"])
    return data, mem


def errors(rows, lang):
    pairs = [utt_errors(r["ref"], r["hyp"], lang) for r in rows]
    return np.array([p[0] for p in pairs], float), np.array([p[1] for p in pairs], float)


def stt_table(data, mem):
    out = defaultdict(dict)
    for lang in LANGS:
        for model, _, _ in STT_SHOW:
            rows = data.get((model, lang))
            if not rows:
                continue
            e, n = errors(rows, lang)
            cat = MODELS["stt"][model]["backend_category"]
            out[lang][model] = {
                "n": len(rows), "err": float(e.sum() / n.sum()),
                "lat_ms": float(statistics.median(r["proc_s"] for r in rows) / K[cat] * 1000),
                "mem_mb": mem.get(model),
            }
    return out


def paired_diff(data, lang, model_a, model_b, n=100, B=4000):
    base = [r["id"] for r in data[("whisper-small-ct2-int8", lang)][:n]]
    a = {r["id"]: r for r in data[(model_a, lang)]}
    b = {r["id"]: r for r in data[(model_b, lang)]}
    ea, na = errors([a[i] for i in base], lang)
    eb, nb = errors([b[i] for i in base], lang)
    idx = rng.integers(0, len(base), size=(B, len(base)))
    d = ea[idx].sum(1) / na[idx].sum(1) - eb[idx].sum(1) / nb[idx].sum(1)
    return float(ea.sum() / na.sum() - eb.sum() / nb.sum()), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


# ---------------------------------------------------------------- 圖 1：STT 錯誤率熱圖
def fig_stt_heatmap(tab):
    names = [label for _, label, _ in STT_SHOW]
    fig, ax = plt.subplots(figsize=(8.6, 5.6))
    vmax = 0.30
    for i, (model, label, kind) in enumerate(STT_SHOW):
        for j, lang in enumerate(LANGS):
            r = tab[lang].get(model)
            if r is None:
                ax.add_patch(plt.Rectangle((j, i), 1, 1, facecolor=MISSING, edgecolor=SURF, linewidth=2))
                ax.text(j + 0.5, i + 0.5, "—", ha="center", va="center", color=MUTED, fontsize=8)
                continue
            level = min(r["err"], vmax) / vmax
            color = SEQ[min(int(level * (len(SEQ) - 1) + 0.5), len(SEQ) - 1)]
            ax.add_patch(plt.Rectangle((j, i), 1, 1, facecolor=color, edgecolor=SURF, linewidth=2))
            best = min(tab[lang].values(), key=lambda x: x["err"])["err"]
            is_best = abs(r["err"] - best) < 1e-9
            txt = pct(r["err"]) + ("★" if is_best else "")
            ax.text(j + 0.5, i + 0.5, txt, ha="center", va="center", fontsize=8.5,
                    color="#ffffff" if level > 0.55 else INK, fontweight="bold" if is_best else "normal")
    ax.set_xlim(0, len(LANGS))
    ax.set_ylim(len(STT_SHOW), 0)
    ax.set_xticks(np.arange(len(LANGS)) + 0.5, [LANG_LABEL[l] for l in LANGS])
    ax.xaxis.tick_top()
    ax.set_yticks(np.arange(len(STT_SHOW)) + 0.5, names)
    ax.tick_params(length=0)
    for side in ("left", "bottom", "top"):
        ax.spines[side].set_visible(False)
    for i, (_, _, kind) in enumerate(STT_SHOW):
        ax.text(len(LANGS) + 0.08, i + 0.5, kind, va="center", fontsize=8, color=MUTED)
    ax.set_title("圖 1　STT 錯誤率（越淺越準；★ = 該語言最低；日語為 CER；顏色上限 30%）", loc="left", pad=28)
    fig.text(0.01, 0.01, "† turbo 每語言只測 50 句，其餘 100 句。— = 不支援該語言。", color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 0.95, 1))
    fig.savefig(OUT / "fig1_stt_error_heatmap.png", dpi=170)
    plt.close(fig)


# ---------------------------------------------------------------- 圖 2：準確度 vs 速度（各語言小圖）
def fig_stt_tradeoff(tab):
    fig, axes = plt.subplots(2, 3, figsize=(10, 6.2), sharex=True)
    for ax, lang in zip(axes.flat, LANGS):
        rows = tab[lang]
        rec = RECOMMEND[lang]
        pts = sorted(rows.items(), key=lambda kv: kv[1]["lat_ms"])
        for model, r in pts:
            if model == rec:
                c, z, size = S1, 4, 64
            elif model == "whisper-small-ct2-int8":
                c, z, size = S2, 3, 56
            else:
                c, z, size = NEUTRAL, 2, 40
            ax.scatter(r["lat_ms"], r["err"] * 100, s=size, color=c, edgecolor=SURF, linewidth=2, zorder=z)
        ymax = max(r["err"] for r in rows.values()) * 100 * 1.18 + 1
        step = ymax * 0.07              # 標籤最小垂直間距
        placed = []                     # 已放的標籤位置（log10 x, y）
        for model, r in sorted(pts, key=lambda kv: -kv[1]["err"]):
            x, y = r["lat_ms"], r["err"] * 100
            ly = y
            while any(abs(px - np.log10(x)) < 0.5 and abs(py - ly) < step for px, py in placed):
                ly -= step              # 和附近標籤太近就往下錯開，並畫細線連回點
            placed.append((np.log10(x), ly))
            emph = model in (rec, "whisper-small-ct2-int8")
            ax.annotate(SHORT[model], (x, y), xytext=(x * 1.12, ly), textcoords="data", va="center",
                        fontsize=7.5 if emph else 7, color=INK if emph else MUTED,
                        fontweight="bold" if model == rec else "normal",
                        arrowprops=dict(arrowstyle="-", color=AXIS, lw=0.7) if abs(ly - y) > 1e-9 else None)
        ax.set_xscale("log")
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1000:g}"))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_xticks([200, 500, 1000, 2000, 5000, 10000])
        ax.set_xlim(150, 14000)
        ax.set_ylim(min(0, min(py for _, py in placed) - step), ymax)
        ax.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_title(LANG_LABEL[lang], loc="left", fontsize=9.5)
        ax.tick_params(labelsize=8, length=0)
    for ax in axes[1]:
        ax.set_xlabel("每句處理時間（秒，Jetson 理論換算，對數刻度）")
    for ax in axes[:, 0]:
        ax.set_ylabel("錯誤率（%）")
    handles = [plt.Line2D([], [], marker="o", ls="", color=S1, markersize=7, label="推薦模型"),
               plt.Line2D([], [], marker="o", ls="", color=S2, markersize=7, label="Whisper small（基準）"),
               plt.Line2D([], [], marker="o", ls="", color=NEUTRAL, markersize=7, label="其他候選")]
    fig.legend(handles=handles, loc="upper right", ncol=3, fontsize=8.5, bbox_to_anchor=(0.99, 0.995))
    fig.suptitle("圖 2　STT 準確度與速度的取捨（越靠左下越好）", x=0.01, ha="left", fontsize=10, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / "fig2_stt_accuracy_vs_speed.png", dpi=170)
    plt.close(fig)


# ---------------------------------------------------------------- 圖 3：專用 vs 多語
def fig_specialized(rows):
    fig, ax = plt.subplots(figsize=(8.2, 2.9))
    for i, r in enumerate(rows):
        sig = r["hi"] < 0 or r["lo"] > 0
        ax.plot([r["lo"] * 100, r["hi"] * 100], [i, i], color=S1 if sig else NEUTRAL, linewidth=2.2, solid_capstyle="round")
        ax.scatter(r["diff"] * 100, i, s=60, color=S1 if sig else NEUTRAL, edgecolor=SURF, linewidth=2, zorder=3)
        verdict = "專用顯著較好" if r["hi"] < 0 else ("多語顯著較好" if r["lo"] > 0 else "差距不顯著")
        ax.text(3.3, i, f"{r['spec_name']} {pct(r['spec_err'])}  vs  {r['multi_name']} {pct(r['multi_err'])}　→ {verdict}",
                va="center", fontsize=8, color=INK if sig else INK2)
    ax.axvline(0, color=INK2, linewidth=1)
    ax.set_yticks(range(len(rows)), [LANG_LABEL[r["lang"]] for r in rows])
    ax.set_ylim(len(rows) - 0.5, -0.5)
    ax.set_xlim(-17, 3)
    ax.set_xlabel("錯誤率差距（百分點）＝ 專用 - 多語；負值代表專用較準。線段為 95% 信賴區間")
    ax.grid(True, axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.spines["left"].set_visible(False)
    ax.set_title("圖 3　語言專用模型 vs 最佳多語模型（相同 100 句，配對 bootstrap）", loc="left")
    fig.tight_layout()
    fig.subplots_adjust(right=0.60)
    fig.savefig(OUT / "fig3_specialized_vs_multilingual.png", dpi=170)
    plt.close(fig)


# ---------------------------------------------------------------- 圖 4：TTS
def load_combined():
    with open(ROOT / "reports" / "combined.csv", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fig_tts(comb):
    tts_models = [("supertonic-3", "Supertonic-3", S1), ("kokoro-82m", "Kokoro-82M", S2), ("piper-medium", "Piper", S3)]
    est = {(r["model"], r["lang"]): r for r in comb if r["task"] == "tts" and r["hw_profile"] == "jetson-orin-nx-est"}
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    width = 0.24
    x = np.arange(len(LANGS))
    table = {}
    for k, (model, label, color) in enumerate(tts_models):
        for panel, (col, scale) in enumerate([("utmos", 1), ("ttfa_ms_p50", 0.001)]):
            ax = axes[panel]
            vals = []
            for lang in LANGS:
                r = est.get((model, lang))
                vals.append(float(r[col]) * scale if r else np.nan)
                if r:
                    table.setdefault(lang, {})[model] = {"utmos": float(r["utmos"]), "asr_err": float(r["asr_err"]),
                                                          "ttfa_ms": float(r["ttfa_ms_p50"]), "mem_mb": float(r["mem_mb"])}
            pos = x + (k - 1) * (width + 0.02)
            ax.bar(pos, np.nan_to_num(vals), width=width, color=color, label=label, zorder=2)
            for p, v in zip(pos, vals):
                if np.isnan(v):
                    ax.text(p, 0.02 * (5 if panel == 0 else 1.8), "不支援", rotation=90, ha="center", va="bottom",
                            fontsize=7, color=MUTED)
    axes[0].set_ylim(0, 5)
    axes[0].set_ylabel("UTMOS（1–5，越高越自然）")
    axes[0].set_title("自然度", loc="left", fontsize=9.5)
    axes[1].set_ylim(0, 1.8)
    axes[1].set_ylabel("首段延遲（秒，Jetson 換算，越低越好）")
    axes[1].set_title("首段聲音延遲", loc="left", fontsize=9.5)
    for ax in axes:
        ax.set_xticks(x, [LANG_LABEL[l] for l in LANGS], fontsize=8)
        ax.grid(True, axis="y", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(length=0)
    axes[0].legend(loc="upper left", ncol=3, fontsize=8, bbox_to_anchor=(0, 1.02))
    fig.suptitle("圖 4　TTS 自然度與速度（兩張圖各自的刻度，不共用座標）", x=0.01, ha="left", fontsize=10, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(OUT / "fig4_tts_quality_speed.png", dpi=170)
    plt.close(fig)
    return table


# ---------------------------------------------------------------- 圖 5：對話延遲拆解
def fig_dialogue():
    # combined.csv 只保留每個組合最新的一次，第二晚的舊基準已被第二輪重測取代，所以直接讀所有換算值
    with open(R / "_estimates" / "summary.csv", encoding="utf-8-sig") as f:
        est = [r for r in csv.DictReader(f) if r["task"] == "dialogue"]
    combos = []
    for run, stt_cond, llm_id, tts_id, name in DIALOGUE_SHOW:
        rs = []
        for r in est:
            stt, llm, tts = r["model"].split("+")
            new_stt = stt_cond == "new" and not stt.startswith("whisper")
            if r["run_id"] == f"est:{run}" and (new_stt or stt == stt_cond) and llm == llm_id and tts == tts_id:
                rs.append(r)
        mean = lambda k: statistics.mean(float(r[k]) for r in rs if r[k])
        stt, llm, tts, vad = mean("stt_ms_p50"), mean("llm_first_sentence_ms_p50"), mean("tts_ttfa_ms_p50"), mean("vad_endpoint_ms")
        facts = [float(r["fact_recall"]) for r in rs if r["fact_recall"]]
        combos.append({"name": name, "run": run, "langs": sorted(r["lang"] for r in rs),
                       "turn_p50_by_lang": {r["lang"]: float(r["turn_latency_ms_p50"]) for r in rs},
                       "vad": vad, "stt": stt, "llm": llm, "tts": tts, "total": vad + stt + llm + tts,
                       "facts_min": min(facts), "facts_max": max(facts)})
    fig, ax = plt.subplots(figsize=(10, 3.4))
    segs = [("vad", "判斷說完（固定 0.3 秒）", NEUTRAL), ("stt", "STT", S1), ("llm", "LLM 第一句", S2), ("tts", "TTS 首段", S3)]
    for i, c in enumerate(combos):
        left = 0
        for key, label, color in segs:
            w = c[key] / 1000
            ax.barh(i, w, left=left, height=0.55, color=color, edgecolor=SURF, linewidth=2,
                    label=label if i == 0 else None, zorder=2)
            left += w
        ax.text(left + 0.08, i, f"{left:.1f} 秒", va="center", fontsize=8, color=INK)
    n_new = sum(c["run"] == DIALOGUE_NEW for c in combos)
    ax.axhline(n_new - 0.5, color=AXIS, linewidth=0.8, zorder=1)
    ax.axvline(1.5, color=INK2, linewidth=1.2, zorder=3)
    ax.text(1.55, -0.75, "目標 1.5 秒", fontsize=8, color=INK2, va="bottom")
    ax.set_yticks(range(len(combos)), [c["name"] for c in combos], fontsize=8)
    ax.set_ylim(len(combos) - 0.4, -1.0)
    ax.set_xlim(0, max(c["total"] for c in combos) / 1000 * 1.12)
    ax.set_xlabel("回合延遲（秒，Jetson 理論換算，各組支援語言的平均）")
    ax.grid(True, axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.spines["left"].set_visible(False)
    ax.legend(loc="lower right", ncol=4, fontsize=8, bbox_to_anchor=(1.0, 1.0))
    ax.set_title("圖 5　對話回合延遲拆解（使用者說完 → 聽到回答）", loc="left", pad=22)
    fig.tight_layout()
    fig.savefig(OUT / "fig5_dialogue_latency.png", dpi=170)
    plt.close(fig)
    return combos


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data, mem = load_stt()
    tab = stt_table(data, mem)
    fig_stt_heatmap(tab)
    fig_stt_tradeoff(tab)
    pairs = [("en", "granite-speech-5.0-470m-ctc", "qwen3-asr-0.6b"),
             ("pt-BR", "parakeet-v3-ptbr-tagarela", "parakeet-tdt-0.6b-v3-int8"),
             ("pt-PT", "parakeet-v3-ptbr-tagarela", "qwen3-asr-0.6b"),
             ("ja", "parakeet-tdt_ctc-0.6b-ja-int8", "sensevoice-small-int8")]
    spec_rows = []
    for lang, spec, multi in pairs:
        d, lo, hi = paired_diff(data, lang, spec, multi)
        spec_rows.append({"lang": lang, "spec_name": SHORT[spec], "multi_name": SHORT[multi],
                          "spec_err": tab[lang][spec]["err"], "multi_err": tab[lang][multi]["err"],
                          "diff": d, "lo": lo, "hi": hi})
    fig_specialized(spec_rows)
    comb = load_combined()
    tts = fig_tts(comb)
    dialogue = fig_dialogue()
    (OUT / "final_report_data.json").write_text(json.dumps(
        {"stt": tab, "specialized": spec_rows, "tts": tts, "dialogue": dialogue}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
