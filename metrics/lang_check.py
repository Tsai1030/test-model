"""粗略判斷 LLM 回答的語言是否正確（啟發式，只分辨 en/es/pt/ja，不分方言變體）。
方言用詞是否正確（pt-PT 或 pt-BR、es-ES 或 es-419）要靠人工評分表。
"""
import re

_STOP = {
    "en": {"the", "is", "and", "you", "to", "of", "it", "are", "we", "this", "can", "at", "on", "with"},
    "es": {"el", "los", "las", "es", "está", "hay", "muy", "y", "pero", "usted", "puede", "del", "al",
           "con", "para", "por", "su", "lo", "se"},
    "pt": {"o", "os", "é", "você", "vocês", "não", "são", "muito", "uma", "ao", "do", "da", "no", "na",
           "em", "com", "para", "pode", "fica", "está"},
}
_JA = re.compile(r"[぀-ヿ一-鿿]")


def detect(text: str) -> str:
    if not text:
        return "unknown"
    if len(_JA.findall(text)) / max(len(text), 1) > 0.2:
        return "ja"
    tokens = re.findall(r"[a-záàâãéêíóôõúçñü]+", text.lower())
    scores = {lang: sum(t in words for t in tokens) for lang, words in _STOP.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"
