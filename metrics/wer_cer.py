"""WER / CER：逐句計算錯誤數與參考長度，再合計成語料層級的錯誤率（業界標準做法），並用 bootstrap 算 95% 信賴區間。"""
import jiwer
import numpy as np

from bench.languages import uses_cer
from metrics.normalize import normalize


def utt_errors(ref: str, hyp: str, lang: str, ja_kana: bool = False):
    """回傳 (錯誤數 S+D+I, 參考長度 N)。英/西/葡以詞計，日語以字元計。"""
    r = normalize(ref, lang, ja_kana)
    h = normalize(hyp, lang, ja_kana)
    unit = list if uses_cer(lang) else str.split
    if not r:
        return len(unit(h)), 0
    if not h:
        n = len(unit(r))
        return n, n
    out = jiwer.process_characters(r, h) if uses_cer(lang) else jiwer.process_words(r, h)
    errors = out.substitutions + out.deletions + out.insertions
    n = out.hits + out.substitutions + out.deletions
    return errors, n


def corpus_rate(errs, ns) -> float:
    total = sum(ns)
    return sum(errs) / total if total else float("nan")


def bootstrap_ci(errs, ns, iters: int = 1000, seed: int = 0):
    if len(errs) < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    e, n = np.asarray(errs), np.asarray(ns)
    idx = rng.integers(0, len(e), size=(iters, len(e)))
    rates = e[idx].sum(axis=1) / np.maximum(n[idx].sum(axis=1), 1)
    return float(np.percentile(rates, 2.5)), float(np.percentile(rates, 97.5))


def keyword_recall(hyp: str, keywords, lang: str):
    """導覽專有名詞召回率：manifest 中標注的關鍵字有幾個被正確辨識。"""
    if not keywords:
        return None
    h = normalize(hyp, lang)
    return sum(normalize(k, lang) in h for k in keywords) / len(keywords)
