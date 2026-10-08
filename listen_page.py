"""產生本機試聽頁 results/<run_id>/listen.html：同一句並排比較各模型的語音，方便人工聽測。

score.py 評分完會自動產生；也可手動執行：
  python listen_page.py results/<run_id>
  python listen_page.py --all            # 所有 run

- TTS：每列一句導覽文本，並排各 TTS 模型的合成語音，附 Whisper 評審聽到的文字
- 對話：每列一個問題，並排各組合的回答語音，附 STT 聽到的問題、回答文字、事實是否答對
網頁只引用本機音檔的相對路徑，用瀏覽器直接開啟即可，不會上傳。
"""
import argparse
import csv
import html
import json
import os
from collections import defaultdict
from pathlib import Path

from bench import languages as L
from metrics.normalize import normalize

ROOT = Path(__file__).resolve().parent
esc = html.escape

CSS = """
:root { --bg:#fcfcfb; --fg:#1a1a18; --muted:#6b6a66; --line:#e6e5e1; --card:#ffffff; --accent:#2a6fd6; --ok:#1f8a4c; --bad:#c2410c; }
@media (prefers-color-scheme: dark) { :root { --bg:#161615; --fg:#ecebe7; --muted:#9a9993; --line:#2e2d2a; --card:#1e1e1c; --accent:#7aa7ff; --ok:#4cc38a; --bad:#fb923c; } }
body { margin:0; padding:24px 16px 64px; background:var(--bg); color:var(--fg);
       font:15px/1.55 system-ui,"Microsoft JhengHei","Noto Sans CJK TC",sans-serif; }
main { max-width:1200px; margin:0 auto; }
h1 { font-size:22px; margin:0 0 4px; } .lead { color:var(--muted); margin:0 0 24px; }
h2 { font-size:17px; margin:32px 0 10px; }
.scroll { overflow-x:auto; border:1px solid var(--line); border-radius:8px; background:var(--card); }
table { border-collapse:collapse; width:100%; min-width:760px; }
th, td { padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
th { font-size:13px; font-weight:600; } tr:last-child td { border-bottom:0; }
td.num { color:var(--muted); width:28px; } td.text { width:32%; } td.na { color:var(--muted); }
table.dlg td { min-width:240px; } table.dlg td.num { min-width:0; } table.dlg td.text { width:auto; min-width:200px; }
audio { width:100%; min-width:220px; height:34px; }
.meta { color:var(--muted); font-size:12px; font-weight:400; margin-top:2px; }
.heard { font-size:12px; margin-top:4px; color:var(--muted); border-left:2px solid var(--accent); padding-left:6px; }
.resp { font-size:13px; margin-top:6px; }
.ok { color:var(--ok); font-weight:600; } .bad { color:var(--bad); font-weight:600; }
"""


