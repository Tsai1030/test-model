# 多語語音模型評測報告
產生時間：2026-10-05 09:08　｜　收錄 run：18 個　｜　硬體：jetson-orin-nx-est, pc

> 讀法：每張表先列通過門檻的模型，再依總分（0–100）排序。`*-est` 是換算的 Jetson 預估值，係數來源見 configs/hardware.yaml（theory = 理論值，尚未用錨點校準）。UTMOS 以英語資料訓練，非英語只能當相對參考；有人工 MOS 時優先採用人工分數。

## 推薦組合（依 target_hw_priority 取第一個有數據的硬體）
| 語言 | STT | TTS | 對話組合 |
|---|---|---|---|
| en | parakeet-tdt-0.6b-v2-int8（96.50 分，jetson-orin-nx-est） | piper-medium（96.90 分，jetson-orin-nx-est） | whisper-small-ct2-int8+qwen2.5-1.5b-q4+kokoro-82m（89.50 分，jetson-orin-nx-est） |
| es-ES | parakeet-tdt-0.6b-v3-int8（95.90 分，jetson-orin-nx-est） | supertonic-3（75.30 分，jetson-orin-nx-est） | whisper-small-ct2-int8+qwen2.5-3b-q4+kokoro-82m（71.90 分，jetson-orin-nx-est） |
| es-419 | whisper-small-ct2-int8（96.50 分，jetson-orin-nx-est） | supertonic-3（74.10 分，jetson-orin-nx-est） | whisper-small-ct2-int8+qwen2.5-3b-q4+kokoro-82m（70.60 分，jetson-orin-nx-est） |
| pt-BR | parakeet-tdt-0.6b-v3-int8（95.90 分，jetson-orin-nx-est） | piper-medium（79.90 分，jetson-orin-nx-est） | whisper-small-ct2-int8+gemma-3-4b-q4+piper-medium（76.80 分，jetson-orin-nx-est） |
| pt-PT | parakeet-tdt-0.6b-v3-int8（52.80 分，jetson-orin-nx-est） | supertonic-3（77.30 分，jetson-orin-nx-est） | whisper-small-ct2-int8+gemma-3-4b-q4+piper-medium（61.40 分，jetson-orin-nx-est） |
| ja | sensevoice-small-int8（96.60 分，jetson-orin-nx-est） | supertonic-3（82.30 分，jetson-orin-nx-est） | whisper-small-ct2-int8+qwen2.5-1.5b-q4+kokoro-82m（75.80 分，jetson-orin-nx-est） |

## STT 語音辨識

> 錯誤率：日語為 CER（字錯誤率），其他語言為 WER（詞錯誤率）。噪音錯誤率與幻覺率只有 stt_full 套件會測，未測時顯示「–」。

### en · English

**jetson-orin-nx-est**

| # | 模型 | 資料集 | 總分 | 門檻 | 錯誤率 | 95% 信賴區間 | 噪音錯誤率 | 幻覺率 | RTF p50 | 延遲 ms p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | parakeet-tdt-0.6b-v2-int8 | fleurs | 96.50 | PASS | 6.0% WER | 4.5%–7.8% | – | – | 0.06 | 567 | 有條件 | 824 | CC-BY-4.0 |
| 2 | whisper-small-ct2-int8 | fleurs | 93.50 | PASS | 6.9% WER | 5.2%–8.6% | – | – | 0.15 | 1388 | 整句 | 699 | MIT |
| 3 | sensevoice-small-int8 | fleurs | 93.00 | PASS | 8.7% WER | 6.9%–10.7% | – | – | 0.03 | 297 | 整句 | 304 | FunASR model license |
| 4 | granite-speech-5.0-470m-ctc | fleurs | 92.20 | PASS | 5.5% WER | 4.1%–6.8% | – | – | 0.04 | 401 | 整句 | 1926 | Apache-2.0 |
| 5 | parakeet-tdt-0.6b-v3-int8 | fleurs | 89.70 | PASS | 8.3% WER | 6.2%–10.7% | – | – | 0.07 | 655 | 有條件 | 1339 | CC-BY-4.0 |
| 6 | whisper-base-ct2-int8 | fleurs | 88.00 | PASS | 11.3% WER | 9.0%–13.7% | – | – | 0.05 | 426 | 整句 | 281 | MIT |
| 7 | whisper-tiny-ct2-int8 | fleurs | 76.00 | PASS | 17.8% WER | 14.7%–20.9% | – | – | 0.02 | 202 | 整句 | 361 | MIT |
| 8 | qwen3-asr-0.6b | fleurs | 81.80 | FAIL:memory | 4.9% WER | 3.6%–6.2% | – | – | 0.24 | 2169 | 有條件 | 3085 | Apache-2.0 |
| 9 | nemotron-3.5-asr-0.6b | fleurs | 79.10 | FAIL:memory | 9.7% WER | 7.8%–11.6% | – | – | 0.09 | 829 | 原生串流 | 2940 | OpenMDW-1.1 |
| 10 | nemotron-3.5-asr-0.6b-stream560 | fleurs | 76.50 | FAIL:memory | 9.4% WER | 4.7%–14.3% | – | – | 0.09 | 835 | 原生串流（首段 515 / 說完後 1056 ms） | 3608 | OpenMDW-1.1 |
| 11 | whisper-medium-ct2-int8 | fleurs | 75.50 | FAIL:memory | 5.9% WER | 4.2%–7.7% | – | – | 0.45 | 4318 | 整句 | 2390 | MIT |
| 12 | distil-large-v3-ct2-int8 | fleurs | 63.40 | FAIL:rtf | 6.7% WER | 5.1%–8.4% | – | – | 0.80 | 7314 | 整句 | 1721 | MIT |
| 13 | whisper-large-v3-turbo-ct2-int8 | fleurs | 56.20 | FAIL:rtf | 5.9% WER | 4.3%–7.5% | – | – | 1.07 | 8941 | 整句 | 1896 | MIT |

**pc**

| # | 模型 | 資料集 | 總分 | 門檻 | 錯誤率 | 95% 信賴區間 | 噪音錯誤率 | 幻覺率 | RTF p50 | 延遲 ms p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | parakeet-tdt-0.6b-v2-int8 | fleurs | 94.40 | PASS | 6.0% WER | 4.5%–7.8% | – | – | 0.16 | 1417 | 有條件 | 824 | CC-BY-4.0 |
| 2 | sensevoice-small-int8 | fleurs | 93.00 | PASS | 8.7% WER | 6.9%–10.7% | – | – | 0.08 | 742 | 整句 | 304 | FunASR model license |
| 3 | granite-speech-5.0-470m-ctc | fleurs | 87.40 | PASS | 5.5% WER | 4.1%–6.8% | – | – | 0.22 | 2003 | 整句 | 1926 | Apache-2.0 |
| 4 | parakeet-tdt-0.6b-v3-int8 | fleurs | 87.00 | PASS | 8.3% WER | 6.2%–10.7% | – | – | 0.17 | 1639 | 有條件 | 1339 | CC-BY-4.0 |
| 5 | whisper-base-ct2-int8 | fleurs | 84.20 | PASS | 11.3% WER | 9.0%–13.7% | – | – | 0.20 | 1704 | 整句 | 281 | MIT |
| 6 | whisper-tiny-ct2-int8 | fleurs | 76.00 | PASS | 17.8% WER | 14.7%–20.9% | – | – | 0.09 | 807 | 整句 | 361 | MIT |
| 7 | whisper-small-ct2-int8 | fleurs | 75.60 | PASS | 6.9% WER | 5.2%–8.6% | – | – | 0.61 | 5552 | 整句 | 699 | MIT |
| 8 | whisper-large-v3-turbo-ct2-int8 | fleurs | 56.20 | PASS | 5.9% WER | 4.3%–7.5% | – | – | 4.27 | 35765 | 整句 | 1896 | MIT |
| 9 | distil-large-v3-ct2-int8 | fleurs | 55.40 | PASS | 6.7% WER | 5.1%–8.4% | – | – | 3.19 | 29258 | 整句 | 1721 | MIT |
| 10 | nemotron-3.5-asr-0.6b | fleurs | 65.50 | FAIL:memory | 9.7% WER | 7.8%–11.6% | – | – | 0.45 | 4146 | 原生串流 | 2940 | OpenMDW-1.1 |
| 11 | nemotron-3.5-asr-0.6b-stream560 | fleurs | 63.30 | FAIL:memory | 9.4% WER | 4.7%–14.3% | – | – | 0.44 | 4176 | 原生串流（首段 2576 / 說完後 5280 ms） | 3608 | OpenMDW-1.1 |
| 12 | whisper-medium-ct2-int8 | fleurs | 53.80 | FAIL:memory | 5.9% WER | 4.2%–7.7% | – | – | 1.78 | 17274 | 整句 | 2390 | MIT |
| 13 | qwen3-asr-0.6b | fleurs | 52.00 | FAIL:memory | 4.9% WER | 3.6%–6.2% | – | – | 1.20 | 10845 | 有條件 | 3085 | Apache-2.0 |

### es-ES · Español (España)

**jetson-orin-nx-est**

| # | 模型 | 資料集 | 總分 | 門檻 | 錯誤率 | 95% 信賴區間 | 噪音錯誤率 | 幻覺率 | RTF p50 | 延遲 ms p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | parakeet-tdt-0.6b-v3-int8 | commonvoice | 95.90 | PASS | 4.1% WER | 2.2%–6.4% | – | – | 0.06 | 335 | 有條件 | 1339 | CC-BY-4.0 |
| 2 | whisper-small-ct2-int8 | commonvoice | 84.30 | PASS | 9.8% WER | 7.2%–12.6% | – | – | 0.25 | 1338 | 整句 | 699 | MIT |
| 3 | whisper-base-ct2-int8 | commonvoice | 77.50 | PASS | 16.9% WER | 12.9%–22.0% | – | – | 0.07 | 398 | 整句 | 281 | MIT |
| 4 | nemotron-3.5-asr-0.6b | commonvoice | 85.80 | FAIL:memory | 6.2% WER | 3.8%–8.8% | – | – | 0.10 | 561 | 原生串流 | 2940 | OpenMDW-1.1 |
| 5 | nemotron-3.5-asr-0.6b-stream560 | commonvoice | 83.20 | FAIL:memory | 5.8% WER | 1.4%–11.7% | – | – | 0.09 | 513 | 原生串流（首段 512 / 說完後 677 ms） | 3608 | OpenMDW-1.1 |
| 6 | qwen3-asr-0.6b | commonvoice | 79.60 | FAIL:memory | 6.4% WER | 4.3%–8.9% | – | – | 0.23 | 1324 | 有條件 | 3085 | Apache-2.0 |
| 7 | whisper-medium-ct2-int8 | commonvoice | 59.70 | FAIL:rtf+memory | 7.2% WER | 4.1%–10.8% | – | – | 0.79 | 4162 | 整句 | 2390 | MIT |
| 8 | whisper-large-v3-turbo-ct2-int8 | commonvoice | 56.70 | FAIL:rtf | 5.6% WER | 2.8%–9.0% | – | – | 1.64 | 8654 | 整句 | 1896 | MIT |
| 9 | whisper-tiny-ct2-int8 | commonvoice | 52.90 | FAIL:accuracy | 30.7% WER | 25.2%–36.2% | – | – | 0.04 | 193 | 整句 | 361 | MIT |

