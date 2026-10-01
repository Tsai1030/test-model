"""onnx-asr（ONNX Runtime）：NVIDIA Parakeet / Canary 等 NeMo 模型的 ONNX 版本，不需 NeMo，Windows CPU 可跑；
Jetson 上可改用 CUDA / TensorRT provider。Parakeet 會自動判斷語言，不接受語言參數。
"""
import numpy as np

from engines.base import STTEngine, STTResult


class OnnxAsrSTT(STTEngine):
    def __init__(self, model, repo_id=None, quantization=None, providers=None):
        super().__init__()
        self.model_name = model        # 內建名稱（如 nemo-parakeet-tdt-0.6b-v3）或模型類型（如 nemo-conformer-tdt）
        self.repo_id = repo_id         # 自訂 HF repo（需搭配模型類型），例如社群微調版
        self.quantization = quantization
        self.providers = providers

    def load(self):
        import onnx_asr
        path = None
        if self.repo_id:
            from huggingface_hub import snapshot_download
            path = snapshot_download(self.repo_id)
        kwargs = {}
        if self.quantization:
            kwargs["quantization"] = self.quantization
        if self.providers:
            kwargs["providers"] = self.providers
        self.model = onnx_asr.load_model(self.model_name, path, **kwargs)

    def transcribe(self, audio, lang):
        text = self.model.recognize(np.asarray(audio, dtype=np.float32), sample_rate=16000)
        return STTResult(str(text).strip(), None)
