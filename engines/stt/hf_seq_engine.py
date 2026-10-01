"""transformers 的 ASR 模型（非 pipeline，依架構呼叫）：
- ctc：AutoModelForCTC，如 IBM Granite-Speech-5.0-470M-TurboCTC（非自回歸，速度快）
- moonshine：MoonshineForConditionalGeneration，如 Moonshine-tiny-ja（依音訊長度限制生成長度，避免重複輸出）
"""
from engines.base import STTEngine, STTResult


class HFSeqSTT(STTEngine):
    def __init__(self, model, kind, device="cpu", dtype="float32", num_threads=None, tokens_per_second=6.5):
        super().__init__()
        self.model_id = model
        self.kind = kind                         # ctc | moonshine
        self.device = device
        self.dtype = dtype
        self.num_threads = num_threads
        self.tokens_per_second = tokens_per_second   # Moonshine 官方建議：英語 6.5、日語 13

    def load(self):
        import torch
        from transformers import AutoModelForCTC, AutoProcessor, MoonshineForConditionalGeneration
        if self.num_threads:
            torch.set_num_threads(self.num_threads)
        self.torch = torch
        self.torch_dtype = getattr(torch, self.dtype)
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        cls = {"ctc": AutoModelForCTC, "moonshine": MoonshineForConditionalGeneration}[self.kind]
        self.model = cls.from_pretrained(self.model_id, dtype=self.torch_dtype).to(self.device).eval()

    def transcribe(self, audio, lang):
        inputs = self.processor(audio, sampling_rate=16000, return_tensors="pt").to(self.device, self.torch_dtype)
        with self.torch.inference_mode():
            if self.kind == "moonshine":
                max_length = max(8, int(len(audio) / 16000 * self.tokens_per_second))
                ids = self.model.generate(**inputs, max_length=max_length)
            else:
                ids = self.model.generate(**inputs)
        text = self.processor.batch_decode(ids, skip_special_tokens=True)[0]
        return STTResult(text.strip(), lang)
