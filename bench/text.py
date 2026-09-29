"""文字處理：斷句（TTS 分句與 LLM 串流首句偵測）、清掉不適合朗讀的符號。"""
import re

_CJK_END = "。！？"
_LATIN_END = ".!?"


def _is_abbrev(text: str, dot_idx: int) -> bool:
    """'a.m.'、'p.'、'Sr.' 這類縮寫或單字母後的句點，不算句尾。"""
    token = re.split(r"\s", text[:dot_idx])[-1]
    return len(token.replace(".", "")) <= 2


def _sentence_ends(text: str, final: bool):
    for i, ch in enumerate(text):
        if ch in _CJK_END:
            yield i + 1
        elif ch in _LATIN_END:
            nxt = text[i + 1] if i + 1 < len(text) else None
            if nxt is None and not final:
                continue  # 串流中，還不知道後面是不是空白
            if nxt is not None and not nxt.isspace():
                continue
            if ch == "." and _is_abbrev(text, i):
                continue
            yield i + 1


def split_sentences(text: str) -> list:
    out, start = [], 0
    for end in _sentence_ends(text, final=True):
        seg = text[start:end].strip()
        if seg:
            out.append(seg)
        start = end
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


def first_complete_sentence(buf: str, min_chars: int = 8):
    """LLM 串流緩衝區中第一個已完整的句子；尚未完整就回傳 None。"""
    for end in _sentence_ends(buf, final=False):
        seg = buf[:end].strip()
        if len(seg) >= min_chars:
            return seg
    return None


def clean_for_tts(text: str) -> str:
    text = re.sub(r"[*_#`>\[\]]", "", text)
    text = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", text)  # emoji
    return re.sub(r"\s+", " ", text).strip()
