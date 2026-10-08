"""LLM 醫療照護評測（計畫見 docs/roadmap.md「LLM 評測：醫療照護情境」）。

兩部分，結果存在 results/<run_id>/：
  care       照護情境題（data/care/scenarios.yaml，6 種語言）。依回答中的 [CALL_NURSE] / [NOTIFY_NURSE]
             標記自動計算緊急漏報率、通報不足率、過度緊急率；評分標準（must / must_not）留待評審模型與護理人員
  knowledge  醫學知識選擇題：Global-MMLU 醫學 8 科（en / es / pt / ja，各語言同一批題目）、
             HEAD-QA 護理（es-ES）、MMedBench 日本醫師國考（ja，只取單選題）

  .venv-core\\Scripts\\python.exe llm_eval.py --models qwen2.5-1.5b-q4 gemma-3-4b-q4 --run-id 20261005_llm_eval_pc
  --tasks care knowledge   先跑完所有模型的 care，再跑 knowledge（care 較重要，沒跑完也先有結果）
  --n-mc 100               每個選擇題子集抽幾題（固定亂數種子，各模型同一批題目）
  --limit 2                冒煙測試：每組只跑前幾題
  --policy policy_v2.md    照護情境用的機器人守則（data/care/ 下的檔名；預設 policy.md，即第 1 版）
用同一個 --run-id 重跑會略過已完成的部分（可中斷續跑）。
LLM 一律用不思考模式、溫度 0（結果可重現）；思考模式在開發機上太慢，留到 Jetson。
"""
import argparse
import datetime
import json
import os
import random
import re
import sys
import time
import traceback
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bench import languages as L  # noqa: E402
from bench.care import (CARE, action_ok, care_system, load_scenarios, spoken_text, strip_think,  # noqa: E402
                        tag_of)
from engines.base import build_engine  # noqa: E402
from metrics.lang_check import detect  # noqa: E402
from metrics.wer_cer import bootstrap_ci  # noqa: E402
from run_all import Log, keep_awake, preflight  # noqa: E402

LLM_DATA = ROOT / "data" / "llm"
MED_SUBJECTS = ["anatomy", "clinical_knowledge", "college_biology", "college_medicine", "medical_genetics",
                "nutrition", "professional_medicine", "virology"]
MC_SYSTEM = ("You are answering a multiple-choice medical exam question. "
             "Reply with only the letter of the correct answer.")


# ---------------------------------------------------------------- 模型
def load_llm(models, mid, n_ctx=4096):
    spec = json.loads(json.dumps(models["llm"][mid]))
    spec.setdefault("params", {})["n_ctx"] = n_ctx   # 照護題的系統提示約 1,000 token，預設 2048 不夠寬裕
    eng = build_engine(spec)
    t = time.perf_counter()
    eng.load()
    return eng, spec, time.perf_counter() - t


def chat(eng, spec, messages, max_tokens):
    """回傳（去掉思考區塊的回答, 計時）。溫度 0。"""
    suffix = spec.get("user_suffix", "")
    if suffix:
        messages = messages[:-1] + [{**messages[-1], "content": messages[-1]["content"] + suffix}]
    t0 = time.perf_counter()
    ttft, text, n = None, "", 0
    for piece in eng.chat_stream(messages, max_tokens, 0.0):
        if ttft is None:
            ttft = time.perf_counter() - t0
        text += piece
        n += 1
    total = time.perf_counter() - t0
    text = strip_think(text).strip()
    return text, {"ttft_s": round(ttft or total, 3), "total_s": round(total, 3), "tokens": n}


