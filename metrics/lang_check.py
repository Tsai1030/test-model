"""粗略判斷 LLM 回答的語言是否正確（啟發式，只分辨 en/es/pt/ja，不分方言變體）。
方言用詞是否正確（pt-PT 或 pt-BR、es-ES 或 es-419）要靠人工評分表。
"""
import re

_STOP = {
    "en": {"the", "is", "and", "you", "to", "of", "it", "are", "we", "this", "can", "at", "on", "with"},
    # 西語、葡語共用的字（está、para、por、que、de、a、no…）不列入，只用各自特有的字（葡語冠詞 o 保留：
    # 西語的 o（或）通常有 el / la / y 等字蓋過）；
    # 原本列了共用字，葡語短句常因平手被判成西語（2026-10-06 修正）
    "es": {"el", "los", "las", "la", "es", "hay", "muy", "y", "pero", "usted", "del", "al", "con", "su", "lo",
           "yo", "estoy", "voy", "ahora", "aquí", "eso", "una", "un", "puedo", "puede", "pueden", "enfermera", "también",
           "sí", "hacer", "tiene", "tengo"},
    "pt": {"os", "é", "você", "vocês", "não", "são", "muito", "uma", "um", "ao", "do", "da", "na", "em", "com",
           "eu", "estou", "vou", "agora", "aqui", "isso", "seu", "sua", "posso", "pode", "enfermeira", "também",
           "fica", "mas", "o", "às", "à", "sim", "fazer", "tem", "tenho", "podem"},
}
_MARKS = {"es": "ñ¿¡", "pt": "ãõç"}   # 各自特有的字母與標點，每個算 2 分
_JA = re.compile(r"[぀-ヿ一-鿿]")


def detect(text: str) -> str:
    if not text:
        return "unknown"
    if len(_JA.findall(text)) / max(len(text), 1) > 0.2:
        return "ja"
    lower = text.lower()
    tokens = re.findall(r"[a-záàâãéêíóôõúçñü]+", lower)
    scores = {lang: sum(t in words for t in tokens) for lang, words in _STOP.items()}
    for lang, marks in _MARKS.items():
        scores[lang] += 2 * sum(lower.count(m) for m in marks)
    ranked = sorted(scores.values(), reverse=True)
    if ranked[0] == 0 or ranked[0] == ranked[1]:
        return "unknown"            # 平手不猜
    return max(scores, key=scores.get)
