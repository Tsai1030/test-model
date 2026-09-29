"""NVIDIA NeMo ASR（Parakeet、Canary）。NeMo 在 Windows 安裝困難，建議用 WSL2 / Colab / Jetson。"""
import os
import tempfile

from bench.audio import STT_SR, save_wav
from engines.base import STTEngine, STTResult


class NeMoSTT(STTEngine):
    def __init__(self, model, device="cpu", canary=False):
        super().__init__()
        self.model_name = model
        self.device = device
        self.canary = canary    # Canary 需要 source_lang / target_lang 參數

    def load(self):
        import nemo.collections.asr as nemo_asr
        self.model = nemo_asr.models.ASRModel.from_pretrained(self.model_name, map_location=self.device)
        self.model.eval()

    def _run(self, inputs, lang):
        kwargs = {"batch_size": 1, "verbose": False}
        if self.canary and lang:
            kwargs.update(source_lang=lang, target_lang=lang)
        return self.model.transcribe(inputs, **kwargs)

    def transcribe(self, audio, lang):
        try:
            out = self._run([audio], lang)
        except (TypeError, ValueError):
            # 舊版 NeMo 只接受檔案路徑
            fd, path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            try:
                save_wav(path, audio, STT_SR)
                out = self._run([path], lang)
            finally:
                os.remove(path)
        hyp = out[0][0] if isinstance(out, tuple) else out[0]
        return STTResult(getattr(hyp, "text", str(hyp)).strip(), lang)
