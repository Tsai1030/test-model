"""Supertonic（ONNX Runtime，約 1 億參數）：31 種語言共用 10 種預設聲音（M1–M5、F1–F5）。
一次合成一整句（非串流）；run.py 依句切分後逐句呼叫，第一句完成即可播放。
"""
import numpy as np

from engines.base import TTSEngine

# 本專案語言碼 → Supertonic 語言碼（不區分方言）
LANG_CODES = {"en": "en", "es-ES": "es", "es-419": "es", "pt-BR": "pt", "pt-PT": "pt", "ja": "ja"}


class SupertonicTTS(TTSEngine):
    def __init__(self, voices, model="supertonic-3", total_steps=8, speed=1.05, num_threads=None):
        super().__init__(voices)
        self.model_name = model
        self.total_steps = total_steps
        self.speed = speed
        self.num_threads = num_threads
        self.styles = {}

    def load(self):
        from supertonic import TTS
        self.tts = TTS(model=self.model_name, intra_op_num_threads=self.num_threads)

    def supports(self, lang):
        return lang in self.voices and lang in LANG_CODES

    def prepare(self, lang):
        if lang not in self.styles:
            self.styles[lang] = self.tts.get_voice_style(self.voices[lang])

    def sample_rate_for(self, lang):
        return self.tts.sample_rate

    def synthesize_stream(self, text, lang):
        ok, bad = self.tts.model.text_processor.validate_text(text)
        if not ok:  # 遇到不支援的字元整句會報錯；LLM 回答偶爾會有，先濾掉
            text = "".join(ch for ch in text if ch not in bad)
        wav, _ = self.tts.synthesize(text, voice_style=self.styles[lang], total_steps=self.total_steps,
                                     speed=self.speed, lang=LANG_CODES[lang])
        yield np.asarray(wav[0], dtype=np.float32)
