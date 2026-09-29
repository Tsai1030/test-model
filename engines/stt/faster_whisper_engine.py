"""faster-whisper（CTranslate2 後端）。Jetson 上需自行編譯 CTranslate2 CUDA 版，或用 jetson-containers。"""
from engines.base import STTEngine, STTResult


class FasterWhisperSTT(STTEngine):
    def __init__(self, model="small", device="cpu", compute_type="int8", cpu_threads=0,
                 beam_size=1, vad_filter=False, **extra):
        super().__init__()
        self.model_name = model          # 例如 small / large-v3-turbo / HF 上的 CT2 repo id
        self.device = device
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        self.extra = extra

    def load(self):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(self.model_name, device=self.device,
                                  compute_type=self.compute_type, cpu_threads=self.cpu_threads)

    def transcribe(self, audio, lang):
        segments, info = self.model.transcribe(
            audio, language=lang, beam_size=self.beam_size, vad_filter=self.vad_filter,
            condition_on_previous_text=False, **self.extra,
        )
        # segments 是 generator，必須迭代完才真正完成推論
        text = "".join(s.text for s in segments).strip()
        return STTResult(text, info.language, info.language_probability)
