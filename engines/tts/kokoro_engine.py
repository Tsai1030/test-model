"""Kokoro-82M（PyTorch）。es / pt 需要系統安裝 espeak-ng；ja 需要 pip install "misaki[ja]"。
Kokoro 不分西語變體，也沒有歐洲葡語聲音（pt-PT 不支援）。
"""
import numpy as np

from engines.base import TTSEngine

LANG_CODES = {"en": "a", "es-ES": "e", "es-419": "e", "pt-BR": "p", "ja": "j"}


class KokoroTTS(TTSEngine):
    def __init__(self, voices, repo_id="hexgrad/Kokoro-82M", device="cpu", speed=1.0):
        super().__init__(voices)
        self.repo_id = repo_id
        self.device = device
        self.speed = speed
        self.pipes = {}

    def load(self):
        from kokoro import KModel
        # 模型只載入一次，各語言的 pipeline 共用
        self.model = KModel(repo_id=self.repo_id).to(self.device).eval()

    def supports(self, lang):
        return lang in self.voices and lang in LANG_CODES

    def prepare(self, lang):
        from kokoro import KPipeline
        code = LANG_CODES[lang]
        if code not in self.pipes:
            self.pipes[code] = KPipeline(lang_code=code, repo_id=self.repo_id, model=self.model)

    def sample_rate_for(self, lang):
        return 24000

    def synthesize_stream(self, text, lang):
        pipe = self.pipes[LANG_CODES[lang]]
        for result in pipe(text, voice=self.voices[lang], speed=self.speed):
            audio = result.audio if hasattr(result, "audio") else result[2]
            if audio is None:
                continue
            if hasattr(audio, "detach"):
                audio = audio.detach().cpu().numpy()
            yield np.asarray(audio, dtype=np.float32)
