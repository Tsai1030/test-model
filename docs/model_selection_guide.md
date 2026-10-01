# 如何挑選適合裝置的語音模型

目標裝置：Jetson Orin NX 16GB（CPU 與 GPU 共用 16 GB 記憶體、頻寬 102.4 GB/s）。本文說明怎麼從參數量估算一個模型放不放得下、跑不跑得動，以及怎麼在 Hugging Face 上找候選。所有估算都只是初篩，**最後一定要實測**。

---

## 1. 三步驟快速判斷

1. **放得下嗎？** 參數量 × 每個參數的位元組數 × 額外開銷，是否在該元件的記憶體預算內（見第 2 節）。
2. **跑得夠快嗎？** 先看模型架構（見第 3 節）：非自回歸的通常很快，LLM 式的通常較慢。再用頻寬粗估。
3. **能用嗎？** 語言（含方言）、授權、有沒有 Jetson 能跑的格式（見第 5 節清單）。

---

## 2. 記憶體：參數量 → 需要多少記憶體

### 每個參數占多少位元組
| 精度 | 每參數 | 1 億參數（100M） | 6 億（0.6B） | 10 億（1B） | 40 億（4B） |
|---|---|---|---|---|---|
| fp32 | 4 bytes | 0.4 GB | 2.4 GB | 4 GB | 16 GB |
| fp16 / bf16（GPU 常用） | 2 bytes | 0.2 GB | 1.2 GB | 2 GB | 8 GB |
| int8 | 1 byte | 0.1 GB | 0.6 GB | 1 GB | 4 GB |
| 4-bit（如 GGUF Q4_K_M） | 約 0.6 byte | 0.06 GB | 0.36 GB | 0.6 GB | 2.4 GB |

### 還要加上額外開銷
實際占用 = 權重 + 執行框架 + 運算暫存（activations）+ LLM 的 KV cache。**小模型的額外開銷可能比權重本身還大**，本專案的實測例子：

| 模型 | 參數 | 權重（int8） | 實測記憶體 | 說明 |
|---|---|---|---|---|
| whisper-small | 0.24B | 約 0.24 GB | 約 0.7 GB | 執行框架與暫存 |
| whisper-medium | 0.77B | 約 0.77 GB | 約 1.7 GB | |
| Kokoro | 0.08B | 約 0.3 GB（fp32） | 約 1.5 GB | 大部分是 PyTorch、spaCy、日語字典 |

**經驗法則**：先用「權重 × 1.5」粗估，候選進入名單後再實測。

### Orin NX 16GB 的預算
系統約占 2–3 GB，剩約 13 GB，本專案的分配是 STT ≤ 2 GB、TTS ≤ 2 GB、LLM ≤ 7 GB、其他（VAD 等）≤ 1 GB（`configs/scoring.yaml`）。換算成參數量：

| 元件 | 預算 | fp16 大約可放 | int8 大約可放 |
|---|---|---|---|
| STT | 2 GB | ≤ 0.6–0.8B | ≤ 1.2–1.5B |
| TTS | 2 GB | ≤ 0.6–0.8B | ≤ 1.2–1.5B |
| LLM | 7 GB | — | 4-bit：記憶體可放到約 8B，但速度考量建議 ≤ 4B |

---

## 3. 速度：架構比參數量更重要

### 看架構就能大致判斷快慢
| 架構 | 例子 | 速度 | 說明 |
|---|---|---|---|
| **CTC / TDT / RNNT（非自回歸或輕量解碼）** | Parakeet、Nemotron、Granite TurboCTC、SenseVoice | **非常快** | 一次處理整段，GPU 上 RTF 常 < 0.01 |
| **編碼器－解碼器（自回歸）** | Whisper | 中等 | 解碼器越小越快（large-v3-turbo 只有 4 層解碼器）。注意：Whisper 一律補到 30 秒處理，短句也不會比較快 |
| **LLM 式 ASR** | Qwen3-ASR、Granite 2B、Voxtral | 較慢 | 準確度通常較高，但一個字一個字生成 |
| **小型 TTS（VITS / flow）** | Piper、Supertonic、Kokoro | 快 | CPU 也能即時 |
| **LLM 式 TTS（codec 語言模型）** | Qwen3-TTS、CosyVoice、Chatterbox | 較慢 | 音質、自然度通常較好，需要 GPU；要特別看「首段延遲」 |

### 自回歸模型：用頻寬粗估速度
自回歸模型每產生一個 token 都要把整個模型讀一次，所以受記憶體頻寬限制：

> 每秒 token 數 ≈ 頻寬 ÷ 模型大小 × 效率（約 0.5–0.7）

以 Orin NX（102.4 GB/s）為例，LLM（4-bit）：

| 模型 | 大小 | 估計 tokens/秒 |
|---|---|---|
| 1.5B | 約 1.0 GB | 約 50–70 |
| 4B | 約 2.5 GB | 約 20–28 |
| 8B | 約 4.9 GB | 約 10–14 |

