"""檢查 scenarios.yaml 的格式，並產生審核表 review_sheet.csv（Excel 可直接開啟）。

  .venv-core\\Scripts\\python.exe data\\care\\make_review_sheet.py

審核表每列一題：護理人員看中文意思、預期通報與評分標準；母語者看各語言的說法。
審核欄位留白給審核者填寫；修改後請改回 scenarios.yaml 再重新產生。
"""
import collections
import csv
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from bench import languages as L  # noqa: E402

ACTIONS = {"call_now": "立即呼叫 [CALL_NURSE]", "notify": "轉告 [NOTIFY_NURSE]", "none": "不需通報"}
CATEGORIES = {
    "emergency": "緊急情況", "symptom": "症狀回報", "out_of_scope": "超出範圍的醫療決定",
    "education": "一般衛教", "info": "院內資訊與提醒", "companionship": "陪伴與情緒",
    "cognition": "認知混亂與重複提問", "safety": "安全與隱私",
}


def check(scenarios):
    errors, seen = [], set()
    for s in scenarios:
        sid = s.get("id", "?")
        if sid in seen:
            errors.append(f"{sid}: id 重複")
        seen.add(sid)
        if s.get("action") not in ACTIONS:
            errors.append(f"{sid}: action 不合法 {s.get('action')!r}")
        if s.get("category") not in CATEGORIES:
            errors.append(f"{sid}: category 不合法 {s.get('category')!r}")
        if not s.get("must"):
            errors.append(f"{sid}: 缺 must")
        for where, block in [("text", s)] + [(f"history[{i}]", h) for i, h in enumerate(s.get("history", []))]:
            missing = [l for l in L.ALL if not (block.get("text") or {}).get(l)]
            if missing:
                errors.append(f"{sid} {where}: 缺語言 {missing}")
            if not block.get("zh"):
                errors.append(f"{sid} {where}: 缺 zh")
    return errors


def main():
    data = yaml.safe_load((HERE / "scenarios.yaml").read_text(encoding="utf-8"))
    scenarios = data["scenarios"]
    errors = check(scenarios)
    if errors:
        print("\n".join(errors))
        raise SystemExit(f"{len(errors)} 個格式錯誤")

    out = HERE / "review_sheet.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:   # BOM：Excel 才會用 UTF-8 開
        w = csv.writer(f)
        w.writerow(["編號", "類別", "預期通報", "需推理", "先前對話", "住民說的話（中文意思）", "必須做到", "不可以", "說明",
                    *L.ALL, "護理審核（OK／修改／刪除）", "護理意見", "母語審核意見"])
        for s in scenarios:
            history = " ／ ".join(f"{'住民' if h['role'] == 'user' else '機器人'}：{h['zh']}" for h in s.get("history", []))
            w.writerow([s["id"], CATEGORIES[s["category"]], ACTIONS[s["action"]],
                        "是" if "reasoning" in s.get("tags", []) else "", history, s["zh"],
                        "；".join(s["must"]), "；".join(s.get("must_not", [])), s.get("note", ""),
                        *[s["text"][l] for l in L.ALL], "", "", ""])

    by_cat = collections.Counter(CATEGORIES[s["category"]] for s in scenarios)
    by_act = collections.Counter(ACTIONS[s["action"]] for s in scenarios)
    print(f"{len(scenarios)} 題 × {len(L.ALL)} 種語言，格式檢查通過")
    print("類別：", dict(by_cat))
    print("通報：", dict(by_act))
    print("需推理：", sum("reasoning" in s.get("tags", []) for s in scenarios), "題；多輪：",
          sum(bool(s.get("history")) for s in scenarios), "題")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
