"""執行測試套件（只做推論與計時，評分交給 score.py）。

  python run.py --suite configs/suites/smoke_stt.yaml --hw pc
  python run.py --suite configs/suites/stt_quick.yaml --hw pc --models whisper-small-ct2-int8 --langs ja

輸出：results/<run_id>/
  run.json                         套件設定、硬體 profile、環境資訊
  raw/<key>.jsonl                  逐句原始結果（一句一行）
  raw/<key>.meta.json              該組合的速度重複測資料
  raw/<model>.model.json           模型載入時間、資源使用、錯誤訊息
  audio/...                        TTS / 對話輸出的音檔（供 UTMOS 與人工聽測）
"""
import argparse
import datetime
import gc
import json
import time
import traceback
from pathlib import Path

import numpy as np
import yaml

from bench import languages as L
from bench.audio import STT_SR, load_audio, resample, save_wav
from bench import care_rules
from bench.care import CARE, action_ok, care_system, load_scenarios, spoken_text, strip_think, tag_of
from bench.envinfo import collect_env
from bench.monitor import ResourceMonitor
from bench.text import clean_for_tts, first_complete_clause, first_complete_sentence, split_sentences
from engines.base import build_engine

ROOT = Path(__file__).resolve().parent
now = time.perf_counter


# ---------------------------------------------------------------- utils
def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def manifest_path(lang, dataset, condition):
    suffix = "" if condition == "clean" else f"__{condition}"
    for folder in (lang, "_any"):
        p = ROOT / "data" / "manifests" / folder / f"{dataset}{suffix}.jsonl"
        if p.exists():
            return p
    return None


def read_texts(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]


class ModelSession:
    """載入模型並在整段使用期間監控資源；結束時寫入 <model>.model.json。"""

    def __init__(self, kind, model_id, spec, out_dir):
        self.kind, self.model_id, self.spec, self.out_dir = kind, model_id, spec, out_dir
        self.meta = {"kind": kind, "model": model_id, "spec": spec, "error": None}
        self.engine = None
        self.failed = False

    def __enter__(self):
        self.monitor = ResourceMonitor().start()
        try:
            self.engine = build_engine(self.spec)
            t = now()
            self.engine.load()
        except Exception as exc:
            # 載入失敗（缺套件、下載失敗等）：記錄後跳過，呼叫端檢查 sess.failed
            self.failed = True
            self._finish(type(exc), exc, exc.__traceback__)
            return self
        self.meta["load_time_s"] = round(now() - t, 3)
        self.meta["rss_after_load_mb"] = round(self.monitor.current_rss_mb(), 1)
        print(f"[{self.kind}] {self.model_id} loaded in {self.meta['load_time_s']}s")
        return self

    def _finish(self, exc_type, exc, tb):
        self.monitor.stop()
        self.meta["resources"] = self.monitor.result()
        if exc is not None:
            self.meta["error"] = "".join(traceback.format_exception(exc_type, exc, tb))
            print(f"!! {self.model_id} failed: {exc!r}")
        write_json(self.out_dir / "raw" / f"{self.model_id}.model.json", self.meta)
        if self.engine is not None:
            self.engine.close()

    def __exit__(self, exc_type, exc, tb):
        if not self.failed:
            self._finish(exc_type, exc, tb)
        # 單一模型失敗不中斷整個套件；但 Ctrl+C 要能中止
        return exc_type is not None and not issubclass(exc_type, KeyboardInterrupt)


