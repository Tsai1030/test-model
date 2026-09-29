"""Hugging Face transformers ASR pipeline（Whisper 系列與 wav2vec2 類皆可）。"""
from engines.base import STTEngine, STTResult


class HFPipelineSTT(STTEngine):
    def __init__(self, model, device="cpu", dtype="float32", num_threads=None,
                 is_whisper=True, chunk_length_s=None, generate_kwargs=None):
        super().__init__()
        self.model_id = model
        self.device = device
        self.dtype = dtype
        self.num_threads = num_threads
        self.is_whisper = is_whisper
        self.chunk_length_s = chunk_length_s
        self.generate_kwargs = generate_kwargs or {}

    def load(self):
        import torch
        from transformers import pipeline
        if self.num_threads:
            torch.set_num_threads(self.num_threads)
        self.pipe = pipeline("automatic-speech-recognition", model=self.model_id,
                             torch_dtype=getattr(torch, self.dtype), device=self.device)

    def transcribe(self, audio, lang):
        kwargs = {}
        if self.chunk_length_s:
            kwargs["chunk_length_s"] = self.chunk_length_s
        if self.is_whisper:
            gk = dict(self.generate_kwargs)
            gk.setdefault("task", "transcribe")
            if lang:
                gk["language"] = lang
            kwargs["generate_kwargs"] = gk
        out = self.pipe({"raw": audio, "sampling_rate": 16000}, **kwargs)
        return STTResult(out["text"].strip(), lang)
