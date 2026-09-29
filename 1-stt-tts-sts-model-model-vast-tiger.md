# 多語語音地端開源模型評測計畫書（STT / TTS / STS）

> 語言：葡萄牙語（pt）、西班牙語（es）、日語（ja）、英語（en）
> 情境：導覽解說與對話；目標是口語自然、流暢、低延遲
> 開發機：i3-10110U（2 核 4 緒）、16GB RAM、Intel UHD（沒有 CUDA）
> 部署機：Jetson Orin NX 16GB（Ampere 1024 CUDA core、32 Tensor Core、8 核 A78AE、16GB 共享記憶體）

---

## 0. Context（為什麼做、要得到什麼）

- **目的**：在 Jetson Orin NX 上建一條完全地端的語音鏈路：STT（語音轉文字）→ 對話/翻譯 → TTS（文字轉語音），也評估 STS（語音到語音）。
- **產出**：
  1. 一套可重複執行的測試腳本（benchmark 框架）
  2. 每個語言 × 每個任務的排行榜
  3. 把開發機的數據換算成 Jetson 的預估值，再用 Jetson 實測校正
  4. 一份指標統一的報告，最後結論是「每個語言該用哪個模型」
- **原則**：不必一個模型包辦四種語言。允許「語言路由」：先做語言辨識（LID），再把請求分派給該語言最好的模型。

---

## 1. 評測指標（業界標準）

### 1.1 STT（語音辨識）

| 類別 | 指標 | 定義 / 算法 | 工具 |
|---|---|---|---|
| 準確度 | **WER**（詞錯誤率） | (S+D+I)/N，用於 en / es / pt | `jiwer` + Whisper normalizer |
| 準確度 | **CER**（字錯誤率） | 用於 ja（日語沒有空格，不適合用 WER） | `jiwer`，先做 NFKC 正規化並去標點 |
| 準確度 | 專有名詞召回率 | 導覽景點名、人名、術語被辨識正確的比例 | 自寫（依關鍵字清單比對） |
| 穩健性 | 噪音下 WER/CER | 疊加 SNR 20/10/5 dB 的環境噪音後重測 | `audiomentations` + MUSAN 噪音庫 |
| 穩健性 | 幻覺率 | 輸入純靜音/噪音時「產生文字」的比例（Whisper 常見問題） | 自寫 |
| 語言 | LID 準確率 | 自動語言辨識是否判對 | 自寫 |
| 速度 | **RTF**（即時率） | 處理時間 ÷ 音訊長度；小於 1 才跟得上即時 | `time.perf_counter` |
| 速度 | 最終延遲 | 使用者說完話 → 拿到最終文字 | 串流模擬器 |
| 速度 | 首個部分結果延遲 | 串流模式下開始說話 → 第一個 partial 結果 | 串流模擬器 |
| 資源 | 峰值 RAM/VRAM、CPU/GPU 使用率、功耗 | 背景執行緒每 50ms 取樣 | `psutil`；Jetson 用 `jtop`/`tegrastats` |
| 資源 | 模型大小、載入時間 | — | — |

### 1.2 TTS（語音合成）

| 類別 | 指標 | 定義 / 算法 | 工具 |
|---|---|---|---|
| 自然度（主觀） | **MOS**（1–5 分，ITU-T P.800） | 母語者聽測，報告平均值與 95% 信賴區間 | 自建聽測網頁 |
| 自然度（主觀） | **CMOS / A-B 偏好** | 兩兩比較，比 MOS 更敏感 | 同上 |
| 自然度（客觀） | **UTMOS**（預測 MOS） | 用模型預測 MOS，適合大量初篩 | `UTMOSv2` |
| 音質 | DNSMOS / NISQA | 雜訊、失真評分 | Microsoft DNSMOS |
| 可懂度 | **ASR 回測 WER/CER** | 合成語音交給強力 ASR（whisper-large-v3）轉文字，再和原文比對 | 共用 STT 評分模組 |
| 語言正確性 | 讀音錯誤率 | 日語漢字讀音、數字/日期/金額唸法、句中英文專名 | 人工抽查清單 |
| 聲音複製 | SECS（說話人相似度） | 有做聲音複製時才測，比較 embedding 的 cosine 相似度 | ECAPA / WavLM-SV |
| 速度 | RTF | 合成時間 ÷ 輸出音訊長度 | — |
| 速度 | **TTFA**（首段音訊延遲） | 送出文字 → 第一個音訊 chunk 可以播放；對話體感最關鍵 | 串流模式 |
| 資源 | 同 STT | — | — |

### 1.3 STS（語音到語音）