def read_jsonl(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def load(run_dir):
    """{task: {lang: {item_id: {model: row}}}}；有 Whisper 評審結果（.judge.jsonl）時優先讀取。"""
    data = {"tts": defaultdict(lambda: defaultdict(dict)), "dialogue": defaultdict(lambda: defaultdict(dict))}
    raw = run_dir / "raw"
    for mp in raw.glob("*.meta.json"):
        meta = json.loads(mp.read_text(encoding="utf-8"))
        if meta["task"] not in data:
            continue
        key = mp.name[: -len(".meta.json")]
        judge, plain = raw / f"{key}.judge.jsonl", raw / f"{key}.jsonl"
        src = judge if judge.exists() else plain
        if not src.exists():
            continue
        for r in read_jsonl(src):
            if r.get("wav"):
                data[meta["task"]][meta["lang"]][r["id"]][meta["model"]] = r
    return data


def load_summary(run_dir):
    p = run_dir / "summary.csv"
    if not p.exists():
        return {}
    with open(p, encoding="utf-8-sig") as f:
        return {(r["model"], r["lang"]): r for r in csv.DictReader(f)}


def fnum(v, scale=1.0, digits=1):
    try:
        return f"{float(v) * scale:.{digits}f}"
    except (TypeError, ValueError):
        return "–"


def short_combo(name):
    """'whisper-small-ct2-int8+qwen2.5-1.5b-q4+kokoro-82m' → 三行：STT / LLM / TTS。"""
    parts = name.split("+")
    labels = ("STT", "LLM", "TTS")
    return "<br>".join(f"<span class='meta'>{lab}</span> {esc(p)}" for lab, p in zip(labels, parts)) if len(parts) == 3 else esc(name)


def tts_section(lang, items, models, summary):
    heads = []
    for m in models:
        s = summary.get((m, lang))
        meta = (f"UTMOS {fnum(s.get('utmos'), digits=2)} · 錯誤率 {fnum(s.get('asr_err'), 100)}%" if s else "不支援此語言")
        heads.append(f"<th>{esc(m)}<div class='meta'>{meta}</div></th>")
    rows = []
    for item_id in sorted(items):
        by_model = items[item_id]
        text = next(iter(by_model.values()))["text"]
        cells = []
        for m in models:
            r = by_model.get(m)
            if not r:
                cells.append("<td class='na'>—</td>")
                continue
            heard = r.get("asr_judge_hyp")
            cells.append(
                f"<td><audio controls preload='none' src='{esc(r['wav'])}'></audio>"
                f"<div class='meta'>{r['audio_s']:.1f} 秒 · 首段 {r['ttfa_s'] * 1000:.0f} ms</div>"
                + (f"<div class='heard'>Whisper 聽到：{esc(heard)}</div>" if heard else "") + "</td>")
        rows.append(f"<tr><td class='num'>{esc(item_id.split('-')[-1])}</td><td class='text'>{esc(text)}</td>{''.join(cells)}</tr>")
    return table_block(lang, "", f"<th>#</th><th>文字</th>{''.join(heads)}", rows)


def fact_marks(r, lang):
    groups = r.get("facts") or []
    if not groups:
        return ""
    resp = normalize(r["response"], lang)
    hits = [any(normalize(alt, lang) in resp for alt in g) for g in groups]
    return "<span class='ok'>事實 ✓</span>" if all(hits) else "<span class='bad'>事實 ✗</span>"


ACTION_LABEL = {"call_now": "應立即呼叫", "notify": "應轉告", "none": "不需通報"}
TAG_LABEL = {"call": "立即呼叫", "notify": "轉告", None: "無通報"}


def care_marks(r):
    """照護情境題：顯示模型的通報標記，以及是否達到預期等級。"""
    if "action" not in r:
        return ""
    ok = "<span class='ok'>✓</span>" if r["action_ok"] else "<span class='bad'>✗</span>"
    out = f"通報：{TAG_LABEL.get(r.get('tag'), r.get('tag'))} {ok}"
    if r.get("rule_hits"):   # 緊急快速通道：規則層命中時先播固定回應
        out += f" · 規則層攔截（{esc(', '.join(r['rule_hits']))}）"
    return out


def dialogue_section(lang, items, combos, summary, run_dir):
    heads = []
    care = any("action" in r for it in items.values() for r in it.values())
    for c in combos:
        s = summary.get((c, lang))
        if not s:
            meta = "不支援此語言"
        elif care:
            meta = (f"預期等級達成 {fnum(s.get('care_action_ok_rate'), 100, 0)}% · 緊急漏報 "
                    f"{fnum(s.get('emergency_miss_rate'), 100, 0)}% · 回合延遲 p50 {fnum(s.get('turn_latency_ms_p50'), 0.001)} s")
        else:
            meta = (f"事實正確 {fnum(s.get('fact_recall'), 100, 0)}% · 回合延遲 p50 "
                    f"{fnum(s.get('turn_latency_ms_p50'), 0.001)} s")
        heads.append(f"<th>{short_combo(c)}<div class='meta'>{meta}</div></th>")
    rows = []
    for item_id in sorted(items):
        by_combo = items[item_id]
        first = next(iter(by_combo.values()))
        q_wav = ROOT / "data" / ("care" if care else "dialogue") / "audio" / lang / f"{item_id}.wav"
        q_audio = (f"<audio controls preload='none' src='{esc(Path(os.path.relpath(q_wav, run_dir)).as_posix())}'></audio>"
                   if q_wav.exists() else "")
        tag = "<div class='meta'>問題語音為 TTS 合成</div>" if first.get("question_synthetic") else ""
        if care:   # 預期通報等級與多輪題的前文
            history = "".join(f"<div class='meta'>{'住民' if h['role'] == 'user' else '機器人'}（前文）：{esc(h['content'])}</div>"
                              for h in first.get("history", []))
            tag = f"<div class='meta'>{ACTION_LABEL[first['action']]}</div>{history}{tag}"
        cells = []
        for c in combos:
            r = by_combo.get(c)
            if not r:
                cells.append("<td class='na'>—</td>")
                continue
            cells.append(
                f"<td><audio controls preload='none' src='{esc(r['wav'])}'></audio>"
                f"<div class='meta'>回合延遲 {r['turn_latency_s']:.1f} s · {fact_marks(r, lang)}{care_marks(r)}</div>"
                f"<div class='heard'>STT 聽到：{esc(r['stt_hyp'])}</div>"
                f"<div class='resp'>{esc(r['response'])}</div></td>")
        rows.append(f"<tr><td class='num'>{esc(item_id)}</td><td class='text'>{esc(first['question'])}{q_audio}{tag}</td>"
                    f"{''.join(cells)}</tr>")
    return table_block(lang, "dlg", f"<th>#</th><th>問題</th>{''.join(heads)}", rows)


def table_block(lang, cls, head, rows):
    return (f"<section><h2>{esc(lang)} · {esc(L.LANGS[lang]['name'])}</h2><div class='scroll'><table class='{cls}'>"
            f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>")


def build(run_dir):
    """產生 run_dir/listen.html；沒有可試聽的音檔時回傳 None。"""
    run_dir = Path(run_dir)
    data = load(run_dir)
    if not data["tts"] and not data["dialogue"]:
        return None
    summary = load_summary(run_dir)
    body = []
    if data["tts"]:
        models = sorted({m for items in data["tts"].values() for it in items.values() for m in it})
        body.append("<h1>TTS 試聽對照</h1><p class='lead'>同一句文字並排比較各模型。「Whisper 聽到」是評分用的 Whisper 辨識出的文字，"
                    "與原文不同處就是被判定唸錯（也可能是 Whisper 聽錯，特別是 pt-PT 口音）。</p>")
        body += [tts_section(l, data["tts"][l], models, summary) for l in L.ALL if l in data["tts"]]
    if data["dialogue"]:
        body.append("<h1>對話試聽對照</h1><p class='lead'>每列一個問題，並排各組合的回答。「STT 聽到」是語音辨識的結果；"
                    "事實 ✓ / ✗ 為自動檢查回答是否包含正確資訊（啟發式，需人工確認）。表格可左右捲動。</p>")
        for l in L.ALL:
            if l in data["dialogue"]:   # 只列出該語言有跑的組合（各語言可能用不同 STT）
                combos = sorted({c for it in data["dialogue"][l].values() for c in it})
                body.append(dialogue_section(l, data["dialogue"][l], combos, summary, run_dir))
    page = (f"<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width, initial-scale=1'><title>試聽 · {esc(run_dir.name)}</title>"
            f"<style>{CSS}</style></head><body><main><p class='meta'>{esc(run_dir.name)}</p>{''.join(body)}</main></body></html>")
    out = run_dir / "listen.html"
    out.write_text(page, encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", nargs="?")
    ap.add_argument("--all", action="store_true", help="為 results/ 下所有 run 產生")
    args = ap.parse_args()
    runs = [p for p in (ROOT / "results").iterdir() if (p / "raw").is_dir()] if args.all else [Path(args.run_dir)]
    for run in runs:
        out = build(run)
        if out:
            print(f"wrote {out}")


if __name__ == "__main__":
    main()