# ---------------------------------------------------------------- STT
def run_stt(suite, models, out, args):
    lang_mode = suite.get("lang_mode", "given")        # given = 指定語言；auto = 讓模型自己偵測（測 LID）
    for model_id in suite["models"]:
        spec = models["stt"][model_id]
        with ModelSession("stt", model_id, spec, out) as sess:
            if sess.failed:
                continue
            engine = sess.engine
            for lang in suite["languages"]:
                if lang not in spec.get("langs", L.ALL):
                    print(f"  skip {lang}: not supported by {model_id}")
                    continue
                lang_arg = (lang if engine.wants_locale else L.base(lang)) if lang_mode == "given" else None
                for dataset in suite["datasets"]:
                    for cond in suite.get("conditions", ["clean"]):
                        mpath = manifest_path(lang, dataset, cond)
                        if mpath is None:
                            print(f"  skip {lang}/{dataset}/{cond}: manifest not found")
                            continue
                        items = read_jsonl(mpath)[: suite.get("n_samples")]
                        key = f"{model_id}__{lang}__{dataset}__{cond}"
                        print(f"  {key}: {len(items)} items")
                        audios = [load_audio(ROOT / it["audio"]) for it in items]   # 讀檔不計時

                        for a in audios[: suite.get("warmup", 2)]:
                            engine.transcribe(a, lang_arg)

                        rows = []
                        for it, audio in zip(items, audios):
                            t = now()
                            res = engine.transcribe(audio, lang_arg)
                            dt = now() - t
                            dur = len(audio) / STT_SR
                            rows.append({
                                "id": it["id"], "lang": lang, "ref": it.get("text", ""), "hyp": res.text,
                                "lang_detected": res.lang, "lang_prob": res.lang_prob,
                                "duration_s": round(dur, 3), "proc_s": round(dt, 4), "rtf": round(dt / dur, 4),
                                "keywords": it.get("keywords"), "expect_empty": it.get("expect_empty", False),
                            })

                        repeats = []
                        for _ in range(suite.get("speed_repeats", 0)):
                            for audio in audios[: suite.get("speed_items", 10)]:
                                t = now()
                                engine.transcribe(audio, lang_arg)
                                repeats.append((now() - t) / (len(audio) / STT_SR))

                        stream = []
                        if engine.supports_streaming and suite.get("stream_chunks_ms"):
                            from bench.streaming_sim import simulate
                            for chunk_ms in suite["stream_chunks_ms"]:
                                for it, audio in list(zip(items, audios))[: suite.get("stream_items", 20)]:
                                    stream.append({"id": it["id"], **simulate(engine, audio, STT_SR, lang_arg, chunk_ms)})

                        write_jsonl(out / "raw" / f"{key}.jsonl", rows)
                        write_json(out / "raw" / f"{key}.meta.json", {
                            "task": "stt", "model": model_id, "lang": lang, "dataset": dataset,
                            "condition": cond, "lang_mode": lang_mode, "speed_repeat_rtf": repeats,
                            "streaming": stream,
                        })
        del sess
        gc.collect()


# ---------------------------------------------------------------- TTS
def synth_timed(engine, text, lang, sentence_split):
    segments = split_sentences(text) if sentence_split else [text]
    t = now()
    ttfa, chunks = None, []
    for seg in segments:
        for chunk in engine.synthesize_stream(seg, lang):
            if ttfa is None:
                ttfa = now() - t
            chunks.append(chunk)
    total = now() - t
    audio = np.concatenate(chunks) if chunks else np.zeros(1, np.float32)
    return audio, ttfa if ttfa is not None else total, total


def run_tts(suite, models, out, args):
    for model_id in suite["models"]:
        spec = models["tts"][model_id]
        with ModelSession("tts", model_id, spec, out) as sess:
            if sess.failed:
                continue
            engine = sess.engine
            for lang in suite["languages"]:
                if not engine.supports(lang):
                    print(f"  skip {lang}: not supported by {model_id}")
                    continue
                engine.prepare(lang)
                sr = engine.sample_rate_for(lang)
                texts = read_texts(ROOT / suite.get("text_dir", "data/tour_texts") / f"{lang}.txt")
                texts = texts[: suite.get("n_samples")]
                key = f"{model_id}__{lang}__{suite.get('text_set', 'tour')}__clean"
                print(f"  {key}: {len(texts)} texts")
                for text in texts[: suite.get("warmup", 2)]:
                    synth_timed(engine, text, lang, suite.get("sentence_split", True))
                rows = []
                for i, text in enumerate(texts):
                    audio, ttfa, total = synth_timed(engine, text, lang, suite.get("sentence_split", True))
                    rel = Path("audio") / model_id / lang / f"{i:03d}.wav"
                    save_wav(out / rel, audio, sr)
                    dur = len(audio) / sr
                    rows.append({
                        "id": f"{lang}-{i:03d}", "lang": lang, "text": text, "wav": rel.as_posix(), "sr": sr,
                        "ttfa_s": round(ttfa, 4), "proc_s": round(total, 4),
                        "audio_s": round(dur, 3), "rtf": round(total / max(dur, 1e-6), 4),
                    })
                write_jsonl(out / "raw" / f"{key}.jsonl", rows)
                write_json(out / "raw" / f"{key}.meta.json", {
                    "task": "tts", "model": model_id, "lang": lang,
                    "dataset": suite.get("text_set", "tour"), "condition": "clean",
                })
        del sess
        gc.collect()


