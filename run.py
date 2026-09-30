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
from bench.envinfo import collect_env
from bench.monitor import ResourceMonitor
from bench.text import clean_for_tts, first_complete_sentence, split_sentences
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
                lang_arg = L.base(lang) if lang_mode == "given" else None
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


def question_audio(q, lang, question_tts, cache):
    """問題音檔：manifest 有就用；沒有就用 question_tts 合成一次並快取（標記 synthetic）。"""
    if q.get("audio"):
        return load_audio(ROOT / q["audio"]), False
    path = ROOT / "data" / "dialogue" / "audio" / lang / f"{q['id']}.wav"
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
    venue = (ROOT / suite.get("venue_file", "data/dialogue/venue.md")).read_text(encoding="utf-8")
    vad_s = suite.get("vad_endpoint_ms", 300) / 1000
    cache = EngineCache(models, out)
    try:
        for combo in suite["combos"]:
            name = f"{combo['stt']}+{combo['llm']}+{combo['tts']}"
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
                if lang not in models["stt"][combo["stt"]].get("langs", L.ALL) or not tts.supports(lang):
                    print(f"  skip {name} {lang}: unsupported")
                    continue
                tts.prepare(lang)
                sr = tts.sample_rate_for(lang)
                questions = read_jsonl(ROOT / "data" / "dialogue" / f"{lang}.jsonl")[: suite.get("n_samples")]
                sys_msg = system_prompt(lang, venue)
                print(f"  {name} {lang}: {len(questions)} questions")

                def turn(q, save_prefix=None):
                    audio, synthetic = question_audio(q, lang, suite["question_tts"], cache)
                    t = now()
                    res = stt.transcribe(audio, L.base(lang))
                    t_stt = now() - t

                    messages = [{"role": "system", "content": sys_msg}, {"role": "user", "content": res.text}]
                    t = now()
                    buf, n_tok, ttft, first_sent, t_first_sent = "", 0, None, None, None
                    for piece in llm.chat_stream(messages, suite.get("max_tokens", 160), suite.get("temperature", 0.3)):
                        n_tok += 1
                        if ttft is None:
                            ttft = now() - t
                        buf += piece
                        if first_sent is None:
                            first_sent = first_complete_sentence(buf)
                            if first_sent is not None:
                                t_first_sent = now() - t
                    t_llm = now() - t
                    response = buf.strip()
                    if first_sent is None:
                        first_sent, t_first_sent = response, t_llm

                    # 第一句先送 TTS：真實系統中 LLM 會同時繼續生成，這裡的首段音訊延遲為下限估計
                    first_audio, t_tts_ttfa, t_tts_first = synth_timed(tts, clean_for_tts(first_sent), lang, False)
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
                    if save_prefix and suite.get("synthesize_full", True):
                        rest = response[len(first_sent):].strip() if response.startswith(first_sent) else ""
                        parts = [first_audio]
                        if rest:
                            parts.append(synth_timed(tts, clean_for_tts(rest), lang, True)[0])
                        rel = Path("audio") / save_prefix / lang / f"{q['id']}.wav"
                        save_wav(out / rel, np.concatenate(parts), sr)
                        row["wav"], row["sr"] = rel.as_posix(), sr
                    return row

                try:
                    for q in questions[: suite.get("warmup", 1)]:
                        turn(q)
                    rows = [turn(q, save_prefix=name) for q in questions]
                except Exception:
                    print(f"!! {name} {lang} failed:\n{traceback.format_exc()}")
                    continue
                key = f"{name}__{lang}__dialogue__clean"
                write_jsonl(out / "raw" / f"{key}.jsonl", rows)
                write_json(out / "raw" / f"{key}.meta.json", {
                    "task": "dialogue", "model": name, "combo": combo, "lang": lang,
                    "dataset": "dialogue", "condition": "clean",
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
