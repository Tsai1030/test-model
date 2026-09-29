"""串流模擬：依真實時間節奏逐 chunk 餵音訊，模擬麥克風輸入。

僅適用實作 stream_session() 的串流型 STT 引擎（例如之後加入的 sherpa-onnx zipformer）。
離線引擎（Whisper 類）的「最終延遲」= 說完話後整句處理時間，由 run.py 直接量測。
"""
import time

import numpy as np


def simulate(engine, audio: np.ndarray, sr: int, lang, chunk_ms: int, realtime: bool = True) -> dict:
    session = engine.stream_session(lang)
    step = int(sr * chunk_ms / 1000)
    t_start = time.perf_counter()
    first_partial = None
    for i in range(0, len(audio), step):
        if realtime:
            # 等到這個 chunk 在真實世界中「錄完」的時間點
            target = t_start + (i + step) / sr
            delay = target - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
        partial = session.accept(audio[i:i + step])
        if partial and first_partial is None:
            first_partial = time.perf_counter() - t_start
    t_audio_end = t_start + len(audio) / sr if realtime else time.perf_counter()
    text = session.finalize()
    t_final = time.perf_counter()
    return {
        "hyp": text,
        "first_partial_s": first_partial,
        "final_latency_s": max(0.0, t_final - t_audio_end),
        "chunk_ms": chunk_ms,
    }