依第 8 節要確認的定義而定，預設是「語音翻譯 / 口譯導覽」：

| 指標 | 說明 | 工具 |
|---|---|---|
| **ASR-BLEU / chrF++** | 輸出語音先轉成文字，再和參考譯文比對（ja 用 `ja-mecab` tokenizer） | `sacrebleu` |
| **COMET** | 語意層級的翻譯品質，比 BLEU 更接近人工判斷 | `unbabel-comet` |
| 端到端延遲 | 說話者停止說話 → 第一個輸出音訊開始播放 | 串流模擬器 |
| 輸出自然度 | UTMOS / MOS | 同 TTS |
| 說話人相似度 | 做聲音轉換（VC）時才測，看 SECS | 同 TTS |

### 1.4 整條鏈路（對話與導覽效率）

- **回合延遲（Turn latency）** = VAD 判斷說完 + STT 最終結果 + LLM 首 token + TTS 首段音訊。目標：< 1.0 秒為佳，< 1.5 秒可以接受。
- **斷句誤切率**：VAD 把一句話在中途切斷的比例。
- **插話（barge-in）反應時間**：使用者插話 → TTS 停止播放。

---

## 2. 語言怎麼分

- 測試矩陣是「**任務 × 語言 × 模型 × 設定**」，每一格單獨出分數。
- 每個語言、每個任務各自產生排行榜，最後可以得出例如「ja 的 STT 用 A、es/pt 用 B」的組合。
- 還要另外測兩種能力：
  - **自動 LID**：模型能不能自己判斷語言，以及判錯時的代價
  - **語碼混用**：例如日語句子裡夾英文景點名
- 需要確認的方言變體：pt-BR 或 pt-PT、es-ES 或拉美西語（會影響 TTS 聲音選擇）。

### 測試資料集

| 資料 | 語言 | 用途 | 備註 |
|---|---|---|---|
| **FLEURS**（Google） | en/es/pt/ja 全有 | STT、STS | 四語是**平行句**，可以直接當翻譯參考答案，最推薦 |
| Common Voice | en/es/pt/ja 全有 | STT | 口音多元，錄音品質參差 |
| Multilingual LibriSpeech | en/es/pt | STT | 朗讀語料 |
| ReazonSpeech test / JSUT | ja | STT、TTS 參考 | — |
| MUSAN / DEMAND | — | 噪音疊加 | 模擬戶外、人潮環境 |
| **自建導覽語料**（最重要） | 四語 | 全部 | 每語 50–100 句導覽腳本，含專有名詞、數字、年份，由母語者錄音 |

樣本量：初篩每語每條件 100 句；正式評測 ≥ 300 句（約 1 小時），用 bootstrap 算 95% 信賴區間。MOS 每語 20 句 × ≥ 5 位母語聽者。

---

## 3. 去哪裡找模型

**搜尋管道**
- Hugging Face：Tasks 篩選 `automatic-speech-recognition` / `text-to-speech`，再用語言篩選
- **Open ASR Leaderboard**（hf-audio，有英文及多語榜）
- **TTS Arena**（HF Space，盲測排名）
- **Jetson AI Lab**（jetson-ai-lab.com）與 `dusty-nv/jetson-containers`：已在 Jetson 上驗證過的語音模型與容器
- `k2-fsa/sherpa-onnx` 預訓練模型列表：輕量、支援串流、有 ARM 版本
- `rhasspy/piper-voices`、ESPnet model zoo、NVIDIA NGC（NeMo 模型）

**初篩條件（硬性門檻）**
1. 授權允許你的用途（若是商用，要排除 CC-BY-NC / CPML 這類禁止商用的授權）
2. 有 aarch64 + CUDA 的推論路徑（CTranslate2、ONNX Runtime GPU、TensorRT、whisper.cpp、llama.cpp 等）
3. 權重大小符合 Jetson 記憶體預算（見第 5 節）

### 初步候選清單

✓ 表示支援，✗ 表示不支援，? 表示需要查證。版本更新很快，Phase 0 會再上網逐一確認。

**STT**

