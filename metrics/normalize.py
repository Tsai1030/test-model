"""WER/CER 前的文字正規化。參考答案和辨識結果一定要用同一套規則，不同模型才能公平比較。

- 全部語言：NFKC（全形轉半形）、小寫、去除標點與符號、合併空白
- en：若有安裝 whisper-normalizer，改用 Whisper 官方 EnglishTextNormalizer（處理數字、縮寫）
- es / pt：數字文字轉阿拉伯數字（text2num），例如 dezenove → 19、mil novecientos ochenta y cinco → 1985。
  不同模型對數字的寫法不同（Whisper 多寫數字、Nemotron 等多寫文字），不統一會被不公平地算成錯誤
- ja：漢字數字〇一…九轉阿拉伯數字（二つ → 2つ；十、百等複合寫法不處理）；去除所有空白，以字元計算（CER）；
  ja_kana=True 時轉成平假名，避免漢字/假名寫法差異被算成錯誤
"""
import re
import unicodedata

from bench.languages import base, uses_cer

_en_norm = None
_KANJI_DIGITS = str.maketrans("〇一二三四五六七八九", "0123456789")


def _alpha2digit(text: str, code: str) -> str:
    try:
        from text_to_num import alpha2digit
    except ImportError:
        return text
    try:
        return alpha2digit(text, code)
    except Exception:
        return text


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
    code = base(lang)
    if code == "en" and _english_normalizer():
        text = _english_normalizer()(text)
    elif code in ("es", "pt"):
        text = _alpha2digit(text, code)
    elif code == "ja":
        text = text.translate(_KANJI_DIGITS)
    text = text.lower()
    text = "".join(" " if unicodedata.category(c)[0] in "PS" else c for c in text)
    text = re.sub(r"\s+", " ", text).strip()
    if uses_cer(lang):
        if ja_kana:
            text = _to_hiragana(text)
        text = text.replace(" ", "")
    return text