**pc**

| # | 模型 | 資料集 | 總分 | 門檻 | 錯誤率 | 95% 信賴區間 | 噪音錯誤率 | 幻覺率 | RTF p50 | 延遲 ms p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | parakeet-tdt-0.6b-v3-int8 | commonvoice | 93.90 | PASS | 4.1% WER | 2.2%–6.4% | – | – | 0.15 | 839 | 有條件 | 1339 | CC-BY-4.0 |
| 2 | whisper-base-ct2-int8 | commonvoice | 69.90 | PASS | 16.9% WER | 12.9%–22.0% | – | – | 0.29 | 1592 | 整句 | 281 | MIT |
| 3 | whisper-large-v3-turbo-ct2-int8 | commonvoice | 56.70 | PASS | 5.6% WER | 2.8%–9.0% | – | – | 6.54 | 34615 | 整句 | 1896 | MIT |
| 4 | whisper-small-ct2-int8 | commonvoice | 55.00 | PASS | 9.8% WER | 7.2%–12.6% | – | – | 0.99 | 5353 | 整句 | 699 | MIT |
| 5 | nemotron-3.5-asr-0.6b | commonvoice | 70.50 | FAIL:memory | 6.2% WER | 3.8%–8.8% | – | – | 0.49 | 2804 | 原生串流 | 2940 | OpenMDW-1.1 |
| 6 | nemotron-3.5-asr-0.6b-stream560 | commonvoice | 69.00 | FAIL:memory | 5.8% WER | 1.4%–11.7% | – | – | 0.46 | 2566 | 原生串流（首段 2561 / 說完後 3387 ms） | 3608 | OpenMDW-1.1 |
| 7 | whisper-medium-ct2-int8 | commonvoice | 51.30 | FAIL:memory | 7.2% WER | 4.1%–10.8% | – | – | 3.14 | 16648 | 整句 | 2390 | MIT |
| 8 | whisper-tiny-ct2-int8 | commonvoice | 51.20 | FAIL:accuracy | 30.7% WER | 25.2%–36.2% | – | – | 0.14 | 773 | 整句 | 361 | MIT |
| 9 | qwen3-asr-0.6b | commonvoice | 49.40 | FAIL:memory | 6.4% WER | 4.3%–8.9% | – | – | 1.15 | 6618 | 有條件 | 3085 | Apache-2.0 |

### es-419 · Español (Latinoamérica)

**jetson-orin-nx-est**

| # | 模型 | 資料集 | 總分 | 門檻 | 錯誤率 | 95% 信賴區間 | 噪音錯誤率 | 幻覺率 | RTF p50 | 延遲 ms p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | whisper-small-ct2-int8 | fleurs | 96.50 | PASS | 5.5% WER | 4.5%–6.7% | – | – | 0.14 | 1472 | 整句 | 699 | MIT |
| 2 | parakeet-tdt-0.6b-v3-int8 | fleurs | 95.90 | PASS | 3.5% WER | 2.6%–4.5% | – | – | 0.07 | 740 | 有條件 | 1339 | CC-BY-4.0 |
| 3 | whisper-base-ct2-int8 | fleurs | 86.50 | PASS | 12.2% WER | 10.3%–14.2% | – | – | 0.04 | 455 | 整句 | 281 | MIT |
| 4 | whisper-tiny-ct2-int8 | fleurs | 76.50 | PASS | 17.5% WER | 15.0%–20.0% | – | – | 0.02 | 226 | 整句 | 361 | MIT |
| 5 | nemotron-3.5-asr-0.6b | fleurs | 87.90 | FAIL:memory | 4.5% WER | 3.3%–5.6% | – | – | 0.10 | 1261 | 原生串流 | 2940 | OpenMDW-1.1 |
| 6 | nemotron-3.5-asr-0.6b-stream560 | fleurs | 84.70 | FAIL:memory | 0.7% WER | 0.0%–1.3% | – | – | 0.09 | 848 | 原生串流（首段 768 / 說完後 1051 ms） | 3608 | OpenMDW-1.1 |
| 7 | qwen3-asr-0.6b | fleurs | 80.70 | FAIL:memory | 3.7% WER | 2.8%–4.8% | – | – | 0.27 | 2906 | 有條件 | 3085 | Apache-2.0 |
| 8 | whisper-medium-ct2-int8 | fleurs | 77.60 | FAIL:memory | 3.6% WER | 2.2%–5.5% | – | – | 0.43 | 4542 | 整句 | 2390 | MIT |
| 9 | whisper-large-v3-turbo-ct2-int8 | fleurs | 60.70 | FAIL:rtf | 2.5% WER | 1.4%–3.9% | – | – | 0.93 | 9136 | 整句 | 1896 | MIT |

**pc**

| # | 模型 | 資料集 | 總分 | 門檻 | 錯誤率 | 95% 信賴區間 | 噪音錯誤率 | 幻覺率 | RTF p50 | 延遲 ms p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | parakeet-tdt-0.6b-v3-int8 | fleurs | 93.10 | PASS | 3.5% WER | 2.6%–4.5% | – | – | 0.17 | 1850 | 有條件 | 1339 | CC-BY-4.0 |
| 2 | whisper-base-ct2-int8 | fleurs | 83.90 | PASS | 12.2% WER | 10.3%–14.2% | – | – | 0.17 | 1818 | 整句 | 281 | MIT |
| 3 | whisper-small-ct2-int8 | fleurs | 80.40 | PASS | 5.5% WER | 4.5%–6.7% | – | – | 0.55 | 5889 | 整句 | 699 | MIT |
| 4 | whisper-tiny-ct2-int8 | fleurs | 76.50 | PASS | 17.5% WER | 15.0%–20.0% | – | – | 0.08 | 903 | 整句 | 361 | MIT |
| 5 | whisper-large-v3-turbo-ct2-int8 | fleurs | 57.90 | PASS | 2.5% WER | 1.4%–3.9% | – | – | 3.71 | 36546 | 整句 | 1896 | MIT |
| 6 | nemotron-3.5-asr-0.6b-stream560 | fleurs | 71.80 | FAIL:memory | 0.7% WER | 0.0%–1.3% | – | – | 0.43 | 4238 | 原生串流（首段 3841 / 說完後 5254 ms） | 3608 | OpenMDW-1.1 |
| 7 | nemotron-3.5-asr-0.6b | fleurs | 71.70 | FAIL:memory | 4.5% WER | 3.3%–5.6% | – | – | 0.52 | 6305 | 原生串流 | 2940 | OpenMDW-1.1 |
| 8 | whisper-medium-ct2-int8 | fleurs | 55.40 | FAIL:memory | 3.6% WER | 2.2%–5.5% | – | – | 1.74 | 18168 | 整句 | 2390 | MIT |
| 9 | qwen3-asr-0.6b | fleurs | 52.00 | FAIL:memory | 3.7% WER | 2.8%–4.8% | – | – | 1.34 | 14528 | 有條件 | 3085 | Apache-2.0 |

### pt-BR · Português (Brasil)

**jetson-orin-nx-est**

| # | 模型 | 資料集 | 總分 | 門檻 | 錯誤率 | 95% 信賴區間 | 噪音錯誤率 | 幻覺率 | RTF p50 | 延遲 ms p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | parakeet-tdt-0.6b-v3-int8 | fleurs | 95.90 | PASS | 4.6% WER | 3.5%–5.8% | – | – | 0.07 | 798 | 有條件 | 1339 | CC-BY-4.0 |
| 2 | whisper-small-ct2-int8 | fleurs | 94.10 | PASS | 7.0% WER | 5.4%–8.8% | – | – | 0.13 | 1532 | 整句 | 699 | MIT |
| 3 | whisper-base-ct2-int8 | fleurs | 81.20 | PASS | 15.0% WER | 13.0%–17.3% | – | – | 0.04 | 450 | 整句 | 281 | MIT |
| 4 | whisper-tiny-ct2-int8 | fleurs | 63.60 | PASS | 24.3% WER | 21.8%–27.0% | – | – | 0.02 | 225 | 整句 | 361 | MIT |
| 5 | parakeet-v3-ptbr-tagarela | fleurs | 87.20 | FAIL:memory | 4.6% WER | 3.6%–5.7% | – | – | 0.07 | 898 | 有條件 | 3108 | CC-BY-4.0 |
| 6 | nemotron-3.5-asr-0.6b | fleurs | 86.20 | FAIL:memory | 6.0% WER | 4.8%–7.3% | – | – | 0.08 | 973 | 原生串流 | 2940 | OpenMDW-1.1 |
| 7 | nemotron-3.5-asr-0.6b-stream560 | fleurs | 82.60 | FAIL:memory | 6.0% WER | 3.7%–8.9% | – | – | 0.11 | 1364 | 原生串流（首段 528 / 說完後 1396 ms） | 3608 | OpenMDW-1.1 |
| 8 | qwen3-asr-0.6b | fleurs | 77.80 | FAIL:memory | 6.8% WER | 5.3%–8.5% | – | – | 0.25 | 3081 | 有條件 | 3085 | Apache-2.0 |
| 9 | whisper-medium-ct2-int8 | fleurs | 70.10 | FAIL:rtf+memory | 5.5% WER | 3.7%–7.4% | – | – | 0.60 | 6762 | 整句 | 2390 | MIT |
| 10 | whisper-large-v3-turbo-ct2-int8 | fleurs | 65.70 | FAIL:rtf | 5.0% WER | 3.2%–7.1% | – | – | 0.80 | 9275 | 整句 | 1896 | MIT |

**pc**

