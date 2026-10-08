"""緊急警訊規則層：在 LLM 之前比對 STT 文字（規則見 data/care/emergency_rules.yaml）。
命中任一規則即視為緊急，系統可立即通知醫護並播放固定回應，不必等 LLM。
"""
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import yaml

from bench import languages as L

RULES_FILE = Path(__file__).resolve().parents[1] / "data" / "care" / "emergency_rules.yaml"


def normalize(text, lang):
    """轉小寫；es / pt / en 去重音；日語去掉空白（SenseVoice 輸出的字詞間有空格）。"""
    base = L.base(lang)
    text = text.lower()
    if base == "ja":
        return re.sub(r"\s+", "", text)
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=None)
def _compiled(path=RULES_FILE):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))["rules"]
    return {lang: [(r["id"], [re.compile(p) for p in r["all"]]) for r in rules] for lang, rules in data.items()}


def match(text, lang, path=RULES_FILE):
    """回傳命中的規則 id 清單（空清單 = 沒有緊急警訊）。"""
    norm = normalize(text or "", lang)
    return [rid for rid, pats in _compiled(path).get(L.base(lang), []) if all(p.search(norm) for p in pats)]
