"""NVIDIA Nemotron-3.5-ASR-Streaming（transformers ≥ 5.13）：cache-aware FastConformer + RNNT。
- 整句模式：transcribe() 一次處理整段錄音
- 串流模式（streaming=True）：stream_session() 依模型的區塊大小逐段處理，邊聽邊輸出文字；
  區塊大小 = (lookahead_tokens + 1) × 80 ms，例如 1 → 160 ms、3 → 320 ms、6 → 560 ms、13 → 1120 ms
以 locale 提示語言，可區分 pt-PT / pt-BR、es-ES / es-US（拉美），因此 wants_locale = True。
"""
import threading

import numpy as np

from engines.base import STTEngine, STTResult

SR = 16000
LOCALES = {"en": "en-US", "es-ES": "es-ES", "es-419": "es-US", "pt-BR": "pt-BR", "pt-PT": "pt-PT", "ja": "ja-JP",
           "es": "es-ES", "pt": "pt-BR"}
STREAM_MAX_NEW_TOKENS = 4096     # 串流時音訊長度事先未知，給足夠大的上限


def max_new_tokens(n_samples):
    return 64 + int(n_samples / SR * 25)


class NemotronASR(STTEngine):
    wants_locale = True

    def __init__(self, model="nvidia/nemotron-3.5-asr-streaming-0.6b", device="cpu", dtype="float32",
                 num_threads=None, streaming=False, lookahead_tokens=6):
        super().__init__()
        self.model_id = model
        self.device = device
        self.dtype = dtype
        self.num_threads = num_threads
        self.supports_streaming = streaming
        self.lookahead_tokens = lookahead_tokens

    def load(self):
        import torch
        from transformers import AutoModelForRNNT, AutoProcessor
        if self.num_threads:
            torch.set_num_threads(self.num_threads)
        self.torch = torch
        self.torch_dtype = getattr(torch, self.dtype)
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = AutoModelForRNNT.from_pretrained(self.model_id, dtype=self.torch_dtype).to(self.device).eval()
        if self.supports_streaming:
            self.processor.set_num_lookahead_tokens(self.lookahead_tokens)
            self.streaming_latency_ms = self.processor.streaming_latency_ms

    def locale(self, lang):
        return LOCALES.get(lang, lang) if lang else "auto"

    def transcribe(self, audio, lang):
        inputs = self.processor(audio, sampling_rate=SR, language=self.locale(lang), return_tensors="pt")
        inputs = inputs.to(self.device, dtype=self.torch_dtype)
        with self.torch.inference_mode():
            # 明確給上限（每秒約 20 個 token 以上綽綽有餘），避免 transformers 每句都警告「用預設 max_length=1600」
            out = self.model.generate(**inputs, return_dict_in_generate=True,
                                      max_new_tokens=max_new_tokens(len(audio)))
        text = self.processor.decode(out.sequences, skip_special_tokens=True)
        return STTResult((text[0] if isinstance(text, list) else text).strip(), lang)

    def stream_session(self, lang):
        return _NemotronStream(self, self.locale(lang))


class _NemotronStream:
    """accept() 收到的音訊依模型區塊切成 mel 特徵，餵給背景執行緒中的 model.generate（官方 transformers 串流用法）；
    TextIteratorStreamer 逐段回傳文字。accept() 回傳目前為止的部分結果；finalize() 補靜音送出最後的字並回傳全文。"""

    def __init__(self, engine, locale):
        from transformers import TextIteratorStreamer
        p = engine.processor
        self.e, self.p, self.locale = engine, p, locale
        self.first_n = p.num_samples_first_audio_chunk
        self.per_n = p.num_samples_per_audio_chunk
        self.first_frames = p.num_mel_frames_first_audio_chunk
        self.per_frames = p.num_mel_frames_per_audio_chunk
        self.hop = p.feature_extractor.hop_length
        self.n_fft = p.feature_extractor.n_fft
        self.buf = np.zeros(0, np.float32)
        self.cond = threading.Condition()
        self.done = False
        self.pieces = []
        self.gen_thread = None
        self.streamer = TextIteratorStreamer(p.tokenizer, skip_special_tokens=True)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _features(self, chunk, first):
        inputs = self.p(chunk, sampling_rate=SR, is_streaming=True, is_first_audio_chunk=first,
                        language=self.locale, return_tensors="pt")
        return inputs.to(self.e.device, dtype=self.e.torch_dtype)

    def _feature_stream(self, first_inputs):
        yield first_inputs.input_features[:, : self.first_frames, :]
        mel_idx = self.first_frames
        start = mel_idx * self.hop - self.n_fft // 2
        while True:
            end = start + self.per_n
            with self.cond:
                while len(self.buf) < end and not self.done:
                    self.cond.wait()
                if len(self.buf) < end:
                    return
                chunk = self.buf[start:end].copy()
            yield self._features(chunk, False).input_features
            mel_idx += self.per_frames
            start = mel_idx * self.hop - self.n_fft // 2

    def _generate(self, kwargs):
        with self.e.torch.inference_mode():
            self.e.model.generate(**kwargs)

    def _start(self):
        first = self._features(self.buf[: self.first_n].copy(), True)
        kwargs = {**first, "input_features": self._feature_stream(first), "streamer": self.streamer,
                  "max_new_tokens": STREAM_MAX_NEW_TOKENS}
        self.gen_thread = threading.Thread(target=self._generate, args=(kwargs,), daemon=True)
        self.gen_thread.start()

    def _read(self):
        for piece in self.streamer:
            self.pieces.append(piece)

    def _append(self, pcm):
        with self.cond:
            self.buf = np.concatenate([self.buf, np.asarray(pcm, np.float32)])
            self.cond.notify_all()

    def accept(self, chunk):
        self._append(chunk)
        if self.gen_thread is None and len(self.buf) >= self.first_n:
            self._start()
        return "".join(self.pieces).strip()

    def finalize(self):
        # 補兩個區塊的靜音，讓模型輸出最後幾個字（右側上下文）；錄音太短時補到第一個區塊的長度
        self._append(np.zeros(2 * self.per_n + max(0, self.first_n - len(self.buf)), np.float32))
        if self.gen_thread is None:
            self._start()
        with self.cond:
            self.done = True
            self.cond.notify_all()
        self.gen_thread.join()
        self.reader.join(timeout=10)
        return "".join(self.pieces).strip()