| # | 模型 | 資料集 | 總分 | 門檻 | 錯誤率 | 95% 信賴區間 | 噪音錯誤率 | 幻覺率 | RTF p50 | 延遲 ms p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | parakeet-tdt-0.6b-v3-int8 | fleurs | 93.20 | PASS | 4.6% WER | 3.5%–5.8% | – | – | 0.17 | 1994 | 有條件 | 1339 | CC-BY-4.0 |
| 2 | whisper-small-ct2-int8 | fleurs | 79.20 | PASS | 7.0% WER | 5.4%–8.8% | – | – | 0.51 | 6130 | 整句 | 699 | MIT |
| 3 | whisper-base-ct2-int8 | fleurs | 79.10 | PASS | 15.0% WER | 13.0%–17.3% | – | – | 0.15 | 1800 | 整句 | 281 | MIT |
| 4 | whisper-tiny-ct2-int8 | fleurs | 63.60 | PASS | 24.3% WER | 21.8%–27.0% | – | – | 0.08 | 900 | 整句 | 361 | MIT |
| 5 | whisper-large-v3-turbo-ct2-int8 | fleurs | 57.90 | PASS | 5.0% WER | 3.2%–7.1% | – | – | 3.20 | 37099 | 整句 | 1896 | MIT |
| 6 | parakeet-v3-ptbr-tagarela | fleurs | 83.80 | FAIL:memory | 4.6% WER | 3.6%–5.7% | – | – | 0.19 | 2244 | 有條件 | 3108 | CC-BY-4.0 |
| 7 | nemotron-3.5-asr-0.6b | fleurs | 74.30 | FAIL:memory | 6.0% WER | 4.8%–7.3% | – | – | 0.40 | 4866 | 原生串流 | 2940 | OpenMDW-1.1 |
| 8 | nemotron-3.5-asr-0.6b-stream560 | fleurs | 65.80 | FAIL:memory | 6.0% WER | 3.7%–8.9% | – | – | 0.53 | 6820 | 原生串流（首段 2641 / 說完後 6981 ms） | 3608 | OpenMDW-1.1 |
| 9 | whisper-medium-ct2-int8 | fleurs | 54.50 | FAIL:memory | 5.5% WER | 3.7%–7.4% | – | – | 2.41 | 27050 | 整句 | 2390 | MIT |
| 10 | qwen3-asr-0.6b | fleurs | 48.60 | FAIL:memory | 6.8% WER | 5.3%–8.5% | – | – | 1.26 | 15403 | 有條件 | 3085 | Apache-2.0 |

### pt-PT · Português (Portugal)

**jetson-orin-nx-est**

| # | 模型 | 資料集 | 總分 | 門檻 | 錯誤率 | 95% 信賴區間 | 噪音錯誤率 | 幻覺率 | RTF p50 | 延遲 ms p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | parakeet-tdt-0.6b-v3-int8 | commonvoice | 52.80 | PASS | 27.9% WER | 20.9%–35.5% | – | – | 0.07 | 292 | 有條件 | 1339 | CC-BY-4.0 |
| 2 | parakeet-v3-ptbr-tagarela | commonvoice | 72.60 | FAIL:memory | 12.8% WER | 8.7%–17.2% | – | – | 0.08 | 351 | 有條件 | 3108 | CC-BY-4.0 |
| 3 | whisper-tiny-ct2-int8 | commonvoice | 52.90 | FAIL:accuracy | 69.6% WER | 61.0%–79.7% | – | – | 0.09 | 291 | 整句 | 270 | MIT |
| 4 | whisper-base-ct2-int8 | commonvoice | 52.70 | FAIL:accuracy | 57.7% WER | 49.0%–67.0% | – | – | 0.11 | 389 | 整句 | 267 | MIT |
| 5 | qwen3-asr-0.6b | commonvoice | 48.00 | FAIL:memory | 23.7% WER | 17.7%–29.9% | – | – | 0.20 | 900 | 有條件 | 3085 | Apache-2.0 |
| 6 | whisper-small-ct2-int8 | commonvoice | 43.40 | FAIL:accuracy | 36.1% WER | 28.5%–44.8% | – | – | 0.31 | 1258 | 整句 | 770 | MIT |
| 7 | nemotron-3.5-asr-0.6b | commonvoice | 41.00 | FAIL:accuracy+memory | 30.4% WER | 23.7%–37.5% | – | – | 0.10 | 410 | 原生串流 | 2940 | OpenMDW-1.1 |
| 8 | nemotron-3.5-asr-0.6b-stream560 | commonvoice | 37.70 | FAIL:accuracy+memory | 40.7% WER | 25.7%–61.4% | – | – | 0.10 | 279 | 原生串流（首段 656 / 說完後 495 ms） | 3608 | OpenMDW-1.1 |
| 9 | whisper-large-v3-turbo-ct2-int8 | commonvoice | 36.60 | FAIL:rtf | 16.3% WER | 9.6%–25.6% | – | – | 2.78 | 8134 | 整句 | 1896 | MIT |
| 10 | whisper-medium-ct2-int8 | commonvoice | 23.60 | FAIL:rtf+memory | 21.9% WER | 13.0%–33.0% | – | – | 1.88 | 6667 | 整句 | 2390 | MIT |

**pc**

| # | 模型 | 資料集 | 總分 | 門檻 | 錯誤率 | 95% 信賴區間 | 噪音錯誤率 | 幻覺率 | RTF p50 | 延遲 ms p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | parakeet-tdt-0.6b-v3-int8 | commonvoice | 49.80 | PASS | 27.9% WER | 20.9%–35.5% | – | – | 0.18 | 731 | 有條件 | 1339 | CC-BY-4.0 |
| 2 | whisper-large-v3-turbo-ct2-int8 | commonvoice | 36.60 | PASS | 16.3% WER | 9.6%–25.6% | – | – | 11.13 | 32536 | 整句 | 1896 | MIT |
| 3 | parakeet-v3-ptbr-tagarela | commonvoice | 68.50 | FAIL:memory | 12.8% WER | 8.7%–17.2% | – | – | 0.20 | 877 | 有條件 | 3108 | CC-BY-4.0 |
| 4 | whisper-tiny-ct2-int8 | commonvoice | 42.50 | FAIL:accuracy | 69.6% WER | 61.0%–79.7% | – | – | 0.37 | 1164 | 整句 | 270 | MIT |
| 5 | whisper-base-ct2-int8 | commonvoice | 40.30 | FAIL:accuracy | 57.7% WER | 49.0%–67.0% | – | – | 0.42 | 1555 | 整句 | 267 | MIT |
| 6 | nemotron-3.5-asr-0.6b | commonvoice | 26.10 | FAIL:accuracy+memory | 30.4% WER | 23.7%–37.5% | – | – | 0.48 | 2048 | 原生串流 | 2940 | OpenMDW-1.1 |
| 7 | whisper-medium-ct2-int8 | commonvoice | 23.60 | FAIL:memory | 21.9% WER | 13.0%–33.0% | – | – | 7.50 | 26667 | 整句 | 2390 | MIT |
| 8 | nemotron-3.5-asr-0.6b-stream560 | commonvoice | 22.00 | FAIL:accuracy+memory | 40.7% WER | 25.7%–61.4% | – | – | 0.50 | 1394 | 原生串流（首段 3280 / 說完後 2473 ms） | 3608 | OpenMDW-1.1 |
| 9 | qwen3-asr-0.6b | commonvoice | 16.70 | FAIL:memory | 23.7% WER | 17.7%–29.9% | – | – | 1.02 | 4499 | 有條件 | 3085 | Apache-2.0 |
| 10 | whisper-small-ct2-int8 | commonvoice | 16.30 | FAIL:accuracy | 36.1% WER | 28.5%–44.8% | – | – | 1.24 | 5032 | 整句 | 770 | MIT |

### ja · 日本語

**jetson-orin-nx-est**

| # | 模型 | 資料集 | 總分 | 門檻 | 錯誤率 | 95% 信賴區間 | 噪音錯誤率 | 幻覺率 | RTF p50 | 延遲 ms p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sensevoice-small-int8 | fleurs | 96.60 | PASS | 6.8% CER | 5.4%–8.4% | – | – | 0.03 | 451 | 整句 | 304 | FunASR model license |
| 2 | parakeet-tdt_ctc-0.6b-ja-int8 | fleurs | 93.60 | PASS | 6.9% CER | 4.9%–9.1% | – | – | 0.06 | 726 | 整句 | 1062 | CC-BY-4.0 |
| 3 | whisper-small-ct2-int8 | fleurs | 86.70 | PASS | 11.0% CER | 9.2%–12.9% | – | – | 0.12 | 1544 | 整句 | 699 | MIT |
| 4 | moonshine-tiny-ja | fleurs | 85.20 | PASS | 12.9% CER | 10.8%–15.1% | – | – | 0.02 | 267 | 整句 | 490 | Moonshine Community License |
| 5 | whisper-base-ct2-int8 | fleurs | 63.80 | PASS | 24.2% CER | 21.6%–27.4% | – | – | 0.04 | 466 | 整句 | 281 | MIT |
| 6 | qwen3-asr-0.6b | fleurs | 77.90 | FAIL:memory | 7.8% CER | 6.4%–9.3% | – | – | 0.21 | 2568 | 有條件 | 3085 | Apache-2.0 |
| 7 | nemotron-3.5-asr-0.6b | fleurs | 73.30 | FAIL:memory | 12.8% CER | 11.0%–14.6% | – | – | 0.08 | 1087 | 原生串流 | 2940 | OpenMDW-1.1 |
| 8 | whisper-large-v3-turbo-ct2-int8 | fleurs | 70.20 | FAIL:rtf | 6.4% CER | 4.4%–8.6% | – | – | 0.62 | 7655 | 整句 | 1896 | MIT |
| 9 | whisper-medium-ct2-int8 | fleurs | 69.30 | FAIL:rtf+memory | 7.4% CER | 5.3%–9.8% | – | – | 0.53 | 6556 | 整句 | 2390 | MIT |
| 10 | nemotron-3.5-asr-0.6b-stream560 | fleurs | 69.30 | FAIL:memory | 13.2% CER | 7.9%–18.2% | – | – | 0.08 | 1012 | 原生串流（首段 896 / 說完後 1343 ms） | 3608 | OpenMDW-1.1 |
| 11 | kotoba-whisper-v2-ct2-int8 | fleurs | 68.10 | FAIL:rtf | 8.1% CER | 5.5%–11.3% | – | – | 0.60 | 7365 | 整句 | 1799 | Apache-2.0 |
| 12 | whisper-tiny-ct2-int8 | fleurs | 52.90 | FAIL:accuracy | 38.6% CER | 35.5%–41.8% | – | – | 0.02 | 235 | 整句 | 361 | MIT |

**pc**

| # | 模型 | 資料集 | 總分 | 門檻 | 錯誤率 | 95% 信賴區間 | 噪音錯誤率 | 幻覺率 | RTF p50 | 延遲 ms p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sensevoice-small-int8 | fleurs | 96.60 | PASS | 6.8% CER | 5.4%–8.4% | – | – | 0.08 | 1128 | 整句 | 304 | FunASR model license |
| 2 | parakeet-tdt_ctc-0.6b-ja-int8 | fleurs | 91.80 | PASS | 6.9% CER | 4.9%–9.1% | – | – | 0.15 | 1814 | 整句 | 1062 | CC-BY-4.0 |
| 3 | moonshine-tiny-ja | fleurs | 84.60 | PASS | 12.9% CER | 10.8%–15.1% | – | – | 0.11 | 1336 | 整句 | 490 | Moonshine Community License |
| 4 | whisper-small-ct2-int8 | fleurs | 72.10 | PASS | 11.0% CER | 9.2%–12.9% | – | – | 0.50 | 6176 | 整句 | 699 | MIT |
| 5 | whisper-base-ct2-int8 | fleurs | 61.80 | PASS | 24.2% CER | 21.6%–27.4% | – | – | 0.15 | 1862 | 整句 | 281 | MIT |
| 6 | whisper-large-v3-turbo-ct2-int8 | fleurs | 55.10 | PASS | 6.4% CER | 4.4%–8.6% | – | – | 2.47 | 30622 | 整句 | 1896 | MIT |
| 7 | kotoba-whisper-v2-ct2-int8 | fleurs | 52.50 | PASS | 8.1% CER | 5.5%–11.3% | – | – | 2.41 | 29460 | 整句 | 1799 | Apache-2.0 |
| 8 | nemotron-3.5-asr-0.6b | fleurs | 61.40 | FAIL:memory | 12.8% CER | 11.0%–14.6% | – | – | 0.41 | 5435 | 原生串流 | 2940 | OpenMDW-1.1 |
| 9 | nemotron-3.5-asr-0.6b-stream560 | fleurs | 58.10 | FAIL:memory | 13.2% CER | 7.9%–18.2% | – | – | 0.39 | 5059 | 原生串流（首段 4482 / 說完後 6717 ms） | 3608 | OpenMDW-1.1 |
| 10 | whisper-tiny-ct2-int8 | fleurs | 52.90 | FAIL:accuracy | 38.6% CER | 35.5%–41.8% | – | – | 0.08 | 939 | 整句 | 361 | MIT |
| 11 | whisper-medium-ct2-int8 | fleurs | 50.90 | FAIL:memory | 7.4% CER | 5.3%–9.8% | – | – | 2.12 | 26225 | 整句 | 2390 | MIT |
| 12 | qwen3-asr-0.6b | fleurs | 46.80 | FAIL:memory | 7.8% CER | 6.4%–9.3% | – | – | 1.03 | 12842 | 有條件 | 3085 | Apache-2.0 |