# ---------------------------------------------------------------- 照護情境題
def run_care(eng, spec, mid, langs, limit, out, log, policy_file="policy.md", ids=None):
    scenarios = load_scenarios(ids)[:limit]
    for lang in langs:
        path = out / "raw" / f"{mid}__care__{lang}.jsonl"
        if path.exists() and len(path.read_text(encoding="utf-8").splitlines()) == len(scenarios):
            log(f"  {mid} care {lang}: 已完成，略過")
            continue
        system = care_system(lang, policy_file)
        rows, t = [], time.perf_counter()
        for i, s in enumerate(scenarios, 1):
            if i % 10 == 0:   # 每 10 題印一次，避免以為程式卡住
                log(f"    … {mid} care {lang} {i}/{len(scenarios)}（{time.perf_counter() - t:.0f}s）")
            messages = [{"role": "system", "content": system}]
            messages += [{"role": h["role"], "content": h["text"][lang]} for h in s.get("history", [])]
            messages.append({"role": "user", "content": s["text"][lang]})
            resp, timing = chat(eng, spec, messages, 200)
            tag = tag_of(resp)
            spoken = spoken_text(resp)
            rows.append({"id": s["id"], "lang": lang, "category": s["category"], "action": s["action"],
                         "reasoning": "reasoning" in s.get("tags", []), "user": s["text"][lang], "response": resp,
                         "tag": tag, "tag_at_start": bool(tag) and resp.lstrip().startswith("["),
                         "action_ok": action_ok(s["action"], tag), "detected_lang": detect(spoken), **timing})
        write_jsonl(path, rows)
        miss = [r for r in rows if r["action"] == "call_now" and r["tag"] != "call"]
        log(f"  {mid} care {lang}: {len(rows)} 題，{time.perf_counter() - t:.0f}s，"
            f"緊急漏報 {len(miss)}/{sum(r['action'] == 'call_now' for r in rows)}")


# ---------------------------------------------------------------- 醫學知識選擇題
def mc_subsets(n, seed=0):
    """回傳 {子集名: (語言, [題目])}；題目為 {"id", "question", "options": {字母: 內容}, "answer": 字母}。"""
    subsets = {}
    frames = {l: pd.read_parquet(LLM_DATA / "global_mmlu" / f"{l}_test.parquet") for l in ["en", "es", "pt", "ja"]}
    ids = sorted(frames["en"][frames["en"].subject.isin(MED_SUBJECTS)].sample_id)
    pick = set(random.Random(seed).sample(ids, min(n, len(ids))))   # 4 種語言同一批題目
    for l, d in frames.items():
        d = d[d.sample_id.isin(pick)].sort_values("sample_id")
        subsets[f"gmmlu_{l}"] = (l, [{"id": r.sample_id, "question": r.question,
                                      "options": {k.upper(): getattr(r, f"option_{k}") for k in "abcd"},
                                      "answer": r.answer} for r in d.itertuples()])
    z = zipfile.ZipFile(LLM_DATA / "head_qa" / "head_qa.zip")
    exams = json.loads(z.read("HEAD/test_HEAD.json"))["exams"]
    items = []
    for name, e in sorted(exams.items()):
        if e["category"] != "nursery":
            continue
        for q in e["data"]:
            letters = "ABCDE"
            opts = {letters[i]: a["atext"] for i, a in enumerate(q["answers"])}
            right = next(i for i, a in enumerate(q["answers"]) if str(a["aid"]) == str(q["ra"]))
            items.append({"id": f"{name}/{q['qid']}", "question": q["qtext"], "options": opts, "answer": letters[right]})
    subsets["headqa_nursing"] = ("es-ES", random.Random(seed).sample(items, min(n, len(items))))
    z = zipfile.ZipFile(LLM_DATA / "mmedbench" / "MMedBench.zip")
    rows = [json.loads(l) for l in z.read("MMedBench/Test/Japanese.jsonl").decode("utf-8").splitlines() if l.strip()]
    items = [{"id": r["problem_id"], "question": r["question"], "options": r["options"], "answer": r["answer_idx"][0]}
             for r in rows if len(r["answer_idx"]) == 1]
    subsets["igakuqa"] = ("ja", random.Random(seed).sample(items, min(n, len(items))))
    return subsets


def parse_letter(text, letters):
    m = re.search(rf"(?<![A-Za-z])([{letters}])(?![A-Za-z])", text.upper())
    return m.group(1) if m else None


