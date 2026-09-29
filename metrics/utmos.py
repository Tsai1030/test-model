"""UTMOS 預測 MOS（SpeechMOS 的 utmos22_strong，透過 torch.hub 載入）。

注意：UTMOS22 以英語資料訓練，其他語言的分數只能當相對參考；
每個語言都要用人工 MOS 驗證相關性（計畫書第 9 節）。
"""
import numpy as np


class UTMOS:
    def __init__(self, device="cpu"):
        import torch
        self.torch = torch
        self.device = device
        self.model = torch.hub.load("tarepan/SpeechMOS:v1.2.0", "utmos22_strong",
                                    trust_repo=True).to(device).eval()

    def score(self, wav: np.ndarray, sr: int) -> float:
        x = self.torch.from_numpy(np.asarray(wav, dtype=np.float32)).unsqueeze(0).to(self.device)
        with self.torch.no_grad():
            return float(self.model(x, sr).item())