## TTS 語音合成

### en · English

**jetson-orin-nx-est**

| # | 模型 | 總分 | 門檻 | 自然度 | ASR 回測錯誤率 | TTFA ms p50 | RTF p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | piper-medium | 96.90 | PASS | 4.39 (UTMOS) | 1.3% | 187 | 0.04 | 逐句 | 765 | GPL-3.0 (engine 1.3+) / per-voice |
| 2 | supertonic-3 | 86.80 | PASS | 4.49 (UTMOS) | 1.3% | 872 | 0.16 | 逐句 | 525 | OpenRAIL-M |
| 3 | kokoro-82m | 79.60 | PASS | 4.50 (UTMOS) | 0.0% | 1049 | 0.22 | 逐句 | 1486 | Apache-2.0 |

**pc**

| # | 模型 | 總分 | 門檻 | 自然度 | ASR 回測錯誤率 | TTFA ms p50 | RTF p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | piper-medium | 91.80 | PASS | 4.39 (UTMOS) | 1.3% | 467 | 0.11 | 逐句 | 765 | GPL-3.0 (engine 1.3+) / per-voice |
| 2 | supertonic-3 | 74.70 | PASS | 4.49 (UTMOS) | 1.3% | 2179 | 0.41 | 逐句 | 525 | OpenRAIL-M |
| 3 | kokoro-82m | 70.90 | PASS | 4.50 (UTMOS) | 0.0% | 5247 | 1.08 | 逐句 | 1486 | Apache-2.0 |

### es-ES · Español (España)

**jetson-orin-nx-est**

| # | 模型 | 總分 | 門檻 | 自然度 | ASR 回測錯誤率 | TTFA ms p50 | RTF p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | supertonic-3 | 75.30 | PASS | 3.97 (UTMOS) | 4.3% | 998 | 0.16 | 逐句 | 525 | OpenRAIL-M |
| 2 | kokoro-82m | 63.20 | PASS | 3.58 (UTMOS) | 0.7% | 1064 | 0.21 | 逐句 | 1486 | Apache-2.0 |
| 3 | piper-medium | 61.90 | PASS | 2.52 (UTMOS) | 0.7% | 317 | 0.07 | 逐句 | 765 | GPL-3.0 (engine 1.3+) / per-voice |

**pc**

| # | 模型 | 總分 | 門檻 | 自然度 | ASR 回測錯誤率 | TTFA ms p50 | RTF p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | supertonic-3 | 65.60 | PASS | 3.97 (UTMOS) | 4.3% | 2496 | 0.40 | 逐句 | 525 | OpenRAIL-M |
| 2 | kokoro-82m | 54.80 | PASS | 3.58 (UTMOS) | 0.7% | 5321 | 1.06 | 逐句 | 1486 | Apache-2.0 |
| 3 | piper-medium | 52.80 | PASS | 2.52 (UTMOS) | 0.7% | 792 | 0.17 | 逐句 | 765 | GPL-3.0 (engine 1.3+) / per-voice |

### es-419 · Español (Latinoamérica)

**jetson-orin-nx-est**

| # | 模型 | 總分 | 門檻 | 自然度 | ASR 回測錯誤率 | TTFA ms p50 | RTF p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | supertonic-3 | 74.10 | PASS | 3.94 (UTMOS) | 5.1% | 1020 | 0.16 | 逐句 | 525 | OpenRAIL-M |
| 2 | piper-medium | 73.40 | PASS | 3.08 (UTMOS) | 3.9% | 238 | 0.04 | 逐句 | 765 | GPL-3.0 (engine 1.3+) / per-voice |
| 3 | kokoro-82m | 59.90 | PASS | 3.48 (UTMOS) | 0.6% | 1142 | 0.22 | 逐句 | 1486 | Apache-2.0 |

**pc**

| # | 模型 | 總分 | 門檻 | 自然度 | ASR 回測錯誤率 | TTFA ms p50 | RTF p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | piper-medium | 66.50 | PASS | 3.08 (UTMOS) | 3.9% | 595 | 0.11 | 逐句 | 765 | GPL-3.0 (engine 1.3+) / per-voice |
| 2 | supertonic-3 | 64.90 | PASS | 3.94 (UTMOS) | 5.1% | 2549 | 0.41 | 逐句 | 525 | OpenRAIL-M |
| 3 | kokoro-82m | 53.00 | PASS | 3.48 (UTMOS) | 0.6% | 5708 | 1.09 | 逐句 | 1486 | Apache-2.0 |

### pt-BR · Português (Brasil)

**jetson-orin-nx-est**

| # | 模型 | 總分 | 門檻 | 自然度 | ASR 回測錯誤率 | TTFA ms p50 | RTF p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | piper-medium | 79.90 | PASS | 3.50 (UTMOS) | 3.5% | 275 | 0.05 | 逐句 | 765 | GPL-3.0 (engine 1.3+) / per-voice |
| 2 | supertonic-3 | 78.90 | PASS | 4.18 (UTMOS) | 2.8% | 998 | 0.17 | 逐句 | 525 | OpenRAIL-M |
| 3 | kokoro-82m | 62.40 | PASS | 3.70 (UTMOS) | 0.0% | 1213 | 0.23 | 逐句 | 1486 | Apache-2.0 |

**pc**

| # | 模型 | 總分 | 門檻 | 自然度 | ASR 回測錯誤率 | TTFA ms p50 | RTF p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | piper-medium | 72.00 | PASS | 3.50 (UTMOS) | 3.5% | 688 | 0.13 | 逐句 | 765 | GPL-3.0 (engine 1.3+) / per-voice |
| 2 | supertonic-3 | 69.30 | PASS | 4.18 (UTMOS) | 2.8% | 2496 | 0.42 | 逐句 | 525 | OpenRAIL-M |
| 3 | kokoro-82m | 56.90 | PASS | 3.70 (UTMOS) | 0.0% | 6065 | 1.13 | 逐句 | 1486 | Apache-2.0 |

### pt-PT · Português (Portugal)

**jetson-orin-nx-est**

| # | 模型 | 總分 | 門檻 | 自然度 | ASR 回測錯誤率 | TTFA ms p50 | RTF p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | supertonic-3 | 77.30 | PASS | 4.15 (UTMOS) | 4.8% | 1052 | 0.17 | 逐句 | 525 | OpenRAIL-M |
| 2 | piper-medium | 61.10 | PASS | 2.76 (UTMOS) | 12.4% | 177 | 0.04 | 逐句 | 765 | GPL-3.0 (engine 1.3+) / per-voice |

**pc**

| # | 模型 | 總分 | 門檻 | 自然度 | ASR 回測錯誤率 | TTFA ms p50 | RTF p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | supertonic-3 | 68.70 | PASS | 4.15 (UTMOS) | 4.8% | 2629 | 0.42 | 逐句 | 525 | OpenRAIL-M |
| 2 | piper-medium | 56.40 | PASS | 2.76 (UTMOS) | 12.4% | 442 | 0.11 | 逐句 | 765 | GPL-3.0 (engine 1.3+) / per-voice |

### ja · 日本語

**jetson-orin-nx-est**

| # | 模型 | 總分 | 門檻 | 自然度 | ASR 回測錯誤率 | TTFA ms p50 | RTF p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | supertonic-3 | 82.30 | PASS | 4.23 (UTMOS) | 2.8% | 873 | 0.16 | 逐句 | 525 | OpenRAIL-M |
| 2 | kokoro-82m | 58.80 | PASS | 3.81 (UTMOS) | 2.1% | 1670 | 0.30 | 逐句 | 1486 | Apache-2.0 |

**pc**

| # | 模型 | 總分 | 門檻 | 自然度 | ASR 回測錯誤率 | TTFA ms p50 | RTF p50 | 串流 | 記憶體 MB | 授權 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | supertonic-3 | 70.20 | PASS | 4.23 (UTMOS) | 2.8% | 2182 | 0.40 | 逐句 | 525 | OpenRAIL-M |
| 2 | kokoro-82m | 58.80 | PASS | 3.81 (UTMOS) | 2.1% | 8348 | 1.48 | 逐句 | 1486 | Apache-2.0 |

## 語音對話機器人（STT → LLM → TTS）

### en · English

**jetson-orin-nx-est**

| # | 組合 (STT+LLM+TTS) | 總分 | 門檻 | 回合延遲 ms p50/p90 | STT ms | LLM 首句 ms | TTS 首段 ms | LLM tok/s | 事實正確 | 語言正確 | 人工相關度 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | whisper-small-ct2-int8+qwen2.5-1.5b-q4+kokoro-82m | 89.50 | PASS | 3683 / 4519 | 1396 | 716 | 1271 | 19.48 | 100.0% | 100.0% | – |
| 2 | whisper-small-ct2-int8+gemma-3-4b-q4+piper-medium | 88.20 | PASS | 3270 / 3911 | 1209 | 1591 | 170 | 10.57 | 100.0% | 100.0% | – |
| 3 | whisper-small-ct2-int8+qwen2.5-3b-q4+kokoro-82m | 86.10 | PASS | 3707 / 4130 | 1281 | 1050 | 1076 | 12.78 | 83.3% | 100.0% | – |
| 4 | whisper-small-ct2-int8+gemma-3-1b-q4+kokoro-82m | 83.70 | PASS | 3463 / 4464 | 1433 | 604 | 1125 | 17.00 | 66.7% | 100.0% | – |
| 5 | whisper-small-ct2-int8+gemma-3-4b-q4+kokoro-82m | 79.10 | PASS | 6372 / 7852 | 1671 | 2494 | 1907 | 7.57 | 100.0% | 100.0% | – |
| 6 | whisper-large-v3-turbo-ct2-int8+gemma-3-4b-q4+kokoro-82m | 65.00 | PASS | 11760 / 15938 | 8347 | 1720 | 1393 | 9.52 | 100.0% | 100.0% | – |

