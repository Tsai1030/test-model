"""語言代碼定義：本專案統一使用 en / es-ES / es-419 / pt-BR / pt-PT / ja。"""

LANGS = {
    "en": {
        "name": "English",
        "base": "en",          # Whisper / 多數模型使用的基本語言碼
        "uses_cer": False,
        "fleurs": "en_us",
        "llm_hint": "English",
    },
    "es-ES": {
        "name": "Español (España)",
        "base": "es",
        "uses_cer": False,
        "fleurs": None,        # FLEURS 西語為拉美西語；歐洲西語請用 Common Voice 篩選或自錄
        "llm_hint": "Spanish from Spain (use 'vosotros' and Peninsular vocabulary)",
    },
    "es-419": {
        "name": "Español (Latinoamérica)",
        "base": "es",
        "uses_cer": False,
        "fleurs": "es_419",
        "llm_hint": "Latin American Spanish (use 'ustedes')",
    },
    "pt-BR": {
        "name": "Português (Brasil)",
        "base": "pt",
        "uses_cer": False,
        "fleurs": "pt_br",
        "llm_hint": "Brazilian Portuguese",
    },
    "pt-PT": {
        "name": "Português (Portugal)",
        "base": "pt",
        "uses_cer": False,
        "fleurs": None,        # 歐洲葡語請用 Common Voice 篩選或自錄
        "llm_hint": "European Portuguese from Portugal (not Brazilian)",
    },
    "ja": {
        "name": "日本語",
        "base": "ja",
        "uses_cer": True,      # 日語沒有空格，用 CER
        "fleurs": "ja_jp",
        "llm_hint": "Japanese (polite desu/masu form)",
    },
}

ALL = list(LANGS)


def base(lang: str) -> str:
    return LANGS[lang]["base"]


def uses_cer(lang: str) -> bool:
    return LANGS[lang]["uses_cer"]
