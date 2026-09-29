"""WER/CER 前的文字正規化。參考答案和辨識結果一定要用同一套規則，不同模型才能公平比較。

- 全部語言：NFKC（全形轉半形）、小寫、去除標點與符號、合併空白
- en：若有安裝 whisper-normalizer，改用 Whisper 官方 EnglishTextNormalizer（處理數字、縮寫）
- ja：去除所有空白，以字元計算（CER）；ja_kana=True 時轉成平假名，避免漢字/假名寫法差異被算成錯誤
"""
import re
import unicodedata

from bench.languages import base, uses_cer

_en_norm = None


def _english_normalizer():
    global _en_norm
    if _en_norm is None:
        try:
            from whisper_normalizer.english import EnglishTextNormalizer
            _en_norm = EnglishTextNormalizer()
        except ImportError:
            _en_norm = False
    return _en_norm


def _to_hiragana(text: str) -> str:
    import pykakasi
    kks = pykakasi.kakasi()
    return "".join(item["hira"] for item in kks.convert(text))


def normalize(text: str, lang: str, ja_kana: bool = False) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    if base(lang) == "en" and _english_normalizer():
        text = _english_normalizer()(text)
    text = text.lower()
    text = "".join(" " if unicodedata.category(c)[0] in "PS" else c for c in text)
    text = re.sub(r"\s+", " ", text).strip()
    if uses_cer(lang):
        if ja_kana:
            text = _to_hiragana(text)
        text = text.replace(" ", "")
    return text
