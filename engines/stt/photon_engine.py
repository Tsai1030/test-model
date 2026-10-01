"""Moondream Photon 本機推論引擎（`pip install moondream`），例如 Parakeet-Redux（1.58-bit 三值權重，178 MB）。

注意：Windows 版 kestrel 的 CPU 擴充模組沒有 AVX2 / VNNI 核心（gemm_isa_available 全為 False），
三值權重無法在本機執行；需在 Linux x86（AVX2）或 Jetson（aarch64 NEON dotprod）上使用。本轉接器尚未在本機驗證。
Parakeet 會自動判斷語言，不接受語言參數。
"""
import os
import tempfile

import numpy as np

from engines.base import STTEngine, STTResult


class PhotonSTT(STTEngine):
    def __init__(self, model="moondream/parakeet-redux", device="cpu"):
        super().__init__()
        self.model_name = model
        self.device = device

    def load(self):
        import moondream as md
        self.client = md.photon(self.model_name, device=self.device)

    def transcribe(self, audio, lang):
        try:
            out = self.client.transcribe(audio=np.asarray(audio, dtype=np.float32))
        except (TypeError, ValueError):
            # 不接受陣列時改傳暫存 wav 路徑
            import soundfile as sf
            fd, path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            try:
                sf.write(path, audio, 16000)
                out = self.client.transcribe(audio=path)
            finally:
                os.remove(path)
        if isinstance(out, dict):
            text = out.get("text") or out.get("transcript") or ""
        else:
            text = str(out)
        return STTResult(str(text).strip(), None)

    def close(self):
        if getattr(self, "client", None) is not None:
            self.client.close()