### 串流 vs 整句處理
| 類型 | STT | TTS | 對延遲的影響 |
|---|---|---|---|
| 原生串流 | 邊聽邊辨識，說完話幾乎馬上有結果（如 Nemotron streaming） | 邊產生邊輸出（如 Qwen3-TTS、CosyVoice） | 最低，但選擇較少 |
| 有條件串流 | 分段模擬（延遲較高），或只在特定後端（如 vLLM）支援 | — | 視設定而定 |
| 整句 / 逐句 | 說完整句才開始辨識（Whisper 等） | 一次合成一句（Kokoro、Piper、Supertonic） | 取決於模型速度：短句 + 快速模型，體感差異小 |

判斷方式：模型卡搜尋 streaming、chunk、cache-aware、first-packet latency 等字眼；要注意「只在某個後端才支援串流」的但書。評測時串流模型另外量「首個部分結果延遲」與「說完話到最終結果」。

### 本專案的速度目標
| 元件 | 目標 |
|---|---|
| STT | RTF ≤ 0.5（門檻）；對話情境最好 ≤ 0.1 |
| TTS | 首段延遲（TTFA）≤ 200–300 ms |
| LLM | 第一句 ≤ 約 0.5 秒 |
| 整個對話回合 | ≤ 1.5 秒（計畫目標，< 1 秒為佳） |

---

## 4. 未來裝置對照（約略值，以 NVIDIA 官方規格為準）

| 裝置 | 記憶體 | 頻寬 | STT / TTS（各） | LLM（4-bit） |
|---|---|---|---|---|
| Jetson Orin Nano Super | 8 GB | 約 102 GB/s | ≤ 約 0.3B（fp16）/ 0.6B（int8） | ≤ 約 1.5B |
| **Jetson Orin NX 16GB（目前）** | 16 GB | 102.4 GB/s | ≤ 約 0.6–0.8B（fp16） | ≤ 約 4B |
| Jetson AGX Orin 32GB | 32 GB | 204.8 GB/s | ≤ 約 1.5B | ≤ 約 8B，速度約為 Orin NX 的 2 倍 |
| Jetson AGX Orin 64GB | 64 GB | 204.8 GB/s | 2B 級 LLM 式 ASR / TTS 可行 | 約 8–14B |
| Jetson Thor | 128 GB | 約 273 GB/s | 大型 LLM 式語音模型可行 | 約 14–30B |

換裝置時：記憶體決定「放得下多大」，頻寬決定「自回歸模型跑多快」，GPU 算力決定「非自回歸模型跑多快」。

---

## 5. 在 Hugging Face 上怎麼找

### 列表篩選
- 依任務：`https://huggingface.co/models?pipeline_tag=automatic-speech-recognition&sort=trending`（TTS 用 `text-to-speech`；`text-to-audio` 多半是音樂、音效生成，通常用不到）
- 加語言：`&language=pt`（`es`、`ja`、`en`）
- 加參數量範圍：`&num_parameters=min:0,max:1B`（若網址參數無效，用頁面左側的 Parameters 篩選器）
- 加執行格式：`&library=onnx`、`ctranslate2`、`gguf`（Jetson 容易部署的格式）
- 排序：`trending`（近期熱門）、`downloads`（成熟度）、`likes`
- 用 API 一次取得參數量、授權、語言、日期（本專案調查時的做法）：
  `https://huggingface.co/api/models?pipeline_tag=automatic-speech-recognition&sort=trendingScore&limit=60&expand[]=safetensors&expand[]=tags&expand[]=createdAt`

### 排行榜
- Open ASR Leaderboard（英語、多語、長音檔三個賽道）：比準確度與速度
- TTS Arena：盲聽投票排名，比自然度

### 模型卡檢查清單
- [ ] **參數量**：模型頁的 Safetensors 資訊會顯示「Model size」
- [ ] **語言與方言**：是否明列需要的語言；葡語要看 pt-BR / pt-PT，西語要看 es-ES / 拉美
- [ ] **授權**：Apache-2.0、MIT、CC-BY 可商用；CC-BY-NC、CPML 禁止商用；「other」要點進去看
- [ ] **公布的指標**：FLEURS、Common Voice 等公開資料集上各語言的 WER / CER（TTS 看 CER / WER 回測、MOS）
- [ ] **執行格式**：ONNX、CTranslate2、GGUF、TensorRT、NeMo 在 Jetson 上都有路徑
- [ ] **串流支援**：對話情境很重要（例如 Nemotron 的串流 ASR）
- [ ] **TTS 聲音**：有預設聲音，還是必須提供參考錄音（聲音複製）
- [ ] **訓練資料**：是否可能和測試資料重疊（例如用 Common Voice 微調的模型，不適合用 Common Voice 測）

### 警訊
- 沒有任何評測數字，或只有自家資料集的數字
- 只有 Apple 專用格式（MLX、CoreML）
- 需要只支援 x86 的 CUDA 套件（例如部分模型強制使用 flash-attn）
- 只支援英語，但需要多語
- 模型卡寫「GPU only」：本機只能等 Colab 或 Jetson 階段再測

---

## 6. 找到候選後怎麼加進評測

1. 在 `engines/stt|tts|llm/` 寫轉接器（繼承 `engines/base.py`）
2. 在 `configs/models.yaml` 註冊（engine、params、langs / voices、backend_category、license）
3. 加入 plan（`configs/plans/*.yaml`），先跑 `run_all.py --smoke-only` 確認能執行
4. 正式測試後看 `reports/report.md` 與各 run 的 `listen.html`
5. 在 `CHANGELOG.md` 記錄新增了什麼