def run_knowledge(eng, spec, mid, subsets, limit, out, log):
    for name, (lang, items) in subsets.items():
        items = items[:limit]
        path = out / "raw" / f"{mid}__knowledge__{name}.jsonl"
        if path.exists() and len(path.read_text(encoding="utf-8").splitlines()) == len(items):
            log(f"  {mid} knowledge {name}: 已完成，略過")
            continue
        rows, t = [], time.perf_counter()
        for i, it in enumerate(items, 1):
            if i % 25 == 0:
                log(f"    … {mid} knowledge {name} {i}/{len(items)}（{time.perf_counter() - t:.0f}s）")
            letters = "".join(it["options"])
            prompt = it["question"].strip() + "\n\n" + "\n".join(f"{k}. {v}" for k, v in it["options"].items()) + "\n\nAnswer:"
            resp, timing = chat(eng, spec, [{"role": "system", "content": MC_SYSTEM}, {"role": "user", "content": prompt}], 12)
            pred = parse_letter(resp, letters)
            rows.append({"id": it["id"], "subset": name, "lang": lang, "answer": it["answer"], "pred": pred,
                         "correct": pred == it["answer"], "response": resp, **timing})
        write_jsonl(path, rows)
        acc = np.mean([r["correct"] for r in rows])
        log(f"  {mid} knowledge {name}: {len(rows)} 題，{time.perf_counter() - t:.0f}s，正確率 {acc:.1%}")


# ---------------------------------------------------------------- 防止同一個 run 重複執行
def acquire_lock(out):
    """同一個 run 已有程序在跑就結束（例如 cmd 與背景各啟動一次）。程序異常結束留下的舊鎖會自動忽略。"""
    lock = out / "running.lock"
    if lock.exists():
        try:
            pid = int(lock.read_text().strip())
            alive = psutil.pid_exists(pid) and "python" in psutil.Process(pid).name().lower()
        except (ValueError, psutil.Error):
            alive = False
        if alive and pid != os.getpid():
            raise SystemExit(f"此 run 已在執行中（PID {pid}），不重複啟動。進度請看 logs\llm_eval_*.log")
    lock.write_text(str(os.getpid()))
    return lock


# ---------------------------------------------------------------- 彙整
def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def rate(rows, cond, hit):
    sel = [r for r in rows if cond(r)]
    return (sum(hit(r) for r in sel) / len(sel)) if sel else None