| 模型 | en | es | pt | ja | 授權 | 備註 |
|---|---|---|---|---|---|---|
| Whisper large-v3 / large-v3-turbo / medium / small | ✓ | ✓ | ✓ | ✓ | MIT | 多語基準線；後端可用 faster-whisper、whisper.cpp、TensorRT |
| kotoba-whisper v2 | ✗ | ✗ | ✗ | ✓ | Apache-2.0 | 日語專用蒸餾版，速度快 |
| ReazonSpeech（k2/NeMo） | ✗ | ✗ | ✗ | ✓ | Apache-2.0 | 日語專用 |
| NVIDIA Parakeet-TDT-0.6B-v3 | ✓ | ✓ | ✓ | ✗ | CC-BY-4.0 | 歐語快速且準確 |
| NVIDIA Canary-1B-v2 | ✓ | ✓ | ✓ | ✗ | CC-BY-4.0 | 內建語音翻譯 |
| Distil-Whisper large-v3 | ✓ | ✗ | ✗ | ✗ | MIT | 英語專用 |
| SenseVoice-Small | ✓ | ✗ | ✗ | ✓ | 模型自有授權（?） | 非自回歸，極快 |
| Vosk / sherpa-onnx zipformer | ✓ | ✓ | ✓ | ? | Apache-2.0 | 超輕量串流，當速度下限參考 |

**TTS**

| 模型 | en | es | pt | ja | 授權 | 備註 |
|---|---|---|---|---|---|---|
| Kokoro-82M | ✓ | ✓ | ✓(BR) | ✓ | Apache-2.0 | 小、快、自然，首推 |
| Piper | ✓ | ✓ | ✓(BR/PT) | ✗ | 引擎 GPL/MIT，聲音各自授權 | CPU 也很快 |
| MeloTTS | ✓ | ✓ | ✗ | ✓ | MIT | — |
| Chatterbox Multilingual | ✓ | ✓ | ✓ | ✓ | MIT | 可聲音複製，需要 GPU |
| CosyVoice 2/3 | ✓ | ? | ? | ✓ | Apache-2.0 | 串流、自然度高 |
| Style-BERT-VITS2 | ✗ | ✗ | ✗ | ✓ | AGPL（程式碼） | 日語自然度高 |
| XTTS-v2 / Fish-Speech / F5-TTS | ✓ | ✓ | ✓/? | ✓/? | **禁止商用** | 只當品質參考上限 |

**STS / 翻譯**
- 串接式（推薦做為主線）：STT → MT/LLM → TTS。
  - MT 候選：Opus-MT（CC-BY）、M2M100-418M（MIT）、MADLAD-400（Apache）、小型 LLM（Qwen3 / Gemma 3，4B 以下量化版，用 llama.cpp 跑）
- 端到端（參考比較）：SeamlessM4T v2 / SeamlessStreaming（CC-BY-NC，不能商用，但可當品質標竿）、Qwen2.5-Omni
- 聲音轉換（若 STS 指的是這個）：OpenVoice v2（MIT）、RVC

---

## 4. 測試腳本設計

### 4.1 專案結構

```
speech-bench/
├─ configs/
│   ├─ models.yaml          # 模型清單、後端、量化、參數
│   ├─ suites/              # 測試套件：stt_quick.yaml、stt_full.yaml、tts_full.yaml ...
│   └─ hardware.yaml        # 硬體 profile（PC / Jetson）
├─ data/manifests/          # 每語每資料集一個 JSONL：{id, audio, text, lang, duration}
├─ engines/                 # Adapter 模式：每個模型一個轉接器
│   ├─ stt/base.py          # load(), transcribe(audio, lang) -> text, stream(chunks)
│   ├─ stt/faster_whisper.py, whisper_cpp.py, nemo.py, sherpa_onnx.py ...
│   ├─ tts/base.py          # load(), synthesize(text, lang, voice) -> wav, stream(text)
│   ├─ tts/kokoro.py, piper.py, melo.py ...
│   └─ sts/cascade.py       # 組合 stt + mt + tts
├─ bench/
│   ├─ timer.py             # 精確計時、warm-up、重複次數
│   ├─ monitor.py           # 資源取樣執行緒（psutil / jtop）
│   ├─ streaming_sim.py     # 依真實時間節奏逐 chunk 餵音訊，模擬麥克風
│   └─ augment.py           # 疊加噪音（依 SNR）
├─ metrics/                 # wer_cer.py、normalize.py、utmos.py、secs.py、bleu_comet.py
├─ run.py                   # python run.py --suite stt_full --hw pc
├─ score.py                 # 讀 raw 結果並計算指標（推論和評分分開）
├─ report.py                # 彙整成 CSV、圖表、HTML 報告
└─ docker/                  # 每類引擎各一個環境（避免 NeMo、PyTorch 版本互相衝突）
```

### 4.2 執行流程（每個 模型×設定×語言×資料集）