# ---------------------------------------------------------------- Dialogue (STT → LLM → TTS)
def system_prompt(lang, venue):
    return (
        "You are a friendly museum tour guide robot talking with a visitor. "
        f"Always answer in {L.LANGS[lang]['llm_hint']}, no matter what language the visitor uses. "
        "Answer in 1 to 3 short, natural spoken sentences. No lists, no markdown, no emoji. "
        "Use only the venue information below; if you don't know, say so politely.\n\n"
        f"VENUE INFORMATION:\n{venue}"
    )


def question_audio(q, lang, question_tts, cache, audio_dir=None):
    """問題音檔：manifest 有就用；沒有就用 question_tts 合成一次並快取（標記 synthetic）。"""
    if q.get("audio"):
        return load_audio(ROOT / q["audio"]), False
    path = (audio_dir or ROOT / "data" / "dialogue" / "audio") / lang / f"{q['id']}.wav"
    if not path.exists():
        tts_id = question_tts.get(lang, question_tts["default"])
        engine = cache.get("tts", tts_id)
        engine.prepare(lang)
        audio, _, _ = synth_timed(engine, q["text"], lang, False)
        save_wav(path, resample(audio, engine.sample_rate_for(lang), STT_SR), STT_SR)
    return load_audio(path), True


class EngineCache:
    """對話測試中多個組合共用已載入的模型，避免重複載入。"""

    def __init__(self, models, out):
        self.models, self.out, self.sessions = models, out, {}

    def get(self, kind, model_id):
        key = (kind, model_id)
        if key not in self.sessions:
            sess = ModelSession(kind, model_id, self.models[kind][model_id], self.out)
            sess.__enter__()
            self.sessions[key] = sess
        if self.sessions[key].failed:
            raise RuntimeError(f"{kind} model {model_id} failed to load (see raw/{model_id}.model.json)")
        return self.sessions[key].engine

    def keep_only(self, keys):
        """釋放 keys 以外的模型。組合之間若不釋放，模型會累積到記憶體不足、系統改用分頁檔，
        越後面的組合越慢（實測 Kokoro 慢到 16 倍），延遲數據就失真。"""
        for key in [k for k in self.sessions if k not in keys]:
            sess = self.sessions.pop(key)
            if not sess.failed:
                sess.__exit__(None, None, None)
        gc.collect()

    def close(self):
        self.keep_only(set())


