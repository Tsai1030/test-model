"""Qwen3-ASR（transformers ≥ 5.13，`-hf` 版本）。LLM 式 ASR：音訊編碼器 + Qwen3 語言模型逐字生成。
CPU 上用 float32（無 AVX-512 的 CPU 跑 bfloat16 很慢）；GPU / Jetson 上用 bfloat16 或 float16，記憶體約減半。
"""
from engines.base import STTEngine, STTResult

LANG_NAMES = {"en": "English", "es": "Spanish", "pt": "Portuguese", "ja": "Japanese"}


class Qwen3ASR(STTEngine):
    def __init__(self, model="Qwen/Qwen3-ASR-0.6B-hf", device="cpu", dtype="float32", num_threads=None,
                 max_new_tokens=256):
        super().__init__()
        self.model_id = model
        self.device = device
        self.dtype = dtype
        self.num_threads = num_threads
        self.max_new_tokens = max_new_tokens

    def load(self):
        import torch
        from transformers import AutoModelForMultimodalLM, AutoProcessor
        if self.num_threads:
            torch.set_num_threads(self.num_threads)
        self.torch = torch
        self.torch_dtype = getattr(torch, self.dtype)
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = AutoModelForMultimodalLM.from_pretrained(self.model_id, dtype=self.torch_dtype).to(self.device).eval()

    def transcribe(self, audio, lang):
        inputs = self.processor.apply_transcription_request(
            audio=audio, language=LANG_NAMES.get(lang) if lang else None,
        ).to(self.device, self.torch_dtype)
        with self.torch.inference_mode():
            out = self.model.generate(**inputs, max_new_tokens=self.max_new_tokens)
        gen = out[:, inputs["input_ids"].shape[1]:]
        parsed = self.processor.decode(gen, return_format="parsed")[0]
        return STTResult(parsed.get("transcription", "").strip(), parsed.get("language"))