**pc**

| # | 組合 (STT+LLM+TTS) | 總分 | 門檻 | 回合延遲 ms p50/p90 | STT ms | LLM 首句 ms | TTS 首段 ms | LLM tok/s | 事實正確 | 語言正確 | 人工相關度 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | whisper-large-v3-turbo-ct2-int8+gemma-3-4b-q4+kokoro-82m | 65.00 | PASS | 45898 / 62520 | 33389 | 5160 | 6964 | 3.17 | 100.0% | 100.0% | – |
| 2 | whisper-small-ct2-int8+gemma-3-4b-q4+kokoro-82m | 65.00 | PASS | 24689 / 30635 | 6683 | 7481 | 9537 | 2.52 | 100.0% | 100.0% | – |
| 3 | whisper-small-ct2-int8+qwen2.5-1.5b-q4+kokoro-82m | 64.90 | PASS | 14806 / 18392 | 5582 | 2149 | 6355 | 6.50 | 100.0% | 100.0% | – |
| 4 | whisper-small-ct2-int8+gemma-3-4b-q4+piper-medium | 62.00 | PASS | 10247 / 12395 | 4837 | 4772 | 425 | 3.52 | 100.0% | 100.0% | – |
| 5 | whisper-small-ct2-int8+qwen2.5-3b-q4+kokoro-82m | 61.70 | PASS | 14795 / 16595 | 5126 | 3149 | 5381 | 4.26 | 83.3% | 100.0% | – |
| 6 | whisper-small-ct2-int8+gemma-3-1b-q4+kokoro-82m | 58.30 | PASS | 13379 / 17521 | 5734 | 1812 | 5627 | 5.67 | 66.7% | 100.0% | – |

### es-ES · Español (España)

**jetson-orin-nx-est**

| # | 組合 (STT+LLM+TTS) | 總分 | 門檻 | 回合延遲 ms p50/p90 | STT ms | LLM 首句 ms | TTS 首段 ms | LLM tok/s | 事實正確 | 語言正確 | 人工相關度 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | whisper-small-ct2-int8+qwen2.5-3b-q4+kokoro-82m | 71.90 | PASS | 4114 / 4843 | 1246 | 1432 | 1136 | 12.46 | 83.3% | 100.0% | – |
| 2 | whisper-small-ct2-int8+qwen2.5-1.5b-q4+kokoro-82m | 67.90 | PASS | 3710 / 5028 | 1517 | 799 | 1094 | 18.23 | 50.0% | 100.0% | – |
| 3 | whisper-small-ct2-int8+gemma-3-1b-q4+kokoro-82m | 63.00 | PASS | 3991 / 5318 | 1567 | 802 | 1322 | 19.80 | 50.0% | 83.3% | – |
| 4 | whisper-small-ct2-int8+gemma-3-4b-q4+kokoro-82m | 62.10 | PASS | 5509 / 7088 | 1746 | 2030 | 1433 | 7.92 | 66.7% | 100.0% | – |
| 5 | whisper-small-ct2-int8+gemma-3-4b-q4+piper-medium | 61.00 | PASS | 2887 / 3641 | 1216 | 1330 | 42 | 10.88 | 66.7% | 100.0% | – |
| 6 | whisper-large-v3-turbo-ct2-int8+gemma-3-4b-q4+kokoro-82m | 48.70 | PASS | 9854 / 10974 | 7269 | 1262 | 1024 | 11.01 | 83.3% | 100.0% | – |

**pc**

| # | 組合 (STT+LLM+TTS) | 總分 | 門檻 | 回合延遲 ms p50/p90 | STT ms | LLM 首句 ms | TTS 首段 ms | LLM tok/s | 事實正確 | 語言正確 | 人工相關度 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | whisper-small-ct2-int8+qwen2.5-3b-q4+kokoro-82m | 49.00 | PASS | 15204 / 18052 | 4985 | 4295 | 5680 | 4.16 | 83.3% | 100.0% | – |
| 2 | whisper-large-v3-turbo-ct2-int8+gemma-3-4b-q4+kokoro-82m | 48.10 | PASS | 39447 / 44034 | 29076 | 3785 | 5120 | 3.67 | 83.3% | 100.0% | – |
| 3 | whisper-small-ct2-int8+gemma-3-4b-q4+kokoro-82m | 44.70 | PASS | 20919 / 27169 | 6982 | 6091 | 7167 | 2.64 | 66.7% | 100.0% | – |
| 4 | whisper-small-ct2-int8+qwen2.5-1.5b-q4+kokoro-82m | 43.40 | PASS | 14493 / 19980 | 6067 | 2397 | 5468 | 6.08 | 50.0% | 100.0% | – |
| 5 | whisper-small-ct2-int8+gemma-3-1b-q4+kokoro-82m | 39.70 | PASS | 15750 / 21305 | 6269 | 2406 | 6610 | 6.60 | 50.0% | 83.3% | – |
| 6 | whisper-small-ct2-int8+gemma-3-4b-q4+piper-medium | 35.00 | PASS | 9563 / 12262 | 4863 | 3989 | 105 | 3.62 | 66.7% | 100.0% | – |

### es-419 · Español (Latinoamérica)

**jetson-orin-nx-est**

| # | 組合 (STT+LLM+TTS) | 總分 | 門檻 | 回合延遲 ms p50/p90 | STT ms | LLM 首句 ms | TTS 首段 ms | LLM tok/s | 事實正確 | 語言正確 | 人工相關度 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | whisper-small-ct2-int8+qwen2.5-3b-q4+kokoro-82m | 70.60 | PASS | 3647 / 4579 | 1172 | 1160 | 1014 | 12.08 | 66.7% | 100.0% | – |
| 2 | whisper-small-ct2-int8+qwen2.5-1.5b-q4+kokoro-82m | 70.40 | PASS | 3772 / 4323 | 1383 | 851 | 1238 | 19.07 | 66.7% | 100.0% | – |
| 3 | whisper-small-ct2-int8+gemma-3-1b-q4+kokoro-82m | 65.30 | PASS | 3798 / 4600 | 1454 | 866 | 1178 | 20.68 | 66.7% | 83.3% | – |
| 4 | whisper-small-ct2-int8+gemma-3-4b-q4+kokoro-82m | 63.60 | PASS | 6273 / 6629 | 1954 | 2403 | 1616 | 8.23 | 83.3% | 100.0% | – |
| 5 | whisper-small-ct2-int8+gemma-3-4b-q4+piper-medium | 63.60 | PASS | 4320 / 10058 | 1340 | 2419 | 261 | 9.55 | 83.3% | 100.0% | – |
| 6 | whisper-large-v3-turbo-ct2-int8+gemma-3-4b-q4+kokoro-82m | 49.30 | PASS | 10944 / 13321 | 7107 | 2104 | 1433 | 10.19 | 83.3% | 100.0% | – |

**pc**

| # | 組合 (STT+LLM+TTS) | 總分 | 門檻 | 回合延遲 ms p50/p90 | STT ms | LLM 首句 ms | TTS 首段 ms | LLM tok/s | 事實正確 | 語言正確 | 人工相關度 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | whisper-large-v3-turbo-ct2-int8+gemma-3-4b-q4+kokoro-82m | 49.30 | PASS | 42720 / 52194 | 28427 | 6313 | 7164 | 3.40 | 83.3% | 100.0% | – |
| 2 | whisper-small-ct2-int8+gemma-3-4b-q4+kokoro-82m | 49.10 | PASS | 25767 / 27286 | 7817 | 7209 | 8078 | 2.75 | 83.3% | 100.0% | – |
| 3 | whisper-small-ct2-int8+qwen2.5-1.5b-q4+kokoro-82m | 46.10 | PASS | 15227 / 17597 | 5533 | 2552 | 6189 | 6.36 | 66.7% | 100.0% | – |
| 4 | whisper-small-ct2-int8+qwen2.5-3b-q4+kokoro-82m | 45.90 | PASS | 13332 / 16964 | 4687 | 3482 | 5072 | 4.03 | 66.7% | 100.0% | – |
| 5 | whisper-small-ct2-int8+gemma-3-4b-q4+piper-medium | 41.50 | PASS | 13501 / 32343 | 5359 | 7257 | 653 | 3.19 | 83.3% | 100.0% | – |
| 6 | whisper-small-ct2-int8+gemma-3-1b-q4+kokoro-82m | 41.10 | PASS | 14500 / 17757 | 5817 | 2598 | 5887 | 6.89 | 66.7% | 83.3% | – |

### pt-BR · Português (Brasil)

**jetson-orin-nx-est**

| # | 組合 (STT+LLM+TTS) | 總分 | 門檻 | 回合延遲 ms p50/p90 | STT ms | LLM 首句 ms | TTS 首段 ms | LLM tok/s | 事實正確 | 語言正確 | 人工相關度 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | whisper-small-ct2-int8+gemma-3-4b-q4+piper-medium | 76.80 | PASS | 3250 / 3708 | 1196 | 1592 | 162 | 10.85 | 100.0% | 100.0% | – |
| 2 | whisper-small-ct2-int8+qwen2.5-3b-q4+kokoro-82m | 75.30 | PASS | 3862 / 4942 | 1188 | 1308 | 1066 | 11.69 | 83.3% | 100.0% | – |
| 3 | whisper-small-ct2-int8+qwen2.5-1.5b-q4+kokoro-82m | 74.60 | PASS | 3415 / 3867 | 1367 | 753 | 995 | 19.39 | 66.7% | 100.0% | – |
| 4 | whisper-small-ct2-int8+gemma-3-4b-q4+kokoro-82m | 71.80 | PASS | 5129 / 5638 | 1503 | 2094 | 1232 | 9.30 | 100.0% | 100.0% | – |
| 5 | whisper-small-ct2-int8+gemma-3-1b-q4+kokoro-82m | 64.90 | PASS | 3762 / 4193 | 1537 | 710 | 1215 | 20.00 | 50.0% | 83.3% | – |
| 6 | whisper-large-v3-turbo-ct2-int8+gemma-3-4b-q4+kokoro-82m | 52.40 | PASS | 14023 / 15103 | 9886 | 2281 | 1556 | 7.10 | 100.0% | 100.0% | – |

**pc**

