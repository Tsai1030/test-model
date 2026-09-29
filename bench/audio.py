"""音訊讀寫與重取樣。所有 STT 輸入統一為 16kHz mono float32。"""
from pathlib import Path

import numpy as np
import soundfile as sf

STT_SR = 16000


def resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return x.astype(np.float32, copy=False)
    import soxr
    return soxr.resample(x, sr_in, sr_out).astype(np.float32)


def load_audio(path, sr: int = STT_SR) -> np.ndarray:
    try:
        data, file_sr = sf.read(str(path), dtype="float32", always_2d=True)
        data = data.mean(axis=1)
    except Exception:
        # soundfile 讀不了的格式（部分 mp3）改用 PyAV（faster-whisper 會一併安裝）
        from faster_whisper import decode_audio
        return decode_audio(str(path), sampling_rate=sr).astype(np.float32)
    return np.ascontiguousarray(resample(data, file_sr, sr), dtype=np.float32)


def save_wav(path, audio: np.ndarray, sr: int) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.clip(audio, -1.0, 1.0), sr, subtype="PCM_16")


def duration(audio: np.ndarray, sr: int) -> float:
    return len(audio) / float(sr)