def run_dialogue(suite, models, out, args):
    # questions: museum（預設，data/dialogue/ 導覽問答）或 care（data/care/ 照護情境題，系統提示與 llm_eval.py 相同）
    care = suite.get("questions") == "care"
    # 延遲改進（2026-10-07）：fast_path = 規則層＋[CALL_NURSE] 觸發時立即通報並播放固定回應；
    # first_chunk: clause = TTS 在逗號等子句標點處就開始唸；short_first = 要求 LLM 第一句很短
    fast_path = care and suite.get("fast_path", False)
    fixed_texts = yaml.safe_load((CARE / "fixed_responses.yaml").read_text(encoding="utf-8")) if fast_path else {}

    def first_chunk(text, lang):
        if suite.get("first_chunk") == "clause":
            return first_complete_clause(text, 6 if L.base(lang) == "ja" else 12)
        return first_complete_sentence(text)
    dataset = "care" if care else "dialogue"
    audio_dir = ROOT / "data" / dataset / "audio"
    venue = (ROOT / suite.get("venue_file", "data/dialogue/venue.md")).read_text(encoding="utf-8")
    vad_s = suite.get("vad_endpoint_ms", 300) / 1000
    cache = EngineCache(models, out)
    try:
        if care:   # 先合成全部提問音檔並釋放 TTS，避免它佔用第一個組合的記憶體、干擾量測
            for lang in suite["languages"]:
                for s in load_scenarios(suite.get("ids"))[: suite.get("n_samples")]:
                    question_audio({"id": s["id"], "text": s["text"][lang]}, lang, suite["question_tts"], cache, audio_dir)
            cache.keep_only(set())
        for combo in suite["combos"]:
            name = f"{combo['stt']}+{combo['llm']}+{combo['tts']}"
            if not set(combo.get("langs", suite["languages"])) & set(suite["languages"]):
                continue    # 這個組合的語言都不在本次範圍（例如冒煙測試只跑部分語言），不必載入模型
            stt = llm = tts = None      # 先放掉上一組的引用，keep_only 才真的釋放得掉
            cache.keep_only({(k, combo[k]) for k in ("stt", "llm", "tts")})
            try:
                stt = cache.get("stt", combo["stt"])
                llm = cache.get("llm", combo["llm"])
                tts = cache.get("tts", combo["tts"])
            except RuntimeError as exc:
                print(f"!! skip combo {name}: {exc}")
                continue
            for lang in suite["languages"]:
                if lang not in combo.get("langs", suite["languages"]):
                    continue    # 組合指定只跑某些語言（依語言選 STT 的部署方式）
                if lang not in models["stt"][combo["stt"]].get("langs", L.ALL) or not tts.supports(lang):
                    print(f"  skip {name} {lang}: unsupported")
                    continue
                tts.prepare(lang)
                sr = tts.sample_rate_for(lang)
                # 固定回應事先合成（實際部署為預錄音檔，播放延遲視為 0）
                fixed_audio = synth_timed(tts, fixed_texts[lang], lang, True)[0] if fast_path else None
                if care:
                    questions = [{"id": s["id"], "text": s["text"][lang], "action": s["action"],
                                  "category": s["category"], "reasoning": "reasoning" in s.get("tags", []),
                                  "history": [{"role": h["role"], "content": h["text"][lang]} for h in s.get("history", [])]}
                                 for s in load_scenarios(suite.get("ids"))][: suite.get("n_samples")]
                    sys_msg = care_system(lang, suite.get("policy", "policy.md"), suite.get("short_first", False))
                else:
                    questions = read_jsonl(ROOT / "data" / "dialogue" / f"{lang}.jsonl")[: suite.get("n_samples")]
                    sys_msg = system_prompt(lang, venue)
                user_suffix = models["llm"][combo["llm"]].get("user_suffix", "")   # 例：Qwen3 的 /no_think
                print(f"  {name} {lang}: {len(questions)} questions")

                def turn(q, save_prefix=None):
                    audio, synthetic = question_audio(q, lang, suite["question_tts"], cache, audio_dir)
                    t = now()
                    res = stt.transcribe(audio, lang if stt.wants_locale else L.base(lang))
                    t_stt = now() - t
                    t = now()
                    rule_hits = care_rules.match(res.text, lang) if fast_path else []   # 規則層：在 LLM 之前比對
                    t_rule = now() - t

                    messages = [{"role": "system", "content": sys_msg}, *q.get("history", []),
                                {"role": "user", "content": res.text + user_suffix}]
                    t = now()
                    buf, n_tok, ttft, first_sent, t_first_sent, t_tag = "", 0, None, None, None, None
                    for piece in llm.chat_stream(messages, suite.get("max_tokens", 160), suite.get("temperature", 0.3)):
                        n_tok += 1
                        if ttft is None:
                            ttft = now() - t
                        buf += piece
                        visible = strip_think(buf)
                        if t_tag is None and tag_of(visible):
                            t_tag = now() - t       # 讀到通報標記的時間：系統此時即可通知醫護
                        if first_sent is None:
                            first_sent = first_chunk(spoken_text(visible), lang)   # 標記不唸
                            if first_sent is not None:
                                t_first_sent = now() - t
                    t_llm = now() - t
                    response = spoken_text(strip_think(buf))
                    if first_sent is None:
                        first_sent, t_first_sent = response, t_llm

                    # 第一句先送 TTS：真實系統中 LLM 會同時繼續生成，這裡的首段音訊延遲為下限估計
                    if first_sent:
                        first_audio, t_tts_ttfa, t_tts_first = synth_timed(tts, clean_for_tts(first_sent), lang, False)
                    else:   # 回答只有通報標記、沒有要唸的內容
                        first_audio, t_tts_ttfa, t_tts_first = np.zeros(int(0.2 * sr), dtype=np.float32), 0.0, 0.0
                    row = {
                        "id": q["id"], "lang": lang, "question": q["text"], "question_synthetic": synthetic,
                        "stt_hyp": res.text, "response": response, "first_sentence": first_sent,
                        "facts": q.get("facts", []),
                        "stt_s": round(t_stt, 4), "llm_ttft_s": round(ttft or t_llm, 4),
                        "llm_first_sentence_s": round(t_first_sent, 4), "llm_total_s": round(t_llm, 4),
                        "llm_tokens": n_tok, "llm_tok_s": round(n_tok / t_llm, 2) if t_llm > 0 else None,
                        "tts_ttfa_s": round(t_tts_ttfa, 4), "tts_first_sentence_s": round(t_tts_first, 4),
                        "vad_endpoint_s": vad_s,
                        "turn_latency_s": round(vad_s + t_stt + t_first_sent + t_tts_ttfa, 4),
                    }
                    if care:
                        tag = tag_of(strip_think(buf))
                        row.update({
                            "history": q["history"], "response_raw": strip_think(buf).strip(), "tag": tag,
                            "action": q["action"], "category": q["category"], "reasoning": q["reasoning"],
                            "action_ok": action_ok(q["action"], tag),
                            "llm_tag_s": round(t_tag, 4) if t_tag is not None else None,
                            # 住民說完 → 系統讀到通報標記（緊急情況真正關鍵的時間，不必等 TTS）
                            "alert_latency_s": round(vad_s + t_stt + t_tag, 4) if t_tag is not None else None,
                        })
                    if fast_path:
                        # 規則命中或 LLM 給出 [CALL_NURSE] → 立即通報並播放固定回應；兩者都有時取規則（較早）
                        trigger = "rule" if rule_hits else ("tag" if tag == "call" else None)
                        final_tag = "call" if rule_hits else tag
                        t_alert = t_rule if trigger == "rule" else t_tag
                        row.update({
                            "rule_hits": rule_hits, "rule_s": round(t_rule, 6), "fast_trigger": trigger,
                            "final_tag": final_tag, "final_action_ok": action_ok(q["action"], final_tag),
                            "rule_alert_latency_s": round(vad_s + t_stt + t_rule, 4) if rule_hits else None,
                            # 實際開口時間：緊急走快速通道（固定回應），其他照一般流程
                            "response_latency_s": round(vad_s + t_stt + t_alert, 4) if trigger else row["turn_latency_s"],
                        })
                    if save_prefix and suite.get("synthesize_full", True):
                        rest = response[len(first_sent):].strip() if response.startswith(first_sent) else ""
                        parts = [first_audio]
                        if fast_path and row.get("fast_trigger"):
                            parts = [fixed_audio, np.zeros(int(0.3 * sr), dtype=np.float32), first_audio]
                        if rest:
                            parts.append(synth_timed(tts, clean_for_tts(rest), lang, True)[0])
                        rel = Path("audio") / save_prefix / lang / f"{q['id']}.wav"
                        save_wav(out / rel, np.concatenate(parts), sr)
                        row["wav"], row["sr"] = rel.as_posix(), sr
                    return row

                # 每個組合×語言各自監控：此時程序內只載入這一組的三個模型，峰值即整條鏈路的記憶體
                mon = ResourceMonitor().start()
                try:
                    for q in questions[: suite.get("warmup", 1)]:
                        turn(q)
                    rows = [turn(q, save_prefix=name) for q in questions]
                except Exception:
                    print(f"!! {name} {lang} failed:\n{traceback.format_exc()}")
                    continue
                finally:
                    mon.stop()
                key = f"{name}__{lang}__{dataset}__clean"
                write_jsonl(out / "raw" / f"{key}.jsonl", rows)
                write_json(out / "raw" / f"{key}.meta.json", {
                    "task": "dialogue", "model": name, "combo": combo, "lang": lang,
                    "dataset": dataset, "condition": "clean", "resources": mon.result(),
                    **({"policy": suite.get("policy", "policy.md")} if care else {}),
                })
    finally:
        cache.close()


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--hw", required=True, help="硬體 profile 名稱，見 configs/hardware.yaml")
    ap.add_argument("--run-id")
    ap.add_argument("--models", nargs="*", help="只跑這些模型（覆蓋套件設定）")
    ap.add_argument("--langs", nargs="*", help="只跑這些語言（覆蓋套件設定）")
    ap.add_argument("--limit", type=int, help="每組最多幾句（覆蓋 n_samples）")
    args = ap.parse_args()

    suite = load_yaml(args.suite)
    models = load_yaml(ROOT / "configs" / "models.yaml")
    hardware = load_yaml(ROOT / "configs" / "hardware.yaml")
    if args.hw not in hardware["profiles"]:
        raise SystemExit(f"unknown --hw {args.hw}; choose from {list(hardware['profiles'])}")
    if args.models:
        suite["models"] = args.models
    if args.langs:
        suite["languages"] = args.langs
    if args.limit:
        suite["n_samples"] = args.limit

    run_id = args.run_id or f"{datetime.datetime.now():%Y%m%d-%H%M%S}_{suite['name']}_{args.hw}"
    out = ROOT / "results" / run_id
    write_json(out / "run.json", {"run_id": run_id, "suite": suite, "hw_profile": args.hw, "env": collect_env()})
    print(f"run_id = {run_id}")

    {"stt": run_stt, "tts": run_tts, "dialogue": run_dialogue}[suite["task"]](suite, models, out, args)
    print(f"done. next: python score.py results/{run_id}")


if __name__ == "__main__":
    main()