| # | 組合 (STT+LLM+TTS) | 總分 | 門檻 | 回合延遲 ms p50/p90 | STT ms | LLM 首句 ms | TTS 首段 ms | LLM tok/s | 事實正確 | 語言正確 | 人工相關度 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | whisper-small-ct2-int8+gemma-3-4b-q4+kokoro-82m | 52.80 | PASS | 19310 / 21313 | 6011 | 6283 | 6160 | 3.10 | 100.0% | 100.0% | – |
| 2 | whisper-large-v3-turbo-ct2-int8+gemma-3-4b-q4+kokoro-82m | 52.40 | PASS | 56099 / 60489 | 39543 | 6844 | 7780 | 2.37 | 100.0% | 100.0% | – |
| 3 | whisper-small-ct2-int8+qwen2.5-3b-q4+kokoro-82m | 51.40 | PASS | 14555 / 18881 | 4750 | 3923 | 5332 | 3.90 | 83.3% | 100.0% | – |
| 4 | whisper-small-ct2-int8+gemma-3-4b-q4+piper-medium | 50.50 | PASS | 10274 / 11820 | 4782 | 4777 | 406 | 3.62 | 100.0% | 100.0% | – |
| 5 | whisper-small-ct2-int8+qwen2.5-1.5b-q4+kokoro-82m | 49.00 | PASS | 12987 / 14829 | 5467 | 2260 | 4973 | 6.46 | 66.7% | 100.0% | – |
| 6 | whisper-small-ct2-int8+gemma-3-1b-q4+kokoro-82m | 40.60 | PASS | 14312 / 16058 | 6147 | 2130 | 6075 | 6.67 | 50.0% | 83.3% | – |

### pt-PT · Português (Portugal)

**jetson-orin-nx-est**

| # | 組合 (STT+LLM+TTS) | 總分 | 門檻 | 回合延遲 ms p50/p90 | STT ms | LLM 首句 ms | TTS 首段 ms | LLM tok/s | 事實正確 | 語言正確 | 人工相關度 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | whisper-small-ct2-int8+gemma-3-4b-q4+piper-medium | 61.40 | PASS | 3643 / 4479 | 1306 | 1957 | 80 | 10.21 | 83.3% | 100.0% | – |

**pc**

| # | 組合 (STT+LLM+TTS) | 總分 | 門檻 | 回合延遲 ms p50/p90 | STT ms | LLM 首句 ms | TTS 首段 ms | LLM tok/s | 事實正確 | 語言正確 | 人工相關度 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | whisper-small-ct2-int8+gemma-3-4b-q4+piper-medium | 36.70 | PASS | 12659 / 15748 | 5222 | 5872 | 201 | 3.40 | 83.3% | 100.0% | – |

### ja · 日本語

**jetson-orin-nx-est**

| # | 組合 (STT+LLM+TTS) | 總分 | 門檻 | 回合延遲 ms p50/p90 | STT ms | LLM 首句 ms | TTS 首段 ms | LLM tok/s | 事實正確 | 語言正確 | 人工相關度 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | whisper-small-ct2-int8+qwen2.5-1.5b-q4+kokoro-82m | 75.80 | PASS | 3552 / 4590 | 1510 | 704 | 1038 | 16.74 | 66.7% | 100.0% | – |
| 2 | whisper-small-ct2-int8+qwen2.5-3b-q4+kokoro-82m | 74.90 | PASS | 3663 / 4161 | 1230 | 1045 | 1088 | 11.48 | 66.7% | 100.0% | – |
| 3 | whisper-small-ct2-int8+gemma-3-4b-q4+kokoro-82m | 69.60 | PASS | 4710 / 5291 | 1380 | 1517 | 1513 | 10.26 | 66.7% | 100.0% | – |
| 4 | whisper-small-ct2-int8+gemma-3-1b-q4+kokoro-82m | 69.30 | PASS | 3583 / 6080 | 1519 | 541 | 1223 | 17.84 | 50.0% | 83.3% | – |
| 5 | whisper-large-v3-turbo-ct2-int8+gemma-3-4b-q4+kokoro-82m | 50.20 | PASS | 14932 / 18191 | 11166 | 1717 | 1749 | 6.38 | 66.7% | 100.0% | – |

**pc**

| # | 組合 (STT+LLM+TTS) | 總分 | 門檻 | 回合延遲 ms p50/p90 | STT ms | LLM 首句 ms | TTS 首段 ms | LLM tok/s | 事實正確 | 語言正確 | 人工相關度 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | whisper-small-ct2-int8+qwen2.5-1.5b-q4+kokoro-82m | 50.70 | PASS | 14346 / 18832 | 6038 | 2112 | 5192 | 5.58 | 66.7% | 100.0% | – |
| 2 | whisper-large-v3-turbo-ct2-int8+gemma-3-4b-q4+kokoro-82m | 50.20 | PASS | 57691 / 70476 | 44665 | 5150 | 8744 | 2.12 | 66.7% | 100.0% | – |
| 3 | whisper-small-ct2-int8+qwen2.5-3b-q4+kokoro-82m | 50.20 | PASS | 13823 / 15827 | 4921 | 3134 | 5438 | 3.83 | 66.7% | 100.0% | – |
| 4 | whisper-small-ct2-int8+gemma-3-4b-q4+kokoro-82m | 49.00 | PASS | 18303 / 20675 | 5519 | 4552 | 7564 | 3.42 | 66.7% | 100.0% | – |
| 5 | whisper-small-ct2-int8+gemma-3-1b-q4+kokoro-82m | 44.40 | PASS | 14228 / 24826 | 6077 | 1622 | 6114 | 5.95 | 50.0% | 83.3% | – |

## 圖表
![stt_pareto_jetson-orin-nx-est.png](stt_pareto_jetson-orin-nx-est.png)
![stt_pareto_pc.png](stt_pareto_pc.png)
![tts_pareto_jetson-orin-nx-est.png](tts_pareto_jetson-orin-nx-est.png)
![tts_pareto_pc.png](tts_pareto_pc.png)

## 權重與門檻
```yaml
target_hw_priority:
- jetson-orin-nx
- jetson-orin-nx-est
- pc
gates:
  commercial_only: false
  jetson_rtf_max: 0.5
  max_err_rate: 0.3
  memory_budget_mb:
    stt: 2048
    tts: 2048
    dialogue: 11264
scales:
  err_rate:
  - 0.05
  - 0.3
  rtf:
  - 0.1
  - 1.0
  ttfa_ms:
  - 200
  - 1500
  mos:
  - 4.5
  - 2.5
  mem_mb:
  - 500
  - 4096
  turn_latency_ms:
  - 1000
  - 10000
  ratio:
  - 1.0
  - 0.0
weights:
  stt:
    accuracy: 40
    speed: 30
    robustness: 15
    resource: 15
  tts:
    naturalness: 35
    intelligibility: 25
    ttfa: 25
    resource: 15
  dialogue:
    quality: 40
    latency: 35
    naturalness: 25
robustness_condition: snr10
```

## 分析與解讀

### 第一輪・第一晚結果解讀（2026-09-29 執行，2026-09-30 撰寫）

#### 執行概況

| 項目 | 內容 |
|---|---|
| 測試範圍 | TTS：Kokoro-82M、Piper medium<br>對話：6 組 STT + LLM + TTS（LLM：Qwen2.5-1.5B / 3B、Gemma-3-1B / 4B，皆 Q4 量化）<br>STT：Whisper tiny / base / small、distil-large-v3（只測 en）、kotoba-whisper v2（只測 ja） |
| 耗時 | 8 小時 54 分（TTS 1h02m、對話 4h37m、STT 3h13m），無執行錯誤 |
| 硬體 | i3-10110U（2 核 4 緒）、16 GB RAM、無 GPU；插電，Windows 電源模式「最佳效能」 |
| 執行環境 | 開跑前背景 CPU 占用 23%（建議 < 20%），速度數據可能略偏慢 |
| STT 資料 | FLEURS（en、es-419、pt-BR、ja）；Common Voice 27.0（es-ES：伊比利半島口音；pt-PT：葡萄牙口音）。每語言 100 句 |
| TTS 資料 | 自寫導覽文本，每語言 10 句 |
| 對話資料 | 每語言 6 題；問題音檔以 TTS 合成（非真人錄音） |

#### 閱讀前須知

1. **準確度類指標與硬體無關**：WER / CER、UTMOS、ASR 回測錯誤率、事實正確率，在這台電腦測到的就是最終值。
2. **`jetson-orin-nx-est` 的速度是理論換算值**，尚未用 Jetson 實測校準，只能用來排序，不能當承諾值。「Jetson RTF > 0.5 淘汰」的門檻判定也因此只是暫定。
3. **UTMOS 以英語資料訓練**，非英語分數只能比較模型之間的相對高低，需以母語者聽測（MOS）確認。
4. **本報告中對話測試的延遲數據不可信**（見「已知問題」），回答內容類指標（事實正確率、語言正確率）不受影響。
5. 不同語言使用不同資料集（FLEURS 與 Common Voice 的錄音條件不同），**錯誤率不要跨語言比較**，只比較同一語言內的模型。

#### STT 語音辨識

| 語言 | 資料集 | 最佳模型 | 錯誤率（95% 信賴區間） | 其他模型 |
|---|---|---|---|---|
| en | FLEURS | whisper-small | WER 6.9%（5.2–8.6%） | distil-large-v3 6.7%、base 11.3%、tiny 17.8% |
| es-ES | Common Voice | whisper-small | WER 10.0%（7.3–13.0%） | base 17.0%、tiny 30.8%（淘汰） |
| es-419 | FLEURS | whisper-small | WER 5.6%（4.6–6.7%） | base 12.2%、tiny 17.5% |
| pt-BR | FLEURS | whisper-small | WER 7.1%（5.5–8.8%） | base 15.1%、tiny 24.4% |
| pt-PT | Common Voice | 無模型通過門檻 | small 43.4%（34.7–53.2%） | base 66.7%、tiny 82.9% |
| ja | FLEURS | whisper-small（總分）<br>kotoba-whisper v2（準確度） | CER 11.3%（9.6–13.2%）<br>CER 8.4%（5.9–11.6%） | base 24.5%、tiny 38.9%（淘汰） |

- **whisper-small 是五個小模型中各語言的最佳選擇**：錯誤率約為 base 的一半；在本機 RTF 約 0.5–1.3，Jetson 換算約 0.12–0.31。
- **tiny、base 太不準**：tiny 在 es-ES（30.8%）、ja（38.9%）超過 30% 門檻被淘汰。
- **distil-large-v3（英語專用）沒有優勢**：錯誤率 6.7% 與 small 的 6.9% 差距在信賴區間內，但在本機慢約 5 倍（RTF 3.19）。
- **kotoba-whisper v2（日語專用）較準但較慢**：CER 8.4% 優於 small 的 11.3%，但在本機慢約 5 倍；Jetson 換算 RTF 0.60 超過 0.5 門檻而判定不合格，此為理論換算，需 Jetson 實測確認。
- **pt-PT 所有模型都超過 30%**，原因有二：
  1. Common Voice 葡語含大量專業術語清單（化學、醫學名詞、古代部族名），前 100 句中有 10 句為純詞表（whisper-small 在這些句子的錯誤率 79.6%），導覽情境不會出現；且平均每句僅約 6 個詞，單一錯誤影響大。排除詞表後試算，small 降至 36.7%，仍超過門檻。
  2. 一般句子也常被誤聽（例如「Havia nove alunas na sala」被辨識為「Eu via Nova Luna neste meu salão」）：葡萄牙葡語母音弱化明顯，而 Whisper 訓練資料以巴西葡語為主，小模型較吃力。
  
  需等 medium / large-v3-turbo / large-v3 的結果判斷大模型能否改善。

  > **資料變更（2026-09-30）**：本節的 pt-PT 數字來自舊資料（190 句，含 18 句詞表）。第二晚起改用排除詞表的新資料（177 句），tiny / base / small 會重測，報告將改採新結果。詳見 `CHANGELOG.md`。