1. **記錄環境**：CPU/GPU 型號、頻率、執行緒數、套件版本、Jetson 功耗模式（`nvpmodel`）
2. **載入模型**：量測載入時間與載入後記憶體
3. **Warm-up**：先跑 3 次，不計入結果
4. **逐句推論**：同時啟動資源監控；每句記錄處理時間、音訊長度、輸出文字/音訊
5. **速度重複測**：取 20 句重複 5 次，報告中位數、p90、p95
6. **原始結果寫入 JSONL**：一句一行，之後可以換正規化方式重新評分，不必重跑推論
7. **評分**：`score.py` 計算 WER/CER、UTMOS、BLEU 等
8. **彙整**：`report.py` 輸出排行榜

**計時規則**：固定執行緒數、接電源、關閉其他程式、記錄 CPU 頻率；串流模式另外測 chunk = 160 / 320 / 640 ms 三種。

### 4.3 測試選項（config 可切換的維度）

| 維度 | 選項 |
|---|---|
| 模型大小 | tiny / small / medium / large ... |
| 量化 | fp32 / fp16 / int8（/ int4 給 LLM） |
| 後端 | PyTorch / ONNX Runtime / CTranslate2 / whisper.cpp / TensorRT |
| 解碼參數 | beam size 1 / 5、溫度、VAD 開或關 |
| 模式 | 離線整句 / 串流（chunk 大小） |
| 語言 | 指定語言 / 自動 LID |
| 條件 | 乾淨 / SNR 20 / 10 / 5 dB / 遠場 |
| 硬體 | pc-cpu / jetson-cpu / jetson-gpu |

測試分三個套件，以免組合爆量：
- **quick**：每語 100 句、只測乾淨條件，用來初篩
- **full**：只跑短名單，全部條件
- **stress**：長時間連續執行，觀察溫度、降頻與記憶體洩漏

### 4.4 統一的結果格式（每筆 summary 一列）

```
run_id, task, model, variant, backend, quant, lang, dataset, condition, hw_profile,
n_samples, wer, cer, wer_ci95, utmos, mos, asr_wer, bleu, comet, secs,
rtf_p50, rtf_p90, latency_ms_p50, latency_ms_p90, ttfa_ms_p50,
peak_ram_mb, peak_vram_mb, avg_power_w, model_size_mb, load_time_s,
license, is_estimated(估算/實測)
```

---

## 5. 硬體換算方法

| 項目 | i3-10110U（開發機） | Jetson Orin NX 16GB |
|---|---|---|
| CPU | 2 核 4 緒、AVX2、最高 4.1GHz | 8 核 A78AE、NEON |
| 記憶體頻寬 | DDR4-2666，雙通道約 42.7 GB/s（單通道減半，需確認） | LPDDR5 102.4 GB/s |
| GPU | UHD 620（不支援 CUDA） | Ampere 1024 core、32 Tensor Core |
| 記憶體 | 16GB（CPU 專用） | 16GB，**CPU 與 GPU 共享**，系統約占 2–3GB |
| AI 算力 | CPU FP32 峰值約 0.25 TFLOPS | 157 TOPS（稀疏 INT8、Super 模式） |

**換算分三層：**

1. **準確度指標和硬體無關**：WER、CER、MOS、BLEU 在開發機上測的就是最終值，前提是用與部署時相同的量化。int8 可能讓 WER 略為變動，所以要一併測 int8 版本。大模型在 i3 上跑很慢，但準確度只需要跑一次，也可以用 Colab 免費 GPU 加速。
2. **速度用理論係數初估**：
   - 自回歸解碼（Whisper decoder、LLM、自回歸 TTS）受記憶體頻寬限制，速度 ≈ 頻寬 ÷ 模型權重大小。CPU→CPU 的理論比例約 2.4 倍。
   - 編碼器、非自回歸 TTS 受算力限制，用 FLOPs 比例估算。
   - 開發機跑的是 x86 CPU，部署機跑的是 CUDA GPU，路徑不同，理論值只能當粗估。
3. **用錨點模型校準**：選 3 個錨點模型（例如 whisper-small int8、Piper medium、Kokoro ONNX），在兩台機器上都實測，得到經驗比例 k = RTF_pc ÷ RTF_jetson。k 分「後端類別」各算一個，再套用到同類的其他模型。
   - 在拿到 Jetson 之前，先用 Jetson AI Lab 或社群公開的數據暫代。
   - 只能用 GPU 跑的模型（例如 Chatterbox）無法在 i3 上測速，改用 Colab T4 當代理，T4 → Orin NX 約慢 2.5–4 倍，也要校準。
4. **最終**：短名單一定要在 Jetson 上實測。報告同時列出「估算值」與「實測值」，並標示誤差。

**Jetson 記憶體預算（初步提案，可以討論）**：STT ≤ 2GB、TTS ≤ 2GB、LLM/MT ≤ 7GB、VAD 等其他元件 ≤ 1GB，其餘留給系統。

