"""sherpa-onnx 離線辨識（ONNX Runtime）：SenseVoice、NeMo CTC（如 Parakeet 日語）等。模型檔由 Hugging Face 下載。
Jetson 上可用 provider="cuda"。
"""
import numpy as np

from engines.base import STTEngine, STTResult

# 本專案基本語言碼 → SenseVoice 語言提示
SENSE_VOICE_LANGS = {"en": "en", "ja": "ja"}


class SherpaOfflineSTT(STTEngine):
    def __init__(self, kind, repo_id, model_file="model.int8.onnx", tokens_file="tokens.txt",
                 num_threads=4, provider="cpu", use_itn=True):
        super().__init__()
        self.kind = kind               # sense_voice | nemo_ctc
        self.repo_id = repo_id
        self.model_file = model_file
        self.tokens_file = tokens_file
        self.num_threads = num_threads
        self.provider = provider
        self.use_itn = use_itn
        self.recognizers = {}

    def load(self):
        import sherpa_onnx
        from huggingface_hub import hf_hub_download
        self.sherpa = sherpa_onnx
        self.model_path = hf_hub_download(self.repo_id, self.model_file)
        self.tokens_path = hf_hub_download(self.repo_id, self.tokens_file)
        self._recognizer(None)         # 先建立一次，載入時間計入 load

    def _recognizer(self, lang):
        key = lang if self.kind == "sense_voice" else None   # SenseVoice 的語言在建立時指定
        if key not in self.recognizers:
            common = dict(model=self.model_path, tokens=self.tokens_path,
                          num_threads=self.num_threads, provider=self.provider)
            if self.kind == "sense_voice":
                rec = self.sherpa.OfflineRecognizer.from_sense_voice(
                    **common, language=SENSE_VOICE_LANGS.get(lang, "auto") if lang else "auto", use_itn=self.use_itn)
            elif self.kind == "nemo_ctc":
                rec = self.sherpa.OfflineRecognizer.from_nemo_ctc(**common)
            else:
                raise ValueError(f"unknown sherpa-onnx kind: {self.kind}")
            self.recognizers[key] = rec
        return self.recognizers[key]

    def transcribe(self, audio, lang):
        rec = self._recognizer(lang)
        stream = rec.create_stream()
        stream.accept_waveform(16000, np.asarray(audio, dtype=np.float32))
        rec.decode_stream(stream)
        res = stream.result
        return STTResult(res.text.strip(), getattr(res, "lang", None) or None)
