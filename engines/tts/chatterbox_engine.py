"""Resemble AI Chatterbox Multilingual（MIT）。0.5B，需 GPU 才實用；i3 上只適合測準確度。
voices 格式：{"ja": "default"} 或 {"ja": "path/to/reference.wav"}（聲音複製參考音檔）
API 依版本可能變動（chatterbox.mtl_tts.ChatterboxMultilingualTTS）。
"""
import numpy as np

from bench.languages import base
from engines.base import TTSEngine


class ChatterboxMultilingualTTS(TTSEngine):
    def __init__(self, voices, device="cpu"):
        super().__init__(voices)
        self.device = device

    def load(self):
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS as Model
        self.model = Model.from_pretrained(device=self.device)

    def sample_rate_for(self, lang):
        return self.model.sr

    def synthesize_stream(self, text, lang):
        ref = self.voices[lang]
        kwargs = {} if ref in (None, "default") else {"audio_prompt_path": ref}
        wav = self.model.generate(text, language_id=base(lang), **kwargs)
        yield wav.squeeze(0).detach().cpu().numpy().astype(np.float32)
