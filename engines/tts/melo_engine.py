"""MeloTTS（MIT）。支援 EN / ES / JP，無葡語。沒有串流 API，整句一次輸出（TTFA = 整句時間）。
Windows 安裝需處理 MeCab / unidic，建議在 WSL2 或 Linux 上跑。
voices 格式：{"ja": "JP:JP", "en": "EN:EN-US", "es-ES": "ES:ES"}（語言:說話人）
"""
import numpy as np

from engines.base import TTSEngine


class MeloTTS(TTSEngine):
    def __init__(self, voices, device="cpu", speed=1.0):
        super().__init__(voices)
        self.device = device
        self.speed = speed
        self.models = {}

    def load(self):
        import melo.api  # noqa: F401

    def prepare(self, lang):
        from melo.api import TTS
        melo_lang = self.voices[lang].split(":")[0]
        if melo_lang not in self.models:
            self.models[melo_lang] = TTS(language=melo_lang, device=self.device)

    def sample_rate_for(self, lang):
        return self.models[self.voices[lang].split(":")[0]].hps.data.sampling_rate

    def synthesize_stream(self, text, lang):
        melo_lang, speaker = self.voices[lang].split(":")
        model = self.models[melo_lang]
        spk_id = model.hps.data.spk2id[speaker]
        audio = model.tts_to_file(text, spk_id, None, speed=self.speed, quiet=True)
        yield np.asarray(audio, dtype=np.float32)
