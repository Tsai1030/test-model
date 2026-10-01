"""引擎統一介面（Adapter 模式）。新增模型 = 新增一個子類別 + 在 configs/models.yaml 註冊。

各引擎的相依套件都在 load() 內才 import，所以每個 venv 只需安裝它要跑的引擎。
"""
import importlib
from dataclasses import dataclass
from typing import Iterator, Optional

import numpy as np


@dataclass
class STTResult:
    text: str
    lang: Optional[str] = None       # 模型偵測到的語言（基本語言碼，如 "ja"）
    lang_prob: Optional[float] = None


class STTEngine:
    supports_streaming = False
    # True：transcribe() 收到本專案完整語言碼（如 pt-PT、es-419）而非基本語言碼（pt、es），
    # 給能區分方言的模型使用（如 Nemotron 的 locale 提示）
    wants_locale = False

    def __init__(self, **params):
        self.params = params

    def load(self) -> None:
        raise NotImplementedError

    def transcribe(self, audio: np.ndarray, lang: Optional[str]) -> STTResult:
        """audio: 16kHz mono float32；lang: 基本語言碼（en/es/pt/ja），None 表示自動偵測。"""
        raise NotImplementedError

    def stream_session(self, lang):
        raise NotImplementedError

    def close(self) -> None:
        pass


class TTSEngine:
    def __init__(self, voices: dict, **params):
        self.voices = voices or {}     # {"ja": "jf_alpha", ...}
        self.params = params

    def load(self) -> None:
        raise NotImplementedError

    def supports(self, lang: str) -> bool:
        return lang in self.voices

    def prepare(self, lang: str) -> None:
        """每個語言第一次使用前呼叫（不計時），例如下載/載入該語言的聲音。"""

    def sample_rate_for(self, lang: str) -> int:
        raise NotImplementedError

    def synthesize_stream(self, text: str, lang: str) -> Iterator[np.ndarray]:
        """逐段 yield float32 音訊；第一段出來的時間 = TTFA。"""
        raise NotImplementedError

    def close(self) -> None:
        pass


class LLMEngine:
    def __init__(self, **params):
        self.params = params

    def load(self) -> None:
        raise NotImplementedError

    def chat_stream(self, messages: list, max_tokens: int = 160,
                    temperature: float = 0.3) -> Iterator[str]:
        raise NotImplementedError

    def close(self) -> None:
        pass


def build_engine(spec: dict):
    """spec["engine"] 格式為 'engines.stt.faster_whisper_engine:FasterWhisperSTT'。"""
    module_path, cls_name = spec["engine"].split(":")
    cls = getattr(importlib.import_module(module_path), cls_name)
    params = dict(spec.get("params", {}))
    if "voices" in spec:
        params["voices"] = spec["voices"]
    return cls(**params)