def summarize(out, models):
    recs = []
    run_args = json.loads((out / "run.json").read_text(encoding="utf-8")).get("args", {}) if (out / "run.json").exists() else {}
    for path in sorted((out / "raw").glob("*.jsonl")):
        mid, task, subset = path.stem.split("__")
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
        base = {"model": mid, "task": task, "subset": subset, "n": len(rows),
                "policy": run_args.get("policy", "policy.md") if task == "care" else None,
                "license": models["llm"].get(mid, {}).get("license"),
                "ttft_ms_p50": np.median([r["ttft_s"] for r in rows]) * 1000,
                "tokens_mean": np.mean([r["tokens"] for r in rows]),
                "tok_s": sum(r["tokens"] for r in rows) / max(sum(r["total_s"] for r in rows), 1e-9)}
        if task == "care":
            base.update({
                "lang": subset,
                "action_ok_rate": rate(rows, lambda r: True, lambda r: r["action_ok"]),
                "emergency_miss_rate": rate(rows, lambda r: r["action"] == "call_now", lambda r: r["tag"] != "call"),
                "notify_miss_rate": rate(rows, lambda r: r["action"] == "notify", lambda r: r["tag"] is None),
                "over_call_rate": rate(rows, lambda r: r["action"] != "call_now", lambda r: r["tag"] == "call"),
                "reasoning_ok_rate": rate(rows, lambda r: r["reasoning"], lambda r: r["action_ok"]),
                "tag_at_start_rate": rate(rows, lambda r: r["tag"] is not None, lambda r: r["tag_at_start"]),
                # 每次彙整都用目前的語言偵測重算（偵測規則更新後不必重跑模型）
                "lang_wrong_rate": rate(rows, lambda r: True,
                                        lambda r: detect(spoken_text(r["response"])) not in (L.base(r["lang"]), "unknown")),
            })
        else:
            c = [float(r["correct"]) for r in rows]
            lo, hi = bootstrap_ci(c, [1] * len(c))
            base.update({"lang": rows[0]["lang"] if rows else None, "accuracy": float(np.mean(c)) if c else None,
                         "acc_ci95_low": lo, "acc_ci95_high": hi,
                         "invalid_rate": rate(rows, lambda r: True, lambda r: r["pred"] is None)})
        recs.append(base)
    df = pd.DataFrame(recs)
    if not df.empty:
        df.to_csv(out / "summary.csv", index=False, encoding="utf-8-sig", float_format="%.4f")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--tasks", nargs="+", default=["care", "knowledge"], choices=["care", "knowledge"])
    ap.add_argument("--langs", nargs="*", default=L.ALL, help="照護情境題的語言")
    ap.add_argument("--n-mc", type=int, default=100)
    ap.add_argument("--limit", type=int, help="冒煙測試：每組只跑前幾題")
    ap.add_argument("--policy", default="policy.md", help="照護情境的機器人守則（data/care/ 下的檔名）")
    ap.add_argument("--ids", nargs="*", help="照護情境只跑這些題目（如 EM10 SY06；冒煙測試用）")
    ap.add_argument("--run-id")
    args = ap.parse_args()

    models = yaml.safe_load((ROOT / "configs" / "models.yaml").read_text(encoding="utf-8"))
    unknown = [m for m in args.models if m not in models["llm"]]
    if unknown:
        raise SystemExit(f"models.yaml 沒有這些 LLM：{unknown}")
    stamp = f"{datetime.datetime.now():%Y%m%d-%H%M%S}"
    run_id = args.run_id or f"{stamp}_llm_eval_pc"
    out = ROOT / "results" / run_id
    out.mkdir(parents=True, exist_ok=True)
    lock = acquire_lock(out)
    log = Log(ROOT / "logs" / f"llm_eval_{stamp}.log")
    if not (CARE / args.policy).exists():
        raise SystemExit(f"找不到守則 data/care/{args.policy}")
    log(f"run_id={run_id} models={args.models} tasks={args.tasks} policy={args.policy} n_mc={args.n_mc} limit={args.limit}")
    (out / "run.json").write_text(json.dumps({"run_id": run_id, "args": vars(args)}, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
    if not args.limit:
        preflight(log)
    subsets = mc_subsets(args.n_mc) if "knowledge" in args.tasks else {}
    t_all = time.perf_counter()
    keep_awake(True)
    try:
        for task in args.tasks:
            for mid in args.models:
                log(f"\n=== {task} · {mid}")
                eng = None
                try:
                    eng, spec, load_s = load_llm(models, mid)
                    log(f"  載入 {load_s:.1f}s")
                    if task == "care":
                        run_care(eng, spec, mid, args.langs, args.limit, out, log, args.policy, args.ids)
                    else:
                        run_knowledge(eng, spec, mid, subsets, args.limit, out, log)
                except Exception:
                    log(f"!! {mid} {task} failed:\n{traceback.format_exc()}")
                finally:
                    if eng is not None:
                        eng.close()
                summarize(out, models)
    finally:
        keep_awake(False)
        lock.unlink(missing_ok=True)
    df = summarize(out, models)
    log(f"\n全部完成，共 {(time.perf_counter() - t_all) / 60:.0f} 分鐘。結果：{out / 'summary.csv'}")
    if not df.empty:
        care = df[df.task == "care"]
        if not care.empty:
            log("\n照護情境（各語言平均）：")
            log(care.groupby("model")[["action_ok_rate", "emergency_miss_rate", "notify_miss_rate", "over_call_rate",
                                       "lang_wrong_rate", "ttft_ms_p50"]].mean().round(3).to_string())
        know = df[df.task == "knowledge"]
        if not know.empty:
            log("\n醫學知識正確率：")
            log(know.pivot_table(index="model", columns="subset", values="accuracy").round(3).to_string())


if __name__ == "__main__":
    main()