#### TTS 語音合成

| 語言 | 模型 | UTMOS | ASR 回測錯誤率 | 首段延遲（本機 / Jetson 換算） | 總分（Jetson 換算） |
|---|---|---|---|---|---|
| en | Kokoro | **4.50** | **0.0%** | 5.2 s / 1.05 s | 79.6 |
| | Piper | 4.39 | 1.3% | 0.47 s / **0.19 s** | **96.9** |
| es-ES | Kokoro | **3.58** | 2.1% | 5.3 s / 1.06 s | **63.2** |
| | Piper | 2.52 | 2.1% | 0.79 s / **0.32 s** | 61.9 |
| es-419 | Kokoro | **3.48** | **1.9%** | 5.7 s / 1.14 s | 59.9 |
| | Piper | 3.08 | 5.1% | 0.60 s / **0.24 s** | **73.3** |
| pt-BR | Kokoro | **3.70** | **2.1%** | 6.1 s / 1.21 s | 62.4 |
| | Piper | 3.50 | 5.6% | 0.69 s / **0.28 s** | **79.4** |
| pt-PT | Piper（唯一） | 2.76 | 14.3% | 0.44 s / 0.18 s | 59.2 |
| ja | Kokoro（唯一） | 3.81 | 2.1% | 8.3 s / 1.67 s | 58.8 |

- **Kokoro 品質較好**：兩者都支援的語言中，Kokoro 的 UTMOS 都較高（差 0.1–1.1，es-ES 差距最大），ASR 回測錯誤率皆 ≤ 2.1%。
- **Piper 快約 10 倍**：本機 RTF 約 0.11–0.17，Kokoro 約 1.06–1.48（比即時還慢）。記憶體 Piper 約 0.8 GB、Kokoro 約 1.5 GB，皆在 2 GB 預算內。
- **報告的自動推薦是 Piper（en、es-419、pt-BR、pt-PT）與 Kokoro（es-ES、ja）**，主因是首段延遲占總分 25%，而 Kokoro 的 Jetson 換算首段延遲為 1.0–1.7 秒、Piper 為 0.2–0.3 秒。
- **最終選擇取決於兩件尚未確認的事**：
  1. **Kokoro 在 Jetson GPU 上的實測速度**：Kokoro 以 PyTorch 執行，可充分利用 GPU，理論換算可能低估其加速幅度。若實測夠快，Kokoro 的品質優勢會使它勝出。
  2. **母語者聽測**（`listening_test.csv`）：UTMOS 只評自然度，不評口音。需確認 Kokoro 西語（西班牙與拉美共用同一聲音）是否像西班牙口音，以及 Piper pt-PT（全部結果中最弱：錯誤率 14.3%、UTMOS 2.76）是否堪用。
- 語言涵蓋：Kokoro 無 pt-PT、Piper 無 ja，因此最終方案需依語言路由至不同 TTS。

#### 語音對話機器人（STT → LLM → TTS）

回答內容（每語言 6 題，結果粗略）：

| LLM | 事實正確率（各語言範圍） | 語言正確率 | 觀察 |
|---|---|---|---|
| Gemma-3-4B | 67–100% | 83–100% | 整體最準 |
| Qwen2.5-3B | 67–83% | 100% | 穩定但較慢 |
| Qwen2.5-1.5B | 50–100% | 100% | 最快，正確率不穩定 |
| Gemma-3-1B | 50–67% | 83–100% | 最不準，偶爾以錯誤語言回答 |

- **延遲數據不可採用**：受記憶體累積問題影響（見下），將於第二晚重跑。
- **即使是理論換算，所有組合的 Jetson 回合延遲都超過 3 秒**，遠高於計畫目標（< 1 秒為佳、< 1.5 秒可接受）；延遲分數因此全為 0，本輪對話總分實際上只反映回答品質與自然度。需 Jetson 實測，並考慮縮短延遲的做法（例如 LLM 與 TTS 並行、預錄常見問答）。

#### 已知問題與修正

| 問題 | 影響 | 處理 |
|---|---|---|
| 對話測試未釋放前一組合的模型，記憶體累積到約 9 GB，系統改用分頁檔 | 越晚執行的組合越慢：Kokoro 每字元合成時間依執行順序為 136 → 152 → 328 → 534 → 2,240 ms，延遲數據失真 | 已修正 `run.py`（每換組合釋放用不到的模型）；第二晚重跑對話 |
| 所有模型錯誤率都超過 30% 時，準確度皆 0 分，排名只剩速度 | 曾推薦 pt-PT 使用錯誤率 82.9% 的 tiny | 已新增門檻 `max_err_rate: 0.30`；無模型通過時顯示「無模型通過門檻」 |
| 載入時間包含 Python 套件匯入（防毒軟體逐檔掃描） | Kokoro 載入 58 秒中大部分是匯入時間 | 不在評分權重內，僅供參考 |

#### 下一步

完整的待辦清單與穩健性測試（噪音錯誤率、幻覺率）的步驟見 `docs/roadmap.md`。

1. **第二、三晚**：Whisper medium、large-v3-turbo、large-v3，以及修正後重跑對話測試。
2. **人工評分**：`listening_test.csv`（TTS，請母語者填 1–5 分）、`rating_sheet.csv`（對話的相關度、自然度、方言是否正確），填完後重新評分。
3. **下一輪候選**：pt-PT 的其他 TTS（Chatterbox、XTTS-v2，需 GPU）、Llama-3.2-3B、擴充對話題目（每語言 6 題過少）。
4. **Jetson 到手後**：以錨點模型（`configs/anchors.yaml`）校準速度換算係數，重新判定 RTF 門檻與推薦結果。

### 第一輪・第二晚結果解讀（2026-09-30 執行，2026-10-01 撰寫）

#### 執行概況

| 項目 | 內容 |
|---|---|
| 測試範圍 | 對話重跑（修正記憶體問題後，6 組）、pt-PT 小模型重測（tiny / base / small，排除詞表的新資料）、Whisper medium 與 large-v3-turbo（每語言 50 句） |
| 耗時 | 7 小時 39 分（對話 2h06m、pt-PT 重測 18m、medium + turbo 5h14m），無執行錯誤 |
| 執行環境 | 白天執行；開跑前背景 CPU 占用 29%（工作管理員開著），速度數據可能略偏慢 |

#### STT：大模型與 small 在相同 50 句上的比較

大模型每語言只測 50 句，因此以下都用**相同的前 50 句**比較，並以配對 bootstrap 計算「與 whisper-small 的錯誤率差距」的 95% 信賴區間（區間不含 0 才算顯著）。

| 語言 | small | medium | large-v3-turbo | kotoba-whisper v2 | turbo 相對 small |
|---|---|---|---|---|---|
| en | 7.5% | 5.9% | **5.9%** | — | −1.7%（顯著） |
| es-ES | 9.2% | 7.2% | **5.6%** | — | −3.6%（顯著） |
| es-419 | 5.1% | 3.6% | **2.5%** | — | −2.6%（顯著） |
| pt-BR | 7.7% | 5.5% | **5.0%** | — | −2.7%（顯著） |
| **pt-PT** | 40.3% | 22.3% | **17.2%** | — | **−23.2%（顯著）** |
| ja（CER） | 11.9% | 7.7% | **6.7%** | 9.6% | −5.2%（顯著） |

- **large-v3-turbo 在 6 種語言都顯著比 small 準**，是目前最準的 STT。
- **pt-PT 有解了**：turbo 降到 17.2%、medium 22.3%，都低於 30% 門檻（small 在新資料上 100 句為 36.3%）。不過只測 50 句，信賴區間較寬，且仍明顯高於其他語言。
- **medium 不合格**：記憶體約 2.39 GB，超過 STT 預算 2 GB；西語兩種的改善也不顯著。
- **日語**：turbo（6.7%）優於日語專用的 kotoba-whisper（9.6%）；kotoba 與 small 在相同 50 句上的差距（−2.3%）不顯著。
- **速度是 turbo 的最大疑問**：本機 RTF 2.5–11，以理論係數（÷4）換算 Jetson 為 0.62–2.78，全部超過 0.5 門檻（`FAIL:rtf`）。Whisper 一律把輸入補到 30 秒處理，Common Voice 的短句（約 5 秒）RTF 因此特別高。理論換算對 GPU 可能過於悲觀，**turbo 在 Jetson GPU 上的實際速度是最需要實測的項目**。
- 報告的 pt-PT STT 推薦（turbo）採用的是 `pc` 數據：Jetson 換算下沒有任何模型通過門檻，推薦表才退回本機數據。

#### 對話（修正後重跑）

修正驗證：Kokoro 每字元合成時間在 6 個組合中穩定在 141–186 ms（第一晚最後一組曾到 2,240 ms），對話測試總時間由 4h37m 降至 2h06m。

各組合中位數（本機 i3，秒）與 Jetson 換算回合延遲：

| 組合 | STT | LLM 首句 | TTS 首段 | 回合（本機） | 回合（Jetson 換算，各語言） | LLM tok/s（本機） |
|---|---|---|---|---|---|---|
| small + Qwen2.5-1.5B + Kokoro | 5.6 | 2.3 | 5.7 | 14.0 | 3.4–3.8 | 6.3 |
| small + Gemma-3-1B + Kokoro | 5.9 | 2.1 | 6.0 | 14.5 | 3.5–4.0 | 6.3 |
| small + Gemma-3-4B + Kokoro | 6.3 | 5.9 | 7.5 | 19.8 | 4.7–6.4 | 2.8 |
| small + Qwen2.5-3B + Kokoro | 4.8 | 3.3 | 5.4 | 14.5 | 3.6–4.1 | 4.0 |
| small + Gemma-3-4B + **Piper** | 4.9 | 5.8 | **0.3** | **11.5** | **2.9–4.3** | 3.5 |
| **turbo** + Gemma-3-4B + Kokoro | **35.1** | 5.2 | 7.6 | 47.6 | 9.9–14.9 | 2.9 |

- **所有組合都達不到 1.5 秒目標**（Jetson 換算最快約 2.9 秒）。換算後最大的兩塊是 **STT**（whisper-small 約 1.2–1.6 秒，受 30 秒補齊影響）與 **Kokoro TTS**（約 1–1.5 秒）；換成 Piper 的組合延遲最低。
- turbo 組合在本機 STT 一題就要 35 秒，換算後仍約 10–15 秒，不適合對話（除非 Jetson 實測遠快於換算）。
- **回答內容**（每語言 6 題，結果粗略）：

