"""評分：讀取 results/<run_id>/raw/，計算指標，輸出 summary.csv（統一欄位格式）。

  python score.py results/<run_id>
  python score.py results/<run_id> --asr-judge whisper-large-v3-turbo-ct2-int8 --utmos   # TTS 可懂度與預測 MOS

另外會產生（已存在則不覆寫，方便填入人工分數後重新評分）：
  listening_test.csv   TTS 聽測表：填 mos_1to5（1–5 分）→ 重跑 score.py 會併入 mos 欄位
  rating_sheet.csv     對話評分表：填 relevance_1to5 / naturalness_1to5 / dialect_ok(y/n)
以及每次都重新產生的：
  listen.html          試聽頁（TTS / 對話）：同一句並排比較各模型的語音，用瀏覽器開啟
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
import yaml

from bench import languages as L
from bench.audio import load_audio
from metrics.lang_check import detect
from metrics.normalize import normalize
from metrics.wer_cer import bootstrap_ci, corpus_rate, keyword_recall, utt_errors

ROOT = Path(__file__).resolve().parent

SUMMARY_COLUMNS = [
    "run_id", "task", "model", "backend_category", "quant", "lang", "dataset", "condition",
    "hw_profile", "is_estimated", "n_samples",
    # 準確度
    "err_metric", "err_rate", "err_ci95_low", "err_ci95_high", "keyword_recall",
    "hallucination_rate", "lid_acc",
    # 速度
    "rtf_p50", "rtf_p90", "latency_ms_p50", "latency_ms_p90", "ttfa_ms_p50", "ttfa_ms_p90",
    "first_partial_ms_p50", "stream_final_ms_p50", "stream_err_rate",
    # TTS 品質
    "asr_err", "utmos", "mos", "mos_n",
    # 對話
    "turn_latency_ms_p50", "turn_latency_ms_p90", "vad_endpoint_ms", "stt_ms_p50", "llm_ttft_ms_p50",
    "llm_first_sentence_ms_p50", "llm_tok_s", "tts_ttfa_ms_p50", "question_err_rate",
    "fact_recall", "lang_ok_rate", "human_relevance", "human_naturalness",
    # 照護情境對話（dataset = care）
    "care_action_ok_rate", "emergency_miss_rate", "notify_miss_rate", "over_call_rate",
    "llm_tag_ms_p50", "alert_latency_ms_p50",
    # 緊急快速通道（規則層＋固定回應）
    "rule_recall", "rule_false_alarm_rate", "final_emergency_miss_rate", "final_over_call_rate",
    "final_action_ok_rate", "rule_alert_latency_ms_p50", "emergency_response_ms_p50", "response_latency_ms_p50",
    "stt_category", "llm_category", "tts_category",
    # 資源
    "peak_ram_mb", "ram_delta_mb", "peak_vram_mb", "sys_ram_delta_mb", "avg_cpu_pct",
    "avg_gpu_pct", "avg_power_w", "load_time_s",
    "license", "error",
]


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def pct(values, q, scale=1.0):
    values = [v for v in values if v is not None]
    return round(float(np.percentile(values, q)) * scale, 4) if values else None


def mean(values):
    values = [v for v in values if v is not None]
    return round(float(np.mean(values)), 4) if values else None


def model_meta(raw, model_id):
    p = raw / f"{model_id}.model.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def spec_info(models, kind, model_id):
    spec = models.get(kind, {}).get(model_id, {})
    params = spec.get("params", {})
    return {
        "backend_category": spec.get("backend_category"),
        "quant": spec.get("quant") or params.get("compute_type"),
        "license": spec.get("license"),
    }


def resource_cols(meta):
    res = meta.get("resources", {}) or {}
    err_lines = (meta.get("error") or "").strip().splitlines()
    return {
        "peak_ram_mb": res.get("peak_ram_mb"), "ram_delta_mb": res.get("ram_delta_mb"),
        "peak_vram_mb": res.get("peak_vram_mb"), "sys_ram_delta_mb": res.get("sys_ram_delta_mb"),
        "avg_cpu_pct": res.get("avg_cpu_pct"), "avg_gpu_pct": res.get("avg_gpu_pct"),
        "avg_power_w": res.get("avg_power_w"), "load_time_s": meta.get("load_time_s"),
        "error": err_lines[-1] if err_lines else None,
    }


# ---------------------------------------------------------------- STT
def score_stt(items, meta, args):
    lang = meta["lang"]
    r = {}
    speech = [it for it in items if not it.get("expect_empty")]
    empty = [it for it in items if it.get("expect_empty")]
    if speech:
        errs, ns = zip(*[utt_errors(it["ref"], it["hyp"], lang, args.ja_kana) for it in speech])
        r["err_metric"] = "cer" if L.uses_cer(lang) else "wer"
        r["err_rate"] = round(corpus_rate(errs, ns), 4)
        lo, hi = bootstrap_ci(errs, ns)
        r["err_ci95_low"], r["err_ci95_high"] = round(lo, 4), round(hi, 4)
        r["keyword_recall"] = mean([keyword_recall(it["hyp"], it["keywords"], lang)
                                    for it in speech if it.get("keywords")])
        if meta.get("lang_mode") == "auto":
            r["lid_acc"] = mean([float(it["lang_detected"] == L.base(lang)) for it in speech])
    if empty:
        r["hallucination_rate"] = mean([float(normalize(it["hyp"], lang) != "") for it in empty])
    rtfs = meta.get("speed_repeat_rtf") or [it["rtf"] for it in items]
    r["rtf_p50"], r["rtf_p90"] = pct(rtfs, 50), pct(rtfs, 90)
    lat = [it["proc_s"] for it in items]
    r["latency_ms_p50"], r["latency_ms_p90"] = pct(lat, 50, 1000), pct(lat, 90, 1000)
    stream = meta.get("streaming") or []
    if stream:
        smallest = min(s["chunk_ms"] for s in stream)
        sel = [s for s in stream if s["chunk_ms"] == smallest]
        r["first_partial_ms_p50"] = pct([s["first_partial_s"] for s in sel], 50, 1000)
        r["stream_final_ms_p50"] = pct([s["final_latency_s"] for s in sel], 50, 1000)
        # 串流模式的辨識結果也算錯誤率：串流看不到後文，準確度可能比整句低
        refs = {it["id"]: it["ref"] for it in speech}
        pairs = [utt_errors(refs[s["id"]], s["hyp"], lang, args.ja_kana) for s in sel if s["id"] in refs]
        if pairs:
            s_errs, s_ns = zip(*pairs)
            r["stream_err_rate"] = round(corpus_rate(s_errs, s_ns), 4)
    return r


# ---------------------------------------------------------------- TTS
class Judges:
    def __init__(self, args, models):
        self.args, self.models = args, models
        self._asr = self._utmos = None

    @property
    def asr(self):
        if self._asr is None and self.args.asr_judge:
            from engines.base import build_engine
            self._asr = build_engine(self.models["stt"][self.args.asr_judge])
            self._asr.load()
        return self._asr

    @property
    def utmos(self):
        if self._utmos is None and self.args.utmos:
            from metrics.utmos import UTMOS
            self._utmos = UTMOS()
        return self._utmos


def intelligibility_and_mos(items, lang, run_dir, judges, text_field):
    r = {}
    with_wav = [it for it in items if it.get("wav")]
    if judges.args.asr_judge and with_wav:
        errs, ns = [], []
        for it in with_wav:
            if "asr_judge_hyp" not in it:      # 沒有快取（raw/*.judge.jsonl）才呼叫評審模型
                it["asr_judge_hyp"] = judges.asr.transcribe(load_audio(run_dir / it["wav"]), L.base(lang)).text
            e, n = utt_errors(it[text_field], it["asr_judge_hyp"], lang)
            errs.append(e)
            ns.append(n)
        r["asr_err"] = round(corpus_rate(errs, ns), 4)
    if judges.utmos and with_wav:
        scores = []
        for it in with_wav:
            wav, sr = sf.read(str(run_dir / it["wav"]), dtype="float32")
            scores.append(judges.utmos.score(wav, sr))
        r["utmos"] = round(float(np.mean(scores)), 3)
    return r


def score_tts(items, meta, run_dir, judges):
    r = {
        "rtf_p50": pct([it["rtf"] for it in items], 50), "rtf_p90": pct([it["rtf"] for it in items], 90),
        "ttfa_ms_p50": pct([it["ttfa_s"] for it in items], 50, 1000),
        "ttfa_ms_p90": pct([it["ttfa_s"] for it in items], 90, 1000),
        "latency_ms_p50": pct([it["proc_s"] for it in items], 50, 1000),
        "latency_ms_p90": pct([it["proc_s"] for it in items], 90, 1000),
    }
    r.update(intelligibility_and_mos(items, meta["lang"], run_dir, judges, "text"))
    if "asr_err" in r:
        r["err_metric"] = "cer" if L.uses_cer(meta["lang"]) else "wer"
    return r


# ---------------------------------------------------------------- Dialogue
def fact_hits(response, facts, lang):
    resp = normalize(response, lang)
    return [any(normalize(alt, lang) in resp for alt in group) for group in facts]


def score_dialogue(items, meta, run_dir, judges):
    lang = meta["lang"]
    hits = [h for it in items for h in fact_hits(it["response"], it.get("facts", []), lang)]
    errs, ns = zip(*[utt_errors(it["question"], it["stt_hyp"], lang) for it in items])
    r = {
        "turn_latency_ms_p50": pct([it["turn_latency_s"] for it in items], 50, 1000),
        "turn_latency_ms_p90": pct([it["turn_latency_s"] for it in items], 90, 1000),
        "vad_endpoint_ms": round(items[0]["vad_endpoint_s"] * 1000),
        "stt_ms_p50": pct([it["stt_s"] for it in items], 50, 1000),
        "llm_ttft_ms_p50": pct([it["llm_ttft_s"] for it in items], 50, 1000),
        "llm_first_sentence_ms_p50": pct([it["llm_first_sentence_s"] for it in items], 50, 1000),
        "llm_tok_s": pct([it["llm_tok_s"] for it in items], 50),
        "tts_ttfa_ms_p50": pct([it["tts_ttfa_s"] for it in items], 50, 1000),
        "question_err_rate": round(corpus_rate(errs, ns), 4),
        "fact_recall": round(float(np.mean(hits)), 4) if hits else None,
        "lang_ok_rate": mean([float(detect(it["response"]) == L.base(lang)) for it in items]),
    }
    if items and "action" in items[0]:   # 照護情境題：依通報標記評分（定義同 llm_eval.py）
        calls = [it for it in items if it["action"] == "call_now"]
        notifies = [it for it in items if it["action"] == "notify"]
        others = [it for it in items if it["action"] != "call_now"]
        called = [it for it in calls if it["tag"] == "call"]
        r.update({
            "care_action_ok_rate": mean([float(it["action_ok"]) for it in items]),
            "emergency_miss_rate": mean([float(it["tag"] != "call") for it in calls]),
            "notify_miss_rate": mean([float(it["tag"] is None) for it in notifies]),
            "over_call_rate": mean([float(it["tag"] == "call") for it in others]),
            "llm_tag_ms_p50": pct([it["llm_tag_s"] for it in called], 50, 1000),
            "alert_latency_ms_p50": pct([it["alert_latency_s"] for it in called], 50, 1000),
        })
        if "final_tag" in items[0]:   # 緊急快速通道：規則層 ＋ LLM 標記，取較高等級
            r.update({
                "rule_recall": mean([float(bool(it["rule_hits"])) for it in calls]),
                "rule_false_alarm_rate": mean([float(bool(it["rule_hits"])) for it in others]),
                "final_emergency_miss_rate": mean([float(it["final_tag"] != "call") for it in calls]),
                "final_over_call_rate": mean([float(it["final_tag"] == "call") for it in others]),
                "final_action_ok_rate": mean([float(it["final_action_ok"]) for it in items]),
                "rule_alert_latency_ms_p50": pct([it["rule_alert_latency_s"] for it in calls], 50, 1000),
                "emergency_response_ms_p50": pct([it["response_latency_s"] for it in calls if it["fast_trigger"]], 50, 1000),
                "response_latency_ms_p50": pct([it["response_latency_s"] for it in items], 50, 1000),
            })
    r.update(intelligibility_and_mos(items, lang, run_dir, judges, "response"))
    return r


# ---------------------------------------------------------------- human ratings
def export_sheets(run_dir, per_key_items):
    lt = run_dir / "listening_test.csv"
    rs = run_dir / "rating_sheet.csv"
    tts_rows, dlg_rows = [], []
    for (task, model, lang), items in per_key_items.items():
        for it in items:
            if task == "tts":
                tts_rows.append({"model": model, "lang": lang, "id": it["id"], "text": it["text"],
                                 "wav": it["wav"], "mos_1to5": ""})
            elif task == "dialogue":
                dlg_rows.append({"model": model, "lang": lang, "id": it["id"], "question": it["question"],
                                 "stt_hyp": it["stt_hyp"], "response": it["response"], "wav": it.get("wav", ""),
                                 "relevance_1to5": "", "naturalness_1to5": "", "dialect_ok": ""})
    if tts_rows and not lt.exists():
        # 打亂順序，聽測時不要一次聽完同一個模型
        pd.DataFrame(tts_rows).sample(frac=1, random_state=0).to_csv(lt, index=False, encoding="utf-8-sig")
    if dlg_rows and not rs.exists():
        pd.DataFrame(dlg_rows).to_csv(rs, index=False, encoding="utf-8-sig")


def merge_ratings(run_dir, df):
    lt = run_dir / "listening_test.csv"
    if lt.exists():
        rated = pd.read_csv(lt)
        rated = rated[pd.to_numeric(rated["mos_1to5"], errors="coerce").notna()]
        if len(rated):
            rated["mos_1to5"] = rated["mos_1to5"].astype(float)
            agg = rated.groupby(["model", "lang"])["mos_1to5"].agg(["mean", "count"]).reset_index()
            for _, a in agg.iterrows():
                m = (df["task"] == "tts") & (df["model"] == a["model"]) & (df["lang"] == a["lang"])
                df.loc[m, "mos"], df.loc[m, "mos_n"] = round(a["mean"], 3), a["count"]
    rs = run_dir / "rating_sheet.csv"
    if rs.exists():
        rated = pd.read_csv(rs)
        for col, target in (("relevance_1to5", "human_relevance"), ("naturalness_1to5", "human_naturalness")):
            vals = rated.assign(v=pd.to_numeric(rated[col], errors="coerce")).dropna(subset=["v"])
            for (model, lang), g in vals.groupby(["model", "lang"]):
                m = (df["task"] == "dialogue") & (df["model"] == model) & (df["lang"] == lang)
                df.loc[m, target] = round(g["v"].mean(), 3)
    return df


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--asr-judge", help="TTS 可懂度用的 STT 模型 id（建議最準的，如 whisper-large-v3-ct2-int8）")
    ap.add_argument("--utmos", action="store_true", help="計算 UTMOS 預測 MOS（需 torch）")
    ap.add_argument("--ja-kana", action="store_true", help="日語 CER 前先轉平假名")
    ap.add_argument("--rejudge", action="store_true", help="忽略已存的評審轉錄（raw/*.judge.jsonl），重新跑 ASR 評審")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    raw = run_dir / "raw"
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    models = load_yaml(ROOT / "configs" / "models.yaml")
    judges = Judges(args, models)

    rows, per_key_items = [], {}
    for meta_path in sorted(raw.glob("*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        key = meta_path.name[: -len(".meta.json")]
        items = read_jsonl(raw / f"{key}.jsonl")
        task = meta["task"]
        judge_cache = raw / f"{key}.judge.jsonl"
        if args.asr_judge and not args.rejudge and judge_cache.exists():
            # 重新評分（如修改正規化規則）時沿用已存的評審轉錄，不必再跑一次 Whisper
            cached = {r["id"]: r.get("asr_judge_hyp") for r in read_jsonl(judge_cache)}
            for it in items:
                if cached.get(it["id"]) is not None:
                    it["asr_judge_hyp"] = cached[it["id"]]
        row = {
            "run_id": run["run_id"], "task": task, "model": meta["model"], "lang": meta["lang"],
            "dataset": meta["dataset"], "condition": meta["condition"], "hw_profile": run["hw_profile"],
            "is_estimated": False, "n_samples": len(items),
        }
        if task == "stt":
            row.update(spec_info(models, "stt", meta["model"]))
            row.update(resource_cols(model_meta(raw, meta["model"])))
            row.update(score_stt(items, meta, args))
        elif task == "tts":
            row.update(spec_info(models, "tts", meta["model"]))
            row.update(resource_cols(model_meta(raw, meta["model"])))
            row.update(score_tts(items, meta, run_dir, judges))
        elif task == "dialogue":
            combo = meta["combo"]
            parts = {k: spec_info(models, k, combo[k]) for k in ("stt", "llm", "tts")}
            row.update({f"{k}_category": parts[k]["backend_category"] for k in parts})
            row["license"] = " / ".join(str(parts[k]["license"]) for k in parts)
            metas = [model_meta(raw, combo[k]) for k in ("stt", "llm", "tts")]
            res = [resource_cols(m) for m in metas]
            # 新版 run 每個組合×語言各自監控；舊 run 沒有，退回取三個模型監控值的最大值
            # （模型跨組合沿用時監控期間較長，會高估）
            own = (meta.get("resources") or {}).get("peak_ram_mb")
            row["peak_ram_mb"] = own or max((r["peak_ram_mb"] or 0) for r in res) or None
            row["load_time_s"] = sum((r["load_time_s"] or 0) for r in res)
            row.update(score_dialogue(items, meta, run_dir, judges))
        if args.asr_judge and task in ("tts", "dialogue"):
            (raw / f"{key}.judge.jsonl").write_text(
                "\n".join(json.dumps(it, ensure_ascii=False) for it in items), encoding="utf-8")
        rows.append(row)
        per_key_items[(task, meta["model"], meta["lang"])] = items
        print(f"scored {key}")

    # 載入或執行失敗的模型也列出來，報告中才看得到「為什麼沒有分數」
    for mpath in sorted(raw.glob("*.model.json")):
        meta = json.loads(mpath.read_text(encoding="utf-8"))
        if meta.get("error") and meta.get("kind") in ("stt", "tts"):
            rows.append({"run_id": run["run_id"], "task": meta["kind"], "model": meta["model"],
                         "hw_profile": run["hw_profile"], "is_estimated": False,
                         **spec_info(models, meta["kind"], meta["model"]), **resource_cols(meta)})

    df = pd.DataFrame(rows).reindex(columns=SUMMARY_COLUMNS)
    df = merge_ratings(run_dir, df)
    df.to_csv(run_dir / "summary.csv", index=False, encoding="utf-8-sig")
    export_sheets(run_dir, per_key_items)
    print(f"wrote {run_dir / 'summary.csv'} ({len(df)} rows)")
    if any(task in ("tts", "dialogue") for task, _, _ in per_key_items):
        from listen_page import build
        page = build(run_dir)
        if page:
            print(f"wrote {page}（試聽頁，用瀏覽器開啟）")


if __name__ == "__main__":
    main()
