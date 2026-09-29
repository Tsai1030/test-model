"""Piper（VITS + ONNX）。聲音從 Hugging Face rhasspy/piper-voices 自動下載。
相容 piper-tts 1.2（synthesize_stream_raw）與 1.3+（synthesize 回傳 AudioChunk）兩種 API。
"""
import numpy as np

from engines.base import TTSEngine


def voice_repo_path(name: str) -> str:
    # "pt_PT-tugão-medium" -> "pt/pt_PT/tugão/medium/pt_PT-tugão-medium.onnx"
    lang_region, speaker, quality = name.split("-", 2)
    family = lang_region.split("_")[0]
    return f"{family}/{lang_region}/{speaker}/{quality}/{name}.onnx"


class PiperTTS(TTSEngine):
    def __init__(self, voices, use_cuda=False, hf_repo="rhasspy/piper-voices"):
        super().__init__(voices)
        self.use_cuda = use_cuda
        self.hf_repo = hf_repo
        self.loaded = {}

    def load(self):
        import piper  # noqa: F401  僅確認套件存在；聲音在 prepare() 依語言載入

    def prepare(self, lang):
        if lang in self.loaded:
            return
        from huggingface_hub import hf_hub_download
        from piper import PiperVoice
        rel = voice_repo_path(self.voices[lang])
        onnx_path = hf_hub_download(self.hf_repo, rel)
        cfg_path = hf_hub_download(self.hf_repo, rel + ".json")
        self.loaded[lang] = PiperVoice.load(onnx_path, config_path=cfg_path, use_cuda=self.use_cuda)

    def sample_rate_for(self, lang):
        return self.loaded[lang].config.sample_rate

    def synthesize_stream(self, text, lang):
        voice = self.loaded[lang]
        if hasattr(voice, "synthesize_stream_raw"):      # piper-tts <= 1.2
            for raw in voice.synthesize_stream_raw(text):
                yield np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        else:                                             # piper-tts >= 1.3
            for chunk in voice.synthesize(text):
                yield np.asarray(chunk.audio_float_array, dtype=np.float32)