| LLM | 事實正確率 | 語言正確率 | 本機速度 |
|---|---|---|---|
| Gemma-3-4B | 67–100% | 100% | 最慢（約 3 tok/s） |
| Qwen2.5-3B | 67–83% | 100% | 中（4.0 tok/s） |
| Qwen2.5-1.5B | 50–100% | 100% | 快（6.3 tok/s） |
| Gemma-3-1B | 50–67% | 83–100%（會用錯語言回答） | 快（6.3 tok/s） |

  **Gemma-3-1B 建議淘汰**。Qwen2.5-1.5B 與 Qwen2.5-3B 在速度與正確率之間較平衡。

#### 已知問題

| 問題 | 影響 | 建議 |
|---|---|---|
| 對話延遲分數全為 0 | 延遲刻度為 0.8 秒（100 分）到 3 秒（0 分），Jetson 換算下所有組合都超過 3 秒，排名只剩回答品質在比；報告因此推薦延遲 10–15 秒的 turbo 組合 | 新增對話延遲門檻，或放寬刻度讓延遲能分出高下（待決定） |
| 理論換算判定大模型速度不合格 | medium、turbo 全部 `FAIL:rtf`，但理論係數對 GPU 可能過於悲觀 | Jetson 實測校準後重新判定 |

#### 對第三晚的意義

1. Whisper 系列裡 turbo 最準，但速度未知；small 夠快，但 pt-PT 不合格。
2. 第三晚的 Parakeet、Nemotron 等非自回歸模型**沒有 30 秒補齊的問題**，在短句上可能同時解決「準確度」（特別是 pt-PT）與「延遲」。
3. 對話延遲中 TTS 占比大，第三晚的 Supertonic-3（與 Piper 同為快速模型）值得重點比較。

### 第一輪・第三晚結果解讀（2026-10-01 執行，2026-10-05 撰寫）

#### 執行概況

| 項目 | 內容 |
|---|---|
| 測試範圍 | 排行榜新模型：多語 STT（Qwen3-ASR-0.6B、Nemotron-3.5-ASR-Streaming、Parakeet-TDT-0.6B-v3、SenseVoice-Small）、語言專用 STT（Parakeet-ja、Moonshine-tiny-ja、Parakeet-v2、Granite-Speech-5.0-470M、Parakeet-v3 巴西葡語微調版）、Nemotron 串流模式、Supertonic-3 TTS |
| 耗時 | 4 小時 40 分（多語 STT 3h05m、專用 STT 20m、串流 40m、TTS 33m），無執行錯誤 |
| 資料 | 與第一、二晚相同（每語言前 100 句），所有模型在**相同句子**上比較；評分已統一數字寫法 |

#### STT：各語言最佳模型（相同句子上的錯誤率；日語為 CER）

turbo、medium 只測了前 50 句，其餘為 100 句；「相對 small」為配對 bootstrap 差距，括號內為 95% 信賴區間。速度為 Jetson 理論換算（本機 ÷ 係數），僅供排序。

| 語言 | 第一名 | 第二名 | 其他重點 | whisper-small |
|---|---|---|---|---|
| en | Qwen3-ASR 4.9% | Granite-470M（英語專用）5.4% | Parakeet-v2（英語專用）6.0%；turbo 5.9%（50 句） | 6.9% |
| es-ES | **Parakeet-v3 4.1%**（−5.6%，顯著） | turbo 5.6%（50 句） | Nemotron 6.2%、Qwen3 6.4% | 9.8% |
| es-419 | turbo 2.5%（50 句） | **Parakeet-v3 3.5%**（−2.0%，顯著） | Qwen3 3.7%、Nemotron 4.5% | 5.6% |
| pt-BR | **Parakeet-v3 4.6%**＝巴西葡語 Parakeet 4.6% | turbo 5.0%（50 句） | Nemotron 6.0%、Qwen3 6.8% | 7.0% |
| **pt-PT** | **巴西葡語 Parakeet 12.8%**（−23.4%，顯著） | turbo 16.3%（50 句） | Qwen3 23.7%、Parakeet-v3 27.9%、Nemotron 30.4% | 36.2% |
| ja | turbo 6.4%（50 句） | **SenseVoice 6.8%** ≈ Parakeet-ja 6.9% | Qwen3 7.8%、kotoba 8.1%、Moonshine-tiny-ja 12.9%、Nemotron 12.8% | 11.0% |

- **Parakeet-v3 是西語、巴西葡語的最佳選擇**：比 small 顯著更準，Jetson 換算延遲約 0.3–0.8 秒（small 約 1.3–1.5 秒），記憶體約 1.3 GB。但它不接受語言參數（自動判斷語言），英語只有 8.3%，比 small 差。
- **pt-PT 終於有快速的解法**：巴西葡語微調的 Parakeet 在 pt-PT 上 12.8%，比 turbo（16.3%）還準，速度快很多（Jetson 換算約 0.35 秒）。推測是 podcast 語料微調提升了葡語整體的穩健性。缺點是只有 fp32 版本（本機約 3.1 GB），**需要自行量化成 int8**（預估約 1 GB）才符合預算。
- **日語**：SenseVoice（6.8%）和 Parakeet-ja（6.9%）都比 small（11.0%）顯著更準，而且非常快；**SenseVoice 記憶體只要約 0.3 GB**，Jetson 換算延遲約 0.45 秒。
- **Nemotron 的準確度令人失望**：西語、巴西葡語還不錯，但英語（9.7%）、日語（12.8%）比 small 差，pt-PT（30.4%）不合格。
- **Qwen3-ASR** 是唯一在 6 種語言都還不錯的小型多語模型（pt-PT 23.7% 偏高），但它是 LLM 式模型，延遲較長（Jetson 換算約 0.9–3.1 秒）。
- **Moonshine-tiny-ja**（2,700 萬參數）比 small 略差，但小非常多，可當極低資源情境的備案。

#### 專用 vs 多語（相同 100 句，配對 bootstrap）

| 語言 | 最佳專用 | 最佳多語 | 差距（95% CI） | 結論 |
|---|---|---|---|---|
| en | Granite-470M 5.4% | Qwen3-ASR 4.9% | +0.6%（−0.3%～+1.5%） | 不顯著 → 多語即可 |
| pt-BR | 巴西葡語 Parakeet 4.6% | Parakeet-v3 4.6% | +0.0%（−0.9%～+1.0%） | 不顯著 → 多語即可 |
| **pt-PT** | **巴西葡語 Parakeet 12.8%** | Qwen3-ASR 23.7% | **−11.0%（−15.2%～−6.9%）** | **專用顯著較好** |
| ja | Parakeet-ja 6.9% | SenseVoice 6.8% | +0.1%（−1.8%～+2.4%） | 不顯著 → 多語即可 |
| es-ES / es-419 | — | — | — | 沒有專用候選 |

依決策規則（顯著且差距 ≥ 2 個百分點才採用專用模型），**只有 pt-PT 應該用專用（葡語）模型**，其他語言多語模型就夠了。

#### 串流（Nemotron，區塊 560 ms，每語言 20 句）

- **串流不損失準確度**：串流與整句的錯誤率幾乎相同（只有 pt-BR 差 0.8 個百分點）。
- **這台 CPU 跟不上即時速度**：首段文字 2.6–4.5 秒才出現，說完話後還要 2.5–7.0 秒，延遲數據無法代表 Jetson。串流的實際效益要在 Jetson GPU 上量。
- 由於 Nemotron 本身的準確度在英語、日語、pt-PT 上不理想，串流目前不足以讓它勝出。

#### TTS：Supertonic-3 表現亮眼

| 語言 | Supertonic-3 | Kokoro | Piper |
|---|---|---|---|
| en | UTMOS 4.49 / 回測 1.3% | **4.50** / 0.0% | 4.39 / 1.3% |
| es-ES | **3.97** / 4.3% | 3.58 / 0.7% | 2.52 / 0.7% |
| es-419 | **3.94** / 5.1% | 3.48 / 0.6% | 3.08 / 3.9% |
| pt-BR | **4.18** / 2.8% | 3.70 / 0.0% | 3.50 / 3.5% |
| pt-PT | **4.15** / 4.8% | 不支援 | 2.76 / 12.4% |
| ja | **4.23** / 2.8% | 3.81 / 2.1% | 不支援 |
| 首段延遲（Jetson 換算） | 約 0.9–1.1 秒 | 約 1.0–1.7 秒 | **約 0.2–0.3 秒** |
| 記憶體 | **約 0.5 GB** | 約 1.5 GB | 約 0.8 GB |

- **Supertonic-3 是唯一支援全部 6 種語言的 TTS**，自然度（UTMOS）在 5 種語言第一、英語與 Kokoro 並列，記憶體最小。**有機會成為單一通用 TTS**。
- 回測錯誤率（2.8–5.1%）略高於 Kokoro，西語約 4–5%，需人工確認是否有唸錯。
- **口音未確認**：Supertonic 不區分 pt-PT / pt-BR、es-ES / es-419，需母語者確認 pt-PT 聽起來是否像葡萄牙口音。
- 首段延遲比 Piper 慢，但比 Kokoro 快。

#### 更新後的推薦（暫定）

| 語言 | STT | TTS |
|---|---|---|
| en | whisper-small 或 Parakeet-v2（英語專用，較快） | Supertonic-3（或 Piper：速度優先） |
| es-ES | **Parakeet-v3** | **Supertonic-3** |
| es-419 | **Parakeet-v3** | **Supertonic-3** |
| pt-BR | **Parakeet-v3** | **Supertonic-3** |
| pt-PT | **巴西葡語 Parakeet**（需量化成 int8） | **Supertonic-3**（口音待確認） |
| ja | **SenseVoice** 或 Parakeet-ja | **Supertonic-3** |

- **STT 最精簡的部署**：Parakeet-v3（en / es / pt-BR）＋巴西葡語 Parakeet（pt-PT）＋SenseVoice（ja）三個模型；或以 Qwen3-ASR 單一模型涵蓋全部語言（pt-PT 較弱、延遲較長）。
- **TTS**：Supertonic-3 單一模型涵蓋全部語言，前提是口音與唸錯情形通過人工聽測。

#### 注意事項

- **記憶體**：torch 模型（Qwen3-ASR、Nemotron、Granite）在 CPU 上以 fp32 執行，本機量到約 2–3 GB；Jetson GPU 上以 fp16 執行約減半。報告的記憶體門檻判定（`FAIL:memory`）因此對它們偏嚴。
- **速度**：全部是理論換算，Jetson 實測可能差很多。
- **Parakeet-v3 不接受語言參數**：在多語環境中若誤判語言（例如把葡語判成西語），錯誤率會上升；本次測試結果已包含這個影響。
- **自然度**：UTMOS 以英語資料訓練，非英語只能比較相對高低。

#### 下一步

1. **人工聽測**：特別是 Supertonic-3 的 pt-PT 口音、西語兩種方言，以及回測錯誤率較高的句子。
2. **巴西葡語 Parakeet 量化成 int8**，確認準確度不變、記憶體符合預算。
3. **用新的最佳組合重跑對話測試**（例如 Parakeet-v3 / SenseVoice + Qwen2.5-1.5B + Supertonic-3），量化端到端延遲的改善。
4. **Jetson 實測**：Parakeet、SenseVoice、Supertonic 的實際速度，以及 Nemotron 串流的真實延遲。
