"""Coqui XTTS-v2（coqui-tts 套件，idiap 維護版）。授權 CPML：非商用，PoC 可用。
支援 en / es / pt / ja，但不分方言變體。沒有 GPU 時非常慢，建議在 Colab / Jetson 上測速。
voices 格式：{"ja": "Ana Florence"}（內建說話人名稱）
"""
import numpy as np

from bench.languages import base
from engines.base import TTSEngine


class XTTSv2(TTSEngine):
    def __init__(self, voices, model="tts_models/multilingual/multi-dataset/xtts_v2", device="cpu"):
        super().__init__(voices)
        self.model_name = model
        self.device = device

    def load(self):
        from TTS.api import TTS
        self.tts = TTS(self.model_name).to(self.device)

    def sample_rate_for(self, lang):
        return 24000

    def synthesize_stream(self, text, lang):
        audio = self.tts.tts(text=text, speaker=self.voices[lang], language=base(lang))
        yield np.asarray(audio, dtype=np.float32)