---

## 6. 統一評分與報告

**步驟一：硬性門檻（Gate）**。沒通過就直接淘汰：
- 授權不符
- Jetson 上 RTF > 0.5
- 超出記憶體預算
- 不支援該語言

**步驟二：把各指標換成 0–100 分**。用固定門檻線性換算，讓不同批次的測試可以互相比較：

| 指標 | 100 分 | 0 分 |
|---|---|---|
| WER / CER | ≤ 5% | ≥ 30% |
| Jetson RTF | ≤ 0.1 | ≥ 1.0 |
| TTFA / 最終延遲 | ≤ 200 ms | ≥ 1500 ms |
| MOS / UTMOS | 4.5 | 2.5 |
| 峰值記憶體 | ≤ 0.5 GB | ≥ 4 GB |

**步驟三：依情境加權**（權重可以討論）：
- STT：準確度 40、延遲 30、穩健性（噪音、專名）15、資源 15
- TTS：自然度 35、可懂度 25、TTFA 25、資源 15
- STS：翻譯品質 40、端到端延遲 35、自然度 25

**報告內容**：
- 每語言排行榜
- **Pareto 圖**（準確度 vs. 延遲），能直接看出取捨
- 雷達圖
- 噪音衰減曲線
- 推薦組合表（每語言 STT + TTS 選誰）
- 附錄：原始數據 CSV 與測試環境紀錄

---

## 7. 執行階段

| 階段 | 內容 | 在哪裡跑 |
|---|---|---|
| P0 | 確認需求、候選清單上網查證（授權、語言、Jetson 相容性） | — |
| P1 | 準備資料：下載 FLEURS / CV 子集、錄製自建導覽語料、做噪音版本 | PC |
| P2 | 建框架，並用 whisper-small + Kokoro 做冒煙測試 | PC |
| P3 | quick 套件：全部候選的準確度初篩 → 短名單 | PC（大模型用 Colab） |
| P4 | 速度測試、錨點校準、換算 Jetson 預估 | PC + Colab |
| P5 | Jetson 實測短名單（TensorRT / CUDA 優化版本）、整條鏈路延遲 | Jetson |
| P6 | 母語者主觀聽測（MOS / CMOS） | 聽測網頁 |
| P7 | 產出報告與推薦組合 | — |

---

## 8a. 已確認決策（2026-09-23）

- STS = **語音對話機器人**（STT → LLM → TTS），核心指標為回合延遲、回答品質、自然度
- 用途：**研究／內部 PoC**，禁止商用授權的模型可列入正式候選（報告仍標註授權）
- 方言：pt-BR、pt-PT、es-ES、es-419 **都測**（語言代碼：en, es-ES, es-419, pt-BR, pt-PT, ja）
- Jetson 尚未到手：P1–P4 在 PC 進行，Jetson 數值先用換算估算
- 專案位置：`C:\Users\50019\speech-bench`

## 8. 需要你確認的問題（原始清單）

1. **STS 指的是哪一種？**（a）語音翻譯（例如遊客說日語，系統用西語回答）；（b）語音對話機器人（語音輸入 → LLM → 語音輸出）；（c）聲音轉換。這會決定 STS 的指標和候選模型。
2. **授權**：是否為商用產品？若是，要排除所有禁止商用的授權（XTTS、Fish-Speech、SeamlessM4T、NLLB 等）。
3. **Jetson 何時能拿到？** 這決定換算要依賴估算多久。
4. **方言變體**：葡語是巴西還是葡萄牙？西語是西班牙還是拉美？
5. **需要聲音複製嗎**（例如用固定導覽員的聲音）？還是現成聲音就可以？
6. **使用環境**：戶外、室內、麥克風距離？這會決定噪音測試的權重。
7. 開發機寫「8g CPU」是指什麼？（記憶體寫的是 16GB，想確認實際規格與是否為雙通道）

---

## 9. 驗證方式（如何確認這套測試是可信的）

- **框架正確性**：用 whisper-small 在 LibriSpeech test-clean 上跑，WER 應接近公開數值（約 3–4%）。差距過大表示正規化或流程有錯。
- **可重現性**：同一設定跑兩次，準確度要完全一致，速度的差異要 < 5%。
- **換算可信度**：Jetson 實測值與估算值的誤差要列在報告中；誤差 > 30% 的後端類別要重新校準 k。
- **主觀與客觀一致性**：檢查 UTMOS 和人工 MOS 的相關性。若相關性低，該語言就不能只靠 UTMOS 初篩。
